#!/usr/bin/env python3
"""
Tests d'intégration réels avec l'API Gemini — SCÉNARIOS MÉTIER COMPLETS.
╔══════════════════════════════════════════════════════════════════════════════╗
║  ATTENTION : Ces tests font de VRAIS appels à Gemini — ils sont PAYANTS.  ║
║  ~17 appels par exécution complète.                                       ║
║  Ne les lance que pour valider le comportement réel après modif.           ║
╚══════════════════════════════════════════════════════════════════════════════╝

Workflows testés (vrais appels Gemini, zéro mock) :
  - TestFluxAvancement  (6 scénarios) : extraction quantite/prix_unitaire/%depuis texte libre
  - TestFluxOperation   (7 scénarios) : classification type + extraction montant/quantite
  - TestFluxDepense     (4 scénarios) : extraction fournisseur/montant/categorie

Chaque scénario simule un input utilisateur réel et vérifie que le format
de sortie est exactement celui attendu par les handlers des workflows Telegram.

Architecture utilisée :
  agents/workflow_extractor.py → WorkflowExtractor
  agents/base/gemini_client.py → GeminiClient (nouvelle lib google-genai, Vertex AI)
  agents/prompts/telegram/     → system_extraction.txt + user_instructions.json

Comment ajouter un scénario :
  1. Ajoute une méthode test_* dans la classe appropriée
  2. Appelle extractor.extract("input texte", "workflow_type")
  3. Vérifie les clés dans result["extracted_data"]
  4. Vérifie les calculs métier si besoin

Prérequis :
  source ~/.bashrc  (qui contient SUREN_GOOGLE_GEMINI_CREDENTIALS_B64)
  ou export GEMINI_API_KEY="..."

Lancement :
  cd surenSaasBack
  source ~/.bashrc && python3 -m pytest tests/scenarios-real-call-ai.py -v -s -m integration
"""

import os
import sys
import json
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.workflow_extractor import WorkflowExtractor


def _has_credentials():
    return bool(
        os.getenv("SUREN_GOOGLE_GEMINI_CREDENTIALS_B64")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("TEST_GOOGLE_GEMINI_CREDENTIALS_B64")
    )


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _has_credentials(), reason="Aucune clé API Gemini configurée"),
]


@pytest.fixture
def extractor():
    return WorkflowExtractor()


# ====================================================================
# AVANCEMENT — Flux complet
# ====================================================================

