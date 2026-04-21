import { NextRequest, NextResponse } from 'next/server';
import { getChantierById, operationsCRF } from '@/lib/chantier-data';
import { ApiResponse } from '@/types/chantier';

// GET /api/chantiers/[id]/operations - Récupérer les opérations d'un chantier
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
    
    // Pour le prototype, retourner les opérations du CRF ou une liste vide
    const operations = id === 'chantier-crf-001' ? operationsCRF : [];
    
    // Trier par date (plus récent d'abord)
    const sortedOperations = [...operations].sort((a, b) => 
      new Date(b.date).getTime() - new Date(a.date).getTime()
    );
    
    const response: ApiResponse<any> = {
      success: true,
      data: sortedOperations,
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error('Erreur API opérations:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible de récupérer les opérations',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}

// POST /api/chantiers/[id]/operations - Ajouter une opération
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
    if (!body.description || !body.type || !body.source) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'Données invalides',
        message: 'Les champs description, type et source sont obligatoires',
      };
      return NextResponse.json(response, { status: 400 });
    }
    
    // Simuler la création
    const newOperation = {
      id: `op-${Date.now()}`,
      chantierId: id,
      description: body.description,
      type: body.type,
      date: body.date || new Date().toISOString(),
      source: body.source,
      sourceDetails: body.sourceDetails || `Ajout ${body.source} – ${new Date().toLocaleDateString('fr-FR')}`,
      statut: 'en_attente',
      montant: body.montant,
      unite: body.unite,
      quantite: body.quantite,
      commentaire: body.commentaire || '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    const response: ApiResponse<any> = {
      success: true,
      data: newOperation,
      message: 'Opération ajoutée avec succès',
    };
    
    return NextResponse.json(response, { status: 201 });
    
  } catch (error) {
    console.error('Erreur création opération:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible d\'ajouter l\'opération',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}