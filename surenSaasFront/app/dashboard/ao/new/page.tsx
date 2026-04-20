"use client";

/**
 * Page Nouvelle Candidature AO
 * 
 * Formulaire de création d'une nouvelle candidature
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/app/contexts/AuthContext";
import { ArrowLeft, Loader2, Save } from "lucide-react";

export default function NewAOPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    nom_projet: "",
    client_nom: "",
    reference_ao: "",
    description: "",
    date_limite_remise: "",
    date_depot: "",
    date_ouverture: "",
    montant_total: "",
    montant_maximum: "",
    duree_travaux_jours: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // TODO: Appeler l'API
      // const response = await fetch('/api/ao/candidatures', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(formData),
      // });
      // const data = await response.json();

      // Simuler la création
      await new Promise((resolve) => setTimeout(resolve, 1000));
      
      router.push("/dashboard/ao");
    } catch (error) {
      console.error("Erreur création:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link href="/dashboard/ao">
          <Button variant="outline" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Nouvelle Candidature</h1>
          <p className="text-muted-foreground">
            Créez une nouvelle candidature à un appel d&apos;offres
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="space-y-6">
          {/* Informations générales */}
          <Card>
            <CardHeader>
              <CardTitle>Informations générales</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="nom_projet">Nom du projet *</Label>
                  <Input
                    id="nom_projet"
                    value={formData.nom_projet}
                    onChange={(e) => handleChange("nom_projet", e.target.value)}
                    placeholder="Ex: Résidence Les Lilas"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="client_nom">Client</Label>
                  <Input
                    id="client_nom"
                    value={formData.client_nom}
                    onChange={(e) => handleChange("client_nom", e.target.value)}
                    placeholder="Ex: ACORUS"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="reference_ao">Référence AO</Label>
                <Input
                  id="reference_ao"
                  value={formData.reference_ao}
                  onChange={(e) => handleChange("reference_ao", e.target.value)}
                  placeholder="Ex: AO-2024-001"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description du projet</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => handleChange("description", e.target.value)}
                  placeholder="Décrivez le projet..."
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          {/* Dates */}
          <Card>
            <CardHeader>
              <CardTitle>Dates importantes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="date_limite_remise">Date limite de remise</Label>
                  <Input
                    id="date_limite_remise"
                    type="date"
                    value={formData.date_limite_remise}
                    onChange={(e) => handleChange("date_limite_remise", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="date_depot">Date de dépôt</Label>
                  <Input
                    id="date_depot"
                    type="date"
                    value={formData.date_depot}
                    onChange={(e) => handleChange("date_depot", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="date_ouverture">Date d&apos;ouverture</Label>
                  <Input
                    id="date_ouverture"
                    type="date"
                    value={formData.date_ouverture}
                    onChange={(e) => handleChange("date_ouverture", e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="duree_travaux_jours">Durée des travaux (jours)</Label>
                <Input
                  id="duree_travaux_jours"
                  type="number"
                  value={formData.duree_travaux_jours}
                  onChange={(e) => handleChange("duree_travaux_jours", e.target.value)}
                  placeholder="Ex: 180"
                />
              </div>
            </CardContent>
          </Card>

          {/* Financier */}
          <Card>
            <CardHeader>
              <CardTitle>Informations financières</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="montant_total">Montant total (€)</Label>
                  <Input
                    id="montant_total"
                    type="number"
                    value={formData.montant_total}
                    onChange={(e) => handleChange("montant_total", e.target.value)}
                    placeholder="Ex: 1250000"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="montant_maximum">Montant maximum (€)</Label>
                  <Input
                    id="montant_maximum"
                    type="number"
                    value={formData.montant_maximum}
                    onChange={(e) => handleChange("montant_maximum", e.target.value)}
                    placeholder="Ex: 1500000"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Link href="/dashboard/ao">
              <Button variant="outline" type="button">
                Annuler
              </Button>
            </Link>
            <Button type="submit" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Création...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Créer la candidature
                </>
              )}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
