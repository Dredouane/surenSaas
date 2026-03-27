#!/usr/bin/env python3
"""
Génère le code FastAPI depuis le fichier OpenAPI à la racine du projet.
Le contrat est dans /openapi/api.yaml (racine projet).
Le code généré va dans app/api/v1/.
"""

import subprocess
import shutil
import os
from pathlib import Path

def generate_api():
    """Génère les contrôleurs FastAPI depuis OpenAPI."""
    
    # Chemins
    backend_dir = Path(__file__).parent.parent
    project_root = backend_dir.parent
    openapi_file = project_root / "openapi" / "api.yaml"
    output_dir = backend_dir / "generated"
    api_dir = backend_dir / "app" / "api" / "v1"
    
    if not openapi_file.exists():
        print(f"❌ Fichier OpenAPI non trouvé : {openapi_file}")
        print("Créez-le à la racine du projet : /openapi/api.yaml")
        return False
    
    print(f"📄 OpenAPI : {openapi_file}")
    print(f"📁 Output : {output_dir}")
    
    # Nettoyer ancien output
    if output_dir.exists():
        shutil.rmtree(output_dir)
    
    # Générer avec openapi-generator-cli
    try:
        subprocess.run([
            "openapi-generator-cli", "generate",
            "-i", str(openapi_file),
            "-g", "python-fastapi",
            "-o", str(output_dir),
            "--additional-properties=packageName=generated",
            "--additional-properties=fastapiImplementationPackage=app.services",
            "--skip-validate-spec"
        ], check=True)
        
        print("✅ Code généré avec succès")
        
        # Copier uniquement les contrôleurs
        generated_api = output_dir / "generated" / "routers"
        if generated_api.exists():
            # Backup des routes auth (non générées)
            auth_backup = api_dir / "auth" if (api_dir / "auth").exists() else None
            
            # Nettoyer et copier
            if api_dir.exists():
                shutil.rmtree(api_dir)
            
            shutil.copytree(generated_api, api_dir)
            
            # Restaurer auth
            if auth_backup:
                shutil.copytree(auth_backup, api_dir / "auth")
            
            print(f"✅ Contrôleurs copiés dans {api_dir}")
        
        # Copier les modèles/schemas
        generated_models = output_dir / "generated" / "models"
        models_dir = backend_dir / "app" / "models"
        if generated_models.exists():
            models_dir.mkdir(exist_ok=True)
            for f in generated_models.glob("*.py"):
                shutil.copy(f, models_dir / f"generated_{f.name}")
            print(f"✅ Modèles copiés dans {models_dir}")
        
        # Nettoyer
        shutil.rmtree(output_dir)
        
        print("\n⚠️  Actions manuelles requises :")
        print("   1. Vérifier les imports dans les contrôleurs générés")
        print("   2. Implémenter la logique dans app/services/")
        print("   3. Ne PAS modifier le code généré directement")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur génération : {e}")
        return False
    except FileNotFoundError:
        print("❌ openapi-generator-cli non trouvé")
        print("Installez-le : npm install -g @openapitools/openapi-generator-cli")
        return False

if __name__ == "__main__":
    success = generate_api()
    exit(0 if success else 1)
