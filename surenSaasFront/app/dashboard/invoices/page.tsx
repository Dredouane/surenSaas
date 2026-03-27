'use client';

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search, Plus, FileText, Calendar, User } from "lucide-react";

interface Invoice {
  id: string;
  invoice_number: string;
  supplier_name: string;
  amount_ttc: number;
  amount_ht?: number;
  vat_amount?: number;
  status: string;
  invoice_date?: string;
  due_date?: string;
  description?: string;
  client_id?: string;
  created_at: string;
}

const DEFAULT_ORG_ID = process.env.NEXT_PUBLIC_ORG_ID;

const statusLabels: Record<string, { label: string; color: string }> = {
  brouillon: { label: "Brouillon", color: "bg-gray-100 text-gray-800" },
  en_attente_validation: { label: "En attente", color: "bg-yellow-100 text-yellow-800" },
  validee: { label: "Validée", color: "bg-blue-100 text-blue-800" },
  en_traitement_comptable: { label: "En traitement", color: "bg-purple-100 text-purple-800" },
  archivee: { label: "Archivée", color: "bg-gray-100 text-gray-600" },
  rejetee: { label: "Rejetée", color: "bg-red-100 text-red-800" },
};

function formatAmount(amount: number): string {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(amount);
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('fr-FR');
}

export default function InvoicesPage() {
  const { user } = useAuth();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Chargement quand user est disponible ou au montage avec fallback
  useEffect(() => {
    console.log('⚡ InvoicesPage MOUNTED');
    console.log('👤 User:', user?.email, 'org_id:', user?.org_id);
    
    // Utiliser user.org_id ou fallback sur l'org_id par défaut
    const orgId = user?.org_id || DEFAULT_ORG_ID;
    if (orgId) {
      fetchInvoices(orgId);
    }
  }, [user?.org_id]);

  const fetchInvoices = async (orgId?: string) => {
    try {
      setLoading(true);
      const effectiveOrgId = orgId || user?.org_id || DEFAULT_ORG_ID;
      console.log('🚀 Fetching invoices...', { user: user?.email, org_id: effectiveOrgId });
      
      if (!effectiveOrgId) {
        console.error('❌ No org_id available');
        setError('Organisation non disponible');
        return;
      }
      
      const url = `/api/v1/invoices?org_id=${effectiveOrgId}`;
      console.log('📡 Calling API:', url);
      
      const response = await fetch(url, { credentials: 'include' });
      console.log('📥 Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API Error:', errorText);
        throw new Error(`Erreur ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log('✅ Data received:', data.length, 'invoices');
      setInvoices(data);
      setError(null);
    } catch (err) {
      console.error('❌ Fetch error:', err);
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  const filteredInvoices = invoices.filter(inv =>
    inv.invoice_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    inv.supplier_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <h1 className="text-3xl font-bold">Factures</h1>
        <Link href="/dashboard/invoices/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Nouvelle facture
          </Button>
        </Link>
      </div>

      {/* Barre de recherche */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Rechercher une facture..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10 max-w-md"
        />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          <p className="mb-2">{error}</p>
          <Button onClick={() => fetchInvoices()} variant="outline" size="sm">
            Réessayer
          </Button>
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-4 w-48" />
                  </div>
                  <Skeleton className="h-8 w-24" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredInvoices.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Aucune facture trouvée</h3>
          <p className="text-muted-foreground mb-4">
            {searchQuery 
              ? "Aucune facture ne correspond à votre recherche"
              : "Commencez par créer votre première facture"
            }
          </p>
          {!searchQuery && (
            <Link href="/dashboard/invoices/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Créer une facture
              </Button>
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredInvoices.map((invoice) => {
            const status = statusLabels[invoice.status] || { label: invoice.status, color: "bg-gray-100" };
            
            return (
              <Link key={invoice.id} href={`/dashboard/invoices/${invoice.id}`}>
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardContent className="p-6">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-3">
                          <h3 className="font-semibold text-lg">{invoice.invoice_number}</h3>
                          <Badge className={status.color}>
                            {status.label}
                          </Badge>
                        </div>
                        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <User className="h-4 w-4" />
                            {invoice.supplier_name}
                          </span>
                          {invoice.invoice_date && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-4 w-4" />
                              {formatDate(invoice.invoice_date)}
                            </span>
                          )}
                        </div>
                        {invoice.description && (
                          <p className="text-sm text-muted-foreground line-clamp-1">
                            {invoice.description}
                          </p>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-bold">{formatAmount(invoice.amount_ttc)}</p>
                        {invoice.amount_ht && (
                          <p className="text-sm text-muted-foreground">
                            HT: {formatAmount(invoice.amount_ht)}
                          </p>
                        )}
                      </div>
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
