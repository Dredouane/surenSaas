import { NextRequest, NextResponse } from 'next/server';
import {
  tousLesChantiers,
  chantierCRFComplet,
  getChantierById,
  filtrerChantiers,
} from '@/lib/chantier-data';
import { ChantierFilters, ApiResponse, PaginatedResponse } from '@/types/chantier';

// GET /api/chantiers - Liste des chantiers avec filtres
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    
    // Récupérer les paramètres de filtrage
    const filters: ChantierFilters = {
      statut: searchParams.get('statut') as any || undefined,
      priorite: searchParams.get('priorite') ? parseInt(searchParams.get('priorite')!) : undefined,
      conducteur: searchParams.get('conducteur') || undefined,
      search: searchParams.get('search') || undefined,
    };
    
    // Pagination
    const page = parseInt(searchParams.get('page') || '1');
    const pageSize = parseInt(searchParams.get('pageSize') || '10');
    
    // Filtrer les chantiers
    let filteredChantiers = filtrerChantiers(tousLesChantiers, filters);
    
    // Trier par priorité (desc) puis par date de mise à jour (desc)
    filteredChantiers.sort((a, b) => {
      if (a.priorite !== b.priorite) return b.priorite - a.priorite;
      return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
    });
    
    // Pagination
    const startIndex = (page - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const paginatedChantiers = filteredChantiers.slice(startIndex, endIndex);
    
    const response: ApiResponse<PaginatedResponse<any>> = {
      success: true,
      data: {
        items: paginatedChantiers,
        total: filteredChantiers.length,
        page,
        pageSize,
        totalPages: Math.ceil(filteredChantiers.length / pageSize),
      },
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error('Erreur API chantiers:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible de récupérer la liste des chantiers',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}

// POST /api/chantiers - Créer un nouveau chantier
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Validation basique
    if (!body.ref || !body.nom || !body.conducteur) {
      const response: ApiResponse<null> = {
        success: false,
        error: 'Données invalides',
        message: 'Les champs ref, nom et conducteur sont obligatoires',
      };
      return NextResponse.json(response, { status: 400 });
    }
    
    // Simuler la création d'un chantier
    const newChantier = {
      id: `chantier-${Date.now()}`,
      ref: body.ref,
      nom: body.nom,
      adresse: body.adresse || '',
      conducteur: body.conducteur,
      montantBase: body.montantBase || 0,
      tsAvenants: body.tsAvenants || 0,
      montantRevise: (body.montantBase || 0) + (body.tsAvenants || 0),
      situationsFacturees: 0,
      pourcentageFacture: 0,
      totalDepenses: 0,
      margeBrute: (body.montantBase || 0) + (body.tsAvenants || 0),
      soldeAFacturer: (body.montantBase || 0) + (body.tsAvenants || 0),
      statut: body.statut || 'en_attente',
      priorite: body.priorite || 0,
      dateOPRPrevue: body.dateOPRPrevue || '',
      dateOPRRealisee: body.dateOPRRealisee || '',
      commentaires: body.commentaires || '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    const response: ApiResponse<any> = {
      success: true,
      data: newChantier,
      message: 'Chantier créé avec succès',
    };
    
    return NextResponse.json(response, { status: 201 });
    
  } catch (error) {
    console.error('Erreur création chantier:', error);
    
    const response: ApiResponse<null> = {
      success: false,
      error: 'Erreur interne du serveur',
      message: 'Impossible de créer le chantier',
    };
    
    return NextResponse.json(response, { status: 500 });
  }
}