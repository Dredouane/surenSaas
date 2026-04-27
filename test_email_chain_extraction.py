#!/usr/bin/env python3
"""
Test d'extraction de chaîne d'emails avec l'agent IA.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

async def test_email_chain_extraction():
    """Teste l'extraction d'une chaîne d'emails."""
    from app.agents.email_agent import EmailExtractionAgent
    from app.core.config import settings
    
    print("🧪 Test d'extraction de chaîne d'emails")
    print("=" * 50)
    
    # Exemple de chaîne d'emails (similaire à ton email)
    raw_content = """Cordialement REDACTED_CONTACT
REDACTED_PHONE
REDACTED_CONTACT
Service études / EXE
28 boulevard de Strasbourg
93600 Aulnay-sous-Bois
www.arev-travaux.fr

De : CAROFF, Enzo
Envoyé : mardi 21 avril 2026 14:55
À : 'Vasile BOC' ; Suren SHIRVANYAN ; REDACTED_CONTACT ; j.boutry ; Carlos DE ALMEID
Cc : ROUSSEAUX, Dimitri ; GONSOLIN, Mayeul ; FASSIH, Youssef ; DA SILVA, Fabien
Objet : CR RC 21/04 - P14 Porte d'Orléans

Bonjour Messieurs,

Vous trouverez ci-dessous le CR de la réunion de coordination de ce jour :

AREV/BOC/WELL : Sécurité : BOC doit resensibiliser ses intervenants sur le stockage et la surcharge de l'échafaudage + resensibiliser sur le fait que les intervenants ne doivent en aucun cas modifier l'échafaudage lors de leurs travaux AREV doit revoir son mode opératoire pour le nettoyage des façades et ce dès aujourd'hui (polyane de protection au droit des halls + ventelles + grilles + joints des fenêtres avant lavage) AREV doit également revoir son mode opératoire PLOMB, protection des plateaux d'échafaudage avec polyane au niveau des garde-corps qui sont traités, protections individuelles sur les intervenants qui travaillent dessus ECHECKIN : Aucune amélioration depuis octobre -> A clôturer pour le 28/04/26 Prochaine réunion de coordination : mardi 28/04/26 à 10H30 ! Réserves : AREV, 3 jours pour lever les réserves après réception BOC, 5 jours pour lever les réserves Sinistres : AREV et BOC traitent les réclamations par leurs propres moyens MAXIMUM 2 semaines pour effectuer les travaux AREV a commencé a traité des réclamations -> A poursuivre BOC doit voir avec le prestataire d'AREV pour le 28/04/26 afin de trouver une solution AREV : 2005 : Portion ROUGE : Date prévisionnelle des OPR le 19/03 OPR décalées au 26/03 OPR décalées au 02/04 car MOE non disponible le 26/03 Réserves non-levées à ce jour, à clôturer pour le 17/04 ! Réserves à clôturer pour le 21/04 ! Portion BLEU : Date prévisionnelle des OPR jeudi 02/04 OPR décalées au 09/04 car travaux non-terminés OPR décalées au 16/04 car travaux non-terminés Levée des réserves à clôturer pour le 21/04 Portion ORANGE : OPR prévues le 16/04 OPR décalées au 23/04 car travaux non-terminés OPR décalées au 30/04 car travaux non-terminés Prévoir le nettoyage du 7 et 8 e étage jeudi 23/04 + 5 mailles supplémentaires Portion VIOLETTE : OPR prévues le 07/05 Démarrage travaux RDC : Date de démarrage à communiquer lors de la prochaine réunion de coordination 2004 : Portion ORANGE : OPR prévisionnelles le 02/04/26 OPR décalées au 09/04/26 Réserves à lever pour le 14/04/26 Réserves à clôturer pour le 22/04 ! Portion VERTE : OPR prévisionnelles le 30/04/26 Nouvelle date à confirmer aujourd'hui Portion BLEU : OPR prévisionnelles le 30/04/26 Portion ROUGE : OPR prévisionnelles le 07/05/26 Nouvelle date à confirmer aujourd'hui 1096 : Témoin escalier de service : Date de démarrage à confirmer Echafaudage réceptionné le vendredi 17/04 BOC : 2005 : Portion ROUGE : OPR prévues le 02/04/26 OPR décalées au 09/04/26 car travaux non terminés Levée des réserves à clôturer pour le 16/04/26 Réserves clôturées le 17/04 Portion BLEU : OPR prévues le 09/04/26 OPR décalées au 16/04/26 car travaux non terminés OPR décalées au 23/04/26 car travaux non terminés Portion ORANGE : OPR prévues le 16/04/26 OPR décalées au 23/04/26 car travaux non terminés OPR décalées au 30/04/26 car travaux non terminés BOC doit laisser intervenir AREV sur cette portion jeudi 23/04 + 5 mailles suivantes Portion VIOLETTE : OPR prévues le 07/05/26 2004 : Portion ORANGE : OPR prévisionnelles le 09/04/26 Levée des réserves à clôturer pour le 16/04/26 Réserves non levées, à clôturer pour le 22/04/26 ! Portion ROUGE : OPR prévisionnelles le 07/05 Portion VERTE : OPR prévisionnelles le 14/05 Portion BLEU : OPR prévisionnelles le 30/04 Vous en souhaitant bonne réception, Bien cordialement, Enzo Caroff Conducteur de travaux DT Paris - HAS REDACTED_PHONE e.caroff@bouygues-construction.com 1, avenue Eugène Freyssinet - Challenger 1NO14 / EC05 78061 GUYANCOURT - SAINT-QUENTIN-EN- YVELINES - Cedex FRANCE www.bouygues-construction.com www.bouygues-batiment-ile-de-france.com

De : CAROFF, Enzo
Envoyé : mardi 14 avril 2026 12:33
À : 'Vasile BOC' < v.boc@groupetcpr.com >; 'Suren SHIRVANYAN' < s.vanyan@REDACTED_DOMAIN >; 'REDACTED_CONTACT' < REDACTED_CONTACT >; j.boutry < j.boutry@wellechafaudage.com >; 'carlos.dealmeida@REDACTED_DOMAIN' < carlos.dealmeida@REDACTED_DOMAIN >
Cc : ROUSSEAUX, Dimitri < di.rousseaux@bouygues-construction.com >; GONSOLIN, Mayeul < m.gonsolin@bouygues-construction.com >; FASSIH, Youssef < y.fassih@bouygues-construction.com >; DA SILVA, Fabien < fa.dasilva@bouygues-construction.com >
Objet : CR RC 14/04 - P14 Porte d'Orléans

Bonjour Messieurs,

Vous trouverez ci-dessous le CR de la réunion de coordination de ce jour :

AREV/BOC/WELL : Sécurité : BOC doit resensibiliser ses intervenants sur le stockage et la surcharge de l'échaf"""

    raw_subject = "TR: CR RC 21/04 - P14 Porte d'Orléans"
    
    print(f"📧 Sujet: {raw_subject}")
    print(f"📏 Taille du contenu: {len(raw_content)} caractères")
    print(f"🔍 Détection de chaîne: {'De :' in raw_content or 'From :' in raw_content}")
    print(f"🔢 Nombre de 'De :': {raw_content.count('De :')}")
    print(f"🔢 Nombre de 'From :': {raw_content.count('From :')}")
    
    try:
        # Initialiser l'agent
        print("\n🔧 Initialisation de l'agent EmailExtractionAgent...")
        agent = EmailExtractionAgent()
        
        # Tester l'extraction de chaîne
        print("🤖 Appel à extract_email_chain...")
        email_chain = await agent.extract_email_chain(
            raw_content=raw_content,
            raw_subject=raw_subject,
            headers=None
        )
        
        print(f"\n✅ Chaîne extraite avec succès!")
        print(f"📊 Métadonnées: {email_chain.metadata}")
        print(f"🔗 Nombre d'emails dans la chaîne: {len(email_chain.emails)}")
        
        for i, email in enumerate(email_chain.emails):
            print(f"\n📧 Email {i+1}/{len(email_chain.emails)}:")
            print(f"   Index: {email.index}")
            print(f"   Original: {email.is_original}")
            print(f"   De: {email.from_email} ({email.from_name})")
            print(f"   À: {email.to_emails[:3]}...")  # Afficher seulement les 3 premiers
            print(f"   Sujet: {email.subject[:50]}...")
            print(f"   Date: {email.date}")
            print(f"   Taille du corps: {len(email.body)} caractères")
            print(f"   Headers: {email.headers_text[:100]}..." if email.headers_text else "   Headers: (vide)")
        
        # Tester aussi l'extraction simple (legacy)
        print("\n🧪 Test de l'extraction simple (legacy)...")
        extracted_email = await agent.extract_email(
            raw_content=raw_content,
            raw_subject=raw_subject,
            headers=None
        )
        
        print(f"✅ Email simple extrait:")
        print(f"   De: {extracted_email.from_email}")
        print(f"   Sujet: {extracted_email.subject[:50]}...")
        print(f"   Taille nettoyée: {len(extracted_email.body_cleaned)} caractères")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Vérifier les variables d'environnement
    if 'GOOGLE_GEMINI_CREDENTIALS_B64' not in os.environ:
        print("⚠️  GOOGLE_GEMINI_CREDENTIALS_B64 non défini")
        print("   Exporte la variable: export GOOGLE_GEMINI_CREDENTIALS_B64='...'")
        sys.exit(1)
    
    if 'GCP_PROJECT_ID' not in os.environ:
        print("⚠️  GCP_PROJECT_ID non défini")
        print("   Exporte la variable: export GCP_PROJECT_ID='suren-saas'")
        sys.exit(1)
    
    result = asyncio.run(test_email_chain_extraction())
    if result:
        print("\n🎉 Test réussi!")
    else:
        print("\n❌ Test échoué!")
        sys.exit(1)