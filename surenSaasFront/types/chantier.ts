export type ChantierStatut = 'en_cours' | 'termine' | 'en_attente' | 'cloture';
export type OperationType = 'demolition' | 'nettoyage' | 'pose_bso' | 'commande' | 'autre' | 'achat_materiel' | 'sous_traitance';
export type OperationSource = 'telegram_voice' | 'telegram_photo' | 'telegram_text' | 'telegram_pdf' | 'manuel' | 'email';
export type OperationStatut = 'en_attente' | 'valide' | 'rejete';
export type AuditAction = 'creation' | 'modification' | 'validation' | 'rejet' | 'suppression';

// Nouveaux types pour les extensions
export type ReceptionStatut = 'planifiee' | 'en_cours' | 'terminee' | 'annulee';
export type ReceptionType = 'livraison' | 'validation' | 'probleme' | 'suivi';
export type TacheStatut = 'en_attente' | 'en_cours' | 'terminee' | 'annulee';
export type SituationStatut = 'ouverte' | 'validee' | 'transmise' | 'payee';
export type TacheType = 'information' | 'action' | 'validation' | 'rapport';
export type TacheSource = 'direction' | 'systeme' | 'client';
export type TachePriorite = 'basse' | 'moyenne' | 'haute';
export type RessourceType = 'homme' | 'machine';
export type PeriodePointage = 'matin' | 'apres_midi' | 'journee';
export type NotificationType = 'tache' | 'reception' | 'pointage' | 'validation' | 'alerte' | 'info' | 'urgence';

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
  statut?: SituationStatut;
  type?: string;
  periodeDebut?: string;
  periodeFin?: string;
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
  invoiceId?: string;
  statut?: 'en_attente' | 'validee' | 'rejetee';
  validePar?: string;
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
  receptions: Reception[];
  taches: Tache[];
  pointages: Pointage[];
  notifications: Notification[];
}

// Nouvelles interfaces pour les extensions

export interface Reception {
  id: string;
  chantierId: string;
  date: Date | string;
  type: ReceptionType;
  statut: ReceptionStatut;
  participants: string[];
  ordreDuJour: string;
  decisions: string;
  pointsARegler: string;
  documents: string[];
  createdAt: Date | string;
  updatedAt: Date | string;
}

export interface TacheReception {
  id: string;
  receptionId: string;
  description: string;
  assigneeId: string;
  assigneeName: string;
  echeance?: Date | string;
  statut: TacheStatut;
  priorite: TachePriorite;
  commentaires?: string;
  createdAt: Date | string;
  updatedAt: Date | string;
}

export interface Tache {
  id: string;
  chantierId?: string;
  titre: string;
  description: string;
  type: TacheType;
  source: TacheSource;
  createurId: string;
  createurNom: string;
  assigneeId: string;
  assigneeNom: string;
  echeance?: Date | string;
  statut: TacheStatut;
  priorite: TachePriorite;
  reponse?: string;
  documents: string[];
  notifications: Notification[];
  createdAt: Date | string;
  updatedAt: Date | string;
}

export interface Ressource {
  id: string;
  nom: string;
  type: RessourceType;
  specialite?: string;
  disponible: boolean;
  chantierId?: string;
  indisponibleJusquau?: Date | string;
  raisonIndisponibilite?: string;
  createdAt: Date | string;
  updatedAt: Date | string;
}

export interface Pointage {
  id: string;
  date: Date | string;
  chantierId: string;
  conducteurId: string;
  ressources: {
    ressourceId: string;
    ressourceNom: string;
    type: RessourceType;
    periode: PeriodePointage;
    heuresPrevues?: number;
  }[];
  commentaires?: string;
  validePar?: string;
  valideLe?: Date | string;
  createdAt: Date | string;
  updatedAt: Date | string;
}

export interface Notification {
  id: string;
  userId: string;
  type: NotificationType;
  entityType: 'chantier' | 'tache' | 'reception' | 'pointage' | 'operation' | 'situation' | 'depense';
  entityId: string;
  titre: string;
  message: string;
  url?: string;
  statut: 'envoyee' | 'lue' | 'validee' | 'refusee' | 'en_attente';
  telegramMessageId?: string;
  createdAt: Date | string;
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
  statut?: SituationStatut;
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

// Nouveaux types pour les formulaires

export interface CreateReceptionInput {
  chantierId: string;
  date: Date | string;
  type: ReceptionType;
  participants: string[];
  ordreDuJour: string;
  decisions?: string;
  pointsARegler?: string;
  documents?: string[];
}

export interface CreateTacheInput {
  chantierId?: string;
  titre: string;
  description: string;
  type: TacheType;
  assigneeId: string;
  echeance?: Date | string;
  priorite: TachePriorite;
  documents?: string[];
}

export interface UpdateTacheInput {
  id: string;
  reponse?: string;
  statut?: TacheStatut;
  commentaires?: string;
}

export interface CreatePointageInput {
  date: Date | string;
  chantierId: string;
  ressources: {
    ressourceId: string;
    periode: PeriodePointage;
    heuresPrevues?: number;
  }[];
  commentaires?: string;
}

export interface CreateNotificationInput {
  userId: string;
  type: NotificationType;
  entityType: 'chantier' | 'tache' | 'reception' | 'pointage' | 'operation' | 'situation' | 'depense';
  entityId: string;
  titre: string;
  message: string;
  url?: string;
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