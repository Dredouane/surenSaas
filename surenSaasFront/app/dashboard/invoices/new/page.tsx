'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft, Plus, Trash2, Save, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface InvoiceItem {
  description: string;
  quantity?: number;
  unit_price?: number;
  total_ht?: number;
  vat_rate?: number;
}

export default function NewInvoicePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [invoice, setInvoice] = useState({
    invoice_number: '',
    supplier_name: '',
    amount_ht: 0,
    vat_amount: 0,
    amount_ttc: 0,
    vat_rate: 20,
    invoice_date: new Date().toISOString().split('T')[0],
    due_date: '',
    description: '',
    items: [] as InvoiceItem[]
  });

  const handleSave = async () => {
    try {
      setSaving(true);
      
      if (!invoice.supplier_name) {
        throw new Error('Le nom du fournisseur est obligatoire');
      }

      const createData = {
        invoice_number: invoice.invoice_number || null,
        supplier_name: invoice.supplier_name,
        amount_ht: invoice.amount_ht,
        vat_amount: invoice.vat_amount,
        amount_ttc: invoice.amount_ttc,
        vat_rate: invoice.vat_rate,
        invoice_date: invoice.invoice_date || null,
        due_date: invoice.due_date || null,
        description: invoice.description || null,
        items: invoice.items
      };

      const response = await fetch(
        `/api/v1/invoices?org_id=${user?.org_id}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(createData)
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          console.error('🔴 Session invalide');
          router.push('/login?error=session_expired');
          return;
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Erreur lors de la création');
      }

      const data = await response.json();
      router.push(`/dashboard/invoices/${data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la création');
    } finally {
      setSaving(false);
    }
  };

  const addItem = () => {
    setInvoice(prev => ({
      ...prev,
      items: [...prev.items, {
        description: '',
        quantity: 1,
        unit_price: 0,
        total_ht: 0,
        vat_rate: prev.vat_rate
      }]
    }));
  };

  const removeItem = (index: number) => {
    setInvoice(prev => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index)
    }));
  };

  const updateItem = (index: number, field: keyof InvoiceItem, value: any) => {
    setInvoice(prev => {
      const newItems = [...prev.items];
      newItems[index] = { ...newItems[index], [field]: value };
      
      // Recalculer le total_ht
      if (field === 'quantity' || field === 'unit_price') {
        const qty = field === 'quantity' ? value : (newItems[index].quantity || 0);
        const price = field === 'unit_price' ? value : (newItems[index].unit_price || 0);
        newItems[index].total_ht = qty * price;
      }
      
      return { ...prev, items: newItems };
    });
  };

  // Recalculer les totaux
  const calculateTotals = () => {
    const total_ht = invoice.items.reduce((sum, item) => sum + (item.total_ht || 0), 0);
    const vat_amount = total_ht * (invoice.vat_rate / 100);
    const amount_ttc = total_ht + vat_amount;
    
    setInvoice(prev => ({
      ...prev,
      amount_ht: total_ht,
      vat_amount: vat_amount,
      amount_ttc: amount_ttc
    }));
  };

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/invoices">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">Nouvelle facture</h1>
            <Badge variant="outline" className="mt-1">Brouillon</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/invoices">
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
            {saving ? 'Création...' : 'Créer la facture'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

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
                  value={invoice.invoice_number}
                  onChange={(e) => setInvoice(prev => ({ ...prev, invoice_number: e.target.value }))}
                  placeholder="FAC-2024-001"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="supplier_name">Fournisseur *</Label>
                <Input
                  id="supplier_name"
                  value={invoice.supplier_name}
                  onChange={(e) => setInvoice(prev => ({ ...prev, supplier_name: e.target.value }))}
                  placeholder="Nom du fournisseur"
                  required
                />
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="invoice_date">Date d'émission</Label>
                <Input
                  id="invoice_date"
                  type="date"
                  value={invoice.invoice_date}
                  onChange={(e) => setInvoice(prev => ({ ...prev, invoice_date: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="due_date">Date d'échéance</Label>
                <Input
                  id="due_date"
                  type="date"
                  value={invoice.due_date}
                  onChange={(e) => setInvoice(prev => ({ ...prev, due_date: e.target.value }))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={invoice.description}
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
            {invoice.items.length > 0 ? (
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
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Totaux</CardTitle>
            <Button type="button" onClick={calculateTotals} variant="outline" size="sm">
              Recalculer
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-w-md ml-auto">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Montant HT</span>
                <span className="font-medium">{invoice.amount_ht.toFixed(2)} €</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">TVA ({invoice.vat_rate}%)</span>
                <span className="font-medium">{invoice.vat_amount.toFixed(2)} €</span>
              </div>
              <div className="flex justify-between pt-3 border-t">
                <span className="font-semibold">Total TTC</span>
                <span className="font-bold text-xl">{invoice.amount_ttc.toFixed(2)} €</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
