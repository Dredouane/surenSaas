'use client';

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { 
  ArrowLeft, 
  FileText, 
  Calendar, 
  User, 
  Building2, 
  Edit, 
  Trash2, 
  CheckCircle, 
  XCircle,
  Printer,
  Download
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface InvoiceItem {
  id: string;
  description: string;
  quantity?: number;
  unit_price?: number;
  total_ht?: number;
  vat_rate?: number;
  sort_order?: number;
}

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
  created_by?: string;
  created_at: string;
  updated_at?: string;
  validated_by?: string;
  validated_at?: string;
  items?: InvoiceItem[];
}


const statusLabels: Record<string, { label: string; color: string }> = {
  brouillon: { label: "Brouillon", color: "bg-gray-100 text-gray-800" },
  en_attente_validation: { label: "En attente", color: "bg-yellow-100 text-yellow-800" },
  validee: { label: "Validée", color: "bg-blue-100 text-blue-800" },
  en_traitement_comptable: { label: "En traitement", color: "bg-purple-100 text-purple-800" },
  archivee: { label: "Archivée", color: "bg-gray-100 text-gray-600" },
  rejetee: { label: "Rejetée", color: "bg-red-100 text-red-800" },
};

export default function InvoiceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [validating, setValidating] = useState(false);

  const invoiceId = params.id as string;

  useEffect(() => {
    if (user?.org_id && invoiceId) {
      fetchInvoice();
    }
  }, [user, invoiceId]);

  const fetchInvoice = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `/api/v1/invoices/${invoiceId}?org_id=${user?.org_id}`,
        { credentials: 'include' }
      );

      if (!response.ok) {
        if (response.status === 401) {
          console.error('🔴 Session invalide ou expirée - Redirection vers login');
          router.push('/login?error=session_expired');
          return;
        }
        if (response.status === 404) {
          throw new Error('Facture non trouvée');
        }
        throw new Error('Erreur lors de la récupération de la facture');
      }

      const data = await response.json();
      setInvoice(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      setDeleting(true);
      const response = await fetch(
        `/api/v1/invoices/${invoiceId}?org_id=${user?.org_id}`,
        {
          method: 'DELETE',
          credentials: 'include',
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          console.error('🔴 Session invalide ou expirée - Redirection vers login');
          router.push('/login?error=session_expired');
          return;
        }
        throw new Error('Erreur lors de la suppression');
      }

      router.push('/dashboard/invoices');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la suppression');
      setDeleting(false);
    }
  };

  const handleValidate = async (action: 'validate' | 'reject') => {
    try {
      setValidating(true);
      const response = await fetch(
        `/api/v1/invoices/${invoiceId}/validate?org_id=${user?.org_id}&action=${action}`,
        {
          method: 'POST',
          credentials: 'include',
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          console.error('🔴 Session invalide ou expirée - Redirection vers login');
          router.push('/login?error=session_expired');
          return;
        }
        throw new Error('Erreur lors de la validation');
      }

      fetchInvoice();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la validation');
    } finally {
      setValidating(false);
    }
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8">
        <Skeleton className="h-8 w-32 mb-6" />
        <Card>
          <CardHeader>
            <Skeleton className="h-8 w-64" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="p-6 lg:p-8">
        <Link href="/dashboard/invoices">
          <Button variant="ghost" className="mb-4 gap-2">
            <ArrowLeft className="h-4 w-4" />
            Retour aux factures
          </Button>
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-8 rounded-lg text-center">
          <h2 className="text-xl font-semibold mb-2">Erreur</h2>
          <p>{error || "Facture non trouvée"}</p>
        </div>
      </div>
    );
  }

  const status = statusLabels[invoice.status] || { label: invoice.status, color: "bg-gray-100" };
  const canEdit = invoice.status === 'brouillon';
  const canValidate = invoice.status === 'en_attente_validation';
  const canDelete = invoice.status === 'brouillon';

  return (
    <div className="p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/invoices">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">{invoice.invoice_number}</h1>
            <Badge className={`${status.color} mt-1`}>
              {status.label}
            </Badge>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {canValidate && (
            <>
              <Button 
                variant="outline" 
                className="gap-2 text-red-600 border-red-200 hover:bg-red-50"
                onClick={() => handleValidate('reject')}
                disabled={validating}
              >
                <XCircle className="h-4 w-4" />
                Rejeter
              </Button>
              <Button 
                className="gap-2 bg-green-600 hover:bg-green-700"
                onClick={() => handleValidate('validate')}
                disabled={validating}
              >
                <CheckCircle className="h-4 w-4" />
                Valider
              </Button>
            </>
          )}
          {canEdit && (
            <Link href={`/dashboard/invoices/${invoiceId}/edit`}>
              <Button variant="outline" className="gap-2">
                <Edit className="h-4 w-4" />
                Modifier
              </Button>
            </Link>
          )}
          <Button variant="outline" className="gap-2">
            <Printer className="h-4 w-4" />
            Imprimer
          </Button>
          {canDelete && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" className="gap-2">
                  <Trash2 className="h-4 w-4" />
                  Supprimer
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
                  <AlertDialogDescription>
                    Êtes-vous sûr de vouloir supprimer cette facture ? Cette action est irréversible.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Annuler</AlertDialogCancel>
                  <AlertDialogAction 
                    onClick={handleDelete}
                    disabled={deleting}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    {deleting ? 'Suppression...' : 'Supprimer'}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Informations générales
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Fournisseur</p>
                  <p className="font-medium">{invoice.supplier_name}</p>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Date d'émission</p>
                  <p>{formatDate(invoice.invoice_date)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Date d'échéance</p>
                  <p>{formatDate(invoice.due_date)}</p>
                </div>
              </div>

              {invoice.description && (
                <div className="pt-4 border-t">
                  <p className="text-sm text-muted-foreground mb-1">Description</p>
                  <p className="whitespace-pre-wrap">{invoice.description}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Section Items */}
          {invoice.items && invoice.items.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Lignes de facture ({invoice.items.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b text-sm text-muted-foreground">
                        <th className="text-left py-2 px-2">Description</th>
                        <th className="text-right py-2 px-2">Qté</th>
                        <th className="text-right py-2 px-2">Prix unit.</th>
                        <th className="text-right py-2 px-2">Total HT</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoice.items.map((item, index) => (
                        <tr key={item.id || index} className="border-b last:border-0">
                          <td className="py-3 px-2">
                            <p className="font-medium">{item.description}</p>
                          </td>
                          <td className="text-right py-3 px-2">
                            {item.quantity || '-'}
                          </td>
                          <td className="text-right py-3 px-2">
                            {item.unit_price ? formatAmount(item.unit_price) : '-'}
                          </td>
                          <td className="text-right py-3 px-2 font-medium">
                            {item.total_ht ? formatAmount(item.total_ht) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t-2">
                      <tr>
                        <td colSpan={3} className="text-right py-3 px-2 font-semibold">
                          Total des lignes :
                        </td>
                        <td className="text-right py-3 px-2 font-bold">
                          {formatAmount(invoice.items.reduce((sum, item) => sum + (item.total_ht || 0), 0))}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Montants</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {invoice.amount_ht && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Montant HT</span>
                  <span>{formatAmount(invoice.amount_ht)}</span>
                </div>
              )}
              {invoice.vat_amount && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">TVA</span>
                  <span>{formatAmount(invoice.vat_amount)}</span>
                </div>
              )}
              <div className="flex justify-between pt-4 border-t">
                <span className="font-semibold">Total TTC</span>
                <span className="font-bold text-xl">{formatAmount(invoice.amount_ttc)}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Détails</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="text-muted-foreground">Créé le</p>
                <p>{formatDate(invoice.created_at)}</p>
              </div>
              {invoice.validated_at && (
                <div>
                  <p className="text-muted-foreground">Validé le</p>
                  <p>{formatDate(invoice.validated_at)}</p>
                </div>
              )}
              {invoice.updated_at && (
                <div>
                  <p className="text-muted-foreground">Dernière modification</p>
                  <p>{formatDate(invoice.updated_at)}</p>
                </div>
              )}
              <div>
                <p className="text-muted-foreground">ID Facture</p>
                <p className="font-mono text-xs">{invoice.id}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
