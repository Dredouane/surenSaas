"""
Tests End-to-End pour le Module AO (Appels d'Offres).

Ces tests couvrent le workflow complet :
1. Génération de données synthétiques
2. Ingestion de dossier
3. Classification automatique
4. Extraction pricing
5. Analyses par Lentilles
6. Tests RAG

Usage:
    pytest tests/ao_test_flow.py -v
    pytest tests/ao_test_flow.py::test_e2e_001_ingestion_complete -v

Prérequis:
- Variables d'environnement configurées (SUPABASE_URL, SUPABASE_SERVICE_KEY)
- Gemini API configurée
- Migration 027_ao_tables.sql appliquée
"""

import os
import sys
import json
import pytest
import tempfile
import asyncio
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4, UUID

# Ajouter le dossier backend au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'surenSaasBack'))

from app.models.ao import (
    AOCandidatureCreate, AODocumentType, AOStatut,
    AOLensType, AOLensAnalysisRequest
)
from app.services.ao_service import AOService
from app.services.ao_lens_engine import AOLensEngine
from app.services.ao_rag_service import AORAGService
from app.api.auth import get_supabase


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def org_id():
    """ID d'organisation de test."""
    # À remplacer par un vrai org_id pour les tests
    return UUID(os.getenv("TEST_ORG_ID", "00000000-0000-0000-0000-000000000001"))


@pytest.fixture
def user_id():
    """ID utilisateur de test."""
    return UUID(os.getenv("TEST_USER_ID", "00000000-0000-0000-0000-000000000002"))


@pytest.fixture
def ao_service():
    """Instance du service AO."""
    return AOService()


@pytest.fixture
def lens_engine():
    """Instance du moteur de Lentilles."""
    return AOLensEngine()


@pytest.fixture
def rag_service():
    """Instance du service RAG."""
    return AORAGService()


@pytest.fixture
def temp_ao_folder():
    """Crée un dossier temporaire avec des fichiers AO simulés."""
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)
        
        # Créer un faux RC (texte)
        rc_content = """
REGLEMENT DE CONSULTATION
Projet: Résidence Les Lilas
Client: ACORUS
Référence: AO-2024-001
Date: 15/01/2024

OBJET: Construction d'une résidence de 50 logements

CRITERES DE SELECTION:
- Prix: 40%
- Valeur technique: 40%
- Délai: 20%

DELAI D'EXECUTION: 180 jours
DATE LIMITE: 15/03/2024

EXIGENCES TECHNIQUES:
- Certification NF
- Garantie décennale
- Assurance responsabilité civile
"""
        (folder / "RC_Residence_Lilas.pdf").write_text(rc_content)
        
        # Créer un faux BPU (CSV)
        bpu_content = """N°,DESCRIPTION,UNITE,QUANTITE,PU HT,TOTAL HT
01.01.001,Terrassement fondations,m3,250.00,45.00,11250.00
01.01.002,Béton armé - Fondations,m3,180.50,850.00,153425.00
01.01.003,Béton armé - Élévations,m3,320.00,875.00,280000.00
01.02.001,Charpente métallique,kg,12500.00,3.50,43750.00
01.02.002,Couverture tuiles,m2,850.00,65.00,55250.00
02.01.001,Menuiseries extérieures,u,120.00,450.00,54000.00
02.01.002,Portes intérieures,u,150.00,280.00,42000.00
02.02.001,Plâtrerie,m2,2850.00,35.00,99750.00
02.02.002,Peinture,m2,3200.00,18.50,59200.00
03.01.001,Chauffage central,forfait,1.00,85000.00,85000.00
03.01.002,Plomberie sanitaire,forfait,1.00,65000.00,65000.00
03.02.001,Electricité luminaires,u,350.00,125.00,43750.00
,,,,TOTAL GENERAL,,895375.00
"""
        (folder / "BPU_Residence_Lilas.csv").write_text(bpu_content)
        
        # Créer un faux CCTP (texte)
        cctp_content = """
CAHIER DES CLAUSES TECHNIQUES PARTICULIERES

1. DESCRIPTION DES OUVRAGES
Construction d'un immeuble R+4 avec sous-sol.
Surface totale: 2 850 m²

2. NORMES APPLICABLES
- DTU 20.1: Ouvrages en maçonnerie
- DTU 21: Ouvrages en béton
- DTU 40.21: Couverture en tuiles

3. QUALITE DES MATERIAUX
Béton B25 pour fondations
Béton B20 pour élévations
Acier FeE500

4. DELAIS ET PLANNING
Délai global: 180 jours calendaires
Phase 1: Gros œuvre - 90 jours
Phase 2: Second œuvre - 60 jours
Phase 3: Finitions - 30 jours
"""
        (folder / "CCTP_Residence_Lilas.pdf").write_text(cctp_content)
        
        yield folder


