#!/usr/bin/env python3
"""
Debug la réponse Gemini pour comprendre le problème JSON.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

def debug_json_response():
    """Debug la réponse JSON de Gemini."""
    
    # Exemple de réponse tronquée (similaire aux logs)
    response_text = """{
    "is_forward": true,
    "email_chain": [
        {
            "index": 0,
            "is_original": false,
            "from_email": "REDACTED_CONTACT",
            "from_name": "REDACTED_CONTACT",
            "to_emails": [
                "REDACTED_EMAIL"
            ],
            "cc_emails": [],
            "bcc_emails": [],
            "subject": "TR: CR RC 21/04 - P14 Porte d'Orléans",
            "date": "2026-04-21T13:12:38+00:00",
            ..."""
    
    print("🧪 Debug de la réponse JSON")
    print("=" * 50)
    
    # Le problème: réponse JSON tronquée ou mal formée
    print("⚠️  Problème identifié: JSON invalide (tronqué)")
    print(f"   Longueur de la réponse: {len(response_text)} caractères")
    print(f"   Derniers 100 caractères: {response_text[-100:]}")
    
    # Essayer de parser pour voir l'erreur exacte
    try:
        data = json.loads(response_text)
        print("✅ JSON valide!")
    except json.JSONDecodeError as e:
        print(f"❌ Erreur JSON: {e}")
        print(f"   Position: {e.pos}")
        print(f"   Ligne: {e.lineno}, Colonne: {e.colno}")
        
        # Afficher le contexte autour de l'erreur
        start = max(0, e.pos - 50)
        end = min(len(response_text), e.pos + 50)
        print(f"   Contexte: ...{response_text[start:end]}...")
    
    # Problème probable: Gemini retourne une réponse trop longue/tronquée
    print("\n🔍 Causes possibles:")
    print("   1. Gemini dépasse max_output_tokens (8192)")
    print("   2. La réponse est tronquée par l'API")
    print("   3. JSON mal formé (guillemets non fermés, etc.)")
    
    # Solution: réduire la taille de l'input ou augmenter max_output_tokens
    print("\n🎯 Solutions:")
    print("   1. Augmenter max_output_tokens dans EmailExtractionAgent")
    print("   2. Tronquer l'input envoyé à Gemini")
    print("   3. Améliorer le parsing JSON (plus tolérant)")
    
    return True

def test_json_parsing_improvement():
    """Teste une amélioration du parsing JSON."""
    print("\n" + "=" * 50)
    print("🧪 Test d'amélioration du parsing JSON")
    print("=" * 50)
    
    # Réponse JSON problématique (avec string non fermée)
    bad_json = '''{
    "is_forward": true,
    "email_chain": [
        {
            "index": 0,
            "body": "Contenu avec "guillemets" problématiques et
lignes multiples..."
        }
    ]
}'''
    
    print("📝 JSON problématique:")
    print(bad_json)
    
    # Méthode de nettoyage améliorée
    def clean_json_response(text):
        """Nettoie une réponse JSON potentiellement mal formée."""
        # Supprimer les marqueurs de code
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
        
        # Essayer de parser d'abord
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Tentative de réparation
            # 1. Fermer les strings ouvertes
            lines = text.split('\n')
            repaired = []
            in_string = False
            escape_next = False
            
            for line in lines:
                new_line = []
                for char in line:
                    if escape_next:
                        new_line.append(char)
                        escape_next = False
                    elif char == '\\':
                        new_line.append(char)
                        escape_next = True
                    elif char == '"':
                        new_line.append(char)
                        in_string = not in_string
                    else:
                        new_line.append(char)
                
                # Si on est encore dans une string à la fin de la ligne, ajouter un guillemet
                if in_string:
                    new_line.append('"')
                    in_string = False
                
                repaired.append(''.join(new_line))
            
            repaired_text = '\n'.join(repaired)
            
            # Essayer de parser à nouveau
            try:
                return json.loads(repaired_text)
            except json.JSONDecodeError as e:
                print(f"⚠️  Réparation échouée: {e}")
                # Fallback: extraire avec regex
                import re
                # Chercher un objet JSON simple
                match = re.search(r'\{.*\}', repaired_text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group())
                    except:
                        pass
                
                return {"error": "JSON invalide", "original_text": text[:500]}
    
    print("\n🔧 Test de nettoyage...")
    result = clean_json_response(bad_json)
    print(f"✅ Résultat: {result}")
    
    return True

if __name__ == "__main__":
    debug_json_response()
    test_json_parsing_improvement()