'use client';

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  ArrowLeft, 
  FolderKanban, 
  Users, 
  MapPin, 
  FileText, 
  Mail, 
  CheckSquare,
  Clock,
  AlertCircle,
  Bot
} from "lucide-react";

interface Dossier {
  id: string;
  name: string;
  client_name?: string;
  client_email?: string;
  address?: string;
  project_type?: string;
  status: 'active' | 'completed' | 'on_hold' | 'cancelled';
  ai_summary?: string;
  thread_count: number;
  document_count: number;
  created_at: string;
}

interface Thread {
  id: string;
  subject: string;
  ai_summary?: string;
  ai_status: string;
  ai_urgency: string;
  email_count: number;
  last_email_at: string;
}

const statusLabels: Record<string, { label: string; color: string }> = {
  active: { label: "Actif", color: "bg-green-100 text-green-800" },
  completed: { label: "Terminé", color: "bg-blue-100 text-blue-800" },
  on_hold: { label: "En pause", color: "bg-yellow-100 text-yellow-800" },
  cancelled: { label: "Annulé", color: "bg-red-100 text-red-800" },
};

export default function DossierDetailPage() {
  const params = useParams();
  const { user } = useAuth();
  const dossierId = params.id as string;
  
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("emails");

  useEffect(() => {
    if (user?.org_slug && dossierId) {
      fetchDossierDetail();
    }
  }, [user?.org_slug, dossierId]);

  const fetchDossierDetail = async () => {
    try {
      setLoading(true);
      
      // Fetch dossier
      const dossierRes = await fetch(
        `/api/v1/${user?.org_slug}/dossiers/${dossierId}`,
        { credentials: 'include' }
      );
      
      if (!dossierRes.ok) throw new Error('Dossier non trouvé');
      
      const dossierData = await dossierRes.json();
      setDossier(dossierData);
      
      // Fetch threads
      const threadsRes = await fetch(
        `/api/v1/${user?.org_slug}/dossiers/${dossierId}/emails`,
        { credentials: 'include' }
      );
      
      if (threadsRes.ok) {
        const threadsData = await threadsRes.json();
        setThreads(threadsData.data || []);
      }
    } catch (err) {
      console.error('❌ Erreur fetch dossier:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8">
        <Skeleton className="h-8 w-32 mb-4" />
        <Skeleton className="h-12 w-64 mb-4" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!dossier) {
    return (
      <div className="p-6 lg:p-8">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Dossier non trouvé</h3>
          <Link href="/dashboard/dossiers">
            <Button variant="outline">Retour aux dossiers</Button>
          </Link>
        </div>
      </div>
    );
  }

  const status = statusLabels[dossier.status] || { label: dossier.status, color: "bg-gray-100" };

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-6">
        <Link href="/dashboard/dossiers">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retour aux dossiers
          </Button>
        </Link>
        
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold">{dossier.name}</h1>
              <Badge className={status.color} variant="secondary">
                {status.label}
              </Badge>
            </div>
            
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              {dossier.client_name && (
                <span className="flex items-center gap-1">
                  <Users className="h-4 w-4" />
                  {dossier.client_name}
                </span>
              )}
              {dossier.address && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-4 w-4" />
                  {dossier.address}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                Créé le {new Date(dossier.created_at).toLocaleDateString('fr-FR')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* AI Summary */}
      {dossier.ai_summary && (
        <Card className="mb-6 bg-blue-50 border-blue-200">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-blue-600" />
              <CardTitle className="text-base text-blue-900">Résumé IA</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-blue-800">{dossier.ai_summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="emails" className="gap-2">
            <Mail className="h-4 w-4" />
            Emails ({dossier.thread_count})
          </TabsTrigger>
          <TabsTrigger value="documents" className="gap-2">
            <FileText className="h-4 w-4" />
            Documents ({dossier.document_count})
          </TabsTrigger>
          <TabsTrigger value="tasks" className="gap-2">
            <CheckSquare className="h-4 w-4" />
            Tâches
          </TabsTrigger>
        </TabsList>

        <TabsContent value="emails">
          {threads.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Mail className="h-12 w-12 mx-auto mb-4" />
              <p>Aucun email lié à ce dossier</p>
            </div>
          ) : (
            <div className="space-y-3">
              {threads.map((thread) => (
                <Link key={thread.id} href={`/dashboard/email-threads/${thread.id}`}>
                  <Card className="hover:shadow-md transition-shadow cursor-pointer">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-semibold mb-1">{thread.subject}</h3>
                          {thread.ai_summary && (
                            <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                              {thread.ai_summary}
                            </p>
                          )}
                          <div className="flex items-center gap-2 text-sm">
                            <Badge variant="outline">{thread.email_count} emails</Badge>
                            {thread.ai_urgency === 'high' && (
                              <Badge className="bg-red-100 text-red-800">Urgent</Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="documents">
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4" />
            <p>Fonctionnalité en cours de développement</p>
            <p className="text-sm">Les documents seront agrégés ici prochainement</p>
          </div>
        </TabsContent>

        <TabsContent value="tasks">
          <div className="text-center py-8 text-muted-foreground">
            <CheckSquare className="h-12 w-12 mx-auto mb-4" />
            <p>Fonctionnalité en cours de développement</p>
            <p className="text-sm">Les tâches détectées par l'IA seront listées ici</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
