"""
Service RAG (Retrieval Augmented Generation) pour le Module AO.

Responsabilités:
- Recherche vectorielle dans les embeddings AO
- Recherche textuelle des postes pricing
- Extraction de contexte historique pour comparaison
- Recommandation de mémoires similaires gagnants
"""

import json
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.core.logging import get_logger
from app.api.auth import get_supabase
from app.agents.base.gemini_client import GeminiClient

logger = get_logger(__name__)


class AORAGService:
    """Service RAG pour enrichir les analyses AO avec le contexte historique."""
    
    def __init__(self):
        self.client = get_supabase()
        self._gemini_client: Optional[GeminiClient] = None
    
    def _get_embedding_client(self) -> GeminiClient:
        """Client Gemini pour générer les embeddings."""
        if self._gemini_client is None:
            from app.core.config import settings
            self._gemini_client = GeminiClient(
                credentials_b64=settings.gemini_api_key,
                project_id=settings.gcp_project_id,
                location=settings.gemini_location or "europe-west1",
                model="text-embedding-004",  # Modèle d'embedding
                temperature=0.0,
                max_output_tokens=768
            )
        return self._gemini_client
    
    # =========================================================================
    # RECHERCHE VECTORIELLE
    # =========================================================================
    
    async def search_similar_content(
        self,
        org_id: UUID,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recherche vectorielle dans les embeddings AO.
        
        Args:
            org_id: ID de l'organisation
            query: Requête textuelle
            tags: Filtre par tags (optionnel)
            limit: Nombre de résultats
            
        Returns:
            Liste des chunks similaires avec score
        """
        logger.info(f"🔍 Recherche vectorielle: '{query[:50]}...'")
        
        # Générer l'embedding de la requête
        query_embedding = await self._generate_embedding(query)
        
        # Appeler la fonction SQL de recherche
        response = self.client.rpc(
            'search_ao_embeddings',
            {
                'p_org_id': str(org_id),
                'p_query_embedding': json.dumps(query_embedding),
                'p_limit': limit,
                'p_tags': tags or []
            }
        ).execute()
        
        results = response.data or []
        
        logger.info(f"✅ {len(results)} résultats trouvés")
        
        return [
            {
                "id": r["id"],
                "doc_id": r["doc_id"],
                "candidature_id": r["candidature_id"],
                "content": r["content"],
                "similarity": r["similarity"],
                "tags": r["tags"]
            }
            for r in results
        ]
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Génère un embedding vectoriel pour un texte."""
        # Note: À implémenter avec l'API d'embedding de Gemini
        # Pour l'instant, retourne un dummy
        # Dans la vraie implémentation:
        # gemini = self._get_embedding_client()
        # response = gemini._client.models.embed_content(...)
        return [0.0] * 768  # Placeholder
    
    async def index_document(
        self,
        document_id: UUID,
        org_id: UUID,
        content: str,
        tags: List[str],
        chunk_size: int = 1000
    ) -> int:
        """
        Indexe un document dans la base vectorielle.
        
        Args:
            document_id: ID du document
            org_id: ID de l'organisation
            content: Contenu textuel à indexer
            tags: Tags pour catégoriser les chunks
            chunk_size: Taille des chunks en caractères
            
        Returns:
            Nombre de chunks créés
        """
        logger.info(f"📚 Indexation document {document_id}")
        
        # Découper le contenu en chunks
        chunks = self._chunk_text(content, chunk_size)
        
        chunks_crees = 0
        for idx, chunk in enumerate(chunks):
            try:
                # Générer l'embedding
                embedding = await self._generate_embedding(chunk)
                
                # Insérer dans ao_embeddings
                insert_data = {
                    "doc_id": str(document_id),
                    "candidature_id": None,  # À récupérer depuis le document
                    "org_id": str(org_id),
                    "content": chunk,
                    "embedding": json.dumps(embedding),
                    "tags": tags,
                    "chunk_index": idx,
                    "chunk_total": len(chunks)
                }
                
                self.client.table("ao_embeddings").insert(insert_data).execute()
                chunks_crees += 1
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur indexation chunk {idx}: {e}")
        
        logger.info(f"✅ {chunks_crees}/{len(chunks)} chunks indexés")
        return chunks_crees
    
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Découpe un texte en chunks avec chevauchement."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        overlap = chunk_size // 10  # 10% de chevauchement
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            # Trouver une coupure propre (fin de phrase)
            if end < len(text):
                while end > start and text[end] not in '.!?\n':
                    end -= 1
                if end == start:
                    end = min(start + chunk_size, len(text))
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return chunks
    
    # =========================================================================
    # RECHERCHE PRICING
    # =========================================================================
    
    async def get_pricing_context(
        self,
        org_id: UUID,
        poste_description: str,
        unite: Optional[str] = None,
        categorie: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Récupère le contexte pricing historique pour un poste donné.
        
        Args:
            org_id: ID de l'organisation
            poste_description: Description du poste à rechercher
            unite: Filtre par unité (optionnel)
            categorie: Filtre par catégorie (optionnel)
            limit: Nombre de résultats
            
        Returns:
            Contexte pricing avec prix moyen, min, max, etc.
        """
        logger.info(f"💰 Contexte pricing pour: {poste_description[:50]}...")
        
        # Recherche textuelle des postes similaires
        response = self.client.rpc(
            'search_ao_postes',
            {
                'p_org_id': str(org_id),
                'p_search_query': poste_description,
                'p_categorie': categorie,
                'p_limit': limit
            }
        ).execute()
        
        postes = response.data or []
        
        # Filtrer par unité si spécifiée
        if unite:
            postes = [p for p in postes if p.get('unite') == unite]
        
        if not postes:
            return {
                "poste_recherche": poste_description,
                "resultats": [],
                "nombre_occurrences": 0,
                "message": "Aucun poste similaire trouvé"
            }
        
        # Calculer les statistiques
        prix = [float(p["prix_unitaire_ht"]) for p in postes if p.get("prix_unitaire_ht")]
        
        if prix:
            prix_moyen = sum(prix) / len(prix)
            prix_min = min(prix)
            prix_max = max(prix)
        else:
            prix_moyen = prix_min = prix_max = None
        
        # Récupérer les candidatures correspondantes pour contexte
        candidature_ids = list(set([p["candidature_id"] for p in postes]))
        
        cand_response = self.client.table("ao_candidatures")\
            .select("id, nom_projet, client_nom, statut")\
            .in_("id", [str(c) for c in candidature_ids[:5]])\
            .execute()
        
        candidatures = {c["id"]: c for c in (cand_response.data or [])}
        
        # Enrichir les résultats
        resultats = []
        for p in postes[:limit]:
            cand = candidatures.get(p["candidature_id"], {})
            resultats.append({
                "numero": p["numero"],
                "description": p["description"],
                "unite": p["unite"],
                "prix_unitaire_ht": float(p["prix_unitaire_ht"]) if p.get("prix_unitaire_ht") else None,
                "categorie": p["categorie"],
                "projet": cand.get("nom_projet"),
                "client": cand.get("client_nom"),
                "statut_ao": cand.get("statut"),
                "rank": p.get("rank", 0)
            })
        
        return {
            "poste_recherche": poste_description,
            "resultats": resultats,
            "nombre_occurrences": len(postes),
            "prix_moyen_historique": Decimal(str(prix_moyen)) if prix_moyen else None,
            "prix_min_historique": Decimal(str(prix_min)) if prix_min else None,
            "prix_max_historique": Decimal(str(prix_max)) if prix_max else None,
            "unite": unite
        }
    
    async def find_similar_successful_ao(
        self,
        org_id: UUID,
        candidature_id: UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Trouve les AO gagnés similaires à une candidature.
        
        Args:
            org_id: ID de l'organisation
            candidature_id: ID de la candidature de référence
            limit: Nombre de résultats
            
        Returns:
            Liste des AO similaires avec score de similarité
        """
        logger.info(f"🔍 Recherche AO similaires à {candidature_id}")
        
        # Récupérer la candidature de référence
        ref_response = self.client.table("ao_candidatures")\
            .select("*")\
            .eq("id", str(candidature_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not ref_response.data:
            raise ValueError(f"Candidature {candidature_id} non trouvée")
        
        reference = ref_response.data
        
        # Récupérer les AO gagnés de l'organisation
        gagnes_response = self.client.table("ao_candidatures")\
            .select("*, ao_postes_pricing(count)")\
            .eq("org_id", str(org_id))\
            .eq("statut", "gagne")\
            .neq("id", str(candidature_id))\
            .limit(50)\
            .execute()
        
        gagnes = gagnes_response.data or []
        
        # Calculer les scores de similarité
        similar_ao = []
        for g in gagnes:
            score = 0.0
            
            # Similarité client (même client = fort bonus)
            if g.get("client_nom") and reference.get("client_nom"):
                if g["client_nom"].lower() == reference["client_nom"].lower():
                    score += 0.4
            
            # Similarité montant (±30%)
            if g.get("montant_total") and reference.get("montant_total"):
                ratio = g["montant_total"] / reference["montant_total"]
                if 0.7 <= ratio <= 1.3:
                    score += 0.3 * (1 - abs(1 - ratio))
            
            # Similarité durée
            if g.get("duree_travaux_jours") and reference.get("duree_travaux_jours"):
                ratio = g["duree_travaux_jours"] / reference["duree_travaux_jours"]
                if 0.7 <= ratio <= 1.3:
                    score += 0.2 * (1 - abs(1 - ratio))
            
            # Similarité nom projet (mots communs)
            if g.get("nom_projet") and reference.get("nom_projet"):
                words_g = set(g["nom_projet"].lower().split())
                words_ref = set(reference["nom_projet"].lower().split())
                common = words_g.intersection(words_ref)
                if common:
                    score += 0.1 * (len(common) / max(len(words_g), len(words_ref)))
            
            if score > 0.2:  # Seuil minimum
                similar_ao.append({
                    "id": g["id"],
                    "nom_projet": g["nom_projet"],
                    "client_nom": g["client_nom"],
                    "montant_total": g.get("montant_total"),
                    "score_similarite": round(score, 3),
                    "date_depot": g.get("date_depot"),
                    "nb_postes": g.get("ao_postes_pricing", [{}])[0].get("count", 0)
                })
        
        # Trier par score décroissant
        similar_ao.sort(key=lambda x: x["score_similarite"], reverse=True)
        
        return similar_ao[:limit]
    
    async def get_pricing_stats_by_category(
        self,
        org_id: UUID,
        candidature_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les statistiques de pricing par catégorie.
        
        Args:
            org_id: ID de l'organisation
            candidature_id: Si fourni, stats spécifiques à cette candidature
            
        Returns:
            Stats par catégorie
        """
        if candidature_id:
            # Stats pour une candidature spécifique
            response = self.client.rpc(
                'get_ao_pricing_stats',
                {'p_candidature_id': str(candidature_id)}
            ).execute()
        else:
            # Stats globales par catégorie pour l'org
            response = self.client.table("ao_postes_pricing")\
                .select("categorie, count, sum(prix_total_ht), avg(prix_unitaire_ht), min(prix_unitaire_ht), max(prix_unitaire_ht)")\
                .eq("org_id", str(org_id))\
                .group("categorie")\
                .execute()
        
        return response.data or []
    
    async def get_memoire_template(
        self,
        org_id: UUID,
        chapitre: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Récupère des extraits de mémoires gagnants comme templates.
        
        Args:
            org_id: ID de l'organisation
            chapitre: Nom du chapitre recherché
            limit: Nombre d'exemples
            
        Returns:
            Extraits de mémoires validés
        """
        logger.info(f"📄 Recherche templates mémoire: {chapitre}")
        
        # Recherche dans les analyses de type redaction validées
        response = self.client.table("ao_analyses")\
            .select("resultat, candidature_id, ao_candidatures(nom_projet, client_nom)")\
            .eq("lens_type", "redaction")\
            .eq("validation_humain", "valide")\
            .eq("org_id", str(org_id))\
            .limit(limit * 2)\
            .execute()
        
        templates = []
        for analysis in (response.data or []):
            resultat = analysis.get("resultat", {})
            content = resultat.get("content", "")
            
            # Vérifier si le contenu correspond au chapitre demandé
            # (simplifié: on vérifie juste si le titre du chapitre apparaît)
            if chapitre.lower() in content.lower():
                templates.append({
                    "candidature_id": analysis["candidature_id"],
                    "nom_projet": analysis.get("ao_candidatures", {}).get("nom_projet"),
                    "client_nom": analysis.get("ao_candidatures", {}).get("client_nom"),
                    "extrait": content[:2000]  # Limiter la taille
                })
            
            if len(templates) >= limit:
                break
        
        return templates
    
    async def compare_pricing_gap(
        self,
        org_id: UUID,
        categorie: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyse le gap de pricing entre AO gagnés et perdus.
        
        Args:
            org_id: ID de l'organisation
            categorie: Filtre par catégorie (optionnel)
            
        Returns:
            Analyse des écarts par catégorie
        """
        # Récupérer les stats historiques
        response = self.client.table("ao_pricing_history")\
            .select("*")\
            .eq("categorie", categorie if categorie else "")\
            .execute()
        
        history = response.data or []
        
        # Agréger par description et statut
        from collections import defaultdict
        
        poste_stats = defaultdict(lambda: {"gagne": [], "perdu": []})
        
        for h in history:
            key = (h.get("description_normalisee"), h.get("unite"))
            if h["statut"] == "gagne":
                poste_stats[key]["gagne"].append(h["prix_moyen"])
            elif h["statut"] == "perdu":
                poste_stats[key]["perdu"].append(h["prix_moyen"])
        
        # Calculer les gaps
        gaps = []
        for (desc, unite), stats in poste_stats.items():
            if stats["gagne"] and stats["perdu"]:
                prix_gagne = sum(stats["gagne"]) / len(stats["gagne"])
                prix_perdu = sum(stats["perdu"]) / len(stats["perdu"])
                
                gap_pct = ((prix_perdu - prix_gagne) / prix_gagne * 100) if prix_gagne else 0
                
                gaps.append({
                    "description": desc,
                    "unite": unite,
                    "prix_moyen_gagne": round(prix_gagne, 2),
                    "prix_moyen_perdu": round(prix_perdu, 2),
                    "gap_pct": round(gap_pct, 2),
                    "nb_gagnes": len(stats["gagne"]),
                    "nb_perdus": len(stats["perdu"])
                })
        
        # Trier par gap décroissant
        gaps.sort(key=lambda x: abs(x["gap_pct"]), reverse=True)
        
        return gaps[:20]


# Instance singleton
ao_rag_service = AORAGService()
