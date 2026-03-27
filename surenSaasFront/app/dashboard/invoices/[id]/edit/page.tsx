'use client';

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Plus, Trash2, Save, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface InvoiceItem {
  id?: string;
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
  vat_rate?: number;
  status: string;
  invoice_date?: string;
  due_date?: string;
  description?: string;
  items?: InvoiceItem[];
}

export default function EditInvoicePage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const invoiceId = params.id as string;
  
  const [invoice, setInvoice] = useState<Partial<Invoice>>({
    invoice_number: '',
    supplier_name: '',
    amount_ht: 0,
    vat_amount: 0,
    amount_ttc: 0,
    vat_rate: 20,
    invoice_date: '',
    due_date: '',
    description: '',
    items: []
  });

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
          console.error('🔴 Session invalide ou expirée');
          router.push('/login?error=session_expired');
          return;
        }
        if (response.status === 404) {
          throw new Error('Facture non trouvée');
        }
        throw new Error('Erreur lors de la récupération');
      }

      const data = await response.json();
      
      // Vérifier que la facture est modifiable
      if (data.status !== 'brouillon') {
        throw new Error('Seules les factures en brouillon peuvent être modifiées');
      }
      
      setInvoice({
        ...data,
        items: data.items || []
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      
      const updateData = {
        invoice_number: invoice.invoice_number,
        supplier_name: invoice.supplier_name,
        amount_ht: invoice.amount_ht,
        vat_amount: invoice.vat_amount,
        amount_ttc: invoice.amount_ttc,
        vat_rate: invoice.vat_rate,
        invoice_date: invoice.invoice_date,
        due_date: invoice.due_date,
        description: invoice.description,
        items: invoice.items
      };

      const response = await fetch(
        `/api/v1/invoices/${invoiceId}?org_id=${user?.org_id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(updateData)
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          console.error('🔴 Session invalide');
          router.push('/login?error=session_expired');
          return;
        }
        throw new Error('Erreur lors de la sauvegarde');
      }

      router.push(`/dashboard/invoices/${invoiceId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  const addItem = () => {
    setInvoice(prev => ({
      ...prev,
      items: [...(prev.items || []), {
        description: '',
        quantity: 1,
        unit_price: 0,
        total_ht: 0,
        vat_rate: prev.vat_rate || 20
      }]
    }));
  };

  const removeItem = (index: number) => {
    setInvoice(prev => ({
      ...prev,
      items: prev.items?.filter((_, i) => i !== index) || []
    }));
  };

  const updateItem = (index: number, field: keyof InvoiceItem, value: any) => {
    setInvoice(prev => {
      const newItems = [...(prev.items || [])];
      newItems[index] = { ...newItems[index], [field]: value };
      
      // Recalculer le total_ht si quantity ou unit_price change
      if (field === 'quantity' || field === 'unit_price') {
        const qty = field === 'quantity' ? value : (newItems[index].quantity || 0);
        const price = field === 'unit_price' ? value : (newItems[index].unit_price || 0);
        newItems[index].total_ht = qty * price;
      }
      
      return { ...prev, items: newItems };
    });
  };

  const calculateTotals = () => {
    const total_ht = invoice.items?.reduce((sum, item) => sum + (item.total_ht || 0), 0) || 0;
    const vat_rate = invoice.vat_rate || 20;
    const vat_amount = total_ht * (vat_rate / 100);
    const amount_ttc = total_ht + vat_amount;
    
    setInvoice(prev => ({
      ...prev,
      amount_ht: total_ht,
      vat_amount: vat_amount,
      amount_ttc: amount_ttc
    }));
  };

  // Recalculer les totaux quand les items changent
  useEffect(() => {
    calculateTotals();
  }, [invoice.items]);

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto">
        <Skeleton className="h-8 w-48 mb-6" />
        <Card>
          <CardContent className="p-6 space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto">
        <Link href={`/dashboard/invoices/${invoiceId}`}>
          <Button variant="ghost" className="mb-4 gap-2">
            <ArrowLeft className="h-4 w-4" />
            Retour
          </Button>
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-8 rounded-lg text-center">
          <h2 className="text-xl font-semibold mb-2">Erreur</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href={`/dashboard/invoices/${invoiceId}`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">Modifier la facture</h1>
            <Badge variant="outline" className="mt-1">Brouillon</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Link href={`/dashboard/invoices/${invoiceId}`}>
            <Button variant="outline" className="gap-2">
              <X className="h-4 w-4" />
              Annuler
            </Button>
          </Link>
          <Button 
            onClick={handleSave} 
            disabled={saving}
            className="gap-2"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Sauvegarde...' : 'Sauvegarder'}
          </Button>
        </div>
      </div>

      <div className="space-y-6">
        {/* Informations générales */}
        <Card>
          <CardHeader>
            <CardTitle>Informations générales</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="invoice_number">Numéro de facture</Label>
                <Input
                  id="invoice_number"
                  value={invoice.invoice_number || ''}
                  onChange={(e) => setInvoice(prev => ({ ...prev, invoice_number: e.target.value }))}
                  placeholder="FAC-2024-001"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="supplier_name">Fournisseur</Label>
                <Input
                  id="supplier_name"
                  value={invoice.supplier_name || ''}
                  onChange={(e) => setInvoice(prev => ({ ...prev, supplier_name: e.target.value }))}
                  placeholder="Nom du fournisseur"
                />
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="invoice_date">Date d'émission</Label>
                <Input
                  id="invoice_date"
                  type="date"
                  value={invoice.invoice_date || ''}
                  onChange={(e) => setInvoice(prev => ({ ...prev, invoice_date: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="due_date">Date d'échéance</Label>
                <Input
                  id="due_date"
                  type="date"
                  value={invoice.due_date || ''}
                  onChange={(e) => setInvoice(prev => ({ ...prev, due_date: e.target.value }))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={invoice.description || ''}
                onChange={(e) => setInvoice(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Description de la facture"
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Lignes de facture */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Lignes de facture</CardTitle>
            <Button type="button" onClick={addItem} variant="outline" size="sm" className="gap-2">
              <Plus className="h-4 w-4" />
              Ajouter une ligne
            </Button>
          </CardHeader>
          <CardContent>
            {invoice.items && invoice.items.length > 0 ? (
              <div className="space-y-4">
                {invoice.items.map((item, index) => (
                  <div key={index} className="grid grid-cols-12 gap-2 items-end p-4 border rounded-lg bg-gray-50">
                    <div className="col-span-6">
                      <Label className="text-xs">Description</Label>
                      <Input
                        value={item.description}
                        onChange={(e) => updateItem(index, 'description', e.target.value)}
                        placeholder="Description du service/produit"
                      />
                    </div>
                    <div className="col-span-2">
                      <Label className="text-xs">Qté</Label>
                      <Input
                        type="number"
                        value={item.quantity || ''}
                        onChange={(e) => updateItem(index, 'quantity', parseFloat(e.target.value) || 0)}
                        placeholder="1"
                      />
                    </div>
                    <div className="col-span-2">
                      <Label className="text-xs">Prix unit. HT</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={item.unit_price || ''}
                        onChange={(e) => updateItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                        placeholder="0.00"
                      />
                    </div>
                    <div className="col-span-1">
                      <Label className="text-xs">Total HT</Label>
                      <div className="h-10 flex items-center font-medium">
                        {(item.total_ht || 0).toFixed(2)} €
                      </div>
                    </div>
                    <div className="col-span-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeItem(index)}
                        className="text-red-600 hover:text-red-800"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>Aucune ligne de facture</p>
                <Button type="button" onClick={addItem} variant="outline" className="mt-2 gap-2">
                  <Plus className="h-4 w-4" />
                  Ajouter une ligne
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Totaux */}
        <Card>
          <CardHeader>
            <CardTitle>Totaux</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-w-md ml-auto">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Montant HT</span>
                <span className="font-medium">{invoice.amount_ht?.toFixed(2) || '0.00'} €</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">TVA ({invoice.vat_rate || 20}%)</span>
                <span className="font-medium">{invoice.vat_amount?.toFixed(2) || '0.00'} €</span>
              </div>
              <div className="flex justify-between pt-3 border-t">
                <span className="font-semibold">Total TTC</span>
                <span className="font-bold text-xl">{invoice.amount_ttc?.toFixed(2) || '0.00'} €</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
