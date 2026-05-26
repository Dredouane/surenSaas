'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft, DollarSign, Building, Calendar, FileText, Package,
} from 'lucide-react';

interface InvoiceItem {
  id: string;
  description: string;
  quantity?: number;
  unit_price?: number;
  total_ht?: number;
  vat_rate?: number;
  sort_order?: number;
}

interface DepenseDetailProps {
  depense: {
    id: string;
    fournisseur: string;
    montant: number;
    description: string;
    date: string;
    categorie: string;
    statut?: string;
    invoice_id?: string;
    invoice_items?: InvoiceItem[];
    facture_ref?: string;
  };
  onBack: () => void;
}

export default function DepenseDetailView({ depense, onBack }: DepenseDetailProps) {
  const items = depense.invoice_items || [];

  const formatMontant = (m: number) =>
    new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 }).format(m);

  const formatDate = (d: string | Date) =>
    new Date(d).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

  const getCategorieBadge = (cat: string) => {
    const colors: Record<string, string> = {
      fournisseur: 'bg-green-100 text-green-800',
      sous_traitant: 'bg-blue-100 text-blue-800',
      achat_direct: 'bg-purple-100 text-purple-800',
      location: 'bg-orange-100 text-orange-800',
      carburant: 'bg-yellow-100 text-yellow-800',
      divers: 'bg-gray-100 text-gray-800',
    };
    return <Badge className={colors[cat] || 'bg-gray-100 text-gray-800'}>{cat}</Badge>;
  };

  const totalHT = items.reduce((s, i) => s + (i.total_ht || 0), 0);

  return (
    <div className="space-y-4">
      <Button variant="ghost" onClick={onBack} className="gap-2 -ml-2">
        <ArrowLeft className="h-4 w-4" />
        Retour aux dépenses
      </Button>

      {/* En-tête */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <DollarSign className="h-5 w-5" />
                {formatMontant(depense.montant)}
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">{depense.fournisseur}</p>
            </div>
            <div className="flex items-center gap-2">
              {getCategorieBadge(depense.categorie)}
              {depense.invoice_id && (
                <Badge className="bg-blue-100 text-blue-800" variant="outline">
                  <FileText className="h-3 w-3 mr-1" />
                  Facture liée
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Building className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Fournisseur :</span>
              <span className="font-medium">{depense.fournisseur}</span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Date :</span>
              <span className="font-medium">{formatDate(depense.date)}</span>
            </div>
            {depense.facture_ref && (
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Réf. facture :</span>
                <span className="font-medium">{depense.facture_ref}</span>
              </div>
            )}
          </div>
          {depense.description && (
            <p className="text-sm text-muted-foreground mt-3">{depense.description}</p>
          )}
        </CardContent>
      </Card>

      {/* Lignes de facture */}
      {items.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Package className="h-5 w-5" />
              Détail de la facture ({items.length} ligne{items.length > 1 ? 's' : ''})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sm truncate">{item.description}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Qté: {item.quantity ?? '-'} × PU: {item.unit_price ? formatMontant(item.unit_price) : '-'}
                      {item.vat_rate ? ` • TVA ${item.vat_rate}%` : ''}
                    </p>
                  </div>
                  <div className="text-right ml-4 flex-shrink-0">
                    <p className="font-medium text-sm">{item.total_ht ? formatMontant(item.total_ht) : '-'}</p>
                    <p className="text-xs text-muted-foreground">HT</p>
                  </div>
                </div>
              ))}
            </div>
            <Separator className="my-3" />
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Total HT</span>
              <span className="text-lg font-bold">{formatMontant(totalHT)}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {!depense.invoice_id && (
        <Card>
          <CardContent className="py-6 text-center text-sm text-muted-foreground">
            <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Cette dépense n'est pas liée à une facture détaillée.</p>
            <p className="text-xs mt-1">Utilise l'upload de facture via Hermes pour avoir des lignes de détail.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