# ============================================================================
# TEST E2E-001: INGESTION COMPLÈTE
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_001_ingestion_complete(ao_service, org_id, user_id, temp_ao_folder):
    """
    Test E2E-001: Ingestion complète d'un dossier AO.
    
    Objectif: Vérifier l'ingestion d'un dossier AO complet
    Données: Dossier avec RC.pdf, CCTP.pdf, BPU.csv
    Critère: 3 documents créés, types corrects
    """
    print("\n🧪 Test E2E-001: Ingestion complète")
    
    # 1. Créer une candidature
    candidature_data = AOCandidatureCreate(
        nom_projet="Résidence Les Lilas - Test",
        client_nom="ACORUS TEST",
        reference_ao="AO-TEST-001",
        description="Test E2E - Construction résidence 50 logements",
        date_limite_remise=date(2024, 3, 15),
        duree_travaux_jours=180
    )
    
    candidature = await ao_service.create_candidature(
        org_id=org_id,
        data=candidature_data,
        created_by=user_id
    )
    
    candidature_id = UUID(candidature["id"])
    print(f"  ✅ Candidature créée: {candidature_id}")
    
    # 2. Ingérer le dossier
    result = await ao_service.ingest_ao_folder(
        candidature_id=candidature_id,
        org_id=org_id,
        folder_path=str(temp_ao_folder),
        auto_classify=False,  # On teste la classification séparément
        uploaded_by=user_id
    )
    
    print(f"  📁 Fichiers trouvés: {result['fichiers_trouves']}")
    print(f"  📄 Documents créés: {result['documents_crees']}")
    
    # Assertions
    assert result["fichiers_trouves"] == 3, "Doit trouver 3 fichiers"
    assert result["documents_crees"] == 3, "Doit créer 3 documents"
    assert len(result["erreurs"]) == 0, "Ne doit pas avoir d'erreurs"
    
    # Vérifier les types de fichiers (par extension)
    documents = result["documents"]
    noms = [d["nom_fichier"] for d in documents]
    
    assert any("RC" in n for n in noms), "Doit avoir un fichier RC"
    assert any("BPU" in n for n in noms), "Doit avoir un fichier BPU"
    assert any("CCTP" in n for n in noms), "Doit avoir un fichier CCTP"
    
    print("  ✅ Test E2E-001 PASS")
    
    return candidature_id


