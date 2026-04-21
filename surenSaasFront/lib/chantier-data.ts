import {
  Chantier,
  Situation,
  Depense,
  Operation,
  AuditEntry,
  ChantierWithDetails,
} from '@/types/chantier';

// Générer un ID unique
const generateId = () => Math.random().toString(36).substring(2) + Date.now().toString(36);

// Date actuelle pour les timestamps
const now = new Date().toISOString();

// Données du chantier CRF basées sur l'Excel
export const chantierCRF: Chantier = {
  id: 'chantier-crf-001',
  ref: 'CRF',
  nom: 'CRF',
  adresse: '6/8 rue Entroncamento 94350 Villiers-sur-Marne',
  conducteur: 'Mohsan MAHMOOD',
  montantBase: 929613.5,
  tsAvenants: 88498.82,
  montantRevise: 1018112.32,
  situationsFacturees: 900789.04,
  pourcentageFacture: 88.48,
  totalDepenses: 613254.33,
  margeBrute: 287534.71,
  soldeAFacturer: 117323.28,
  statut: 'en_cours',
  priorite: 0,
  dateOPRPrevue: '',
  dateOPRRealisee: '',
  commentaires: 'Chantier de rénovation complète - Suivi financier Excel',
  createdAt: '2024-01-15T00:00:00Z',
  updatedAt: now,
};

// Situations facturées du chantier CRF (11 lignes)
export const situationsCRF: Situation[] = [
  {
    id: 'sit-001',
    chantierId: 'chantier-crf-001',
    date: '2025-05-23',
    numero: 1,
    libelle: 'Situation N° 01',
    montant: 55240.18,
    reglementObservation: '',
    createdAt: '2025-05-23T00:00:00Z',
    updatedAt: '2025-05-23T00:00:00Z',
  },
  {
    id: 'sit-002',
    chantierId: 'chantier-crf-001',
    date: '2025-06-23',
    numero: 2,
    libelle: 'Situation N° 02',
    montant: 84978.08,
    reglementObservation: '',
    createdAt: '2025-06-23T00:00:00Z',
    updatedAt: '2025-06-23T00:00:00Z',
  },
  {
    id: 'sit-003',
    chantierId: 'chantier-crf-001',
    date: '2025-07-21',
    numero: 3,
    libelle: 'Situation N° 03',
    montant: 129012.13,
    reglementObservation: '',
    createdAt: '2025-07-21T00:00:00Z',
    updatedAt: '2025-07-21T00:00:00Z',
  },
  {
    id: 'sit-004',
    chantierId: 'chantier-crf-001',
    date: '2025-08-29',
    numero: 4,
    libelle: 'Situation N° 04',
    montant: 65246.58,
    reglementObservation: '',
    createdAt: '2025-08-29T00:00:00Z',
    updatedAt: '2025-08-29T00:00:00Z',
  },
  {
    id: 'sit-005',
    chantierId: 'chantier-crf-001',
    date: '2025-09-29',
    numero: 5,
    libelle: 'Situation N° 05',
    montant: 56104.41,
    reglementObservation: '',
    createdAt: '2025-09-29T00:00:00Z',
    updatedAt: '2025-09-29T00:00:00Z',
  },
  {
    id: 'sit-006',
    chantierId: 'chantier-crf-001',
    date: '2025-11-05',
    numero: 6,
    libelle: 'Situation N° 06',
    montant: 75411.35,
    reglementObservation: '',
    createdAt: '2025-11-05T00:00:00Z',
    updatedAt: '2025-11-05T00:00:00Z',
  },
  {
    id: 'sit-007',
    chantierId: 'chantier-crf-001',
    date: '2025-12-05',
    numero: 7,
    libelle: 'Situation N° 07',
    montant: 61478.68,
    reglementObservation: '',
    createdAt: '2025-12-05T00:00:00Z',
    updatedAt: '2025-12-05T00:00:00Z',
  },
  {
    id: 'sit-008',
    chantierId: 'chantier-crf-001',
    date: '2025-12-26',
    numero: 8,
    libelle: 'Situation N° 08',
    montant: 107726.24,
    reglementObservation: '',
    createdAt: '2025-12-26T00:00:00Z',
    updatedAt: '2025-12-26T00:00:00Z',
  },
  {
    id: 'sit-009',
    chantierId: 'chantier-crf-001',
    date: '2026-01-21',
    numero: 9,
    libelle: 'Situation N° 09',
    montant: 71211.91,
    reglementObservation: '',
    createdAt: '2026-01-21T00:00:00Z',
    updatedAt: '2026-01-21T00:00:00Z',
  },
  {
    id: 'sit-010',
    chantierId: 'chantier-crf-001',
    date: '2026-02-20',
    numero: 10,
    libelle: 'Situation N° 10',
    montant: 107760.65,
    reglementObservation: '',
    createdAt: '2026-02-20T00:00:00Z',
    updatedAt: '2026-02-20T00:00:00Z',
  },
  {
    id: 'sit-011',
    chantierId: 'chantier-crf-001',
    date: '2026-04-02',
    numero: 11,
    libelle: 'Situation N° 11',
    montant: 86618.83,
    reglementObservation: '',
    createdAt: '2026-04-02T00:00:00Z',
    updatedAt: '2026-04-02T00:00:00Z',
  },
];

