import { Situation, Depense } from '@/types/chantier';

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

// Fonction pour obtenir les tâches d'une réception
export function getTachesDeReception(receptionId: string): any[] {
  return [];
}