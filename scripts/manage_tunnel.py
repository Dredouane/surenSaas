#!/usr/bin/env python3
"""
Gestionnaire de tunnels ngrok pour SurenSaaS.

Usage:
    # Mode "backend" — tunnel sur le port 8080 + configure le webhook Telegram
    python3 scripts/manage_tunnel.py --env test --service backend

    # Mode "frontend" — tunnel sur le port 3000 (TMA : /mini-app)
    python3 scripts/manage_tunnel.py --env test --service frontend

    # Mode "all" — deux tunnels simultanés (recommandé, mais les logs sont mélangés)
    python3 scripts/manage_tunnel.py --env test --service all
"""

import subprocess
import time
import sys
import os
import signal
import requests
import argparse


# Configuration des ports
SERVICES = {
    "backend": {"port": 8080,  "label": "Backend (FastAPI)"},
    "frontend": {"port": 3000, "label": "Frontend TMA (Next.js)"},
}

NGROK_API = "http://localhost:4040/api/tunnels"


def get_ngrok_url() -> str:
    """Récupère l'URL publique depuis l'API ngrok locale."""
    time.sleep(2)
    try:
        resp = requests.get(NGROK_API).json()
        for tunnel in resp.get("tunnels", []):
            url = tunnel.get("public_url", "")
            if url:
                return url
    except Exception as e:
        print(f"⚠️ Impossible de récupérer l'URL ngrok: {e}")
    return ""


def get_org_id() -> str:
    """Récupère l'org_id depuis les variables d'environnement."""
    org_id = os.getenv("NEXT_PUBLIC_ORG_ID") or os.getenv("TEST_ORG_ID") or ""
    if not org_id:
        print("❌ NEXT_PUBLIC_ORG_ID non défini. Ajoute-le à ~/.bashrc ou dans le .env frontend.")
        print("   Valeur attendue: REDACTEDORG")
        sys.exit(1)
    return org_id


def set_telegram_webhook(public_url: str):
    """Configure le webhook Telegram sur l'URL publique du backend."""
    org_id = get_org_id()
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")

    # Récupérer le webhook_token actuel depuis la DB
    webhook_token = "construction"
    if supabase_url and supabase_key:
        try:
            from supabase import create_client
            sb = create_client(supabase_url, supabase_key)
            r = sb.table("telegram_bots").select("webhook_url").eq("org_id", org_id).eq("is_active", True).limit(1).execute()
            if r.data:
                old_url = r.data[0]["webhook_url"]
                webhook_token = old_url.rstrip("/").rsplit("/", 1)[-1]
                print(f"ℹ️  Webhook token existant : {webhook_token}")
        except Exception as e:
            print(f"⚠️ Impossible de lire le webhook_token depuis Supabase: {e}")

    token = os.getenv("SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN")
    if not token:
        print("❌ Token Telegram introuvable (SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN)")
        return

    webhook_url = f"{public_url}/api/v1/{org_id}/telegram/webhook/{webhook_token}"
    print(f"🔗 Configuration du webhook vers: {webhook_url}")

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url},
        )
        if resp.status_code == 200:
            print("✅ Webhook configuré avec succès.")
        else:
            print(f"❌ Erreur webhook: {resp.text}")
    except Exception as e:
        print(f"❌ Exception webhook: {e}")


def start_tunnel(port: int, label: str) -> subprocess.Popen:
    """Lance un tunnel ngrok pour le port donné."""
    print(f"🚀 [{label}] Démarrage du tunnel ngrok sur le port {port}...")
    try:
        process = subprocess.Popen(
            ["ngrok", "http", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        return process
    except FileNotFoundError:
        print(f"❌ [{label}] 'ngrok' non trouvé. Installe-le avec: npm i -g ngrok")
        sys.exit(1)


def stop_tunnel(process: subprocess.Popen, label: str = ""):
    """Arrête un tunnel ngrok."""
    tag = f" [{label}]" if label else ""
    print(f"\n🛑{tag} Arrêt du tunnel...")
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        print(f"✅{tag} Tunnel arrêté.")
    except Exception:
        pass


def run_single(port: int, label: str, env: str, do_webhook: bool):
    """Lance un tunnel unique et le maintient jusqu'à Ctrl+C."""
    proc = start_tunnel(port, label)
    url = get_ngrok_url()

    if url:
        print(f"✅ [{label}] URL publique : {url}")
        print(f"   → TMA accessible : {url}/mini-app")
        print(f"   → Export pour le bot : export TMA_HOST=\"{url.replace('https://','')}\"")

        if do_webhook:
            set_telegram_webhook(url)

    print(f"\nAppuie sur Ctrl+C pour arrêter [{label}].")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_tunnel(proc, label)


def run_all():
    """Lance les deux tunnels simultanément. ATTENTION : ngrok API est partagée."""
    procs = {}
    urls = {}

    for name, cfg in SERVICES.items():
        procs[name] = start_tunnel(cfg["port"], cfg["label"])

    for name, cfg in SERVICES.items():
        urls[name] = get_ngrok_url()

    for name, cfg in SERVICES.items():
        url = urls.get(name, "")
        if url:
            print(f"\n✅ [{cfg['label']}] URL publique : {url}")
            print(f"   → TMA accessible : {url}/mini-app")
            print(f"   → Export : export TMA_HOST=\"{url.replace('https://','')}\"")

    # Webhook sur l'URL backend
    backend_url = urls.get("backend", "")
    if backend_url:
        set_telegram_webhook(backend_url)
    else:
        print("⚠️ Impossible de configurer le webhook — URL backend introuvable.")

    print("\nAppuie sur Ctrl+C pour arrêter les deux tunnels.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for name, proc in procs.items():
            stop_tunnel(proc, SERVICES[name]["label"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gestionnaire de tunnels ngrok")
    parser.add_argument("--env", default="test", choices=["test", "prod"], help="Environnement")
    parser.add_argument(
        "--service", default="backend",
        choices=["backend", "frontend", "all"],
        help="Service à exposer (backend=8080, frontend=3000, all=les deux)",
    )
    args = parser.parse_args()

    if args.service == "all":
        run_all()
    elif args.service == "frontend":
        cfg = SERVICES["frontend"]
        run_single(cfg["port"], cfg["label"], args.env, do_webhook=False)
    else:
        cfg = SERVICES["backend"]
        run_single(cfg["port"], cfg["label"], args.env, do_webhook=True)