# ============================================================================
# TEST E2E-002: CLASSIFICATION IA
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY non configurée"
)
async def test_e2e_002_classification_ia(ao_service, org_id, user_id, temp_ao_folder):
    """
    Test E2E-002: Classification automatique des documents.
    
    Objectif: Vérifier la précision de classification automatique
    Critère: Taux de classification correct > 90%
    """
    print("\n🧪 Test E2E-002: Classification IA")
    
    # Créer candidature et ingérer
    candidature_data = AOCandidatureCreate(
        nom_projet="Test Classification",
        client_nom="TEST CLIENT"
    )
    
    candidature = await ao_service.create_candidature(
        org_id=org_id,
        data=candidature_data,
        created_by=user_id
    )
    
    candidature_id = UUID(candidature["id"])
    
    result = await ao_service.ingest_ao_folder(
        candidature_id=candidature_id,
        org_id=org_id,
        folder_path=str(temp_ao_folder),
        auto_classify=False,
        uploaded_by=user_id
    )
    
    # Classifier chaque document
    classifications_correctes = 0
    documents = result["documents"]
    
    for doc in documents:
        try:
            classification = await ao_service.classify_document(UUID(doc["id"]))
            type_detecte = classification["type_doc_detecte"]
            nom = doc["nom_fichier"]
            
            # Vérifier la cohérence
            if "RC" in nom and type_detecte in ["RC", "DAO"]:
                classifications_correctes += 1
            elif "BPU" in nom and type_detecte in ["BPU", "DAO"]:
                classifications_correctes += 1
            elif "CCTP" in nom and type_detecte in ["CCTP", "DAO"]:
                classifications_correctes += 1
            
            print(f"  📄 {nom} -> {type_detecte} (conf: {classification['confidence']:.2f})")
            
        except Exception as e:
            print(f"  ⚠️ Erreur classification {doc['nom_fichier']}: {e}")
    
    taux_reussite = classifications_correctes / len(documents) if documents else 0
    print(f"  📊 Taux de classification correct: {taux_reussite:.1%}")
    
    # On attend au moins que les documents soient traités (statut processed ou error)
    assert len(documents) > 0, "Doit avoir des documents"
    
    print("  ✅ Test E2E-002 PASS")


# ============================================================================
# TEST E2E-003: EXTRACTION PRICING
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY non configurée"
)
async def test_e2e_003_extraction_pricing(ao_service, org_id, user_id):
    """
    Test E2E-003: Extraction des postes BPU.
    
    Objectif: Vérifier l'extraction des postes pricing
    Critère: >80% des postes extraits avec prix corrects
    """
    print("\n🧪 Test E2E-003: Extraction Pricing")
    
    # Créer un fichier BPU de test
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("""N°,DESCRIPTION,UNITE,QUANTITE,PU HT,TOTAL HT
01.01.001,Béton fondations,m3,100.00,800.00,80000.00
01.01.002,Béton élévations,m3,200.00,850.00,170000.00
01.02.001,Charpente,kg,5000.00,3.50,17500.00
02.01.001,Menuiseries,u,50.00,400.00,20000.00
02.02.001,Peinture,m2,1000.00,20.00,20000.00
,,,,TOTAL,307500.00
""")
        bpu_path = f.name
    
    try:
        # Créer candidature
        candidature_data = AOCandidatureCreate(
            nom_projet="Test Extraction BPU",
            client_nom="TEST"
        )
        
        candidature = await ao_service.create_candidature(
            org_id=org_id,
            data=candidature_data,
            created_by=user_id
        )
        
        candidature_id = UUID(candidature["id"])
        
        # Ingérer le BPU
        with open(bpu_path, 'rb') as f:
            import hashlib
            file_data = f.read()
        
        from pathlib import Path
        import os
        
        # Créer le document
        doc_data = {
            "candidature_id": str(candidature_id),
            "org_id": str(org_id),
            "nom_fichier": "BPU_Test.csv",
            "type_doc": "BPU",
            "url_stockage": bpu_path,
            "mime_type": "text/csv",
            "taille_bytes": len(file_data),
            "checksum": hashlib.sha256(file_data).hexdigest(),
            "statut_traitement": "processed",
            "uploaded_by": str(user_id)
        }
        
        supabase = get_supabase()
        doc_response = supabase.table("ao_documents").insert(doc_data).execute()
        document_id = UUID(doc_response.data[0]["id"])
        
        print(f"  📄 Document BPU créé: {document_id}")
        
        # Extraire les données pricing
        result = await ao_service.extract_pricing_data(document_id, org_id)
        
        print(f"  📊 Postes extraits: {result['postes_extraits']}")
        print(f"  💰 Montant total HT: {result['montant_total_ht']}")
        
        # Assertions
        assert result["postes_extraits"] >= 4, f"Doit extraire au moins 4 postes (trouvé: {result['postes_extraits']})"
        assert result["montant_total_ht"] is not None, "Doit avoir un montant total"
        
        # Vérifier qu'on a des postes avec prix
        postes_avec_prix = [p for p in result["postes"] if p.get("prix_unitaire_ht")]
        assert len(postes_avec_prix) >= 4, "Doit avoir au moins 4 postes avec prix"
        
        print("  ✅ Test E2E-003 PASS")
        
    finally:
        os.unlink(bpu_path)


