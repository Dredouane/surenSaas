import { NextRequest, NextResponse } from 'next/server';
import { getChantierById } from '@/lib/chantier-data';
import { ApiResponse } from '@/types/chantier';

// GET /api/chantiers/[id] - Récupérer un chantier par ID
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
    
    const chantier = getChantierById(id);
    
    if (!chantier) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'Non trouvé',
        message: `Chantier avec l'ID ${id} non trouvé`,
      };
      return NextResponse.json(response, { status: 404 });
    }
    
    const response: ApiResponse<any> = {
      success: true,
      data: chantier,
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error('Erreur API chantier détail:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible de récupérer les détails du chantier',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}

// PUT /api/chantiers/[id] - Mettre à jour un chantier
export async function PUT(
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
    
    // Simuler la mise à jour
    const chantierExistant = getChantierById(id);
    
    if (!chantierExistant) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'Non trouvé',
        message: `Chantier avec l'ID ${id} non trouvé`,
      };
      return NextResponse.json(response, { status: 404 });
    }
    
    // Calculer les nouvelles valeurs
    const montantRevise = (body.montantBase || chantierExistant.montantBase) + 
                         (body.tsAvenants || chantierExistant.tsAvenants);
    
    const updatedChantier = {
      ...chantierExistant,
      ...body,
      montantRevise,
      updatedAt: new Date().toISOString(),
    };
    
    const response: ApiResponse<any> = {
      success: true,
      data: updatedChantier,
      message: 'Chantier mis à jour avec succès',
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error('Erreur mise à jour chantier:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible de mettre à jour le chantier',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}

// DELETE /api/chantiers/[id] - Supprimer un chantier
export async function DELETE(
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
    
    // Simuler la suppression
    const chantierExistant = getChantierById(id);
    
    if (!chantierExistant) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'Non trouvé',
        message: `Chantier avec l'ID ${id} non trouvé`,
      };
      return NextResponse.json(response, { status: 404 });
    }
    
    const response: ApiResponse<null> = {
      success: true,
      message: 'Chantier supprimé avec succès',
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error('Erreur suppression chantier:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible de supprimer le chantier',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}