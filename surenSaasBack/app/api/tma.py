"""
API TMA — Auth Bridge pour Telegram Mini App.

Endpoints :
  POST /api/v1/tma/auth  → valide initData, retourne JWT
  GET  /api/v1/tma/context → retourne chantier + user + org (nécessite JWT)
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.services.tma_auth_service import TmaAuthService, decode_start_param
from app.services.database import supabase_client
from app.api.tma_extract import extract_workflow
from app.services.transcribe_service import transcribe_with_gemini

logger = get_logger(__name__)
router = APIRouter(prefix="/tma", tags=["tma"])

auth_service = TmaAuthService()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AuthRequest(BaseModel):
    initData: str
    start_param: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    expires_at: str


class ContextResponse(BaseModel):
    chantier: Optional[dict] = None
    user: Optional[dict] = None
    org: Optional[dict] = None
    correlation_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/auth", response_model=AuthResponse)
async def tma_auth(body: AuthRequest, request: Request):
    """
    Valide le initData Telegram, résout le chantier, retourne un JWT short-lived.
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    data = auth_service.validate_init_data(body.initData)
    if not data:
        raise HTTPException(status_code=401, detail="InitData invalide ou signature erronée")

    # L'id Telegram est dans l'objet "user" du initData
    import json as _json
    user_data = data.get("user", {})
    if isinstance(user_data, str):
        try:
            user_data = _json.loads(user_data)
        except _json.JSONDecodeError:
            user_data = {}

    telegram_id = 0
    if user_data and isinstance(user_data, dict):
        telegram_id = int(user_data.get("id", 0))
    if not telegram_id:
        # Fallback : chercher à la racine du initData
        telegram_id = int(data.get("id", 0))
    if not telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id manquant dans initData")

    # Résoudre user_id + org_id depuis telegram_users
    tu_result = supabase_client.table("telegram_users").select(
        "user_id, org_id, last_chantier_id"
    ).eq("telegram_id", telegram_id).maybe_single().execute()

    if not tu_result.data:
        raise HTTPException(status_code=404, detail="Utilisateur Telegram non trouvé")

    tu = tu_result.data
    user_id = tu["user_id"]
    org_id = tu["org_id"]
    last_chantier_id = tu.get("last_chantier_id")

    # Résoudre chantier_id depuis start_param ou last_chantier_id
    chantier_id = None
    workflow = None
    if body.start_param:
        start_data = decode_start_param(body.start_param)
        chantier_id = start_data.get("c") or last_chantier_id
        workflow = start_data.get("w")
    else:
        chantier_id = last_chantier_id

    # Récupérer le rôle depuis users
    user_result = supabase_client.table("users").select("role").eq("id", user_id).maybe_single().execute()
    role = "conducteur"
    if user_result.data:
        role = user_result.data.get("role", "conducteur")

    token = auth_service.generate_jwt(
        telegram_id=telegram_id,
        user_id=user_id,
        org_id=org_id,
        chantier_id=chantier_id,
        role=role,
    )

    logger.info(
        f"TMA Auth OK: telegram_id={telegram_id} user_id={user_id} org_id={org_id} "
        f"chantier_id={chantier_id} workflow={workflow} correlation_id={correlation_id}"
    )

    import jwt as _jwt
    payload = _jwt.decode(token, auth_service.jwt_secret, algorithms=["HS256"])
    expires_at = payload.get("exp", "")

    return AuthResponse(token=token, expires_at=str(expires_at))


# ---------------------------------------------------------------------------
# Extract endpoint — utilisé par les écrans TMA (progression, opérations, dépenses)
# ---------------------------------------------------------------------------

class ExtractRequest(BaseModel):
    text: str
    workflow: str


@router.post("/extract")
async def tma_extract(body: ExtractRequest, request: Request):
    """
    Extrait et valide les données depuis un texte utilisateur.
    Workflows supportés : avancement, operation, depense
    """
    result = await extract_workflow(body.workflow, body.text)
    return result


# ---------------------------------------------------------------------------
# Extract-file — OCR/texte depuis un fichier (photo, PDF)
# ---------------------------------------------------------------------------

@router.post("/extract-file")
async def tma_extract_file(
    request: Request,
    file: UploadFile = File(...),
    workflow: str = Form("ocr"),
):
    """
    Extrait le texte d'un fichier (image/PDF) via Gemini OCR.
    Retourne le texte brut extrait.
    """
    content = await file.read()
    if not content or len(content) < 100:
        return {"text": ""}

    try:
        import tempfile
        suffix = Path(file.filename or "file").suffix or ".tmp"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(content)
        tmp.close()

        from app.agents.workflow_extractor import WorkflowExtractor
        extractor = WorkflowExtractor(model=settings.tma_extraction_model)
        result = extractor.extract(f"Extrais le texte de ce fichier: {file.filename or 'document'}", "avancement", tmp.name)
        if hasattr(result, '__await__'):
            result = await result

        os.unlink(tmp.name)

        text = ""
        if result and not result.get("_fallback"):
            ed = result.get("extracted_data") or result
            text = ed.get("description") or ed.get("text") or ""

        return {"text": text}
    except Exception as e:
        logger.error(f"Erreur extract-file: {e}")
        return {"text": ""}


# ---------------------------------------------------------------------------
# Process — endpoint unique pour la TMA : prend tout type d'input
# (texte, audio, image, PDF) et retourne les données structurées + validées
# ---------------------------------------------------------------------------