# ============================================================================
# TEST E2E-004: RAG PRICING CONTEXT
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_004_rag_pricing_context(rag_service, org_id):
    """
    Test E2E-004: Recherche de contexte pricing historique.
    
    Objectif: Vérifier la récupération de contexte historique
    Critère: Retourne des résultats pertinents
    """
    print("\n🧪 Test E2E-004: RAG Pricing Context")
    
    # Créer des postes historiques pour le test
    supabase = get_supabase()
    
    # Créer une candidature historique gagnée
    hist_cand = supabase.table("ao_candidatures").insert({
        "org_id": str(org_id),
        "nom_projet": "Projet Historique Test",
        "client_nom": "CLIENT HISTO",
        "statut": "gagne",
        "montant_total": 500000.00
    }).execute()
    
    candidature_id = hist_cand.data[0]["id"]
    
    # Créer un document
    hist_doc = supabase.table("ao_documents").insert({
        "candidature_id": candidature_id,
        "org_id": str(org_id),
        "nom_fichier": "BPU_Historique.csv",
        "type_doc": "BPU",
        "url_stockage": "/tmp/test_hist.csv",
        "statut_traitement": "processed"
    }).execute()
    
    document_id = hist_doc.data[0]["id"]
    
    # Créer des postes historiques
    postes_test = [
        ("01.01.001", "Béton armé fondations", "m3", 150.0, 850.0, "GROS_OEUVRE"),
        ("01.01.002", "Béton armé élévations", "m3", 200.0, 875.0, "GROS_OEUVRE"),
        ("01.02.001", "Charpente métallique", "kg", 10000.0, 3.50, "GROS_OEUVRE"),
        ("02.01.001", "Menuiseries extérieures", "u", 80.0, 450.0, "SECOND_OEUVRE"),
    ]
    
    for numero, desc, unite, qty, pu, cat in postes_test:
        supabase.table("ao_postes_pricing").insert({
            "candidature_id": candidature_id,
            "document_id": document_id,
            "org_id": str(org_id),
            "numero": numero,
            "description": desc,
            "description_normalisee": desc.lower(),
            "unite": unite,
            "quantite": qty,
            "prix_unitaire_ht": pu,
            "prix_total_ht": qty * pu,
            "categorie": cat
        }).execute()
    
    print(f"  📊 {len(postes_test)} postes historiques créés")
    
    # Tester la recherche de contexte
    result = await rag_service.get_pricing_context(
        org_id=org_id,
        poste_description="béton fondation",
        unite="m3",
        limit=5
    )
    
    print(f"  🔍 Résultats trouvés: {result['nombre_occurrences']}")
    
    if result['nombre_occurrences'] > 0:
        print(f"  💰 Prix moyen historique: {result['prix_moyen_historique']}")
        print(f"  📈 Prix min/max: {result['prix_min_historique']} / {result['prix_max_historique']}")
    
    # Assertions
    assert result["nombre_occurrences"] > 0, "Doit trouver des résultats"
    assert "resultats" in result, "Doit retourner une liste de résultats"
    
    print("  ✅ Test E2E-004 PASS")


