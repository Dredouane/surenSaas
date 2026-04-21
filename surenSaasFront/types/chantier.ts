export type ChantierStatut = 'en_cours' | 'termine' | 'en_attente' | 'cloture';
export type OperationType = 'demolition' | 'nettoyage' | 'pose_bso' | 'commande' | 'autre' | 'achat_materiel' | 'sous_traitance';
export type OperationSource = 'telegram_voice' | 'telegram_photo' | 'telegram_text' | 'telegram_pdf' | 'manuel' | 'email';
export type OperationStatut = 'en_attente' | 'valide' | 'rejete';
export type AuditAction = 'creation' | 'modification' | 'validation' | 'rejet' | 'suppression';

export interface Chantier {
  id: string;
  ref: string;
  nom: string;
  adresse: string;
  conducteur: string;
  montantBase: number;
  tsAvenants: number;
  montantRevise: number;
  situationsFacturees: number;
  pourcentageFacture: number;
  totalDepenses: number;
  margeBrute: number;
  soldeAFacturer: number;
  statut: ChantierStatut;
  priorite: number;
  dateOPRPrevue?: Date | string;
  dateOPRRealisee?: Date | string;
  commentaires?: string;
  createdAt: Date | string;
  updatedAt: Date | string;
}

export interface Situation {
  id: string;
  chantierId: string;
  date: Date | string;
  numero: number;
  libelle: string;
  montant: number;
  reglementObservation?: string;
  createdAt: Date | string;
  updatedAt: Date | string;
}

export interface Depense {
  id: string;
  chantierId: string;
  date: Date | string;
  fournisseur: string;
  categorie: 'sous_traitant' | 'fournisseur' | 'autre' | 'conducteur';
  description: string;
  montant: number;
  factureRef?: string;
  createdAt: Date | string;
  updatedAt: Date | string;
}

export interface Operation {
  id: string;
  chantierId: string;
  description: string;
  type: OperationType;
  date: Date | string;
  source: OperationSource;
  sourceDetails: string;
  statut: OperationStatut;
  validePar?: string;
  valideLe?: Date | string;
  commentaire?: string;
  montant?: number;
  unite?: string;
  quantite?: number;
  createdAt: Date | string;
  updatedAt: Date | string;
}

export interface AuditEntry {
  id: string;
  entityType: 'chantier' | 'situation' | 'depense' | 'operation';
  entityId: string;
  timestamp: Date | string;
  action: AuditAction;
  userId: string;
  userName: string;
  details: string;
  changes?: Record<string, { old: any; new: any }>;
}

export interface ChantierWithDetails extends Chantier {
  situations: Situation[];
  depenses: Depense[];
  operations: Operation[];
  auditTrail: AuditEntry[];
}

// Types pour les formulaires
export interface CreateChantierInput {
  ref: string;
  nom: string;
  adresse: string;
  conducteur: string;
  montantBase: number;
  tsAvenants: number;
  statut: ChantierStatut;
  priorite: number;
  dateOPRPrevue?: Date | string;
  commentaires?: string;
}

export interface UpdateChantierInput extends Partial<CreateChantierInput> {
  id: string;
}

export interface CreateSituationInput {
  chantierId: string;
  date: Date | string;
  numero: number;
  libelle: string;
  montant: number;
  reglementObservation?: string;
}

export interface CreateDepenseInput {
  chantierId: string;
  date: Date | string;
  fournisseur: string;
  categorie: 'sous_traitant' | 'fournisseur' | 'autre';
  description: string;
  montant: number;
  factureRef?: string;
}

export interface CreateOperationInput {
  chantierId: string;
  description: string;
  type: OperationType;
  date: Date | string;
  source: OperationSource;
  sourceDetails: string;
  montant?: number;
  unite?: string;
  quantite?: number;
  commentaire?: string;
}

export interface ValidateOperationInput {
  operationId: string;
  validePar: string;
  commentaire?: string;
  statut: OperationStatut;
}

// Types pour les réponses API
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Types pour les filtres
export interface ChantierFilters {
  statut?: ChantierStatut;
  priorite?: number;
  conducteur?: string;
  search?: string;
  dateFrom?: Date | string;
  dateTo?: Date | string;
}

// Types pour les calculs
export interface ChantierCalculations {
  pourcentageFacture: number;
  margeBrute: number;
  soldeAFacturer: number;
  totalSituations: number;
  totalDepenses: number;
  margePourcentage: number;
}