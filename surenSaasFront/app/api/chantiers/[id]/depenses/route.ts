import { NextRequest, NextResponse } from 'next/server';
import { getChantierById, depensesCRF } from '@/lib/chantier-data';
import { ApiResponse } from '@/types/chantier';

// GET /api/chantiers/[id]/depenses - Récupérer les dépenses d'un chantier
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
    
    // Pour le prototype, retourner les dépenses du CRF ou une liste vide
    const depenses = id === 'chantier-crf-001' ? depensesCRF : [];
    
    const response: ApiResponse<any> = {
      success: true,
      data: depenses,
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error('Erreur API dépenses:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible de récupérer les dépenses',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}

// POST /api/chantiers/[id]/depenses - Ajouter une dépense
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
    if (!body.date || !body.fournisseur || !body.description || !body.montant) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'Données invalides',
        message: 'Les champs date, fournisseur, description et montant sont obligatoires',
      };
      return NextResponse.json(response, { status: 400 });
    }
    
    // Simuler la création
    const newDepense = {
      id: `dep-${Date.now()}`,
      chantierId: id,
      date: body.date,
      fournisseur: body.fournisseur,
      categorie: body.categorie || 'autre',
      description: body.description,
      montant: body.montant,
      factureRef: body.factureRef || '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    const response: ApiResponse<any> = {
      success: true,
      data: newDepense,
      message: 'Dépense ajoutée avec succès',
    };
    
    return NextResponse.json(response, { status: 201 });
    
  } catch (error) {
    console.error('Erreur création dépense:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible d\'ajouter la dépense',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}