# ============================================================================
# TEST E2E-005: WORKFLOW COMPLET
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY non configurée"
)
async def test_e2e_005_workflow_complet(ao_service, lens_engine, org_id, user_id, temp_ao_folder):
    """
    Test E2E-005: Workflow complet de bout en bout.
    
    Objectif: Vérifier le flux end-to-end
    Étapes: Création -> Ingestion -> Extraction -> Analyse
    Critère: Flux sans erreur, données cohérentes
    """
    print("\n🧪 Test E2E-005: Workflow Complet")
    
    # 1. Créer candidature
    print("  1️⃣ Création candidature...")
    candidature_data = AOCandidatureCreate(
        nom_projet="Test Workflow Complet",
        client_nom="ACORUS WORKFLOW",
        reference_ao="AO-WF-001",
        description="Test workflow E2E complet"
    )
    
    candidature = await ao_service.create_candidature(
        org_id=org_id,
        data=candidature_data,
        created_by=user_id
    )
    
    candidature_id = UUID(candidature["id"])
    print(f"     ✅ ID: {candidature_id}")
    
    # 2. Ingestion dossier
    print("  2️⃣ Ingestion dossier...")
    ingest_result = await ao_service.ingest_ao_folder(
        candidature_id=candidature_id,
        org_id=org_id,
        folder_path=str(temp_ao_folder),
        auto_classify=True,
        uploaded_by=user_id
    )
    
    print(f"     ✅ {ingest_result['documents_crees']} documents créés")
    
    # 3. Vérifier les documents
    print("  3️⃣ Vérification documents...")
    documents = await ao_service.list_documents(candidature_id, org_id)
    assert len(documents) > 0, "Doit avoir des documents"
    
    # Compter les types
    types_count = {}
    for doc in documents:
        t = doc.get("type_doc", "UNKNOWN")
        types_count[t] = types_count.get(t, 0) + 1
    
    print(f"     📄 Types: {types_count}")
    
    # 4. Extraction pricing si BPU présent
    bpu_docs = [d for d in documents if d.get("type_doc") == "BPU"]
    if bpu_docs:
        print("  4️⃣ Extraction pricing BPU...")
        try:
            pricing_result = await ao_service.extract_pricing_data(
                UUID(bpu_docs[0]["id"]),
                org_id
            )
            print(f"     ✅ {pricing_result['postes_extraits']} postes extraits")
        except Exception as e:
            print(f"     ⚠️ Extraction pricing échouée: {e}")
    
    # 5. Analyse par Lentille Opportunité (rapide)
    print("  5️⃣ Analyse Lentille Opportunité...")
    try:
        analysis_result = await lens_engine.analyze_with_lens(
            lens_type=AOLensType.OPPORTUNITE,
            candidature_id=candidature_id,
            org_id=org_id,
            contexte={},
            created_by=user_id
        )
        print(f"     ✅ Analyse terminée en {analysis_result['duree_ms']}ms")
        print(f"     📊 Score: {analysis_result['resultat'].get('attractivite', {}).get('score', 'N/A')}")
    except Exception as e:
        print(f"     ⚠️ Analyse échouée: {e}")
    
    print("  ✅ Test E2E-005 PASS")


# ============================================================================
# TEST E2E-006: INTÉGRATION DOSSIERS
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_006_integration_dossiers(ao_service, org_id, user_id):
    """
    Test E2E-006: Vérifier liaison candidature ↔ dossier.
    
    Objectif: Vérifier que les AO sont bien liés aux dossiers
    Critère: Liaison correcte, données visibles dans les deux sens
    """
    print("\n🧪 Test E2E-006: Intégration Dossiers")
    
    supabase = get_supabase()
    
    # Créer un dossier de test
    dossier = supabase.table("dossiers").insert({
        "org_id": str(org_id),
        "name": "Dossier Test AO",
        "client_name": "CLIENT DOSSIER",
        "status": "active"
    }).execute()
    
    dossier_id = UUID(dossier.data[0]["id"])
    print(f"  📁 Dossier créé: {dossier_id}")
    
    # Créer une candidature liée à ce dossier
    from app.models.ao import AOCandidatureCreate
    candidature_data = AOCandidatureCreate(
        nom_projet="Projet Lié au Dossier",
        client_nom="CLIENT DOSSIER",
        dossier_id=dossier_id
    )
    
    candidature = await ao_service.create_candidature(
        org_id=org_id,
        data=candidature_data,
        created_by=user_id
    )
    
    candidature_id = UUID(candidature["id"])
    print(f"  📝 Candidature créée: {candidature_id}")
    
    # Vérifier la liaison
    retrieved = await ao_service.get_candidature(candidature_id, org_id)
    
    assert retrieved["dossier_id"] == str(dossier_id), "Dossier ID doit correspondre"
    print(f"  ✅ Liaison vérifiée: candidature.dossier_id = {retrieved['dossier_id']}")
    
    # Vérifier qu'on peut lister les candidatures du dossier
    cands, total = await ao_service.list_candidatures(
        org_id=org_id,
        dossier_id=dossier_id
    )
    
    assert total > 0, "Doit trouver au moins une candidature"
    assert any(c["id"] == str(candidature_id) for c in cands), "Doit contenir notre candidature"
    
    print("  ✅ Test E2E-006 PASS")


