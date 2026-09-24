#!/usr/bin/env python3
"""
🔧 Script pour mettre à jour les mots de passe via SQL direct

Usage:
    python scripts/update-test-passwords-sql.py
"""

import os
import sys

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("TEST_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

# SQL pour mettre à jour les mots de passe
# Note: Ceci ne fonctionnera que si vous avez accès à la console SQL Supabase
SQL_SCRIPT = """
-- Mettre à jour les mots de passe des utilisateurs de test
-- Les mots de passe doivent être hashés par Supabase Auth

DO $$
DECLARE
    user_record RECORD;
BEGIN
    -- Pour chaque utilisateur de test
    FOR user_record IN 
        SELECT id, email 
        FROM auth.users 
        WHERE email LIKE 'test-e2e-%@suren.com'
    LOOP
        -- Générer un nouveau hash de mot de passe
        -- Note: En pratique, vous devriez utiliser l'API auth.admin
        RAISE NOTICE 'Mise à jour: %', user_record.email;
    END LOOP;
END $$;
"""

print("🔧 Mise à jour des mots de passe")
print("=" * 50)
print()
print("⚠️  Pour mettre à jour les mots de passe, vous devez:")
print()
print("Option 1 - SQL (recommandé):")
print("  1. Allez dans Supabase Dashboard > SQL Editor")
print("  2. Exécutez cette requête pour voir les utilisateurs:")
print()
print("     SELECT id, email, email_confirmed_at ")
print("     FROM auth.users ")
print("     WHERE email LIKE 'test-e2e-%@suren.com';")
print()
print("Option 2 - API Directe:")
print("  Utilisez l'API Supabase Auth avec service_role:")
print()
print("Option 3 - Recréer les utilisateurs:")
print("  Supprimez les utilisateurs existants et relancez le script de création")
print()
print("💡 Les utilisateurs existent avec ces mots de passe aléatoires:")
print("   test-e2e-admin@suren.com: [mot de passe aléatoire]")
print("   test-e2e-conducteur@suren.com: [mot de passe aléatoire]")
print("   test-e2e-gerant@suren.com: [mot de passe aléatoire]")
print("   test-e2e-comptable@suren.com: [mot de passe aléatoire]")
print()
print("📝 Pour les tests E2E, utilisez les identifiants affichés")
print("   lors de la création des utilisateurs.")
