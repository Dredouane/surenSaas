#!/usr/bin/env python3
"""
Script pour configurer les variables Cloudflare R2.
Exécutez ce script pour vérifier et configurer les credentials R2.
"""

import os
import sys
from pathlib import Path

def check_r2_config():
    """Vérifie la configuration R2 actuelle."""
    print("🔍 Vérification de la configuration Cloudflare R2...")
    
    # Variables requises
    required_vars = [
        "SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT",
        "SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID", 
        "SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY",
        "SUREN_GED_CLOUDFLARE_TOKEN",
        "SUREN_GED_CLOUDFLARE_BUCKET_NAME"
    ]
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Fichier .env non trouvé dans le répertoire courant")
        return False
    
    # Lire le fichier .env
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    # Vérifier les variables
    missing = []
    for var in required_vars:
        if var not in env_vars or not env_vars[var]:
            missing.append(var)
    
    if missing:
        print(f"❌ Variables R2 manquantes: {', '.join(missing)}")
        print("\n📝 Pour configurer R2, ajoutez ces variables à votre fichier .env:")
        print("""
# Cloudflare R2 Configuration (S3-Compatible)
SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT=https://xxx.r2.cloudflarestorage.com
SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID=your_access_key_id
SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY=your_secret_access_key
SUREN_GED_CLOUDFLARE_TOKEN=optional_token_if_needed
SUREN_GED_CLOUDFLARE_BUCKET_NAME=your_bucket_name
""")
        return False
    
    print("✅ Toutes les variables R2 sont configurées")
    
    # Tester la connexion
    print("\n🔗 Test de connexion à R2...")
    try:
        from app.services.file_storage_service import FileStorageService
        service = FileStorageService()
        print("✅ Service FileStorageService initialisé avec succès")
        print(f"   Bucket: {service.bucket_name}")
        print(f"   Environnement: {service.environment}")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        print("\n💡 Le système utilisera le stockage local en fallback")
        return False

def setup_local_fallback():
    """Configure le fallback local pour le développement."""
    print("\n🛠️ Configuration du fallback local...")
    
    # Créer le répertoire temporaire pour les fichiers AO
    tmp_dir = Path("/tmp/ao")
    tmp_dir.mkdir(exist_ok=True, parents=True)
    print(f"✅ Répertoire temporaire créé: {tmp_dir}")
    
    print("\n📋 Résumé:")
    print("   • Stockage S3/R2: ❌ Non configuré (AccessDenied)")
    print("   • Fallback local: ✅ Activé (/tmp/ao/)")
    print("   • Fichiers seront stockés localement pour le développement")
    print("\n⚠️  Note: Pour la production, configurez les credentials R2")

if __name__ == "__main__":
    # Changer vers le répertoire du script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("=" * 60)
    print("Configuration Cloudflare R2 pour SurenSaaS")
    print("=" * 60)
    
    if not check_r2_config():
        setup_local_fallback()
    
    print("\n" + "=" * 60)
    print("Pour tester le système AO:")
    print("1. Upload d'un dossier ZIP via l'interface frontend")
    print("2. Les fichiers seront stockés localement (/tmp/ao/)")
    print("3. Téléchargement via les boutons dans AOExplorer")
    print("=" * 60)