"""
Moteur des Lentilles AO - Système d'analyse par prompts interchangeables.

Responsabilités:
- Exécuter les analyses via différentes "Lentilles" (Pricing, Rédaction, Risque)
- Gérer les appels aux modèles Gemini appropriés
- Stocker les résultats des analyses
- Gérer les itérations sur les drafts (Petit Prompt)
"""

import json
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from app.core.logging import get_logger
from app.core.config import settings
from app.api.auth import get_supabase
from app.models.ao import (
    AOLensType, AOAnalyseDetail, AOValidationStatus,
    AODraftingRequest, AODraftingIterateRequest
)
from app.agents.base.gemini_client import GeminiClient
from app.agents.prompts.ao_prompts import ao_lens_prompts
from app.services.ao_rag_service import ao_rag_service

logger = get_logger(__name__)


class AOLensEngine:
    """Moteur d'analyse par Lentilles pour les AO."""
    
    def __init__(self):
        self.client = get_supabase()
        self._gemini_flash: Optional[GeminiClient] = None
        self._gemini_pro: Optional[GeminiClient] = None
    
    def _get_gemini_flash(self) -> GeminiClient:
        """Client Gemini Flash pour tâches rapides."""
        if self._gemini_flash is None:
            self._gemini_flash = GeminiClient(
                credentials_b64=settings.gemini_api_key,
                project_id=settings.gcp_project_id,
                location=settings.gemini_location or "europe-west1",
                model="gemini-2.5-flash-lite",
                temperature=0.1,
                max_output_tokens=2048
            )
        return self._gemini_flash
    
    def _get_gemini_pro(self) -> GeminiClient:
        """Client Gemini Pro pour analyses complexes."""
        if self._gemini_pro is None:
            self._gemini_pro = GeminiClient(
                credentials_b64=settings.gemini_api_key,
                project_id=settings.gcp_project_id,
                location=settings.gemini_location or "europe-west1",
                model="gemini-2.5-pro",
                temperature=0.2,
                max_output_tokens=8192
            )
        return self._gemini_pro
    
    async def analyze_with_lens(
        self,
        lens_type: AOLensType,
        candidature_id: UUID,
        org_id: UUID,
        contexte: Dict[str, Any],
        document_ids: Optional[List[UUID]] = None,
        created_by: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Lance une analyse via une Lentille spécifique.
        
        Args:
            lens_type: Type de lentille (pricing, redaction, risque, etc.)
            candidature_id: ID de la candidature
            org_id: ID de l'organisation
            contexte: Contexte additionnel pour l'analyse
            document_ids: Documents spécifiques à analyser (optionnel)
            created_by: ID de l'utilisateur
            
        Returns:
            Résultat de l'analyse stockée
        """
        logger.info(f"🔬 Analyse Lentille {lens_type.value} pour candidature {candidature_id}")
        
        start_time = time.time()
        
        # Récupérer la candidature
        cand_response = self.client.table("ao_candidatures")\
            .select("*")\
            .eq("id", str(candidature_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not cand_response.data:
            raise ValueError(f"Candidature {candidature_id} non trouvée")
        
        candidature = cand_response.data
        
        # Récupérer les documents si non spécifiés
        if document_ids is None:
            docs_response = self.client.table("ao_documents")\
                .select("*")\
                .eq("candidature_id", str(candidature_id))\
                .eq("statut_traitement", "processed")\
                .execute()
            document_ids = [UUID(d["id"]) for d in (docs_response.data or [])]
        
        # Router vers la bonne lentille
        if lens_type == AOLensType.PRICING:
            result = await self._lens_pricing(candidature, org_id, contexte)
            model_used = "gemini-2.5-pro"
        elif lens_type == AOLensType.REDACTION:
            result = await self._lens_redaction(candidature, org_id, contexte)
            model_used = "gemini-2.5-pro"
        elif lens_type == AOLensType.RISQUE:
            result = await self._lens_risque(candidature, document_ids, org_id)
            model_used = "gemini-2.5-pro"
        elif lens_type == AOLensType.COMPARAISON:
            result = await self._lens_comparaison(candidature, org_id)
            model_used = "gemini-2.5-pro"
        elif lens_type == AOLensType.OPPORTUNITE:
            result = await self._lens_opportunite(candidature, org_id)
            model_used = "gemini-2.5-flash-lite"
        else:
            raise ValueError(f"Type de lentille inconnu: {lens_type}")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Stocker le résultat
        analyse_data = {
            "candidature_id": str(candidature_id),
            "org_id": str(org_id),
            "lens_type": lens_type.value,
            "prompt_version": "1.0",
            "contexte": contexte,
            "documents_analyses": [str(d) for d in document_ids],
            "resultat": result,
            "score_confiance": result.get("_confiance", 0.75),
            "validation_humain": "pending",
            "duree_ms": duration_ms,
            "model_utilise": model_used,
            "created_by": str(created_by) if created_by else None
        }
        
        # Supprimer la clé interne _confiance avant stockage
        if "_confiance" in result:
            del result["_confiance"]
        
        response = self.client.table("ao_analyses").insert(analyse_data).execute()
        
        logger.info(f"✅ Analyse {lens_type.value} terminée en {duration_ms}ms")
        
        return {
            "analyse_id": response.data[0]["id"],
            "lens_type": lens_type.value,
            "resultat": result,
            "duree_ms": duration_ms,
            "model_utilise": model_used
        }
    
    async def _lens_pricing(
        self,
        candidature: Dict[str, Any],
        org_id: UUID,
        contexte: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Lentille d'analyse comparative de pricing."""
        
        # Récupérer les postes de la candidature
        postes_response = self.client.table("ao_postes_pricing")\
            .select("*")\
            .eq("candidature_id", candidature["id"])\
            .execute()
        
        postes_candidature = postes_response.data or []
        
        # Récupérer l'historique de postes similaires gagnés via RAG
        historique_gagnant = []
        
        if postes_candidature:
            # Extraire les descriptions des postes principaux pour la recherche
            descriptions_principales = []
            for poste in postes_candidature[:10]:  # Prendre les 10 premiers postes
                description = poste.get("description", "")
                if description and len(description) > 10:
                    descriptions_principales.append(description)
            
            # Rechercher des postes similaires dans l'historique gagné
            if descriptions_principales:
                # Prendre la description la plus longue comme requête
                query = max(descriptions_principales, key=len)
                
                try:
                    # Utiliser le service RAG pour trouver le contexte pricing
                    pricing_context = await ao_rag_service.get_pricing_context(
                        org_id=org_id,
                        poste_description=query,
                        limit=15
                    )
                    
                    # Extraire les postes du contexte
                    if pricing_context.get("resultats"):
                        historique_gagnant = pricing_context["resultats"]
                        logger.info(f"🔍 RAG: {len(historique_gagnant)} postes similaires trouvés pour '{query[:50]}...'")
                    else:
                        # Fallback: recherche SQL directe
                        historique_response = self.client.rpc(
                            "search_ao_postes",
                            {
                                "p_org_id": str(org_id),
                                "p_search_query": query[:100],
                                "p_limit": 15
                            }
                        ).execute()
                        historique_gagnant = historique_response.data or []
                        logger.info(f"🔍 SQL fallback: {len(historique_gagnant)} postes trouvés")
                        
                except Exception as e:
                    logger.warning(f"⚠️ RAG échoué, fallback SQL: {e}")
                    # Fallback: recherche SQL
                    historique_response = self.client.rpc(
                        "search_ao_postes",
                        {
                            "p_org_id": str(org_id),
                            "p_search_query": query[:100],
                            "p_limit": 15
                        }
                    ).execute()
                    historique_gagnant = historique_response.data or []
        
        # Construire le prompt
        system_prompt = ao_lens_prompts.PRICING_SYSTEM_PROMPT
        user_prompt = ao_lens_prompts.pricing_user_prompt(
            postes_candidature=postes_candidature,
            historique_gagnant=historique_gagnant,
            contexte_projet={
                "nom_projet": candidature.get("nom_projet"),
                "client_nom": candidature.get("client_nom"),
                "montant_total": candidature.get("montant_total")
            }
        )
        
        # Appel Gemini Pro
        gemini = self._get_gemini_pro()
        
        from google.genai import types
        
        response = gemini._client.models.generate_content(
            model=gemini.model_name,
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")]
            )],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=8192,
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        result["_confiance"] = 0.85  # Confiance estimée
        
        return result
    
    async def _lens_redaction(
        self,
        candidature: Dict[str, Any],
        org_id: UUID,
        contexte: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Lentille de rédaction de mémoire technique."""
        
        chapitre = contexte.get("chapitre", "Présentation de l'entreprise")
        
        # Récupérer les exigences du RC
        rc_docs = self.client.table("ao_documents")\
            .select("contenu_texte")\
            .eq("candidature_id", candidature["id"])\
            .eq("type_doc", "RC")\
            .execute()
        
        rc_content = rc_docs.data[0].get("contenu_texte", "") if rc_docs.data else ""
        
        # Extraire les exigences pertinentes pour ce chapitre (simplifié)
        exigences = [
            "Présenter l'organigramme de l'entreprise",
            "Décrire l'expérience sur projets similaires",
            "Détailler les moyens techniques disponibles",
            "Présenter les certifications qualité"
        ]
        
        # Récupérer des références de mémoires gagnants via RAG
        references_gagnantes = []
        
        try:
            # Utiliser le service RAG pour trouver des templates de mémoires
            memoire_template = await ao_rag_service.get_memoire_template(
                org_id=org_id,
                chapitre=chapitre,
                limit=3
            )
            
            if memoire_template.get("extraits"):
                references_gagnantes = memoire_template["extraits"]
                logger.info(f"📝 RAG: {len(references_gagnantes)} extraits trouvés pour chapitre '{chapitre}'")
            else:
                # Fallback: recherche directe en base
                refs_response = self.client.table("ao_analyses")\
                    .select("resultat")\
                    .eq("lens_type", "redaction")\
                    .eq("validation_humain", "valide")\
                    .limit(3)\
                    .execute()
                
                references_gagnantes = [
                    r.get("resultat", {}).get("content", "")[:500]
                    for r in (refs_response.data or [])
                ]
                logger.info(f"📝 SQL fallback: {len(references_gagnantes)} références trouvées")
                
        except Exception as e:
            logger.warning(f"⚠️ RAG échoué pour rédaction, fallback SQL: {e}")
            # Fallback: recherche directe en base
            refs_response = self.client.table("ao_analyses")\
                .select("resultat")\
                .eq("lens_type", "redaction")\
                .eq("validation_humain", "valide")\
                .limit(3)\
                .execute()
            
            references_gagnantes = [
                r.get("resultat", {}).get("content", "")[:500]
                for r in (refs_response.data or [])
            ]
        
        # Construire le prompt
        system_prompt = ao_lens_prompts.REDACTION_SYSTEM_PROMPT
        user_prompt = ao_lens_prompts.redaction_user_prompt(
            chapitre=chapitre,
            exigences_rc=exigences,
            references_gagnantes=references_gagnantes,
            contexte_projet={
                "nom_projet": candidature.get("nom_projet"),
                "client_nom": candidature.get("client_nom"),
                "description": candidature.get("description"),
                "montant_total": candidature.get("montant_total"),
                "duree_travaux_jours": candidature.get("duree_travaux_jours")
            }
        )
        
        # Appel Gemini Pro
        gemini = self._get_gemini_pro()
        
        from google.genai import types
        
        response = gemini._client.models.generate_content(
            model=gemini.model_name,
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")]
            )],
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=8192,
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        result["_confiance"] = 0.80
        
        return result
    
    async def _lens_risque(
        self,
        candidature: Dict[str, Any],
        document_ids: List[UUID],
        org_id: UUID
    ) -> Dict[str, Any]:
        """Lentille d'analyse des risques."""
        
        # Récupérer le contenu des documents RC et CCTP
        rc_content = ""
        cctp_content = ""
        
        for doc_id in document_ids:
            doc_response = self.client.table("ao_documents")\
                .select("type_doc, contenu_texte")\
                .eq("id", str(doc_id))\
                .single()\
                .execute()
            
            if doc_response.data:
                doc = doc_response.data
                if doc["type_doc"] == "RC":
                    rc_content = doc.get("contenu_texte", "")[:8000]
                elif doc["type_doc"] == "CCTP":
                    cctp_content = doc.get("contenu_texte", "")[:5000]
        
        if not rc_content:
            return {
                "error": "Aucun document RC trouvé pour analyse",
                "score_global": 50,
                "niveau_risque": "inconnu",
                "_confiance": 0.5
            }
        
        # Construire le prompt
        system_prompt = ao_lens_prompts.RISQUE_SYSTEM_PROMPT
        user_prompt = ao_lens_prompts.risque_user_prompt(
            contenu_rc=rc_content,
            contenu_cctp=cctp_content if cctp_content else None
        )
        
        # Appel Gemini Pro
        gemini = self._get_gemini_pro()
        
        from google.genai import types
        
        response = gemini._client.models.generate_content(
            model=gemini.model_name,
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")]
            )],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096,
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        result["_confiance"] = 0.82
        
        return result
    
    async def _lens_comparaison(
        self,
        candidature: Dict[str, Any],
        org_id: UUID
    ) -> Dict[str, Any]:
        """Lentille de comparaison avec historique."""
        
        # Récupérer des AO similaires gagnés et perdus
        gagnes = self.client.table("ao_candidatures")\
            .select("nom_projet, montant_total, client_nom, ai_score_gagner")\
            .eq("org_id", str(org_id))\
            .eq("statut", "gagne")\
            .limit(5)\
            .execute()
        
        perdus = self.client.table("ao_candidatures")\
            .select("nom_projet, montant_total, client_nom")\
            .eq("org_id", str(org_id))\
            .eq("statut", "perdu")\
            .limit(5)\
            .execute()
        
        # Construire le prompt
        system_prompt = ao_lens_prompts.COMPARAISON_SYSTEM_PROMPT
        user_prompt = ao_lens_prompts.comparaison_user_prompt(
            candidature_actuelle=candidature,
            gagnes_similaires=gagnes.data or [],
            perdus_similaires=perdus.data or []
        )
        
        # Appel Gemini Pro
        gemini = self._get_gemini_pro()
        
        from google.genai import types
        
        response = gemini._client.models.generate_content(
            model=gemini.model_name,
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")]
            )],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096,
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        result["_confiance"] = 0.75
        
        return result
    
    async def _lens_opportunite(
        self,
        candidature: Dict[str, Any],
        org_id: UUID
    ) -> Dict[str, Any]:
        """Lentille d'analyse d'opportunité (Flash-Lite)."""
        
        # Construire le prompt
        system_prompt = ao_lens_prompts.OPPORTUNITE_SYSTEM_PROMPT
        user_prompt = ao_lens_prompts.opportunite_user_prompt(
            contexte_ao=candidature
        )
        
        # Appel Gemini Flash-Lite
        gemini = self._get_gemini_flash()
        
        from google.genai import types
        
        response = gemini._client.models.generate_content(
            model=gemini.model_name,
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")]
            )],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        result["_confiance"] = 0.70
        
        return result
    
    async def iterate_draft(
        self,
        current_content: str,
        instruction: str
    ) -> Dict[str, Any]:
        """
        Itère sur un draft via le "Petit Prompt".
        
        Args:
            current_content: Contenu actuel du draft
            instruction: Instruction de modification
            
        Returns:
            Nouveau contenu et résumé des changements
        """
        logger.info(f"✏️ Itération draft: {instruction[:50]}...")
        
        system_prompt = ao_lens_prompts.PETIT_PROMPT_SYSTEM
        user_prompt = ao_lens_prompts.petit_prompt_user(
            current_content=current_content,
            instruction=instruction
        )
        
        # Appel Gemini Flash-Lite (suffisant pour l'itération)
        gemini = self._get_gemini_flash()
        
        from google.genai import types
        
        response = gemini._client.models.generate_content(
            model=gemini.model_name,
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")]
            )],
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096,
                response_mime_type="application/json"
            )
        )
        
        try:
            result = json.loads(response.text)
        except:
            # Fallback si le modèle ne retourne pas du JSON
            result = {
                "content": response.text,
                "changes_summary": "Modifications appliquées"
            }
        
        return {
            "content": result.get("content", response.text),
            "changes_summary": result.get("changes_summary", "Modifications appliquées"),
            "model_used": "gemini-2.5-flash-lite"
        }
    
    async def validate_analysis(
        self,
        analyse_id: UUID,
        org_id: UUID,
        validation: AOValidationStatus,
        commentaire: Optional[str] = None,
        valide_par: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Valide ou rejette une analyse IA."""
        
        update_data = {
            "validation_humain": validation.value,
            "valide_par": str(valide_par) if valide_par else None,
            "date_validation": datetime.utcnow().isoformat(),
            "commentaire_validation": commentaire
        }
        
        response = self.client.table("ao_analyses")\
            .update(update_data)\
            .eq("id", str(analyse_id))\
            .eq("org_id", str(org_id))\
            .execute()
        
        if not response.data:
            raise ValueError(f"Analyse {analyse_id} non trouvée")
        
        logger.info(f"✅ Analyse {analyse_id} validée: {validation.value}")
        
        return response.data[0]


# Instance singleton
ao_lens_engine = AOLensEngine()
