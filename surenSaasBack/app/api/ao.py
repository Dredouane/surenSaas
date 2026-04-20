"""
Routes API pour le Module AO (Appels d'Offres).

Endpoints:
- /api/v1/ao/candidatures - CRUD candidatures
- /api/v1/ao/candidatures/{id}/documents - Gestion documents
- /api/v1/ao/documents/{id}/download - Téléchargement document
- /api/v1/ao/documents/{id}/preview - Prévisualisation document
- /api/v1/ao/candidatures/{id}/ingest - Ingestion dossier
- /api/v1/ao/candidatures/{id}/analyze - Analyses par Lentilles
- /api/v1/ao/candidatures/{id}/postes - Postes pricing
- /api/v1/ao/rag/* - Services RAG
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import RedirectResponse

from app.core.logging import get_logger
from app.api.auth import get_current_user, get_org_id_from_user, get_supabase
from app.models.ao import (
    AOCandidatureCreate, AOCandidatureUpdate, AOCandidatureDetail,
    AOCandidatureListResponse, AODocumentListResponse, AODocumentType,
    AOLensType, AOLensAnalysisRequest, AOValidationRequest,
    AODraftingRequest, AODraftingIterateRequest,
    AOIngestFolderRequest, AOClassifyDocumentRequest,
    AOExtractPricingRequest
)
from app.services.ao_service import ao_service
from app.services.ao_lens_engine import ao_lens_engine
from app.services.ao_rag_service import ao_rag_service
from app.services.file_storage_service import file_storage_service

logger = get_logger(__name__)
router = APIRouter(prefix="/ao", tags=["Appels d'Offres"])


# ============================================================================
# CANDIDATURES
# ============================================================================

@router.post("/candidatures", response_model=AOCandidatureDetail)
async def create_candidature(
    data: AOCandidatureCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crée une nouvelle candidature."""
    org_id = get_org_id_from_user(current_user)
    user_id = UUID(current_user["sub"])
    
    try:
        result = await ao_service.create_candidature(
            org_id=org_id,
            data=data,
            created_by=user_id
        )
        return result
    except Exception as e:
        logger.error(f"Erreur création candidature: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création: {str(e)}"
        )


