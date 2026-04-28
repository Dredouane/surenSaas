import subprocess
import time
import sys
import os
import signal
import requests

# Configuration
PORT = 8080
NGROK_CMD = ["ngrok", "http", str(PORT)]

def set_telegram_webhook(public_url):
    token = os.getenv("SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN")
    if not token:
        print("❌ Erreur: Token Telegram introuvable dans les variables d'environnement.")
        return

    webhook_url = f"{public_url}/api/v1/webhook/construction"
    print(f"🔗 Configuration du webhook vers: {webhook_url}")
    
    try:
        api_url = f"https://api.telegram.org/bot{token}/setWebhook"
        resp = requests.post(api_url, json={"url": webhook_url})
        if resp.status_code == 200:
            print("✅ Webhook configuré avec succès.")
        else:
            print(f"❌ Erreur configuration webhook: {resp.text}")
    except Exception as e:
        print(f"❌ Exception lors de la configuration: {e}")

def start_tunnel():
    print(f"🚀 Démarrage du tunnel ngrok sur le port {PORT}...")
    try:
        process = subprocess.Popen(
            NGROK_CMD, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Attendre que ngrok expose l'API (généralement sur le port 4040)
        time.sleep(2)
        try:
            resp = requests.get("http://localhost:4040/api/tunnels").json()
            url = resp['tunnels'][0]['public_url']
            print(f"✅ Tunnel démarré ! URL publique: {url}")
            # Configuration auto du webhook
            set_telegram_webhook(url)
        except:
            print("⚠️ Tunnel démarré, mais impossible de récupérer l'URL via API.")
            
        return process
    except FileNotFoundError:
        print("❌ Erreur: 'ngrok' non trouvé.")
        sys.exit(1)

def stop_tunnel(process):
    print("\n🛑 Arrêt du tunnel...")
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    print("✅ Tunnel arrêté.")

if __name__ == "__main__":
    proc = start_tunnel()
    print("Appuyez sur Ctrl+C pour arrêter le tunnel et quitter.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_tunnel(proc)
