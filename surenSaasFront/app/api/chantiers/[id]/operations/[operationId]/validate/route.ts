import { NextRequest, NextResponse } from 'next/server';
import { getChantierById, operationsCRF } from '@/lib/chantier-data';
import { ApiResponse } from '@/types/chantier';

// POST /api/chantiers/[id]/operations/[operationId]/validate - Valider/rejeter une opération
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string; operationId: string } }
) {
  try {
    const { id, operationId } = params;
    const body = await request.json();
    
    if (!id || !operationId) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'ID manquant',
        message: 'L\'ID du chantier et de l\'opération sont requis',
      };
      return NextResponse.json(response, { status: 400 });
    }
    
    if (!body.validePar || !body.statut) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'Données invalides',
        message: 'Les champs validePar et statut sont obligatoires',
      };
      return NextResponse.json(response, { status: 400 });
    }
    
    // Pour le prototype, simuler la validation
    const operation = operationsCRF.find(op => op.id === operationId);
    
    if (!operation) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'Non trouvé',
        message: `Opération avec l'ID ${operationId} non trouvée`,
      };
      return NextResponse.json(response, { status: 404 });
    }
    
    // Simuler la mise à jour
    const updatedOperation = {
      ...operation,
      statut: body.statut,
      validePar: body.validePar,
      valideLe: new Date().toISOString(),
      commentaire: body.commentaire || operation.commentaire,
      updatedAt: new Date().toISOString(),
    };
    
    const response: ApiResponse<any> = {
      success: true,
      data: updatedOperation,
      message: `Opération ${body.statut === 'valide' ? 'validée' : 'rejetée'} avec succès`,
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error('Erreur validation opération:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible de valider l\'opération',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}