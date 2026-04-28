'use client';

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Activity, Cpu, GitBranch, RefreshCw, AlertCircle, Clock, DollarSign } from "lucide-react";

type ActivityRow = Record<string, any>;
type AgentRow = Record<string, any>;
type CorrelationRow = Record<string, any>;

const ACTION_BADGES: Record<string, string> = {
  create: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  update: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  delete: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  validate: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  reject: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
  status_change: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
};

const STATUS_BADGES: Record<string, string> = {
  completed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  pending: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  processing: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
};

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("fr-FR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function truncate(str: string | null | undefined, max = 80): string {
  if (!str) return "-";
  return str.length > max ? str.substring(0, max) + "…" : str;
}

function JsonDialog({ title, data, children }: { title: string; data: any; children: React.ReactNode }) {
  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto max-h-[60vh] whitespace-pre-wrap break-all">
          {JSON.stringify(data, null, 2)}
        </pre>
      </DialogContent>
    </Dialog>
  );
}

export default function AuditAdminPage() {
  const [activeTab, setActiveTab] = useState("activity");

  // Activity state
  const [activities, setActivities] = useState<ActivityRow[]>([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [activityPage, setActivityPage] = useState(1);
  const [activityFilterAction, setActivityFilterAction] = useState("");
  const [activityFilterTable, setActivityFilterTable] = useState("");

  // Agents state
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [agentTotal, setAgentTotal] = useState(0);
  const [agentPage, setAgentPage] = useState(1);
  const [agentFilterType, setAgentFilterType] = useState("");
  const [agentFilterStatus, setAgentFilterStatus] = useState("");

  // Correlations state
  const [correlations, setCorrelations] = useState<CorrelationRow[]>([]);
  const [correlationTotal, setCorrelationTotal] = useState(0);
  const [correlationPage, setCorrelationPage] = useState(1);

  // Stats
  const [stats, setStats] = useState({ total_activites: 0, total_agents: 0, agents_echoues: 0, cout_estime_total: 0 });
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes] = await Promise.all([
        fetch("/api/v1/admin/audit/stats"),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (err) {
      console.error("Erreur chargement stats audit:", err);
    }
    setLoading(false);
  }, []);

  const fetchActivities = useCallback(async (page: number, action?: string, table?: string) => {
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (action) params.set("action", action);
    if (table) params.set("table_name", table);
    try {
      const res = await fetch(`/api/v1/admin/audit/activity?${params}`);
      if (res.ok) {
        const data = await res.json();
        setActivities(data.items);
        setActivityTotal(data.total);
        setActivityPage(data.page);
      }
    } catch (err) {
      console.error("Erreur chargement activités:", err);
    }
  }, []);

  const fetchAgents = useCallback(async (page: number, agentType?: string, status?: string) => {
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (agentType) params.set("agent_type", agentType);
    if (status) params.set("status", status);
    try {
      const res = await fetch(`/api/v1/admin/audit/agents?${params}`);
      if (res.ok) {
        const data = await res.json();
        setAgents(data.items);
        setAgentTotal(data.total);
        setAgentPage(data.page);
      }
    } catch (err) {
      console.error("Erreur chargement agents:", err);
    }
  }, []);

  const fetchCorrelations = useCallback(async (page: number) => {
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    try {
      const res = await fetch(`/api/v1/admin/audit/correlations?${params}`);
      if (res.ok) {
        const data = await res.json();
        setCorrelations(data.items);
        setCorrelationTotal(data.total);
        setCorrelationPage(data.page);
      }
    } catch (err) {
      console.error("Erreur chargement corrélations:", err);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { fetchActivities(1); }, [fetchActivities]);
  useEffect(() => { fetchAgents(1); }, [fetchAgents]);
  useEffect(() => { fetchCorrelations(1); }, [fetchCorrelations]);

  const totalPages = (total: number, pageSize = 25) => Math.max(1, Math.ceil(total / pageSize));

  const statsCards = [
    { label: "Activités", value: stats.total_activites, icon: Activity, color: "text-blue-600" },
    { label: "Agents IA", value: stats.total_agents, icon: Cpu, color: "text-purple-600" },
    { label: "Échecs", value: stats.agents_echoues, icon: AlertCircle, color: "text-red-600" },
    { label: "Coût estimé", value: `${stats.cout_estime_total.toFixed(4)} €`, icon: DollarSign, color: "text-green-600" },
  ];

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Audit & Monitoring</h1>
          <p className="text-muted-foreground mt-1">
            Consultation des activités, appels IA et corrélations
          </p>
        </div>
        <Button variant="outline" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Rafraîchir
        </Button>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        {statsCards.map((card) => (
          <Card key={card.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">{card.label}</CardTitle>
              <card.icon className={`h-4 w-4 ${card.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{card.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="activity" className="flex items-center gap-2">
            <Activity className="h-4 w-4" /> Activité
          </TabsTrigger>
          <TabsTrigger value="agents" className="flex items-center gap-2">
            <Cpu className="h-4 w-4" /> Agents IA
          </TabsTrigger>
          <TabsTrigger value="correlations" className="flex items-center gap-2">
            <GitBranch className="h-4 w-4" /> Corrélations
          </TabsTrigger>
        </TabsList>

        {/* ====== TAB ACTIVITÉ ====== */}
        <TabsContent value="activity">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-wrap gap-2 items-center">
                <Select value={activityFilterAction} onValueChange={(v) => { setActivityFilterAction(v); fetchActivities(1, v, activityFilterTable); }}>
                  <SelectTrigger className="w-36"><SelectValue placeholder="Action" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value=" ">Toutes</SelectItem>
                    <SelectItem value="create">create</SelectItem>
                    <SelectItem value="update">update</SelectItem>
                    <SelectItem value="delete">delete</SelectItem>
                    <SelectItem value="validate">validate</SelectItem>
                    <SelectItem value="reject">reject</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  placeholder="Table (chantiers, clients…)"
                  className="w-48"
                  value={activityFilterTable}
                  onChange={(e) => setActivityFilterTable(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') fetchActivities(1, activityFilterAction, activityFilterTable); }}
                />
                <Button size="sm" variant="secondary" onClick={() => fetchActivities(1, activityFilterAction, activityFilterTable)}>
                  Filtrer
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left p-3 font-medium">Date</th>
                      <th className="text-left p-3 font-medium">Action</th>
                      <th className="text-left p-3 font-medium">Table</th>
                      <th className="text-left p-3 font-medium">Entité</th>
                      <th className="text-left p-3 font-medium">Utilisateur</th>
                      <th className="text-left p-3 font-medium">IP</th>
                      <th className="text-left p-3 font-medium">Durée</th>
                      <th className="text-left p-3 font-medium">Détail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activities.length === 0 ? (
                      <tr><td colSpan={8} className="text-center p-6 text-muted-foreground">Aucune activité</td></tr>
                    ) : activities.map((a) => (
                      <tr key={a.id} className="border-t hover:bg-muted/30">
                        <td className="p-3 whitespace-nowrap">{formatDate(a.created_at)}</td>
                        <td className="p-3">
                          <Badge className={ACTION_BADGES[a.action] || ""}>{a.action}</Badge>
                        </td>
                        <td className="p-3 font-mono text-xs">{a.table_name}</td>
                        <td className="p-3 font-mono text-xs">{a.entity_ref || a.entity_id?.substring(0, 8) || "-"}</td>
                        <td className="p-3">{a.user_name || "-"}</td>
                        <td className="p-3 font-mono text-xs">{a.ip_address || "-"}</td>
                        <td className="p-3">{a.processing_duration_ms != null ? `${a.processing_duration_ms}ms` : "-"}</td>
                        <td className="p-3">
                          <JsonDialog title={`Activité ${a.action} sur ${a.table_name}`} data={{ delta: a.delta, previous_state: a.previous_state, new_state: a.new_state }}>
                            <Button size="sm" variant="ghost">JSON</Button>
                          </JsonDialog>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between p-3 border-t text-sm text-muted-foreground">
                <span>Total: {activityTotal}</span>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" disabled={activityPage <= 1}
                    onClick={() => fetchActivities(activityPage - 1, activityFilterAction, activityFilterTable)}>Précédent</Button>
                  <span className="py-1 px-2">{activityPage} / {totalPages(activityTotal)}</span>
                  <Button size="sm" variant="outline" disabled={activityPage >= totalPages(activityTotal)}
                    onClick={() => fetchActivities(activityPage + 1, activityFilterAction, activityFilterTable)}>Suivant</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ====== TAB AGENTS IA ====== */}
        <TabsContent value="agents">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-wrap gap-2 items-center">
                <Select value={agentFilterType} onValueChange={(v) => { setAgentFilterType(v); fetchAgents(1, v, agentFilterStatus); }}>
                  <SelectTrigger className="w-44"><SelectValue placeholder="Type agent" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value=" ">Tous</SelectItem>
                    <SelectItem value="gemini_extraction">gemini_extraction</SelectItem>
                    <SelectItem value="gemini_chat">gemini_chat</SelectItem>
                    <SelectItem value="gemini_ocr">gemini_ocr</SelectItem>
                    <SelectItem value="gemini_classification">gemini_classification</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={agentFilterStatus} onValueChange={(v) => { setAgentFilterStatus(v); fetchAgents(1, agentFilterType, v); }}>
                  <SelectTrigger className="w-36"><SelectValue placeholder="Statut" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value=" ">Tous</SelectItem>
                    <SelectItem value="completed">completed</SelectItem>
                    <SelectItem value="failed">failed</SelectItem>
                    <SelectItem value="pending">pending</SelectItem>
                    <SelectItem value="processing">processing</SelectItem>
                  </SelectContent>
                </Select>
                <Button size="sm" variant="secondary" onClick={() => fetchAgents(1, agentFilterType, agentFilterStatus)}>
                  Filtrer
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left p-3 font-medium">Date</th>
                      <th className="text-left p-3 font-medium">Type</th>
                      <th className="text-left p-3 font-medium">Modèle</th>
                      <th className="text-left p-3 font-medium">Statut</th>
                      <th className="text-left p-3 font-medium">Prompt</th>
                      <th className="text-left p-3 font-medium">Tokens</th>
                      <th className="text-left p-3 font-medium">Coût</th>
                      <th className="text-left p-3 font-medium">Détail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.length === 0 ? (
                      <tr><td colSpan={8} className="text-center p-6 text-muted-foreground">Aucun agent IA</td></tr>
                    ) : agents.map((a) => (
                      <tr key={a.id} className="border-t hover:bg-muted/30">
                        <td className="p-3 whitespace-nowrap">{formatDate(a.created_at)}</td>
                        <td className="p-3 font-mono text-xs">{a.agent_type}</td>
                        <td className="p-3 font-mono text-xs">{a.model}</td>
                        <td className="p-3">
                          <Badge className={STATUS_BADGES[a.status] || ""}>{a.status}</Badge>
                        </td>
                        <td className="p-3 max-w-xs truncate" title={a.user_prompt}>{truncate(a.user_prompt)}</td>
                        <td className="p-3">{a.total_tokens != null ? a.total_tokens.toLocaleString() : "-"}</td>
                        <td className="p-3">{a.cost_estimate != null ? `${a.cost_estimate.toFixed(6)} €` : "-"}</td>
                        <td className="p-3">
                          <JsonDialog title={`Agent ${a.agent_type} - ${a.model}`} data={{
                            prompt: a.user_prompt,
                            response: a.response_text,
                            raw_input: a.raw_input,
                            raw_output: a.raw_output,
                            guardrail_issues: a.guardrail_issues,
                            validation: a.validation_result,
                            métriques: {
                              tokens: { input: a.input_tokens, output: a.output_tokens, total: a.total_tokens },
                              durée_ms: a.processing_duration_ms,
                              coût: a.cost_estimate,
                            }
                          }}>
                            <Button size="sm" variant="ghost">JSON</Button>
                          </JsonDialog>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between p-3 border-t text-sm text-muted-foreground">
                <span>Total: {agentTotal}</span>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" disabled={agentPage <= 1}
                    onClick={() => fetchAgents(agentPage - 1, agentFilterType, agentFilterStatus)}>Précédent</Button>
                  <span className="py-1 px-2">{agentPage} / {totalPages(agentTotal)}</span>
                  <Button size="sm" variant="outline" disabled={agentPage >= totalPages(agentTotal)}
                    onClick={() => fetchAgents(agentPage + 1, agentFilterType, agentFilterStatus)}>Suivant</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ====== TAB CORRÉLATIONS ====== */}
        <TabsContent value="correlations">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Corrélations</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left p-3 font-medium">Correlation ID</th>
                      <th className="text-left p-3 font-medium">Nb activités</th>
                      <th className="text-left p-3 font-medium">Nb agents</th>
                      <th className="text-left p-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {correlations.length === 0 ? (
                      <tr><td colSpan={4} className="text-center p-6 text-muted-foreground">Aucune corrélation</td></tr>
                    ) : correlations.map((c, i) => (
                      <tr key={c.correlation_id || i} className="border-t hover:bg-muted/30">
                        <td className="p-3 font-mono text-xs">{c.correlation_id}</td>
                        <td className="p-3">{c.nb_activites}</td>
                        <td className="p-3">{c.nb_agents}</td>
                        <td className="p-3">
                          <Dialog>
                            <DialogTrigger asChild>
                              <Button size="sm" variant="outline">Voir le détail</Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto">
                              <DialogHeader>
                                <DialogTitle className="font-mono text-sm break-all">Corrélation: {c.correlation_id}</DialogTitle>
                              </DialogHeader>
                              <CorrelationDetail correlationId={c.correlation_id} />
                            </DialogContent>
                          </Dialog>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between p-3 border-t text-sm text-muted-foreground">
                <span>Total: {correlationTotal}</span>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" disabled={correlationPage <= 1}
                    onClick={() => fetchCorrelations(correlationPage - 1)}>Précédent</Button>
                  <span className="py-1 px-2">{correlationPage} / {totalPages(correlationTotal)}</span>
                  <Button size="sm" variant="outline" disabled={correlationPage >= totalPages(correlationTotal)}
                    onClick={() => fetchCorrelations(correlationPage + 1)}>Suivant</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function CorrelationDetail({ correlationId }: { correlationId: string }) {
  const [data, setData] = useState<{ activites: ActivityRow[]; agents: AgentRow[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`/api/v1/admin/audit/correlations/${correlationId}`);
        if (res.ok) setData(await res.json());
      } catch (err) {
        console.error("Erreur détail corrélation:", err);
      }
      setLoading(false);
    })();
  }, [correlationId]);

  if (loading) return <p className="text-muted-foreground p-4">Chargement...</p>;
  if (!data) return <p className="text-red-500 p-4">Erreur de chargement</p>;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold mb-2 flex items-center gap-2"><Activity className="h-4 w-4" /> Activités ({data.activites.length})</h3>
        {data.activites.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aucune activité</p>
        ) : (
          <div className="space-y-1 max-h-48 overflow-auto">
            {data.activites.map((a) => (
              <div key={a.id} className="text-xs p-2 bg-muted/30 rounded flex gap-2 items-center">
                <Badge className="text-[10px] px-1 py-0">{a.action}</Badge>
                <span className="font-mono">{a.table_name}</span>
                <span className="text-muted-foreground">{formatDate(a.created_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div>
        <h3 className="font-semibold mb-2 flex items-center gap-2"><Cpu className="h-4 w-4" /> Agents IA ({data.agents.length})</h3>
        {data.agents.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aucun agent</p>
        ) : (
          <div className="space-y-1 max-h-48 overflow-auto">
            {data.agents.map((a) => (
              <div key={a.id} className="text-xs p-2 bg-muted/30 rounded flex gap-2 items-center">
                <Badge className="text-[10px] px-1 py-0">{a.status}</Badge>
                <span className="font-mono">{a.agent_type}</span>
                <span className="text-muted-foreground">{a.model}</span>
                <span className="text-muted-foreground">{formatDate(a.created_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