class TestFluxAvancement:
    """Scénarios réels d'avancement. Vérifie le format exact attendu par
    handle_avancement_input_data (lignes 73-97 de bot_construction_avancements.py)."""

    def test_enduit_facade_50m2_25euro_80pc(self, extractor):
        """
        Input: "Enduit façade 50m2 25€/m2 80%"
        Handler attend: description, quantite, prix_unitaire, avancement_pourcentage
        Dans extract_and_refine_avancement: montant_total = quantite * prix_unitaire
                                             avancement_montant = montant_total * avancement_pourcentage / 100
        """
        result = extractor.extract("Enduit façade 50m2 25€/m2 80%", "avancement")
        print(f"\n[Enduit façade] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        description = d.get("description")
        quantite = d.get("quantite")
        prix_unitaire = d.get("prix_unitaire")
        avancement = d.get("avancement_pourcentage")

        assert description, f"description manquante ou vide: {d}"
        assert quantite is not None, f"quantite manquant: {d}"
        assert prix_unitaire is not None, f"prix_unitaire manquant: {d}"
        assert avancement is not None, f"avancement_pourcentage manquant: {d}"

        qte_f = float(quantite)
        pu_f = float(prix_unitaire)
        pct_f = float(avancement)
        assert qte_f == 50, f"quantite devrait être 50, reçu {qte_f}"
        assert pu_f == 25, f"prix_unitaire devrait être 25, reçu {pu_f}"
        assert pct_f == 80, f"avancement_pourcentage devrait être 80, reçu {pct_f}"

        mt = qte_f * pu_f
        am = mt * pct_f / 100
        print(f"  => Vérification calculs: montant_total={mt}, avancement_montant={am}")
        assert mt == 1250, f"montant_total devrait être 1250, calculé {mt}"
        assert am == 1000, f"avancement_montant devrait être 1000, calculé {am}"

    def test_peinture_couloir_120m2_18euro_100pc(self, extractor):
        """
        Input: "Peinture couloir RDC 120m2 18€/m2 100%"
        """
        result = extractor.extract("Peinture couloir RDC 120m2 18€/m2 100%", "avancement")
        print(f"\n[Peinture couloir] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("quantite") is not None
        assert float(d["quantite"]) == 120
        assert float(d.get("prix_unitaire", 0)) == 18
        assert float(d.get("avancement_pourcentage", 0)) == 100

    def test_carrelage_sdb_15m2_45euro_60pc(self, extractor):
        """
        Input: "Carrelage salle de bain 15m2 45€/m2 60%"
        """
        result = extractor.extract("Carrelage salle de bain 15m2 45€/m2 60%", "avancement")
        print(f"\n[Carrelage SdB] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert float(d.get("quantite", 0)) == 15
        assert float(d.get("prix_unitaire", 0)) == 45
        assert float(d.get("avancement_pourcentage", 0)) == 60

    def test_texte_libre_sans_chiffres(self, extractor):
        """
        Input: "J'ai fini la pose du carrelage dans la cuisine"
        Pas de quantite/prix → null. avancement doit être déduit (100% si "fini").
        """
        result = extractor.extract("J'ai fini la pose du carrelage dans la cuisine", "avancement")
        print(f"\n[texte libre] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("description"), f"description devrait exister: {d}"
        # Pas de chiffres → null
        assert d.get("quantite") is None, f"quantite devrait être null pas de chiffres: {d}"
        assert d.get("prix_unitaire") is None, f"prix_unitaire devrait être null pas de chiffres: {d}"

    def test_electricite_200m_ml_15euro_50pc(self, extractor):
        """
        Input: "Tirage câbles électriques 200ml 15€/ml 50%"
        Vérifie que l'unité 'ml' (mètre linéaire) est reconnue.
        """
        result = extractor.extract("Tirage câbles électriques 200ml 15€/ml 50%", "avancement")
        print(f"\n[Électricité ml] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert float(d.get("quantite", 0)) == 200
        assert float(d.get("prix_unitaire", 0)) == 15
        assert float(d.get("avancement_pourcentage", 0)) == 50
        assert d.get("unite") in ("ml", "m", "mètre", None), f"unité inattendue: {d.get('unite')}"

    def test_terrassement_sans_prix_30pc(self, extractor):
        """
        Input: "Terrassement fondations 300m3 30%"
        Pas de prix unitaire mentionné → doit être null.
        """
        result = extractor.extract("Terrassement fondations 300m3 30%", "avancement")
        print(f"\n[Terrassement] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert float(d.get("quantite", 0)) == 300
        assert d.get("prix_unitaire") is None, f"prix_unitaire devrait être null (pas mentionné): {d}"
        assert float(d.get("avancement_pourcentage", 0)) == 30


# ====================================================================
# OPÉRATION — Flux complet
# ====================================================================

class TestFluxOperation:
    """Scénarios réels d'opérations HITL.
    Format attendu par handle_operation_media : type, description, montant, quantite, unite."""

    def test_demolition_mur_porteur(self, extractor):
        """
        Input: "Démolition mur porteur au RDC 2500€"
        Attend: type=demolition, montant=2500
        """
        result = extractor.extract("Démolition mur porteur au RDC 2500€", "operation")
        print(f"\n[Démolition] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("type") == "demolition", f"type devrait être demolition: {d}"
        assert float(d.get("montant", 0)) == 2500, f"montant devrait être 2500: {d}"
        assert d.get("description"), f"description manquante: {d}"

    def test_nettoyage_chantier(self, extractor):
        """
        Input: "Nettoyage du chantier après démolition"
        Attend: type=nettoyage, pas de montant
        """
        result = extractor.extract("Nettoyage du chantier après démolition", "operation")
        print(f"\n[Nettoyage] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("type") == "nettoyage", f"type devrait être nettoyage: {d}"

    def test_pose_bso(self, extractor):
        """
        Input: "Pose BSO baie vitrée salon 3 unités"
        Attend: type=pose_bso, quantite=3
        """
        result = extractor.extract("Pose BSO baie vitrée salon 3 unités", "operation")
        print(f"\n[Pose BSO] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("type") == "pose_bso", f"type devrait être pose_bso: {d}"
        # 3 unités doit être extrait
        assert d.get("quantite") is not None, f"quantite devrait exister: {d}"

    def test_commande_ciment(self, extractor):
        """
        Input: "Commande de 50 sacs de ciment chez Point P"
        Attend: type=commande, quantite=50
        """
        result = extractor.extract("Commande de 50 sacs de ciment chez Point P", "operation")
        print(f"\n[Commande ciment] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("type") == "commande", f"type devrait être commande: {d}"
        assert float(d.get("quantite", 0)) == 50, f"quantite devrait être 50: {d}"

    def test_achat_materiel_avec_montant(self, extractor):
        """
        Input: "Achat carrelage salle de bain 850€"
        Attend: type=achat_materiel, montant=850
        """
        result = extractor.extract("Achat carrelage salle de bain 850€", "operation")
        print(f"\n[Achat matériel] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("type") == "achat_materiel", f"type devrait être achat_materiel: {d}"
        assert float(d.get("montant", 0)) == 850, f"montant devrait être 850: {d}"

    def test_sous_traitance_plomberie(self, extractor):
        """
        Input: "Sous-traitance plomberie par SARL EAU 4500€"
        Attend: type=sous_traitance, montant=4500
        """
        result = extractor.extract("Sous-traitance plomberie par SARL EAU 4500€", "operation")
        print(f"\n[Sous-traitance] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("type") == "sous_traitance", f"type devrait être sous_traitance: {d}"
        assert float(d.get("montant", 0)) == 4500

    def test_autre_operation(self, extractor):
        """
        Input: "Réunion de coordination avec le maître d'oeuvre"
        Attend: type=autre (rien dans la liste des types connus)
        """
        result = extractor.extract("Réunion de coordination avec le maître d'oeuvre", "operation")
        print(f"\n[Autre] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("type") == "autre", f"type devrait être autre: {d}"


# ====================================================================
# DÉPENSE — Flux complet
# ====================================================================

class TestFluxDepense:
    """Scénarios réels de dépenses.
    Format attendu par handle_depense_media : fournisseur, montant, description, categorie."""

    def test_facture_art_concept(self, extractor):
        """
        Input: "Facture ART CONCEPT plomberie 3200€"
        Attend: fournisseur="ART CONCEPT", montant=3200, categorie="fournisseur"
        """
        result = extractor.extract("Facture ART CONCEPT plomberie 3200€", "depense")
        print(f"\n[ART CONCEPT] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("fournisseur") == "ART CONCEPT", f"fournisseur devrait être ART CONCEPT: {d}"
        assert float(d.get("montant", 0)) == 3200, f"montant devrait être 3200: {d}"
        assert d.get("categorie") == "fournisseur", f"categorie devrait être fournisseur: {d}"

    def test_sous_traitant_elec(self, extractor):
        """
        Input: "Sous-traitant électricité SARL ELEC 5800€ TTC"
        Attend: fournisseur="SARL ELEC", montant=5800, categorie="sous_traitant"
        """
        result = extractor.extract("Sous-traitant électricité SARL ELEC 5800€ TTC", "depense")
        print(f"\n[SARL ELEC] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("fournisseur") == "SARL ELEC", f"fournisseur devrait être SARL ELEC: {d}"
        assert float(d.get("montant", 0)) == 5800, f"montant devrait être 5800: {d}"
        assert d.get("categorie") == "sous_traitant", f"categorie devrait être sous_traitant: {d}"

    def test_bob_renov_fournisseur(self, extractor):
        """
        Input: "Facture BOB RENOV fournitures 1250€"
        Attend: fournisseur="BOB RENOV", montant=1250
        """
        result = extractor.extract("Facture BOB RENOV fournitures 1250€", "depense")
        print(f"\n[BOB RENOV] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        assert d.get("fournisseur") == "BOB RENOV", f"fournisseur devrait être BOB RENOV: {d}"
        assert float(d.get("montant", 0)) == 1250

    def test_depense_sans_fournisseur_sans_montant(self, extractor):
        """
        Input: "Achat de consommables divers"
        Ni fournisseur ni montant clair → null.
        """
        result = extractor.extract("Achat de consommables divers", "depense")
        print(f"\n[Consommables] Résultat:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result.get("_fallback") is not True

        d = result.get("extracted_data") or result
        # Pas de montant mentionné → null
        assert d.get("montant") is None or float(d.get("montant", 0)) == 0, f"montant devrait être 0/null: {d}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
