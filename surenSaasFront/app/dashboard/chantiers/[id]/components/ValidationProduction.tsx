'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CheckCircle, XCircle, Image, Target, Clock } from 'lucide-react';

interface ValidationProductionProps {
  chantierId: string;
  orgId: string;
  onRefresh?: () => void;
}

interface SituationLigne {
  id: string;
  situation_id: string;
  description: string;
  quantite: number;
  prix_unitaire: number;
  montant_total: number;
  avancement_pourcentage: number;
  avancement_montant: number;
  photo_url: string;
  approuvee: boolean;
  approuvee_par: string | null;
  created_at: string;
}

export default function ValidationProduction({ chantierId, orgId, onRefresh }: ValidationProductionProps) {
  const [lignes, setLignes] = useState<SituationLigne[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLignes();
  }, [chantierId, orgId]);

  const fetchLignes = async () => {
    try {
      const resp = await fetch(`/api/v1/chantiers/${chantierId}/situations?org_id=${orgId}&statut=ouverte`);
      const situations = await resp.json();
      if (!Array.isArray(situations)) return;

      const allLignes: SituationLigne[] = [];
      for (const s of situations) {
        const r = await fetch(`/api/v1/chantiers/${chantierId}/situations/${s.id}/lignes?org_id=${orgId}`);
        const lignesData = await r.json();
        if (Array.isArray(lignesData)) allLignes.push(...lignesData);
      }
      setLignes(allLignes);
    } catch (e) {
      console.error("Erreur chargement avancements:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleApprouver = async (ligneId: string, avancement?: number) => {
    try {
      const url = `/api/v1/chantiers/${chantierId}/situations/_/lignes/${ligneId}/approuver?org_id=${orgId}&approuver=true${avancement !== undefined ? '&avancement=' + avancement : ''}`;
      await fetch(url, { method: 'PUT' });
      fetchLignes();
      if (onRefresh) onRefresh();
    } catch (e) {
      console.error("Erreur approbation:", e);
    }
  };

  if (loading) return <div className="text-center py-8 text-muted-foreground">Chargement des avancements...</div>;

  const enAttente = lignes.filter(l => !l.approuvee);
  const approuvees = lignes.filter(l => l.approuvee);

  return (
    <div className="space-y-6">
      {enAttente.length === 0 && approuvees.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <Target className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Aucun avancement en attente. Les conducteurs peuvent signaler des avancements depuis Telegram.</p>
          </CardContent>
        </Card>
      )}

      {enAttente.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-500" />
              Avancements à valider ({enAttente.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Description</TableHead>
                  <TableHead>Qté</TableHead>
                  <TableHead>PU</TableHead>
                  <TableHead>%</TableHead>
                  <TableHead>Montant</TableHead>
                  <TableHead>Photo</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {enAttente.map(l => (
                  <TableRow key={l.id}>
                    <TableCell className="font-medium">{l.description}</TableCell>
                    <TableCell>{l.quantite}</TableCell>
                    <TableCell>{l.prix_unitaire}€</TableCell>
                    <TableCell>
                      <Badge variant={l.avancement_pourcentage >= 100 ? "default" : "secondary"}>
                        {l.avancement_pourcentage}%
                      </Badge>
                    </TableCell>
                    <TableCell>{l.avancement_montant.toFixed(2)}€</TableCell>
                    <TableCell>
                      {l.photo_url ? (
                        <Button variant="ghost" size="sm"><Image className="h-4 w-4" /></Button>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button size="sm" variant="default" onClick={() => handleApprouver(l.id)}>
                          <CheckCircle className="h-4 w-4 mr-1" /> Approuver
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {approuvees.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              Avancements approuvés ({approuvees.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Description</TableHead>
                  <TableHead>Qté</TableHead>
                  <TableHead>%</TableHead>
                  <TableHead>Montant</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {approuvees.map(l => (
                  <TableRow key={l.id}>
                    <TableCell className="font-medium">{l.description}</TableCell>
                    <TableCell>{l.quantite}</TableCell>
                    <TableCell>{l.avancement_pourcentage}%</TableCell>
                    <TableCell>{l.avancement_montant.toFixed(2)}€</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
