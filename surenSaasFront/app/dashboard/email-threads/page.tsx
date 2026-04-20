"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Search,
  Mail,
  Calendar,
  User,
  AlertCircle,
  Clock,
  CheckCircle2,
  Flag,
  Paperclip,
} from "lucide-react";

interface EmailThread {
  id: string;
  subject: string;
  subject_cleaned?: string;
  participants: {
    emails: string[];
    names: string[];
  };
  ai_summary?: string;
  ai_urgency?: "low" | "medium" | "high";
  ai_status?: "new" | "in_progress" | "waiting" | "resolved";
  metrics: {
    email_count: number;
    attachment_count: number;
    first_email_at: string | null;
    last_email_at: string | null;
  };
  flags: {
    is_archived: boolean;
    is_starred: boolean;
  };
  is_historical_partial?: boolean;
  created_at: string;
  updated_at: string;
}

const statusLabels: Record<string, { label: string; color: string }> = {
  new: { label: "Nouveau", color: "bg-blue-100 text-blue-800" },
  in_progress: { label: "En cours", color: "bg-yellow-100 text-yellow-800" },
  waiting: { label: "En attente", color: "bg-orange-100 text-orange-800" },
  resolved: { label: "Résolu", color: "bg-green-100 text-green-800" },
};

const urgencyLabels: Record<string, { label: string; color: string }> = {
  low: { label: "Basse", color: "bg-gray-100 text-gray-600" },
  medium: { label: "Moyenne", color: "bg-yellow-100 text-yellow-700" },
  high: { label: "Haute", color: "bg-red-100 text-red-700" },
};

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffTime = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  } else if (diffDays === 1) {
    return "Hier";
  } else if (diffDays < 7) {
    const days = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"];
    return days[date.getDay()];
  } else {
    return date.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
  }
}

export default function EmailThreadsPage() {
  const { user } = useAuth();
  const [threads, setThreads] = useState<EmailThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    if (user?.org_slug) {
      fetchThreads();
    }
  }, [user?.org_slug, statusFilter]);

  const fetchThreads = async () => {
    if (!user?.org_slug) return;

    setLoading(true);
    setError(null);

    try {
      let url = `/api/v1/${user.org_slug}/email-threads?limit=50`;
      if (statusFilter) {
        url += `&status=${statusFilter}`;
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Erreur lors du chargement des emails");
      }

      const data = await response.json();
      setThreads(data.data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Une erreur est survenue");
    } finally {
      setLoading(false);
    }
  };

  const filteredThreads = threads.filter((thread) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    const senderEmail = thread.participants?.emails?.[0] || "";
    const senderName = thread.participants?.names?.[0] || "";
    return (
      thread.subject?.toLowerCase().includes(query) ||
      senderEmail.toLowerCase().includes(query) ||
      senderName.toLowerCase().includes(query) ||
      thread.ai_summary?.toLowerCase().includes(query)
    );
  });

  const getInitials = (name: string): string => {
    return name.charAt(0).toUpperCase();
  };

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Emails</h1>
        <p className="text-gray-500 mt-1">
          Gérez vos conversations email avec l&apos;assistant IA
        </p>
      </div>

      {/* Search and Filters */}
      <div className="mb-6 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
          <Input
            placeholder="Rechercher par sujet, expéditeur ou contenu..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant={statusFilter === "" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("")}
          >
            Tous
          </Button>
          <Button
            variant={statusFilter === "new" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("new")}
          >
            Nouveaux
          </Button>
          <Button
            variant={statusFilter === "in_progress" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("in_progress")}
          >
            En cours
          </Button>
          <Button
            variant={statusFilter === "waiting" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("waiting")}
          >
            En attente
          </Button>
          <Button
            variant={statusFilter === "resolved" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("resolved")}
          >
            Résolus
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="text-red-700">{error}</span>
          <Button variant="outline" size="sm" onClick={fetchThreads} className="ml-auto">
            Réessayer
          </Button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-1/3" />
                    <Skeleton className="h-3 w-1/4" />
                    <Skeleton className="h-3 w-3/4" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredThreads.length === 0 && (
        <div className="text-center py-16">
          <Mail className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Aucun email trouvé</h3>
          <p className="text-gray-500">
            {searchQuery
              ? "Aucun résultat pour votre recherche"
              : "Vous n'avez pas encore d'emails dans cette catégorie"}
          </p>
        </div>
      )}

      {/* Thread List */}
      {!loading && filteredThreads.length > 0 && (
        <div className="space-y-3">
          {filteredThreads.map((thread) => (
            <Link key={thread.id} href={`/dashboard/email-threads/${thread.id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    {/* Avatar */}
                    <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium flex-shrink-0">
                      {getInitials(thread.participants?.names?.[0] || thread.participants?.emails?.[0] || "?")}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold text-gray-900 truncate">
                          {thread.subject || "(Pas de sujet)"}
                        </h3>
                        <span className="text-sm text-gray-500 whitespace-nowrap">
                          {thread.metrics?.last_email_at ? formatDate(thread.metrics.last_email_at) : "-"}
                        </span>
                      </div>

                      <p className="text-sm text-gray-600 truncate">
                        {thread.participants?.names?.[0] || thread.participants?.emails?.[0] || "-"}
                      </p>

                      {thread.ai_summary && (
                        <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                          {thread.ai_summary}
                        </p>
                      )}

                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        {/* Status Badge */}
                        <Badge
                          className={statusLabels[thread.ai_status || "new"]?.color || "bg-gray-100"}
                          variant="secondary"
                        >
                          {statusLabels[thread.ai_status || "new"]?.label || thread.ai_status}
                        </Badge>

                        {/* Urgency Badge */}
                        {thread.ai_urgency && thread.ai_urgency !== "low" && (
                          <Badge
                            className={urgencyLabels[thread.ai_urgency]?.color || "bg-gray-100"}
                            variant="secondary"
                          >
                            {urgencyLabels[thread.ai_urgency]?.label}
                          </Badge>
                        )}

                        {/* Historical Partial Badge */}
                        {thread.is_historical_partial && (
                          <Badge
                            className="bg-gray-100 text-gray-600 border border-gray-300"
                            variant="secondary"
                            title="Thread créé depuis un forward externe - historique peut être incomplet"
                          >
                            Historique partiel
                          </Badge>
                        )}

                        {/* Icons */}
                        {thread.metrics?.attachment_count > 0 && (
                          <Paperclip className="h-4 w-4 text-gray-400" />
                        )}
                        {thread.flags?.is_starred && (
                          <Flag className="h-4 w-4 text-red-500" />
                        )}

                        {/* Message Count */}
                        <span className="text-xs text-gray-400 flex items-center gap-1">
                          <Mail className="h-3 w-3" />
                          {thread.metrics?.email_count || 0}
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
