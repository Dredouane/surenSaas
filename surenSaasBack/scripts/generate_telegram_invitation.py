#!/usr/bin/env python3
"""
Script pour générer une invitation Telegram pour un utilisateur.
Usage: python generate_telegram_invitation.py <user_id> [bot_id]
"""

import sys
import os

# Configuration
os.environ['ENVIRONMENT'] = 'test'

# Ajouter le backend au path
sys.path.insert(0, '/home/redouane/dev/AI-ERA/surenSaas/surenSaasBack')

from app.services.telegram_invitation_service import telegram_invitation_service
from app.api.auth import get_supabase

def generate_invitation(user_id: str, bot_id: str = "construction"):
    """Génère un lien d'invitation Telegram."""
    
    print(f"🔍 Recherche de l'utilisateur {user_id}...")
    
    # Récupérer l'utilisateur
    supabase = get_supabase()
    user_result = supabase.table('users') \
        .select('id, email, full_name, org_id') \
        .eq('id', user_id) \
        .single() \
        .execute()
    
    if not user_result.data:
        print(f"❌ Utilisateur {user_id} non trouvé")
        return None
    
    user = user_result.data
    print(f"✅ Utilisateur trouvé: {user.get('full_name')} ({user['email']})")
    print(f"   Organisation: {user['org_id']}")
    
    # Vérifier si le bot est configuré
    bot_config = telegram_invitation_service.get_bot_config(bot_id)
    if not bot_config:
        print(f"❌ Bot '{bot_id}' non configuré")
        print("   Vérifiez que SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN est défini")
        return None
    
    print(f"✅ Bot configuré: @{bot_config.username}")
    
    # Générer l'invitation
    try:
        invitation = telegram_invitation_service.generate_invitation_link(
            user_id=user_id,
            org_id=user['org_id'],
            bot_id=bot_id,
            expires_in_hours=168  # 7 jours
        )
        
        print("\n" + "="*70)
        print("🎉 INVITATION GÉNÉRÉE AVEC SUCCÈS")
        print("="*70)
        print(f"\n📱 Lien Telegram:")
        print(f"   {invitation['telegram_link']}")
        print(f"\n👤 Utilisateur: {user.get('full_name')}")
        print(f"📧 Email: {user['email']}")
        print(f"🤖 Bot: @{invitation['bot_username']}")
        print(f"⏰ Expire le: {invitation['expires_at']}")
        print(f"\n💡 Instructions:")
        print(f"   1. Cliquez sur le lien ci-dessus")
        print(f"   2. Le bot s'ouvrira dans Telegram")
        print(f"   3. Cliquez sur 'Démarrer' (/start)")
        print(f"   4. Votre compte sera automatiquement lié")
        print("="*70)
        
        return invitation
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_telegram_invitation.py <user_id> [bot_id]")
        print("Example: python generate_telegram_invitation.py c45f6626-ec5e-459d-9dc5-340c3181f3e8 construction")
        sys.exit(1)
    
    user_id = sys.argv[1]
    bot_id = sys.argv[2] if len(sys.argv) > 2 else "construction"
    
    generate_invitation(user_id, bot_id)
