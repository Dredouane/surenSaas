"""
Routeur Sémantique Chantier — Hermès.

Pour un email donné (sujet + corps + expéditeur), détermine quel chantier
est concerné via une stratégie hybride en 3 passes :

  1. Keyword SQL (ILIKE sur nom, ref, adresse)
  2. pgvector RPC match_chantiers (similarité cosinus)
  3. LLM fallback with_structured_output (si score < seuil)

Retourne chantier_id (str UUID) ou None si non-identifiable.
"""

import asyncio
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.api.auth import get_supabase
from app.services.emails.embedding_service import embedding_service

logger = get_logger(__name__)

VECTOR_MATCH_THRESHOLD = 0.72
LLM_CONFIDENCE_THRESHOLD = 0.60
LLM_MAX_CHANTIERS = 20


class ChantierRouterResult(BaseModel):
    chantier_id: Optional[str] = None
    confidence: float = 0.0
    method: str = "none"
    reason: str = ""


class _LLMRoutingOutput(BaseModel):
    chantier_id: Optional[str] = Field(None, description="UUID du chantier identifié. null si aucun ne correspond.")
    confidence: float = Field(0.0, description="Score de confiance entre 0.0 et 1.0")
    reason: str = Field("", description="Justification en 1-2 phrases")


class ChantierRouter:
    """Routeur sémantique d'emails vers les chantiers."""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            from app.core import vertex as vertex_service
            base_llm = vertex_service.get_chat_model()
            self._llm = base_llm.with_structured_output(_LLMRoutingOutput)
        return self._llm

    async def route(
        self,
        org_id: str,
        subject: str,
        body: str,
        sender_email: str = "",
    ) -> ChantierRouterResult:
        search_text = f"{subject} {body[:500]}"

        result = await self._keyword_match(org_id, search_text)
        if result:
            logger.info(f"[ChantierRouter] Passe 1 (keyword) → chantier {result.chantier_id}")
            return result

        result = await self._vector_match(org_id, search_text)
        if result:
            logger.info(f"[ChantierRouter] Passe 2 (vector) → chantier {result.chantier_id} (score={result.confidence:.2f})")
            return result

        result = await self._llm_match(org_id, subject, body[:1500], sender_email)
        logger.info(f"[ChantierRouter] Passe 3 (llm) → {result.chantier_id or 'ignored'} (conf={result.confidence:.2f})")
        return result

    async def _keyword_match(self, org_id: str, text: str) -> Optional[ChantierRouterResult]:
        try:
            sb = get_supabase()
            chantiers_resp = sb.table("chantiers")\
                .select("id, nom, ref, adresse")\
                .eq("org_id", org_id)\
                .in_("statut", ["en_cours", "en_attente"])\
                .execute()

            if not chantiers_resp.data:
                return None

            text_lower = text.lower()
            matches = []

            for c in chantiers_resp.data:
                nom = (c.get("nom") or "").lower()
                ref = (c.get("ref") or "").lower()
                if (nom and len(nom) >= 4 and nom in text_lower) or \
                   (ref and len(ref) >= 3 and ref in text_lower):
                    matches.append(c)

            if len(matches) == 1:
                return ChantierRouterResult(
                    chantier_id=matches[0]["id"],
                    confidence=0.90,
                    method="keyword",
                    reason=f"Correspondance exacte sur nom/ref: {matches[0].get('nom')}"
                )

        except Exception as e:
            logger.warning(f"[ChantierRouter] Erreur keyword match: {e}")

        return None

    async def _vector_match(self, org_id: str, text: str) -> Optional[ChantierRouterResult]:
        try:
            vector = await embedding_service.generate_embedding(text)

            loop = asyncio.get_event_loop()
            sb = get_supabase()

            def _rpc():
                return sb.rpc("match_chantiers", {
                    "query_embedding": vector,
                    "org_id_filter": org_id,
                    "match_threshold": VECTOR_MATCH_THRESHOLD,
                    "match_count": 3,
                }).execute()

            response = await loop.run_in_executor(None, _rpc)

            if response.data and len(response.data) > 0:
                top = response.data[0]
                similarity = top.get("similarity", 0.0)

                if similarity >= VECTOR_MATCH_THRESHOLD:
                    return ChantierRouterResult(
                        chantier_id=str(top["chantier_id"]),
                        confidence=round(similarity, 3),
                        method="vector",
                        reason=f"Similarité cosinus: {similarity:.2f}"
                    )

        except Exception as e:
            logger.warning(f"[ChantierRouter] Erreur vector match: {e}")

        return None

    async def _llm_match(
        self,
        org_id: str,
        subject: str,
        body_excerpt: str,
        sender_email: str,
    ) -> ChantierRouterResult:
        try:
            sb = get_supabase()

            chantiers_resp = sb.table("chantiers")\
                .select("id, nom, ref, adresse, statut")\
                .eq("org_id", org_id)\
                .in_("statut", ["en_cours", "en_attente"])\
                .limit(LLM_MAX_CHANTIERS)\
                .execute()

            if not chantiers_resp.data:
                return ChantierRouterResult(
                    method="ignored",
                    reason="Aucun chantier actif dans l'organisation"
                )

            chantiers_list = "\n".join([
                f"- ID: {c['id']} | Nom: {c.get('nom','?')} | Ref: {c.get('ref','?')} | Adresse: {c.get('adresse','?')}"
                for c in chantiers_resp.data
            ])

            prompt = f"""Tu es un assistant de gestion de chantiers BTP.

CHANTIERS ACTIFS DE L'ORGANISATION :
{chantiers_list}

EMAIL REÇU :
- De : {sender_email}
- Sujet : {subject}
- Corps (extrait) : {body_excerpt}

QUESTION : Quel chantier de la liste ci-dessus est concerné par cet email ?
- Si un seul chantier correspond clairement, donne son UUID exact.
- Si plusieurs pourraient correspondre mais un est plus probable, choisis-le avec un score bas.
- Si aucun chantier ne correspond, retourne null.
- Le champ "confidence" doit refléter ta certitude (0.0 à 1.0).
"""
            from langchain_core.messages import HumanMessage

            llm = self._get_llm()

            loop = asyncio.get_event_loop()
            output: _LLMRoutingOutput = await loop.run_in_executor(
                None,
                lambda: llm.invoke([HumanMessage(content=prompt)])
            )

            if output and output.chantier_id and output.confidence >= LLM_CONFIDENCE_THRESHOLD:
                check = sb.table("chantiers")\
                    .select("id")\
                    .eq("id", output.chantier_id)\
                    .eq("org_id", org_id)\
                    .execute()

                if check.data:
                    return ChantierRouterResult(
                        chantier_id=output.chantier_id,
                        confidence=output.confidence,
                        method="llm",
                        reason=output.reason
                    )

            return ChantierRouterResult(
                method="ignored",
                confidence=output.confidence if output else 0.0,
                reason=output.reason if output else "LLM n'a pas identifié de chantier ou confiance insuffisante"
            )

        except Exception as e:
            logger.error(f"[ChantierRouter] Erreur LLM match: {e}", exc_info=True)
            return ChantierRouterResult(
                method="ignored",
                reason=f"Erreur LLM: {e}"
            )


chantier_router = ChantierRouter()
