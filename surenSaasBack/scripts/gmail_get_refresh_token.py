import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

# Configuration à partir de tes variables d'environnement
client_id = os.getenv('SUREN_GMAIL_OAUTH_CLIENT_ID') # Vérifie le nom exact dans ton .bashrc
client_secret = os.getenv('SUREN_GMAIL_OAUTH_CLIENT_SECRET')

if not client_id or not client_secret:
    print("Erreur : SUREN_GMAIL_OAUTH_CLIENT_ID ou SUREN_GMAIL_OAUTH_CLIENT_SECRET non trouvés dans l'environnement.")
    exit(1)

# Création du dictionnaire de configuration au format attendu par Google
client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# Scope nécessaire pour LIRE les mails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    
    # Cette commande ouvre ton navigateur par défaut
    # CONNECTE-TOI AVEC L'ADRESSE GMAIL B (celle à pooler)
    creds = flow.run_local_server(port=0)

    print("\n" + "="*50)
    print(" AUTHENTIFICATION RÉUSSIE !")
    print("="*50)
    print(f"Refresh Token : {creds.refresh_token}")
    print("="*50)
    print("\nSauvegarde ce Refresh Token précieusement dans ton Secret Manager.")

if __name__ == '__main__':
    main()