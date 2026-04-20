"use client";

/**
 * ValidationBadge - Système de badges pour validation humaine
 * 
 * Affiche des badges interactifs OUI/NON/PARTIEL pour valider
 * les suggestions de l'IA. Utilisé dans le cadre de l'analyse
 * comparative et des recommandations IA.
 */

import React, { useState } from 'react';
import { 
  Check, 
  X, 
  HelpCircle, 
  MessageSquare,
  Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type ValidationStatus = 'pending' | 'valide' | 'rejete' | 'partiel';

export interface ValidationItem {
  id: string;
  label: string;
  description?: string;
  status: ValidationStatus;
  commentaire?: string;
  validatedBy?: string;
  validatedAt?: Date;
}

interface ValidationBadgeProps {
  item: ValidationItem;
  onValidate: (id: string, status: ValidationStatus, commentaire?: string) => Promise<void>;
  size?: 'sm' | 'md' | 'lg';
  showComment?: boolean;
  className?: string;
}

export function ValidationBadge({
  item,
  onValidate,
  size = 'md',
  showComment = true,
  className
}: ValidationBadgeProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isCommentOpen, setIsCommentOpen] = useState(false);
  const [comment, setComment] = useState(item.commentaire || '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleValidate = async (status: ValidationStatus) => {
    setIsSubmitting(true);
    try {
      await onValidate(item.id, status, comment);
    } finally {
      setIsSubmitting(false);
      setIsCommentOpen(false);
    }
  };

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2'
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5'
  };

  // Si déjà validé, afficher le statut
  if (item.status !== 'pending') {
    return (
      <div className={cn("inline-flex flex-col gap-1", className)}>
        <div className={cn(
          "inline-flex items-center gap-1.5 rounded-full border font-medium",
          sizeClasses[size],
          item.status === 'valide' && "bg-green-100 text-green-800 border-green-200",
          item.status === 'rejete' && "bg-red-100 text-red-800 border-red-200",
          item.status === 'partiel' && "bg-yellow-100 text-yellow-800 border-yellow-200"
        )}>
          {item.status === 'valide' && <Check className={iconSizes[size]} />}
          {item.status === 'rejete' && <X className={iconSizes[size]} />}
          {item.status === 'partiel' && <HelpCircle className={iconSizes[size]} />}
          <span>
            {item.status === 'valide' && 'Validé'}
            {item.status === 'rejete' && 'Rejeté'}
            {item.status === 'partiel' && 'Partiel'}
          </span>
        </div>
        
        {showComment && item.commentaire && (
          <p className="text-xs text-gray-500 italic">
            "{item.commentaire}"
          </p>
        )}
        
        {showComment && item.validatedBy && (
          <p className="text-xs text-gray-400">
            par {item.validatedBy} {item.validatedAt && 
              `le ${item.validatedAt.toLocaleDateString('fr-FR')}`
            }
          </p>
        )}
      </div>
    );
  }

  // En attente de validation
  return (
    <div 
      className={cn("inline-flex flex-col gap-2", className)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Label */}
      <div className="text-sm text-gray-700">
        {item.label}
        {item.description && (
          <p className="text-xs text-gray-500 mt-0.5">{item.description}</p>
        )}
      </div>

      {/* Boutons de validation */}
      <div className={cn(
        "flex items-center gap-2 transition-opacity",
        isHovered ? 'opacity-100' : 'opacity-70'
      )}>
        <button
          onClick={() => handleValidate('valide')}
          disabled={isSubmitting}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-colors",
            "bg-green-100 text-green-700 hover:bg-green-200",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
          OUI
        </button>

        <button
          onClick={() => handleValidate('rejete')}
          disabled={isSubmitting}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-colors",
            "bg-red-100 text-red-700 hover:bg-red-200",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          <X className="w-4 h-4" />
          NON
        </button>

        <button
          onClick={() => handleValidate('partiel')}
          disabled={isSubmitting}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-colors",
            "bg-yellow-100 text-yellow-700 hover:bg-yellow-200",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          <HelpCircle className="w-4 h-4" />
          PARTIEL
        </button>

        {/* Bouton commentaire */}
        <button
          onClick={() => setIsCommentOpen(!isCommentOpen)}
          className={cn(
            "p-1.5 rounded-lg transition-colors",
            isCommentOpen ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'
          )}
          title="Ajouter un commentaire"
        >
          <MessageSquare className="w-4 h-4" />
        </button>
      </div>

      {/* Zone de commentaire */}
      {isCommentOpen && (
        <div className="mt-2 p-3 bg-gray-50 rounded-lg border">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Ajouter un commentaire (optionnel)..."
            className="w-full px-3 py-2 border rounded text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={2}
          />
        </div>
      )}
    </div>
  );
}

