#!/usr/bin/env python3
"""
Test direct de l'extraction d'email avec l'agent IA.
"""

import asyncio
import sys
import os
import json

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "surenSaasBack"))

# Mock des variables d'environnement
os.environ.update({
    'GEMINI_API_KEY': 'mock' if 'GOOGLE_GEMINI_CREDENTIALS_B64' not in os.environ else '',
    'GCP_PROJECT_ID': 'suren-saas',
    'VERTEX_AI_LOCATION': 'europe-west1',
    'SUPABASE_URL': 'mock',
    'SUPABASE_SERVICE_KEY': 'mock',
    'DEBUG': 'true'
})

async def test_with_real_email():
    """Test avec un email réel (à remplacer par le vrai contenu)."""
    print("🧪 Test direct de l'extraction d'email")
    
    # REMPLACE CE CONTENU PAR LE VRAI CONTENU DE L'EMAIL
    # Tu peux le récupérer depuis Gmail ou la base de données
    email_content = """
TR: CR RC 21/04 - P14 Porte d'Orléans

[INSÉRER ICI LE VRAI CONTENU DE L'EMAIL]
"""
    
    if "[INSÉRER" in email_content:
        print("❌ Remplace le contenu de l'email dans le script!")
        print("   Récupère-le depuis Gmail ou la base de données.")
        return
    
    from app.agents.email_agent import EmailExtractionAgent
    from app.services.emails.content_cleaner import content_cleaner
    
    print(f"📧 Taille de l'email: {len(email_content)} caractères")
    print(f"📧 200 premiers caractères: {email_content[:200]}...")
    print()
    
    # Test avec l'agent IA
    print("1. Test avec l'agent IA:")
    try:
        agent = EmailExtractionAgent()
        extracted_ia = await agent.extract_email(
            raw_content=email_content,
            raw_subject="TR: CR RC 21/04 - P14 Porte d'Orléans"
        )
        
        print(f"   ✅ Sujet IA: {extracted_ia.subject}")
        print(f"   ✅ From IA: {extracted_ia.from_email} ({extracted_ia.from_name})")
        print(f"   ✅ To IA: {extracted_ia.to_emails}")
        print(f"   ✅ Body cleaned IA (100 premiers): {extracted_ia.body_cleaned[:100]}...")
        print(f"   ✅ Taille body cleaned: {len(extracted_ia.body_cleaned)} caractères")
    except Exception as e:
        print(f"   ❌ Erreur IA: {e}")
    
    print()
    
    # Test avec regex
    print("2. Test avec regex (content_cleaner):")
    try:
        extracted_regex = content_cleaner.extract_original(
            email_content,
            "TR: CR RC 21/04 - P14 Porte d'Orléans"
        )
        
        print(f"   ✅ Sujet regex: {extracted_regex.subject}")
        print(f"   ✅ From regex: {extracted_regex.from_email} ({extracted_regex.from_name})")
        print(f"   ✅ To regex: {extracted_regex.to_emails}")
        print(f"   ✅ Body cleaned regex (100 premiers): {extracted_regex.body_cleaned[:100]}...")
        print(f"   ✅ Taille body cleaned: {len(extracted_regex.body_cleaned)} caractères")
    except Exception as e:
        print(f"   ❌ Erreur regex: {e}")
    
    print()
    
    # Comparaison
    print("3. Comparaison:")
    if 'extracted_ia' in locals() and 'extracted_regex' in locals():
        print(f"   Sujets identiques: {extracted_ia.subject == extracted_regex.subject}")
        print(f"   From identiques: {extracted_ia.from_email == extracted_regex.from_email}")
        print(f"   Body cleaned similaires: {extracted_ia.body_cleaned[:50] == extracted_regex.body_cleaned[:50]}")
        
        # Afficher les différences
        if extracted_ia.body_cleaned != extracted_regex.body_cleaned:
            print(f"   ⚠️ Différences dans le body cleaned!")
            print(f"   IA length: {len(extracted_ia.body_cleaned)}, Regex length: {len(extracted_regex.body_cleaned)}")


def analyze_email_structure():
    """Analyse la structure de l'email."""
    print("\n🔍 Analyse de la structure d'email")
    
    # Remplacer par le vrai contenu
    email_content = "[CONTENU DE L'EMAIL]"
    
    from app.services.emails.content_cleaner import ContentCleaner
    cleaner = ContentCleaner()
    
    # Vérifier les séparateurs
    print("Séparateurs trouvés:")
    for pattern in cleaner.FORWARD_SEPARATOR_PATTERNS:
        import re
        if re.search(pattern, email_content, re.IGNORECASE):
            print(f"  ✓ {pattern[:40]}...")
    
    # Vérifier les headers
    print("\nHeaders potentiels:")
    header_patterns = ["De :", "From :", "À :", "To :", "Objet :", "Subject :", "Date :", "Envoyé :"]
    for pattern in header_patterns:
        if pattern in email_content:
            print(f"  ✓ {pattern}")


if __name__ == "__main__":
    print("🚀 Debug de l'extraction d'email")
    print("=" * 50)
    
    # Demander le contenu de l'email
    print("\nPour debugger, j'ai besoin du contenu réel de l'email.")
    print("Tu peux:")
    print("1. Le copier depuis Gmail (afficher l'original)")
    print("2. Le récupérer depuis la base de données")
    print("3. Utiliser l'API pour le récupérer")
    print()
    print("Ensuite, remplace le contenu dans le script et relance-le.")
    
    # Exécuter les tests
    asyncio.run(test_with_real_email())
    analyze_email_structure()