// Dépenses du chantier CRF (13 lignes - données exactes Excel)
export const depensesCRF: Depense[] = [
  {
    id: 'dep-001',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'ART CONCEPT',
    categorie: 'sous_traitant',
    description: 'Achat matériels pour Fehmi PointP',
    montant: 41663.61,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-002',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'ART CONCEPT',
    categorie: 'sous_traitant',
    description: 'Achats divers',
    montant: 58218.97,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-003',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'ART CONCEPT',
    categorie: 'sous_traitant',
    description: 'Avances sur situations (virements)',
    montant: 281256.96,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-004',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'BOB RENOV',
    categorie: 'fournisseur',
    description: 'Mext',
    montant: 61366.99,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-005',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'PCCR',
    categorie: 'sous_traitant',
    description: 'Plomberie CVCPB',
    montant: 48742.0,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-006',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'B6 CONCEPT',
    categorie: 'fournisseur',
    description: 'BET',
    montant: 5850.0,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-007',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'AA Ingénierie',
    categorie: 'fournisseur',
    description: 'BET',
    montant: 2900.0,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-008',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'Polybat',
    categorie: 'fournisseur',
    description: 'RAVALEMENT',
    montant: 38844.0,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-009',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'SENBAIE',
    categorie: 'fournisseur',
    description: 'BSO',
    montant: 19000.0,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-010',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'Copypage',
    categorie: 'fournisseur',
    description: 'IMPRESSION PLANS',
    montant: 200.0,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-011',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'FULFILER',
    categorie: 'fournisseur',
    description: 'IMPRESSION PLANS',
    montant: 265.0,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-012',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'EDM',
    categorie: 'fournisseur',
    description: 'INSTALLATION DE CHANTIER',
    montant: 4546.8,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
  {
    id: 'dep-013',
    chantierId: 'chantier-crf-001',
    date: '2026-04-17',
    fournisseur: 'MOHSAN MAHMOOD',
    categorie: 'conducteur',
    description: 'SUIVI DE CHANTIER',
    montant: 50400.0,
    factureRef: '',
    createdAt: '2026-04-17T00:00:00Z',
    updatedAt: '2026-04-17T00:00:00Z',
  },
];

// Opérations/Tâches du chantier CRF (exemples pour démo HITL)
export const operationsCRF: Operation[] = [
  {
    id: 'op-001',
    chantierId: 'chantier-crf-001',
    description: 'Démolition mur est',
    type: 'demolition',
    date: '2026-04-15T09:42:00Z',
    source: 'telegram_voice',
    sourceDetails: 'Voice Telegram – Mohsan – 15/04/2026 09:42',
    statut: 'valide',
    validePar: 'Gérant Principal',
    valideLe: '2026-04-15T10:05:00Z',
    commentaire: 'Travail conforme aux plans',
    createdAt: '2026-04-15T09:42:00Z',
    updatedAt: '2026-04-15T10:05:00Z',
  },
  {
    id: 'op-002',
    chantierId: 'chantier-crf-001',
    description: 'Nettoyage façade sud',
    type: 'nettoyage',
    date: '2026-04-16T14:30:00Z',
    source: 'telegram_text',
    sourceDetails: 'Texte Telegram – Mohsan – 16/04/2026 14:30',
    statut: 'valide',
    validePar: 'Gérant Principal',
    valideLe: '2026-04-16T15:15:00Z',
    commentaire: '180 m² nettoyés',
    quantite: 180,
    unite: 'm²',
    createdAt: '2026-04-16T14:30:00Z',
    updatedAt: '2026-04-16T15:15:00Z',
  },
  {
    id: 'op-003',
    chantierId: 'chantier-crf-001',
    description: 'Commande 3 échafaudages chez PointP',
    type: 'commande',
    date: '2026-04-17T11:20:00Z',
    source: 'telegram_voice',
    sourceDetails: 'Voice Telegram – Mohsan – 17/04/2026 11:20',
    statut: 'valide',
    validePar: 'Gérant Principal',
    valideLe: '2026-04-17T12:00:00Z',
    commentaire: 'Pour livraison le 20/04',
    montant: 12000,
    quantite: 3,
    unite: 'unités',
    createdAt: '2026-04-17T11:20:00Z',
    updatedAt: '2026-04-17T12:00:00Z',
  },
  {
    id: 'op-004',
    chantierId: 'chantier-crf-001',
    description: 'Pose de 4 BSO (Blocs Sécurité Ouvrants)',
    type: 'pose_bso',
    date: '2026-04-18T16:45:00Z',
    source: 'telegram_photo',
    sourceDetails: 'Photo Telegram – Mohsan – 18/04/2026 16:45',
    statut: 'en_attente',
    commentaire: 'En attente de validation du gérant',
    quantite: 4,
    unite: 'unités',
    createdAt: '2026-04-18T16:45:00Z',
    updatedAt: '2026-04-18T16:45:00Z',
  },
  {
    id: 'op-005',
    chantierId: 'chantier-crf-001',
    description: 'Réception bon de livraison matériaux',
    type: 'achat_materiel',
    date: '2026-04-19T10:15:00Z',
    source: 'telegram_pdf',
    sourceDetails: 'PDF Telegram – Mohsan – 19/04/2026 10:15',
    statut: 'en_attente',
    commentaire: 'Document à vérifier',
    createdAt: '2026-04-19T10:15:00Z',
    updatedAt: '2026-04-19T10:15:00Z',
  },
  {
    id: 'op-006',
    chantierId: 'chantier-crf-001',
    description: 'Préparation chantier pour peinture',
    type: 'autre',
    date: '2026-04-20T08:30:00Z',
    source: 'manuel',
    sourceDetails: 'Ajout manuel – Gérant – 20/04/2026 08:30',
    statut: 'valide',
    validePar: 'Gérant Principal',
    valideLe: '2026-04-20T08:30:00Z',
    commentaire: 'À faire avant le 22/04',
    createdAt: '2026-04-20T08:30:00Z',
    updatedAt: '2026-04-20T08:30:00Z',
  },
];

// Audit trail pour le chantier CRF
export const auditTrailCRF: AuditEntry[] = [
  {
    id: 'audit-001',
    entityType: 'chantier',
    entityId: 'chantier-crf-001',
    timestamp: '2024-01-15T10:00:00Z',
    action: 'creation',
    userId: 'user-admin-001',
    userName: 'Admin System',
    details: 'Création du chantier CRF',
  },
  {
    id: 'audit-002',
    entityType: 'operation',
    entityId: 'op-001',
    timestamp: '2026-04-15T10:05:00Z',
    action: 'validation',
    userId: 'user-manager-001',
    userName: 'Gérant Principal',
    details: 'Validation de l\'opération "Démolition mur est"',
    changes: {
      statut: { old: 'en_attente', new: 'valide' },
      validePar: { old: undefined, new: 'Gérant Principal' },
      valideLe: { old: undefined, new: '2026-04-15T10:05:00Z' },
    },
  },
  {
    id: 'audit-003',
    entityType: 'depense',
    entityId: 'dep-001',
    timestamp: '2026-04-15T11:30:00Z',
    action: 'creation',
    userId: 'user-mohsan-001',
    userName: 'Mohsan MAHMOOD',
    details: 'Ajout de la dépense "Achat matériels pour Fehmi PointP"',
  },
  {
    id: 'audit-004',
    entityType: 'situation',
    entityId: 'sit-011',
    timestamp: '2026-03-20T14:20:00Z',
    action: 'creation',
    userId: 'user-admin-001',
    userName: 'Admin System',
    details: 'Ajout de la situation N° 11',
  },
];

// Chantiers supplémentaires pour le tableau de suivi
export const autresChantiers: Chantier[] = [
  {
    id: 'chantier-ch014-001',
    ref: 'CH-014',
    nom: 'Rénovation Appartement Paris 15',
    adresse: '12 rue de Vaugirard, 75015 Paris',
    conducteur: 'Jean DUPONT',
    montantBase: 125000,
    tsAvenants: 15000,
    montantRevise: 140000,
    situationsFacturees: 85000,
    pourcentageFacture: 60.71,
    totalDepenses: 95000,
    margeBrute: 45000,
    soldeAFacturer: 55000,
    statut: 'en_cours',
    priorite: 1,
    dateOPRPrevue: '2026-06-30',
    commentaires: 'Rénovation complète appartement 80m²',
    createdAt: '2024-02-10T00:00:00Z',
    updatedAt: now,
  },
  {
    id: 'chantier-ch015-001',
    ref: 'CH-015',
    nom: 'Extension Maison Versailles',
    adresse: '45 avenue de Paris, 78000 Versailles',
    conducteur: 'Marie LEROY',
    montantBase: 285000,
    tsAvenants: 35000,
    montantRevise: 320000,
    situationsFacturees: 220000,
    pourcentageFacture: 68.75,
    totalDepenses: 195000,
    margeBrute: 125000,
    soldeAFacturer: 100000,
    statut: 'en_cours',
    priorite: 2,
    dateOPRPrevue: '2026-08-15',
    commentaires: 'Extension + rénovation cuisine',
    createdAt: '2024-03-05T00:00:00Z',
    updatedAt: now,
  },
  {
    id: 'chantier-ch016-001',
    ref: 'CH-016',
    nom: 'Bureaux Société Tech',
    adresse: 'Tour Montparnasse, 75014 Paris',
    conducteur: 'Pierre MARTIN',
    montantBase: 450000,
    tsAvenants: 50000,
    montantRevise: 500000,
    situationsFacturees: 400000,
    pourcentageFacture: 80.00,
    totalDepenses: 320000,
    margeBrute: 180000,
    soldeAFacturer: 100000,
    statut: 'en_cours',
    priorite: 0,
    dateOPRPrevue: '2026-05-20',
    dateOPRRealisee: '2026-05-18',
    commentaires: 'Aménagement bureaux open space 500m²',
    createdAt: '2024-01-20T00:00:00Z',
    updatedAt: now,
  },
  {
    id: 'chantier-ch017-001',
    ref: 'CH-017',
    nom: 'Rénovation Hôtel Particulier',
    adresse: '8 rue de la Paix, 75002 Paris',
    conducteur: 'Sophie DURAND',
    montantBase: 750000,
    tsAvenants: 125000,
    montantRevise: 875000,
    situationsFacturees: 600000,
    pourcentageFacture: 68.57,
    totalDepenses: 520000,
    margeBrute: 355000,
    soldeAFacturer: 275000,
    statut: 'en_attente',
    priorite: 3,
    dateOPRPrevue: '2026-09-30',
    commentaires: 'En attente de permis de construire',
    createdAt: '2024-04-01T00:00:00Z',
    updatedAt: now,
  },
  {
    id: 'chantier-ch018-001',
    ref: 'CH-018',
    nom: 'Magasin Commercial',
    adresse: 'Centre Commercial, 93100 Montreuil',
    conducteur: 'Thomas BERNARD',
    montantBase: 320000,
    tsAvenants: 30000,
    montantRevise: 350000,
    situationsFacturees: 350000,
    pourcentageFacture: 100.00,
    totalDepenses: 280000,
    margeBrute: 70000,
    soldeAFacturer: 0,
    statut: 'termine',
    priorite: 0,
    dateOPRPrevue: '2026-03-15',
    dateOPRRealisee: '2026-03-10',
    commentaires: 'Livré avec 5 jours d\'avance',
    createdAt: '2024-02-15T00:00:00Z',
    updatedAt: now,
  },
];

// Tous les chantiers
export const tousLesChantiers: Chantier[] = [chantierCRF, ...autresChantiers];

// Chantier CRF avec tous les détails
export const chantierCRFComplet: ChantierWithDetails = {
  ...chantierCRF,
  situations: situationsCRF,
  depenses: depensesCRF,
  operations: operationsCRF,
  auditTrail: auditTrailCRF,
};

// Fonctions utilitaires pour les calculs
export function calculerPourcentageFacture(montantRevise: number, situationsFacturees: number): number {
  if (montantRevise === 0) return 0;
  return (situationsFacturees / montantRevise) * 100;
}

export function calculerMargeBrute(montantRevise: number, totalDepenses: number): number {
  return montantRevise - totalDepenses;
}

export function calculerSoldeAFacturer(montantRevise: number, situationsFacturees: number): number {
  return montantRevise - situationsFacturees;
}

export function calculerTotalSituations(situations: Situation[]): number {
  return situations.reduce((total, situation) => total + situation.montant, 0);
}

export function calculerTotalDepenses(depenses: Depense[]): number {
  return depenses.reduce((total, depense) => total + depense.montant, 0);
}

export function calculerMargePourcentage(montantRevise: number, totalDepenses: number): number {
  if (montantRevise === 0) return 0;
  return ((montantRevise - totalDepenses) / montantRevise) * 100;
}

// Fonction pour obtenir un chantier par ID
export function getChantierById(id: string): ChantierWithDetails | undefined {
  if (id === 'chantier-crf-001') {
    return chantierCRFComplet;
  }
  
  // Pour les autres chantiers, retourner une structure basique
  const chantier = autresChantiers.find(c => c.id === id);
  if (chantier) {
    return {
      ...chantier,
      situations: [],
      depenses: [],
      operations: [],
      auditTrail: [],
    };
  }
  
  return undefined;
}

// Fonction pour filtrer les chantiers
export function filtrerChantiers(
  chantiers: Chantier[],
  filters: {
    statut?: string;
    priorite?: number;
    conducteur?: string;
    search?: string;
  }
): Chantier[] {
  return chantiers.filter(chantier => {
    if (filters.statut && chantier.statut !== filters.statut) return false;
    if (filters.priorite !== undefined && chantier.priorite !== filters.priorite) return false;
    if (filters.conducteur && !chantier.conducteur.toLowerCase().includes(filters.conducteur.toLowerCase())) return false;
    
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        chantier.ref.toLowerCase().includes(searchLower) ||
        chantier.nom.toLowerCase().includes(searchLower) ||
        chantier.adresse.toLowerCase().includes(searchLower) ||
        chantier.conducteur.toLowerCase().includes(searchLower)
      );
    }
    
    return true;
  });
}