#!/usr/bin/env python3
"""
Script pour appliquer la migration AO (027_ao_tables.sql) à Supabase.

Usage:
    python apply_ao_migration.py

Prérequis:
    - Variables d'environnement SUPABASE_URL et SUPABASE_SERVICE_KEY configurées
    - Ou fichier .env à la racine du projet
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du backend
sys.path.insert(0, str(Path(__file__).parent / 'surenSaasBack'))

from app.core.config import settings
from app.api.auth import get_supabase

def apply_migration():
    """Applique la migration SQL pour les tables AO."""
    
    migration_file = Path(__file__).parent / 'db' / 'schema' / '027_ao_tables.sql'
    
    if not migration_file.exists():
        print(f"❌ Fichier de migration non trouvé: {migration_file}")
        return False
    
    print(f"📄 Lecture de la migration: {migration_file}")
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    print(f"📊 Taille du script SQL: {len(sql)} caractères")
    
    # Connexion Supabase
    try:
        client = get_supabase()
        print("✅ Connexion Supabase établie")
    except Exception as e:
        print(f"❌ Erreur connexion Supabase: {e}")
        return False
    
    # Exécuter le SQL
    # Note: Supabase Python client ne supporte pas directement l'exécution de SQL arbitraire
    # Il faut utiliser la fonction RPC ou l'API REST directement
    
    print("\n⚠️  IMPORTANT: La migration doit être appliquée via l'interface Supabase:")
    print("\n1. Allez dans l'interface Supabase: https://app.supabase.io")
    print("2. Sélectionnez votre projet")
    print("3. Allez dans 'SQL Editor'")
    print("4. Copiez-collez le contenu du fichier:")
    print(f"   {migration_file}")
    print("5. Exécutez le script")
    print("\nAlternative avec CLI Supabase:")
    print(f"   supabase db reset --db-url {settings.supabase_url}")
    print("\nOu avec psql:")
    print(f"   psql {settings.supabase_url} -f {migration_file}")
    
    return True

if __name__ == "__main__":
    apply_migration()