@router.get("/candidatures", response_model=AOCandidatureListResponse)
async def list_candidatures(
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    dossier_id: Optional[UUID] = Query(None, description="Filtrer par dossier"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Liste les candidatures avec pagination."""
    org_id = get_org_id_from_user(current_user)
    
    # Convertir le statut en enum si fourni
    statut_enum = None
    if statut:
        from app.models.ao import AOStatut
        try:
            statut_enum = AOStatut(statut)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Statut invalide: {statut}"
            )
    
    try:
        data, total = await ao_service.list_candidatures(
            org_id=org_id,
            statut=statut_enum,
            dossier_id=dossier_id,
            page=page,
            limit=limit
        )
        
        return {
            "data": data,
            "total": total,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Erreur liste candidatures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/candidatures/{candidature_id}", response_model=AOCandidatureDetail)
async def get_candidature(
    candidature_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Récupère une candidature par ID."""
    org_id = get_org_id_from_user(current_user)
    
    candidature = await ao_service.get_candidature(candidature_id, org_id)
    
    if not candidature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidature non trouvée"
        )
    
    return candidature


@router.patch("/candidatures/{candidature_id}", response_model=AOCandidatureDetail)
async def update_candidature(
    candidature_id: UUID,
    data: AOCandidatureUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Met à jour une candidature."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        result = await ao_service.update_candidature(candidature_id, org_id, data)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur mise à jour candidature: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# DOCUMENTS
# ============================================================================

@router.get("/candidatures/{candidature_id}/documents", response_model=AODocumentListResponse)
async def list_documents(
    candidature_id: UUID,
    type_doc: Optional[AODocumentType] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Liste les documents d'une candidature."""
    org_id = get_org_id_from_user(current_user)
    
    # Vérifier que la candidature existe et appartient à l'org
    candidature = await ao_service.get_candidature(candidature_id, org_id)
    if not candidature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidature non trouvée"
        )
    
    documents = await ao_service.list_documents(candidature_id, org_id, type_doc)
    
    return {
        "data": documents,
        "total": len(documents)
    }


@router.post("/candidatures/{candidature_id}/ingest")
async def ingest_folder(
    candidature_id: UUID,
    request: AOIngestFolderRequest,
    current_user: dict = Depends(get_current_user)
):
    """Ingère un dossier de fichiers pour une candidature."""
    org_id = get_org_id_from_user(current_user)
    user_id = UUID(current_user["sub"])
    
    try:
        result = await ao_service.ingest_ao_folder(
            candidature_id=candidature_id,
            org_id=org_id,
            folder_path=request.folder_path,
            auto_classify=request.auto_classify,
            uploaded_by=user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur ingestion dossier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/documents/{document_id}/classify")
async def classify_document(
    document_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Classifie un document via IA."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        result = await ao_service.classify_document(document_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur classification document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Télécharge un document AO.
    
    Récupère le document depuis S3/R2 via son storage_key et redirige vers l'URL signée.
    """
    org_id = get_org_id_from_user(current_user)
    
    try:
        # Récupérer le document depuis la base
        supabase = get_supabase()
        doc_response = supabase.table("ao_documents")\
            .select("*")\
            .eq("id", str(document_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not doc_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        document = doc_response.data
        storage_path = document.get("url_stockage")
        
        if not storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non stocké"
            )
        
        # Vérifier le type de stockage (S3 ou local)
        from app.core.config import get_settings
        settings = get_settings()
        environment = settings.environment.lower()
        s3_prefix = f"{environment}/org/{org_id}/"
        
        if storage_path.startswith(s3_prefix):
            # Stockage S3/R2
            # Vérifier que le storage_path appartient à l'organisation
            if not storage_path.startswith(s3_prefix):
                logger.warning(
                    f"🚫 Tentative d'accès non autorisé au document\n"
                    f"   User: {current_user.get('email')} (org: {org_id})\n"
                    f"   Storage path: {storage_path}\n"
                    f"   Expected prefix: {s3_prefix}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accès non autorisé à ce document"
                )
            
            # Vérifier que le fichier existe sur S3
            exists = await file_storage_service.file_exists(storage_path)
            if not exists:
                logger.warning(f"⚠️ Document non trouvé sur S3: {storage_path}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document non trouvé sur le stockage"
                )
            
            # Générer URL signée (valide 1 heure)
            download_url = await file_storage_service.get_presigned_url(
                key=storage_path,
                filename=document.get("nom_fichier"),
                expires=3600
            )
            
            # Rediriger vers l'URL signée S3
            return RedirectResponse(url=download_url)
            
        else:
            # Stockage local (fallback pour développement/test)
            # Vérifier que le chemin local est sécurisé
            local_prefix = f"/tmp/ao/{org_id}/"
            if not storage_path.startswith(local_prefix):
                logger.warning(
                    f"🚫 Tentative d'accès non autorisé au document local\n"
                    f"   User: {current_user.get('email')} (org: {org_id})\n"
                    f"   Storage path: {storage_path}\n"
                    f"   Expected prefix: {local_prefix}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accès non autorisé à ce document"
                )
            
            # Vérifier que le fichier existe localement
            import os
            if not os.path.exists(storage_path):
                logger.warning(f"⚠️ Document non trouvé localement: {storage_path}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document non trouvé localement"
                )
            
            # Pour le stockage local, on peut servir le fichier directement
            # ou créer une route dédiée. Pour l'instant, on redirige vers une route de fichier local.
            # Note: En production, il faudrait migrer tous les fichiers vers S3.
            logger.info(f"📥 Téléchargement document local: {storage_path}")
            
            # Créer une route temporaire pour servir le fichier local
            # Pour simplifier, on va utiliser FastAPI pour servir le fichier
            from fastapi.responses import FileResponse
            return FileResponse(
                path=storage_path,
                filename=document.get("nom_fichier"),
                media_type=document.get("mime_type", "application/octet-stream")
            )
        
        logger.info(
            f"📥 Téléchargement document AO\n"
            f"   User: {current_user.get('email')}\n"
            f"   Document: {document.get('nom_fichier')}\n"
            f"   Type: {document.get('type_doc')}"
        )
        
        # Rediriger vers l'URL signée S3
        return RedirectResponse(url=download_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du téléchargement: {str(e)}"
        )


@router.get("/documents/{document_id}/preview")
async def preview_document(
    document_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Prépare la prévisualisation d'un document AO.
    
    Retourne les métadonnées et l'URL signée pour prévisualisation.
    """
    org_id = get_org_id_from_user(current_user)
    
    try:
        # Récupérer le document depuis la base
        supabase = get_supabase()
        doc_response = supabase.table("ao_documents")\
            .select("*")\
            .eq("id", str(document_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not doc_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        document = doc_response.data
        storage_path = document.get("url_stockage")
        
        if not storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non stocké"
            )
        
        # Vérifier le type de stockage (S3 ou local)
        from app.core.config import get_settings
        settings = get_settings()
        environment = settings.environment.lower()
        s3_prefix = f"{environment}/org/{org_id}/"
        
        preview_url = None
        is_local = False
        
        if storage_path.startswith(s3_prefix):
            # Stockage S3/R2
            # Vérifier que le storage_path appartient à l'organisation
            if not storage_path.startswith(s3_prefix):
                logger.warning(
                    f"🚫 Tentative d'accès non autorisé au document\n"
                    f"   User: {current_user.get('email')} (org: {org_id})\n"
                    f"   Storage path: {storage_path}\n"
                    f"   Expected prefix: {s3_prefix}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accès non autorisé à ce document"
                )
            
            # Vérifier que le fichier existe sur S3
            exists = await file_storage_service.file_exists(storage_path)
            if not exists:
                logger.warning(f"⚠️ Document non trouvé sur S3: {storage_path}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document non trouvé sur le stockage"
                )
            
            # Générer URL signée pour prévisualisation (valide 2 heures)
            preview_url = await file_storage_service.get_presigned_url(
                key=storage_path,
                filename=document.get("nom_fichier"),
                expires=7200
            )
            
        else:
            # Stockage local (fallback pour développement/test)
            # Vérifier que le chemin local est sécurisé
            local_prefix = f"/tmp/ao/{org_id}/"
            if not storage_path.startswith(local_prefix):
                logger.warning(
                    f"🚫 Tentative d'accès non autorisé au document local\n"
                    f"   User: {current_user.get('email')} (org: {org_id})\n"
                    f"   Storage path: {storage_path}\n"
                    f"   Expected prefix: {local_prefix}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accès non autorisé à ce document"
                )
            
            # Vérifier que le fichier existe localement
            import os
            if not os.path.exists(storage_path):
                logger.warning(f"⚠️ Document non trouvé localement: {storage_path}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document non trouvé localement"
                )
            
            # Pour le stockage local, créer une URL de téléchargement direct
            is_local = True
            # L'URL sera générée par le frontend en utilisant l'endpoint download
            preview_url = f"/api/v1/ao/documents/{document_id}/download"
            logger.info(f"👁️ Prévisualisation document local: {storage_path}")
        
        # Extraire les métadonnées pour la prévisualisation
        metadata = document.get("metadata", {})
        contenu_texte = document.get("contenu_texte", "")
        
        # Détecter le type de document pour la prévisualisation
        mime_type = document.get("mime_type", "")
        is_pdf = mime_type == "application/pdf" or document.get("nom_fichier", "").lower().endswith(".pdf")
        is_image = mime_type.startswith("image/")
        is_text = mime_type.startswith("text/") or mime_type in ["application/json", "application/xml"]
        
        logger.info(
            f"👁️ Prévisualisation document AO\n"
            f"   User: {current_user.get('email')}\n"
            f"   Document: {document.get('nom_fichier')}\n"
            f"   Type: {document.get('type_doc')}\n"
            f"   MIME: {mime_type}"
        )
        
        return {
            "document": {
                "id": document["id"],
                "nom_fichier": document.get("nom_fichier"),
                "type_doc": document.get("type_doc"),
                "mime_type": mime_type,
                "taille_bytes": document.get("taille_bytes"),
                "created_at": document.get("created_at"),
                "metadata": metadata
            },
            "preview_info": {
                "preview_url": preview_url,
                "storage_type": "local" if is_local else "s3",
                "is_pdf": is_pdf,
                "is_image": is_image,
                "is_text": is_text,
                "has_text_content": bool(contenu_texte),
                "text_preview": contenu_texte[:1000] if contenu_texte else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur prévisualisation document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la prévisualisation: {str(e)}"
        )


# ============================================================================
# POSTES PRICING
# ============================================================================

@router.get("/candidatures/{candidature_id}/postes")
async def get_postes_pricing(
    candidature_id: UUID,
    categorie: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Récupère les postes pricing d'une candidature."""
    org_id = get_org_id_from_user(current_user)
    
    postes = await ao_service.get_postes_pricing(candidature_id, org_id, categorie)
    
    # Calculer le montant total
    total = sum(
        float(p["prix_total_ht"]) for p in postes 
        if p.get("prix_total_ht")
    )
    
    return {
        "data": postes,
        "total": len(postes),
        "montant_total_ht": total
    }


@router.post("/documents/{document_id}/extract-pricing")
async def extract_pricing(
    document_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Extrait les données pricing d'un document BPU."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        result = await ao_service.extract_pricing_data(document_id, org_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur extraction pricing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# ANALYSES PAR LENTILLES
# ============================================================================

@router.post("/candidatures/{candidature_id}/analyze")
async def analyze_with_lens(
    candidature_id: UUID,
    request: AOLensAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Lance une analyse par Lentille sur une candidature."""
    org_id = get_org_id_from_user(current_user)
    user_id = UUID(current_user["sub"])
    
    try:
        result = await ao_lens_engine.analyze_with_lens(
            lens_type=request.lens_type,
            candidature_id=candidature_id,
            org_id=org_id,
            contexte=request.contexte,
            document_ids=request.document_ids,
            created_by=user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur analyse lentille: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/analyses/{analyse_id}/validate")
async def validate_analysis(
    analyse_id: UUID,
    request: AOValidationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Valide ou rejette une analyse IA."""
    org_id = get_org_id_from_user(current_user)
    user_id = UUID(current_user["sub"])
    
    try:
        result = await ao_lens_engine.validate_analysis(
            analyse_id=analyse_id,
            org_id=org_id,
            validation=request.validation,
            commentaire=request.commentaire,
            valide_par=user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur validation analyse: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# RÉDACTION ASSISTÉE
# ============================================================================

@router.post("/candidatures/{candidature_id}/draft")
async def generate_draft(
    candidature_id: UUID,
    request: AODraftingRequest,
    current_user: dict = Depends(get_current_user)
):
    """Génère un draft de mémoire technique via la Lentille Rédaction."""
    org_id = get_org_id_from_user(current_user)
    user_id = UUID(current_user["sub"])
    
    try:
        result = await ao_lens_engine.analyze_with_lens(
            lens_type=AOLensType.REDACTION,
            candidature_id=candidature_id,
            org_id=org_id,
            contexte={
                "chapitre": request.chapitre,
                "contexte_additionnel": request.contexte_additionnel,
                "references_memoires_gagnants": [
                    str(r) for r in request.references_memoires_gagnants
                ] if request.references_memoires_gagnants else None
            },
            created_by=user_id
        )
        return result
    except Exception as e:
        logger.error(f"Erreur génération draft: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/draft/iterate")
async def iterate_draft(
    request: AODraftingIterateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Itère sur un draft via le Petit Prompt."""
    try:
        result = await ao_lens_engine.iterate_draft(
            current_content=request.current_content,
            instruction=request.instruction
        )
        return result
    except Exception as e:
        logger.error(f"Erreur itération draft: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# RAG - RECHERCHE ET CONTEXTE
# ============================================================================

@router.get("/rag/pricing-context")
async def get_pricing_context(
    poste_description: str,
    unite: Optional[str] = Query(None),
    categorie: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Récupère le contexte pricing historique pour un poste."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        result = await ao_rag_service.get_pricing_context(
            org_id=org_id,
            poste_description=poste_description,
            unite=unite,
            categorie=categorie,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Erreur récupération contexte pricing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/candidatures/{candidature_id}/similar")
async def find_similar_ao(
    candidature_id: UUID,
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """Trouve les AO gagnés similaires."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        result = await ao_rag_service.find_similar_successful_ao(
            org_id=org_id,
            candidature_id=candidature_id,
            limit=limit
        )
        return {
            "candidature_id": str(candidature_id),
            "similar_ao": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur recherche AO similaires: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/rag/pricing-gap")
async def get_pricing_gap(
    categorie: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Analyse le gap de pricing entre gagnés et perdus."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        result = await ao_rag_service.compare_pricing_gap(org_id, categorie)
        return {
            "categorie": categorie or "toutes",
            "gaps": result
        }
    except Exception as e:
        logger.error(f"Erreur analyse gap pricing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/rag/memoire-templates")
async def get_memoire_templates(
    chapitre: str = Query(..., description="Nom du chapitre recherché"),
    limit: int = Query(3, ge=1, le=10),
    current_user: dict = Depends(get_current_user)
):
    """Récupère des templates de mémoires gagnants."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        result = await ao_rag_service.get_memoire_template(
            org_id=org_id,
            chapitre=chapitre,
            limit=limit
        )
        return {
            "chapitre": chapitre,
            "templates": result
        }
    except Exception as e:
        logger.error(f"Erreur récupération templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# STATS ET DASHBOARD
# ============================================================================

@router.get("/stats/dashboard")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user)
):
    """Récupère les statistiques pour le dashboard AO."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        # Total candidatures
        total_response = self.client.table("ao_candidatures")\
            .select("*", count="exact")\
            .eq("org_id", str(org_id))\
            .execute()
        
        total = total_response.count or 0
        
        # Par statut
        par_statut = {}
        for statut in ["en_cours", "gagne", "perdu", "abandonne"]:
            r = self.client.table("ao_candidatures")\
                .select("*", count="exact")\
                .eq("org_id", str(org_id))\
                .eq("statut", statut)\
                .execute()
            par_statut[statut] = r.count or 0
        
        # Montants
        montants = self.client.table("ao_candidatures")\
            .select("statut, montant_total")\
            .eq("org_id", str(org_id))\
            .execute()
        
        montant_gagne = sum(
            float(m["montant_total"]) for m in montants.data or []
            if m["statut"] == "gagne" and m.get("montant_total")
        )
        montant_perdu = sum(
            float(m["montant_total"]) for m in montants.data or []
            if m["statut"] == "perdu" and m.get("montant_total")
        )
        
        # Taux de réussite
        gagnes_perdus = par_statut.get("gagne", 0) + par_statut.get("perdu", 0)
        taux_reussite = (par_statut.get("gagne", 0) / gagnes_perdus * 100) if gagnes_perdus > 0 else 0
        
        return {
            "total_candidatures": total,
            "par_statut": par_statut,
            "taux_reussite": round(taux_reussite, 2),
            "montant_total_gagne": montant_gagne,
            "montant_total_perdu": montant_perdu
        }
        
    except Exception as e:
        logger.error(f"Erreur stats dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# UPLOAD ET TRAITEMENT DE DOCUMENTS
# ============================================================================

@router.post("/candidatures/{candidature_id}/documents/upload")
async def upload_document(
    candidature_id: UUID,
    file: UploadFile = File(...),
    process_ocr: bool = Query(True, description="Lancer l'OCR après upload"),
    vectorize: bool = Query(True, description="Vectoriser le document après OCR"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload un fichier individuel et l'associe à une candidature AO.
    
    - OCR automatique via Gemini
    - Vectorisation pour RAG
    - Supporte PDF, DOC, DOCX, XLS, XLSX, CSV, TXT
    """
    org_id = get_org_id_from_user(current_user)
    user_id = UUID(current_user["sub"])
    
    try:
        # Lire le fichier
        file_data = await file.read()
        
        if len(file_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fichier vide"
            )
        
        # Upload et traitement
        result = await ao_service.upload_document(
            candidature_id=candidature_id,
            org_id=org_id,
            file_data=file_data,
            filename=file.filename,
            mime_type=file.content_type,
            uploaded_by=user_id,
            process_ocr=process_ocr,
            vectorize=vectorize
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur upload document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/documents/{document_id}/process")
async def process_document(
    document_id: UUID,
    process_ocr: bool = Query(True, description="Lancer l'OCR"),
    vectorize: bool = Query(True, description="Vectoriser le document"),
    current_user: dict = Depends(get_current_user)
):
    """
    Traite un document existant (OCR + vectorisation).
    Utile pour re-traiter des documents ou traiter en arrière-plan.
    """
    org_id = get_org_id_from_user(current_user)
    
    try:
        result = await ao_service.process_existing_document(
            document_id=document_id,
            org_id=org_id,
            process_ocr=process_ocr,
            vectorize=vectorize
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur traitement document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/documents/{document_id}/ocr")
async def run_ocr(
    document_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Lance l'OCR sur un document."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        result = await ao_service.extract_document_text(
            document_id=document_id,
            org_id=org_id
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur OCR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/documents/{document_id}/vectorize")
async def run_vectorization(
    document_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Vectorise un document (nécessite que l'OCR ait été fait)."""
    org_id = get_org_id_from_user(current_user)
    
    try:
        # Récupérer le document pour avoir le candidature_id
        doc_response = get_supabase().table("ao_documents")\
            .select("candidature_id")\
            .eq("id", str(document_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not doc_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        candidature_id = UUID(doc_response.data["candidature_id"])
        
        result = await ao_service.vectorize_document(
            document_id=document_id,
            org_id=org_id,
            candidature_id=candidature_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur vectorisation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# UPLOAD DOSSIER ZIP + CREATION AUTO CANDIDATURE
# ============================================================================

@router.post("/upload-folder")
async def upload_folder_create_ao(
    folder_zip: UploadFile = File(..., description="Fichier ZIP contenant le dossier AO"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload un dossier ZIP contenant les documents d'un AO.
    
    - Décompresse le ZIP
    - Analyse les documents pour extraire les métadonnées (client, projet, montant, dates)
    - Crée automatiquement une candidature
    - Upload et traite tous les documents (OCR + Vectorisation)
    - Extrait les postes pricing si BPU présent
    
    Retourne la candidature créée avec les documents et métadonnées extraites.
    """
    org_id = get_org_id_from_user(current_user)
    user_id = UUID(current_user["sub"])
    
    # Vérifier que c'est bien un ZIP
    if not folder_zip.filename.endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier doit être un ZIP"
        )
    
    try:
        # Lire le ZIP
        zip_data = await folder_zip.read()
        
        if len(zip_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fichier ZIP vide"
            )
        
        if len(zip_data) > 500 * 1024 * 1024:  # 500 MB max
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fichier ZIP trop volumineux (max 500 MB)"
            )
        
        # Lancer le processus complet
        result = await ao_service.upload_and_create_from_zip(
            org_id=org_id,
            zip_data=zip_data,
            filename=folder_zip.filename,
            uploaded_by=user_id
        )
        
        return {
            "success": True,
            "message": "Candidature créée avec succès",
            "candidature_id": result["candidature"]["id"],
            "candidature": result["candidature"],
            "documents_created": result["documents_created"],
            "postes_extraits": result["postes_extraits"],
            "metadata_extracted": result["metadata_extracted"],
            "documents_errors": result["documents_errors"]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur upload dossier: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement du dossier: {str(e)}"
        )


@router.post("/candidatures/from-folder")
async def create_from_folder_path(
    folder_path: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Crée une candidature à partir d'un dossier déjà présent sur le serveur.
    Utile pour traiter des dossiers déjà uploadés ou montés.
    
    - Analyse le dossier pour extraire les métadonnées
    - Crée la candidature
    - Traite tous les documents
    """
    org_id = get_org_id_from_user(current_user)
    user_id = UUID(current_user["sub"])
    
    try:
        result = await ao_service.analyze_and_create_from_folder(
            org_id=org_id,
            folder_path=folder_path,
            uploaded_by=user_id
        )
        
        return {
            "success": True,
            "candidature_id": result["candidature"]["id"],
            "candidature": result["candidature"],
            "documents_created": result["documents_created"],
            "postes_extraits": result["postes_extraits"],
            "metadata_extracted": result["metadata_extracted"]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur création depuis dossier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
