#!/usr/bin/env python3
"""Test script pour vérifier la structure d'un ZIP et simuler le traitement AO"""

import zipfile
import tempfile
from pathlib import Path

zip_path = "/home/redouane/dev/AI-ERA/dce-v2.zip"

try:
    with zipfile.ZipFile(zip_path, 'r') as zf:
        print("Contenu du ZIP:")
        for name in zf.namelist()[:20]:  # Afficher les 20 premiers fichiers
            print(f"  {name}")
        
        print(f"\nNombre total de fichiers: {len(zf.namelist())}")
        
        # Tester l'extraction
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_folder = Path(tmpdir) / "extracted"
            extract_folder.mkdir()
            
            zf.extractall(extract_folder)
            
            print(f"\nExtraction dans: {extract_folder}")
            
            # Lister les fichiers extraits
            root_items = list(extract_folder.iterdir())
            print(f"\nÉléments à la racine ({len(root_items)}):")
            for item in root_items:
                item_type = "📁" if item.is_dir() else "📄"
                print(f"  {item_type} {item.name}")
            
            # Trouver tous les fichiers récursivement
            all_files = list(extract_folder.rglob('*'))
            files_only = [f for f in all_files if f.is_file()]
            
            print(f"\nTous les fichiers trouvés ({len(files_only)}):")
            for f in files_only[:10]:
                rel_path = f.relative_to(extract_folder)
                print(f"  📄 {rel_path}")
                
except Exception as e:
    print(f"Erreur: {e}")
    import traceback
    traceback.print_exc()
