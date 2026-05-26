'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Calendar, Users, Truck, Clock, CheckCircle, XCircle,
} from 'lucide-react';
import type { Pointage } from '@/types/chantier';

interface PointageMobileListProps {
  pointages: Pointage[];
  onSelect: (pointage: Pointage) => void;
}

export default function PointageMobileList({ pointages, onSelect }: PointageMobileListProps) {
  const formatDate = (dateString: string | Date) => {
    const d = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (d.toDateString() === today.toDateString()) return "Aujourd'hui";
    if (d.toDateString() === yesterday.toDateString()) return 'Hier';
    return d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
  };

  const getStatusStyle = (p: Pointage) => {
    if (p.validePar) return { bg: 'bg-green-50 border-green-200', icon: <CheckCircle className="h-5 w-5 text-green-600" />, label: 'Validé' };
    const s = (p as any).status;
    if (s === 'en_attente_validation') return { bg: 'bg-amber-50 border-amber-200', icon: <Clock className="h-5 w-5 text-amber-600" />, label: 'En attente' };
    return { bg: 'bg-gray-50 border-gray-200', icon: <Clock className="h-5 w-5 text-gray-500" />, label: 'Brouillon' };
  };

  if (pointages.length === 0) {
    return (
      <div className="text-center py-12">
        <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-lg font-medium">Aucun pointage</h3>
        <p className="text-sm text-muted-foreground mt-2">
          Les pointages enregistrés apparaîtront ici.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {pointages.map((p) => {
        const style = getStatusStyle(p);
        const hommes = p.ressources.filter(r => r.type === 'homme').length;
        const machines = p.ressources.filter(r => r.type === 'machine').length;
        return (
          <Card
            key={p.id}
            className={`cursor-pointer hover:shadow-md transition-shadow ${style.bg}`}
            onClick={() => onSelect(p)}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  {style.icon}
                  <div className="min-w-0">
                    <p className="font-medium truncate">{formatDate(p.date)}</p>
                    <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" />
                        {hommes}
                      </span>
                      <span className="flex items-center gap-1">
                        <Truck className="h-3.5 w-3.5" />
                        {machines}
                      </span>
                    </div>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className={
                    p.validePar
                      ? 'border-green-200 text-green-700 bg-green-50'
                      : 'border-amber-200 text-amber-700 bg-amber-50'
                  }
                >
                  {style.label}
                </Badge>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
