'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/app/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, FolderKanban } from "lucide-react";

export default function NewDossierPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    client_name: "",
    client_email: "",
    address: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;

    try {
      setLoading(true);
      
      const response = await fetch(`/api/v1/${user?.org_slug}/dossiers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Erreur création dossier');
      }

      const data = await response.json();
      router.push(`/dashboard/dossiers/${data.id}`);
    } catch (err) {
      console.error('❌ Erreur création:', err);
      alert('Erreur lors de la création du dossier');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-2xl">
      <Link href="/dashboard/dossiers">
        <Button variant="ghost" size="sm" className="mb-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Retour aux dossiers
        </Button>
      </Link>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FolderKanban className="h-5 w-5" />
            <CardTitle>Nouveau dossier</CardTitle>
          </div>
        </CardHeader>
        
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="name">Nom du dossier *</Label>
              <Input
                id="name"
                placeholder="Ex: Résidence Les Lilas - Salle de bain"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </div>

            <div>
              <Label htmlFor="client_name">Client</Label>
              <Input
                id="client_name"
                placeholder="Nom du client ou entreprise"
                value={formData.client_name}
                onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
              />
            </div>

            <div>
              <Label htmlFor="client_email">Email client</Label>
              <Input
                id="client_email"
                type="email"
                placeholder="contact@client.fr"
                value={formData.client_email}
                onChange={(e) => setFormData({ ...formData, client_email: e.target.value })}
              />
            </div>

            <div>
              <Label htmlFor="address">Adresse du chantier</Label>
              <Input
                id="address"
                placeholder="12 rue des Lilas, 75019 Paris"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              />
            </div>

            <div className="flex gap-3 pt-4">
              <Button type="submit" disabled={loading}>
                {loading ? "Création..." : "Créer le dossier"}
              </Button>
              <Link href="/dashboard/dossiers">
                <Button variant="outline" type="button">Annuler</Button>
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
