"""
Routeur Hermès — Knowledge Base (RAG).

Recherche sémantique globale sur l'ensemble des contenus ingérés :
- Emails (email_embeddings)
- Chantiers (chantier_embeddings)

Utilise pgvector et les RPC existantes search_similar_emails / match_chantiers.
"""

import asyncio
from typing import List, Optional
from fastapi import APIRouter, Header, Query, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.logging import get_logger
from app.api.auth import get_supabase
from app.services.emails.embedding_service import embedding_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/kb", tags=["hermes_kb"])


class KBSearchRequest(BaseModel):
    query: str = Field(..., description="Texte de la recherche (question ou mots-clés)")
    org_id: str = Field(..., description="UUID de l'organisation")
    company_id: Optional[str] = Field(None, description="Filtrer par entreprise")
    chantier_id: Optional[str] = Field(None, description="Filtrer par chantier")
    limit: int = Field(10, ge=1, le=50, description="Nombre max de résultats")
    match_threshold: float = Field(0.65, ge=0.0, le=1.0, description="Seuil de similarité")
    sources: List[str] = Field(
        ["emails", "chantiers"],
        description="Sources à interroger : 'emails', 'chantiers'"
    )


def _verify_key(x_api_key: str):
    from app.api.tools_rest import verify_tools_api_key
    return verify_tools_api_key(x_api_key)


@router.post("/search")
async def kb_search(
    body: KBSearchRequest,
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """Recherche sémantique globale sur la base de connaissances.

    Gènère un embedding de la query, puis interroge les sources configurées
    (emails, chantiers) via pgvector. Fusionne et trie les résultats par similarité.
    """
    _verify_key(x_api_key)

    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query vide")

    # 1. Générer l'embedding de la requête
    try:
        vector = await embedding_service.generate_embedding(body.query)
    except Exception as e:
        logger.error(f"[KB] Erreur génération embedding: {e}")
        raise HTTPException(status_code=502, detail=f"Erreur embedding: {e}")

    sb = get_supabase()
    results = []

    # 2. Recherche parallèle dans les sources demandées
    tasks = []
    if "emails" in body.sources:
        tasks.append(_search_emails(sb, vector, body))
    if "chantiers" in body.sources:
        tasks.append(_search_chantiers(sb, vector, body))

    source_results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in source_results:
        if isinstance(res, list):
            results.extend(res)
        elif isinstance(res, Exception):
            logger.warning(f"[KB] Erreur source: {res}")

    # 3. Trier par similarité décroissante
    results.sort(key=lambda r: r.get("similarity", 0), reverse=True)

    # 4. Limiter le nombre final
    results = results[:body.limit]

    return {
        "success": True,
        "query": body.query,
        "count": len(results),
        "results": results,
    }


async def _search_emails(sb, vector: list, body: KBSearchRequest) -> list:
    """Recherche dans email_embeddings via la RPC search_similar_emails."""
    results = []
    try:
        loop = asyncio.get_event_loop()

        def _rpc():
            return sb.rpc("search_similar_emails", {
                "query_embedding": vector,
                "target_org_id": body.org_id,
                "target_company_id": body.company_id or None,
                "match_threshold": body.match_threshold,
                "match_count": body.limit,
            }).execute()

        response = await loop.run_in_executor(None, _rpc)

        for row in (response.data or []):
            email_id = row.get("email_id")
            # Récupérer le sujet et le thread associé
            email_resp = sb.table("emails").select("subject, gmail_thread_id")\
                .eq("id", email_id).maybe_single().execute()

            subject = None
            thread_id = None
            if email_resp.data:
                subject = email_resp.data.get("subject")
                thread_id = email_resp.data.get("gmail_thread_id")

            # Si chantier_id filtré, vérifier que le thread y est associé
            if body.chantier_id and thread_id:
                thread_check = sb.table("email_threads").select("id")\
                    .eq("gmail_thread_id", thread_id)\
                    .eq("org_id", body.org_id)\
                    .eq("detected_chantier_id", body.chantier_id)\
                    .maybe_single().execute()
                if not thread_check.data:
                    continue

            results.append({
                "source": "email",
                "email_id": str(email_id),
                "thread_id": str(thread_id) if thread_id else None,
                "subject": subject,
                "content": row.get("content_chunk", ""),
                "similarity": round(row.get("similarity", 0), 4),
            })

    except Exception as e:
        logger.warning(f"[KB] Erreur recherche emails: {e}")

    return results


async def _search_chantiers(sb, vector: list, body: KBSearchRequest) -> list:
    """Recherche dans chantier_embeddings via la RPC match_chantiers."""
    results = []
    try:
        loop = asyncio.get_event_loop()

        def _rpc():
            return sb.rpc("match_chantiers", {
                "query_embedding": vector,
                "org_id_filter": body.org_id,
                "match_threshold": body.match_threshold,
                "match_count": body.limit,
            }).execute()

        response = await loop.run_in_executor(None, _rpc)

        for row in (response.data or []):
            chantier_id = str(row["chantier_id"])

            # Si chantier_id filtré, ne garder que celui-ci
            if body.chantier_id and chantier_id != body.chantier_id:
                continue

            # Récupérer le nom du chantier
            c_resp = sb.table("chantiers").select("nom, ref")\
                .eq("id", chantier_id).maybe_single().execute()
            chantier_nom = c_resp.data.get("nom") if c_resp.data else None
            chantier_ref = c_resp.data.get("ref") if c_resp.data else None

            results.append({
                "source": "chantier",
                "chantier_id": chantier_id,
                "chantier_nom": chantier_nom,
                "chantier_ref": chantier_ref,
                "content": row.get("content", ""),
                "similarity": round(row.get("similarity", 0), 4),
            })

    except Exception as e:
        logger.warning(f"[KB] Erreur recherche chantiers: {e}")

    return results
