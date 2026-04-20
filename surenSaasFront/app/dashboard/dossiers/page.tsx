'use client';

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { FolderKanban, Plus, Search, MapPin, Users, FileText, Clock } from "lucide-react";

interface Dossier {
  id: string;
  name: string;
  client_name?: string;
  address?: string;
  status: 'active' | 'completed' | 'on_hold' | 'cancelled';
  thread_count: number;
  document_count: number;
  ai_summary?: string;
  updated_at: string;
}

const statusLabels: Record<string, { label: string; color: string }> = {
  active: { label: "Actif", color: "bg-green-100 text-green-800" },
  completed: { label: "Terminé", color: "bg-blue-100 text-blue-800" },
  on_hold: { label: "En pause", color: "bg-yellow-100 text-yellow-800" },
  cancelled: { label: "Annulé", color: "bg-red-100 text-red-800" },
};

export default function DossiersPage() {
  const { user } = useAuth();
  const [dossiers, setDossiers] = useState<Dossier[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    if (user?.org_slug) {
      fetchDossiers();
    }
  }, [user?.org_slug]);

  const fetchDossiers = async () => {
    try {
      setLoading(true);
      const url = `/api/v1/${user?.org_slug}/dossiers?limit=50${statusFilter ? `&status=${statusFilter}` : ''}${searchQuery ? `&search=${searchQuery}` : ''}`;
      
      const response = await fetch(url, { credentials: 'include' });
      
      if (!response.ok) {
        throw new Error(`Erreur ${response.status}`);
      }
      
      const data = await response.json();
      setDossiers(data.data || []);
    } catch (err) {
      console.error('❌ Erreur fetch dossiers:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredDossiers = dossiers.filter(d =>
    d.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.client_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.address?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">Dossiers</h1>
          <p className="text-muted-foreground mt-1">
            Gérez vos chantiers et projets clients
          </p>
        </div>
        <Link href="/dashboard/dossiers/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Nouveau dossier
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher un dossier..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {['active', 'completed', 'on_hold'].map((status) => (
            <Button
              key={status}
              variant={statusFilter === status ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(statusFilter === status ? "" : status)}
            >
              {statusLabels[status]?.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Loading State */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredDossiers.length === 0 ? (
        <div className="text-center py-12">
          <FolderKanban className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Aucun dossier trouvé</h3>
          <p className="text-muted-foreground mb-4">
            {searchQuery || statusFilter
              ? "Aucun dossier ne correspond à vos critères"
              : "Créez votre premier dossier pour regrouper vos emails par projet"}
          </p>
          <Link href="/dashboard/dossiers/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Créer un dossier
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDossiers.map((dossier) => {
            const status = statusLabels[dossier.status] || { label: dossier.status, color: "bg-gray-100" };
            
            return (
              <Link key={dossier.id} href={`/dashboard/dossiers/${dossier.id}`}>
                <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-lg font-semibold line-clamp-2">
                        {dossier.name}
                      </CardTitle>
                      <Badge className={status.color} variant="secondary">
                        {status.label}
                      </Badge>
                    </div>
                    {dossier.client_name && (
                      <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                        <Users className="h-3 w-3" />
                        {dossier.client_name}
                      </p>
                    )}
                  </CardHeader>
                  
                  <CardContent>
                    {dossier.address && (
                      <p className="text-sm text-muted-foreground flex items-center gap-1 mb-3">
                        <MapPin className="h-3 w-3" />
                        <span className="line-clamp-1">{dossier.address}</span>
                      </p>
                    )}
                    
                    {dossier.ai_summary && (
                      <p className="text-sm text-gray-600 line-clamp-2 mb-3">
                        {dossier.ai_summary}
                      </p>
                    )}
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <FileText className="h-3 w-3" />
                        {dossier.thread_count} email{dossier.thread_count > 1 ? 's' : ''}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {dossier.document_count} doc.
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
