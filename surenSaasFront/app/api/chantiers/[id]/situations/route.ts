import { NextRequest, NextResponse } from 'next/server';
import { getChantierById, situationsCRF } from '@/lib/chantier-data';
import { ApiResponse } from '@/types/chantier';

// GET /api/chantiers/[id]/situations - Récupérer les situations d'un chantier
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const id = params.id;
    
    if (!id) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'ID manquant',
        message: 'L\'ID du chantier est requis',
      };
      return NextResponse.json(response, { status: 400 });
    }
    
    // Pour le prototype, retourner les situations du CRF ou une liste vide
    const situations = id === 'chantier-crf-001' ? situationsCRF : [];
    
    const response: ApiResponse<any> = {
      success: true,
      data: situations,
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error('Erreur API situations:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible de récupérer les situations',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}

// POST /api/chantiers/[id]/situations - Ajouter une situation
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const id = params.id;
    const body = await request.json();
    
    if (!id) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'ID manquant',
        message: 'L\'ID du chantier est requis',
      };
      return NextResponse.json(response, { status: 400 });
    }
    
    // Validation
    if (!body.date || !body.libelle || !body.montant) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'Données invalides',
        message: 'Les champs date, libelle et montant sont obligatoires',
      };
      return NextResponse.json(response, { status: 400 });
    }
    
    // Simuler la création
    const newSituation = {
      id: `sit-${Date.now()}`,
      chantierId: id,
      date: body.date,
      numero: body.numero || 1,
      libelle: body.libelle,
      montant: body.montant,
      reglementObservation: body.reglementObservation || '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    const response: ApiResponse<any> = {
      success: true,
      data: newSituation,
      message: 'Situation ajoutée avec succès',
    };
    
    return NextResponse.json(response, { status: 201 });
    
  } catch (error) {
    console.error('Erreur création situation:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible d\'ajouter la situation',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}