class ProcessResponse(BaseModel):
    is_valid: bool
    data: dict = {}
    guardrail_issues: list = []
    error: Optional[str] = None


@router.post("/process", response_model=ProcessResponse)
async def tma_process(
    request: Request,
    text: Optional[str] = Form(None),
    workflow: str = Form(...),
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
):
    """
    Endpoint unique pour la TMA.
    - text: saisie manuelle
    - audio: enregistrement vocal
    - file: photo/PDF
    Retourne les données structurées selon le workflow.
    """
    input_text = text or ""

    # 1. Si audio → transcrire d'abord
    if audio:
        content = await audio.read()
        if content and len(content) > 200:
            from app.services.transcribe_service import transcribe_with_gemini
            transcript = transcribe_with_gemini(content, audio.content_type or "audio/webm")
            if transcript:
                input_text = transcript

    # 2. Si fichier (photo/PDF) → OCR
    file_path = None
    if file:
        content = await file.read()
        if content and len(content) > 200:
            import tempfile
            suffix = Path(file.filename or "file").suffix or ".tmp"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(content)
            tmp.close()
            file_path = tmp.name

    # 3. Extraction structurée
    if not input_text and not file_path:
        return ProcessResponse(is_valid=False, error="Aucun input fourni", data={})

    result = await extract_workflow(workflow, input_text, file_path)

    # Nettoyage fichier temporaire
    if file_path:
        try:
            os.unlink(file_path)
        except Exception:
            pass

    return ProcessResponse(
        is_valid=result.get("is_valid", False),
        data=result.get("data", {}),
        guardrail_issues=result.get("guardrail_issues", []),
        error=result.get("error"),
    )


# ---------------------------------------------------------------------------
# Transcribe — transcription audio via Gemini (MediaRecorder API)
# ---------------------------------------------------------------------------

async def transcribe_audio(audio_data: bytes, mime_type: str = "audio/webm") -> dict:
    """Transcrit un flux audio via Gemini. Fonction exportée pour les tests."""
    try:
        text = transcribe_with_gemini(audio_data, mime_type)
        if text:
            return {"is_valid": True, "text": text}
        return {"is_valid": False, "error": "Échec de la transcription audio"}
    except Exception as e:
        logger.error(f"Erreur transcription: {e}")
        return {"is_valid": False, "error": str(e)}


@router.post("/transcribe")
async def tma_transcribe(
    request: Request,
    audio: UploadFile = File(...),
):
    """
    Transcrit un fichier audio (webm/ogg/wav) en texte via Gemini.
    Utilisé par le VoiceRecorder de la TMA.
    """
    content = await audio.read()
    if not content or len(content) < 100:
        return {"is_valid": False, "error": "Fichier audio vide ou trop court"}

    mime_type = audio.content_type or "audio/webm"
    return await transcribe_audio(content, mime_type)


# ---------------------------------------------------------------------------
# Transcribe + Structure — Pipeline Whisper + Gemini
# ---------------------------------------------------------------------------

@router.post("/transcribe-and-structure")
async def tma_transcribe_and_structure(
    request: Request,
    audio: UploadFile = File(...),
):
    """
    Pipeline audio complet :
      1. Whisper (OpenRouter) → texte brut
      2. Gemini (Vertex AI)   → JSON structuré

    Nécessite un JWT valide. Le résultat inclut transcript et structured.
    Chaque étape est loggée dans logs_agents.
    """
    # Vérifier l'authentification
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"is_valid": False, "error": "Token manquant"}

    token = auth_header.replace("Bearer ", "")
    try:
        payload = auth_service.verify_jwt(token)
        org_id = payload.get("org_id", "")
    except Exception:
        return {"is_valid": False, "error": "Token invalide"}

    content = await audio.read()
    if not content or len(content) < 100:
        return {"is_valid": False, "error": "Fichier audio vide ou trop court"}

    mime_type = audio.content_type or "audio/webm"
    correlation_id = getattr(request.state, "correlation_id", None)

    result = await transcribe_pipeline(
        audio_data=content,
        mime_type=mime_type,
        org_id=org_id,
        correlation_id=correlation_id or "",
    )

    return result


# ---------------------------------------------------------------------------

@router.get("/context", response_model=ContextResponse)
async def tma_context(request: Request):
    """
    Retourne le contexte complet (chantier, user, org) à partir du JWT.
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")

    token = auth_header.replace("Bearer ", "")
    payload = auth_service.verify_jwt(token)

    user_id = payload.get("user_id")
    org_id = payload.get("org_id")
    chantier_id = payload.get("chantier_id")

    user = None
    if user_id:
        result = supabase_client.table("users").select(
            "id, email, full_name, role"
        ).eq("id", user_id).maybe_single().execute()
        if result.data:
            user = result.data

    chantier = None
    if chantier_id:
        result = supabase_client.table("chantiers").select(
            "id, ref, nom, adresse, statut, montant_revise, situations_facturees, conducteur"
        ).eq("id", chantier_id).maybe_single().execute()
        if result.data:
            chantier = result.data

    org = None
    if org_id:
        result = supabase_client.table("organizations").select(
            "id, name, slug"
        ).eq("id", org_id).maybe_single().execute()
        if result.data:
            org = result.data

    return ContextResponse(
        chantier=chantier,
        user=user,
        org=org,
        correlation_id=correlation_id,
    )
