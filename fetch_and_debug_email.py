#!/usr/bin/env python3
"""
Récupère un email depuis la base et debug l'extraction.
"""

import asyncio
import sys
import os
import json

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "surenSaasBack"))

# Configuration minimale
os.environ.update({
    'SUPABASE_URL': 'https://REDACTED.supabase.co',
    'DEBUG': 'true'
})

async def fetch_email_from_db(email_id: str = None, message_id: str = None):
    """Récupère un email depuis la base de données."""
    print(f"🔍 Récupération de l'email depuis la base...")
    
    from app.services.email_database_service import EmailDatabaseService
    
    db = EmailDatabaseService()
    
    if email_id:
        print(f"   Recherche par email_id: {email_id}")
        email = await db.get_email(email_id)
    elif message_id:
        print(f"   Recherche par message_id: {message_id}")
        email = await db.get_email_by_message_id(message_id)
    else:
        print("❌ Spécifie email_id ou message_id")
        return None
    
    if email:
        print(f"✅ Email trouvé: {email.get('subject', 'Sans sujet')[:50]}...")
        return email
    else:
        print("❌ Email non trouvé")
        return None

async def debug_email_extraction(email_data: dict):
    """Debug l'extraction d'un email."""
    print("\n🧪 Debug de l'extraction")
    print("=" * 50)
    
    raw_content = email_data.get("content_text_raw", "")
    subject = email_data.get("subject", "")
    
    print(f"📧 Sujet original: {subject}")
    print(f"📧 Taille du contenu brut: {len(raw_content)} caractères")
    print(f"📧 300 premiers caractères du brut:")
    print("-" * 50)
    print(raw_content[:300])
    print("-" * 50)
    print()
    
    # Test avec content_cleaner (regex)
    from app.services.emails.content_cleaner import content_cleaner
    
    print("1. Extraction avec content_cleaner (regex):")
    extracted_regex = content_cleaner.extract_original(raw_content, subject)
    
    print(f"   ✅ Sujet extrait: {extracted_regex.subject}")
    print(f"   ✅ From: {extracted_regex.from_email} ({extracted_regex.from_name})")
    print(f"   ✅ To: {extracted_regex.to_emails}")
    print(f"   ✅ Date: {extracted_regex.date}")
    print(f"   ✅ Body cleaned (200 premiers):")
    print("   " + extracted_regex.body_cleaned[:200].replace("\n", "\n   "))
    print(f"   ✅ Taille body cleaned: {len(extracted_regex.body_cleaned)} caractères")
    print()
    
    # Test avec agent IA (si credentials disponibles)
    print("2. Extraction avec agent IA:")
    try:
        from app.agents.email_agent import EmailExtractionAgent
        
        agent = EmailExtractionAgent()
        extracted_ia = await agent.extract_email(
            raw_content=raw_content,
            raw_subject=subject
        )
        
        print(f"   ✅ Sujet extrait: {extracted_ia.subject}")
        print(f"   ✅ From: {extracted_ia.from_email} ({extracted_ia.from_name})")
        print(f"   ✅ To: {extracted_ia.to_emails}")
        print(f"   ✅ Date: {extracted_ia.date}")
        print(f"   ✅ Body cleaned (200 premiers):")
        print("   " + extracted_ia.body_cleaned[:200].replace("\n", "\n   "))
        print(f"   ✅ Taille body cleaned: {len(extracted_ia.body_cleaned)} caractères")
        print()
        
        # Comparaison
        print("3. Comparaison IA vs Regex:")
        print(f"   Sujets identiques: {extracted_ia.subject == extracted_regex.subject}")
        print(f"   From identiques: {extracted_ia.from_email == extracted_regex.from_email}")
        
        if extracted_ia.body_cleaned != extracted_regex.body_cleaned:
            print(f"   ⚠️ Body cleaned DIFFÉRENT!")
            print(f"   IA length: {len(extracted_ia.body_cleaned)}")
            print(f"   Regex length: {len(extracted_regex.body_cleaned)}")
            
            # Trouver les différences
            ia_lines = extracted_ia.body_cleaned.split('\n')
            regex_lines = extracted_regex.body_cleaned.split('\n')
            
            print(f"   IA lines: {len(ia_lines)}, Regex lines: {len(regex_lines)}")
            
            # Afficher les premières lignes différentes
            for i in range(min(10, len(ia_lines), len(regex_lines))):
                if ia_lines[i] != regex_lines[i]:
                    print(f"   Ligne {i+1} différente:")
                    print(f"     IA: {ia_lines[i][:100]}")
                    print(f"     Regex: {regex_lines[i][:100]}")
                    break
        
    except Exception as e:
        print(f"   ❌ Erreur agent IA: {e}")
        import traceback
        traceback.print_exc()
    
    # Analyse de la structure
    print("\n4. Analyse de la structure:")
    from app.services.emails.content_cleaner import ContentCleaner
    cleaner = ContentCleaner()
    
    is_forward = cleaner.detect_forward(raw_content)
    print(f"   Détecté comme forward: {is_forward}")
    
    # Chercher les séparateurs
    print("   Séparateurs trouvés:")
    found = False
    for pattern in cleaner.FORWARD_SEPARATOR_PATTERNS:
        import re
        matches = list(re.finditer(pattern, raw_content, re.IGNORECASE))
        if matches:
            found = True
            print(f"     ✓ {pattern[:40]}... ({len(matches)} fois)")
            for match in matches[:2]:  # Afficher les 2 premiers
                start = max(0, match.start() - 50)
                end = min(len(raw_content), match.end() + 50)
                print(f"       Position {match.start()}: ...{raw_content[start:end]}...")
    
    if not found:
        print("     ✗ Aucun séparateur standard trouvé")
        
        # Chercher TR: ou autres indicateurs
        if "TR:" in raw_content.upper():
            print("     ✓ 'TR:' trouvé (Transmis)")
        if "FW:" in raw_content.upper() or "FWD:" in raw_content.upper():
            print("     ✓ 'FW:' ou 'FWD:' trouvé")
        if "RE:" in raw_content.upper():
            print("     ✓ 'RE:' trouvé (Réponse)")
    
    # Chercher des patterns de headers
    print("\n   Patterns de headers trouvés:")
    header_patterns = [
        (r"De\s*:\s*", "De :"),
        (r"From\s*:\s*", "From :"),
        (r"À\s*:\s*", "À :"),
        (r"To\s*:\s*", "To :"),
        (r"Objet\s*:\s*", "Objet :"),
        (r"Subject\s*:\s*", "Subject :"),
        (r"Date\s*:\s*", "Date :"),
        (r"Envoyé\s*:\s*", "Envoyé :"),
    ]
    
    for pattern, name in header_patterns:
        import re
        if re.search(pattern, raw_content, re.IGNORECASE):
            print(f"     ✓ {name}")

async def main():
    """Fonction principale."""
    print("🚀 Debug de l'extraction d'email")
    print("=" * 50)
    
    # Demander quel email debugger
    print("\nOptions:")
    print("1. Email par message_id (ex: 19db02c16b1ced99)")
    print("2. Email par email_id (UUID)")
    print()
    
    choice = input("Choix (1 ou 2): ").strip()
    
    if choice == "1":
        message_id = input("message_id: ").strip()
        email_data = await fetch_email_from_db(message_id=message_id)
    elif choice == "2":
        email_id = input("email_id: ").strip()
        email_data = await fetch_email_from_db(email_id=email_id)
    else:
        print("❌ Choix invalide")
        return
    
    if email_data:
        await debug_email_extraction(email_data)
    else:
        print("❌ Impossible de récupérer l'email")

if __name__ == "__main__":
    # Le SUPABASE_SERVICE_KEY doit être dans l'environnement
    if 'SUPABASE_SERVICE_KEY' not in os.environ:
        print("⚠️  SUPABASE_SERVICE_KEY non défini dans l'environnement")
        print("   Exporte-le: export SUPABASE_SERVICE_KEY=ton_clef")
        sys.exit(1)
    
    asyncio.run(main())