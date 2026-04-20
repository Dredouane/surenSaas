#!/usr/bin/env python3
"""Test direct de l'API backend pour upload de dossier AO"""

import requests
import sys

# URL du backend directement
url = "http://localhost:8080/api/v1/ao/upload-folder"

# Cookie de session (à remplacer par le vôtre)
cookie = "session_token=VOTRE_TOKEN_ICI"

# Fichier ZIP
zip_path = "/home/redouane/dev/AI-ERA/dce-v2.zip"

try:
    with open(zip_path, 'rb') as f:
        files = {'folder_zip': ('dce-v2.zip', f, 'application/zip')}
        headers = {'Cookie': cookie}
        
        print(f"Envoi de {zip_path} vers {url}...")
        response = requests.post(url, files=files, headers=headers, timeout=120)
        
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {response.text[:1000]}")
        
except Exception as e:
    print(f"Erreur: {e}")
    import traceback
    traceback.print_exc()