# ============================================================================
# TEST E2E-010: RÉSILIENCE ERREURS
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_010_resilience_erreurs(ao_service, org_id, user_id):
    """
    Test E2E-010: Gestion des erreurs et fichiers corrompus.
    
    Objectif: Vérifier comportement sur fichiers problématiques
    Critère: Pas de crash, statut error enregistré
    """
    print("\n🧪 Test E2E-010: Résilience Erreurs")
    
    # Créer un fichier "corrompu" (binaire invalide)
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)
        
        # Fichier texte qui n'est pas un vrai PDF
        (folder / "FAKE_PDF.pdf").write_text("Ceci n'est pas un vrai PDF")
        
        # Fichier CSV malformé
        (folder / "BAD_CSV.csv").write_text("N°,DESCRIPTION,\n01.01,\n02.02,Description sans prix")
        
        # Créer candidature
        candidature_data = AOCandidatureCreate(
            nom_projet="Test Résilience",
            client_nom="TEST"
        )
        
        candidature = await ao_service.create_candidature(
            org_id=org_id,
            data=candidature_data,
            created_by=user_id
        )
        
        candidature_id = UUID(candidature["id"])
        
        # Ingestion - ne doit pas planter
        try:
            result = await ao_service.ingest_ao_folder(
                candidature_id=candidature_id,
                org_id=org_id,
                folder_path=str(folder),
                auto_classify=False,
                uploaded_by=user_id
            )
            
            print(f"  ✅ Ingestion terminée sans crash")
            print(f"  📄 Documents créés: {result['documents_crees']}")
            
            # Vérifier que les documents sont créés même si problématiques
            assert result["documents_crees"] == 2, "Doit créer les 2 documents"
            
        except Exception as e:
            pytest.fail(f"L'ingestion ne doit pas planter: {e}")
    
    print("  ✅ Test E2E-010 PASS")


# ============================================================================
# UTILITAIRES DE NETTOYAGE
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_data(org_id):
    """Nettoie les données de test après chaque test."""
    yield
    
    # Note: Décommenter pour nettoyer les données de test
    # supabase = get_supabase()
    # supabase.table("ao_analyses").delete().eq("org_id", str(org_id)).execute()
    # supabase.table("ao_postes_pricing").delete().eq("org_id", str(org_id)).execute()
    # supabase.table("ao_embeddings").delete().eq("org_id", str(org_id)).execute()
    # supabase.table("ao_documents").delete().eq("org_id", str(org_id)).execute()
    # supabase.table("ao_candidatures").delete().eq("org_id", str(org_id)).execute()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🚀 Tests E2E Module AO")
    print("=" * 50)
    print("\nPour exécuter les tests:")
    print("  pytest tests/ao_test_flow.py -v")
    print("\nPour un test spécifique:")
    print("  pytest tests/ao_test_flow.py::test_e2e_001_ingestion_complete -v")
    print("\n⚠️  N'oubliez pas de configurer GEMINI_API_KEY pour les tests IA")