// ========== LISTE DE VALIDATIONS ==========

interface ValidationListProps {
  items: ValidationItem[];
  onValidate: (id: string, status: ValidationStatus, commentaire?: string) => Promise<void>;
  title?: string;
  className?: string;
}

export function ValidationList({ 
  items, 
  onValidate, 
  title,
  className 
}: ValidationListProps) {
  const [filter, setFilter] = useState<ValidationStatus | 'all'>('all');

  const filteredItems = filter === 'all' 
    ? items 
    : items.filter(item => item.status === filter);

  const stats = {
    total: items.length,
    pending: items.filter(i => i.status === 'pending').length,
    valide: items.filter(i => i.status === 'valide').length,
    rejete: items.filter(i => i.status === 'rejete').length,
    partiel: items.filter(i => i.status === 'partiel').length
  };

  return (
    <div className={cn("bg-white rounded-xl border", className)}>
      {/* Header */}
      {title && (
        <div className="px-4 py-3 border-b">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-gray-900">{title}</h3>
            <span className="text-sm text-gray-500">
              {stats.valide + stats.partiel}/{stats.total} validés
            </span>
          </div>
        </div>
      )}

      {/* Filtres */}
      <div className="px-4 py-2 border-b bg-gray-50">
        <div className="flex flex-wrap gap-2">
          {(['all', 'pending', 'valide', 'partiel', 'rejete'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={cn(
                "px-2 py-1 rounded text-xs font-medium transition-colors",
                filter === status 
                  ? "bg-gray-800 text-white" 
                  : "bg-white text-gray-600 hover:bg-gray-100"
              )}
            >
              {status === 'all' && `Tous (${stats.total})`}
              {status === 'pending' && `En attente (${stats.pending})`}
              {status === 'valide' && `Validés (${stats.valide})`}
              {status === 'partiel' && `Partiels (${stats.partiel})`}
              {status === 'rejete' && `Rejetés (${stats.rejete})`}
            </button>
          ))}
        </div>
      </div>

      {/* Liste */}
      <div className="divide-y">
        {filteredItems.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-500">
            Aucun élément à valider
          </div>
        ) : (
          filteredItems.map((item) => (
            <div key={item.id} className="px-4 py-3">
              <ValidationBadge
                item={item}
                onValidate={onValidate}
                showComment={true}
              />
            </div>
          ))
        )}
      </div>

      {/* Footer avec progression */}
      <div className="px-4 py-3 border-t bg-gray-50">
        <div className="flex items-center gap-2 text-sm">
          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-green-500 transition-all"
              style={{ 
                width: `${stats.total > 0 ? ((stats.valide + stats.partiel) / stats.total) * 100 : 0}%` 
              }}
            />
          </div>
          <span className="text-gray-600 whitespace-nowrap">
            {Math.round(stats.total > 0 ? ((stats.valide + stats.partiel) / stats.total) * 100 : 0)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ========== EXEMPLE D'UTILISATION ==========

export function ValidationExample() {
  const [items, setItems] = useState<ValidationItem[]>([
    {
      id: '1',
      label: 'Lier à l\'ouvrage: Béton Armé ?',
      description: 'L\'IA suggère de lier ce poste à la catégorie GROS_OEUVRE > Béton Armé',
      status: 'pending'
    },
    {
      id: '2',
      label: 'Prix de référence correct ?',
      description: 'Le prix unitaire de 850€/m3 est cohérent avec l\'historique',
      status: 'valide',
      commentaire: 'Confirmé avec le bureau d\'études',
      validatedBy: 'Jean Dupont',
      validatedAt: new Date()
    },
    {
      id: '3',
      label: 'Quantité estimée: 250m3 ?',
      description: 'L\'IA estime la quantité à 250m3 basé sur la surface',
      status: 'partiel',
      commentaire: 'À vérifier sur chantier'
    },
    {
      id: '4',
      label: 'Recommandation d\'ajustement: -15% ?',
      description: 'L\'IA suggère de réduire le prix de 15% pour être compétitif',
      status: 'pending'
    }
  ]);

  const handleValidate = async (id: string, status: ValidationStatus, commentaire?: string) => {
    // Simuler l'appel API
    await new Promise(resolve => setTimeout(resolve, 500));
    
    setItems(prev => prev.map(item => 
      item.id === id 
        ? { 
            ...item, 
            status, 
            commentaire,
            validatedBy: 'Utilisateur',
            validatedAt: new Date()
          }
        : item
    ));
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h2 className="text-xl font-bold mb-4">Validation des Suggestions IA</h2>
      <ValidationList
        title="Suggestions de l'Analyse Pricing"
        items={items}
        onValidate={handleValidate}
      />
    </div>
  );
}
