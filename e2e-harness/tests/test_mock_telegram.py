"""Tests du mock Telegram (mock_telegram.py).

Lance le mock sur un port aléatoire, teste tous les endpoints
via httpx, puis arrête le serveur."""
import subprocess
import time
import sys
from pathlib import Path

import httpx
import pytest

HERE = Path(__file__).resolve().parent.parent
MOCK_SCRIPT = HERE / "mock_telegram.py"
MOCK_PORT = 18081  # port fixe pour éviter conflit avec le vrai mock
MOCK_URL = f"http://localhost:{MOCK_PORT}"
FAKE_TOKEN = "123456:test-fake-token"


@pytest.fixture(scope="module")
def mock_server():
    """Lance le mock sur un port dédié, yield le client, arrête à la fin."""
    proc = subprocess.Popen(
        [sys.executable, str(MOCK_SCRIPT), "--port", str(MOCK_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Attendre que le serveur soit prêt
    client = httpx.Client(base_url=MOCK_URL, timeout=5.0)
    for _ in range(10):
        try:
            r = client.get("/health")
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.3)
    else:
        proc.kill()
        pytest.fail("Mock server did not start")
    yield client
    client.close()
    proc.kill()
    proc.wait()


# ── Tests ─────────────────────────────────────────────────────────────────


def test_health(mock_server):
    r = mock_server.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_get_me(mock_server):
    r = mock_server.get(f"/bot{FAKE_TOKEN}/getMe")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["result"]["id"] == 12345678
    assert data["result"]["is_bot"] is True
    assert data["result"]["username"] == "SurenTestBot"


def test_send_message_and_get_updates(mock_server):
    """sendMessage stocke le message, getUpdates le retourne."""
    # Envoyer un message
    r = mock_server.post(
        f"/bot{FAKE_TOKEN}/sendMessage",
        json={"chat_id": 999, "text": "Bonjour test"},
    )
    assert r.status_code == 200
    send_data = r.json()
    assert send_data["ok"] is True
    assert send_data["result"]["text"] == "Bonjour test"
    assert send_data["result"]["chat"]["id"] == 999

    # Récupérer via getUpdates
    r = mock_server.get(f"/bot{FAKE_TOKEN}/getUpdates")
    assert r.status_code == 200
    updates = r.json()
    assert updates["ok"] is True
    # Au moins le message qu'on vient d'envoyer
    texts = [u["message"]["text"] for u in updates["result"] if "message" in u]
    assert "Bonjour test" in texts


def test_get_chat_always_ok(mock_server):
    """getChat retourne toujours ok, quel que soit le chat_id."""
    r = mock_server.get(f"/bot{FAKE_TOKEN}/getChat?chat_id=999999")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["result"]["id"] == 999999


def test_debug_reset_clears_buffer(mock_server):
    """debug/reset vide entièrement le buffer."""
    # Envoyer un message
    mock_server.post(f"/bot{FAKE_TOKEN}/sendMessage", json={"chat_id": 1, "text": "a"})
    mock_server.post(f"/bot{FAKE_TOKEN}/sendMessage", json={"chat_id": 2, "text": "b"})

    # Vérifier qu'il y a des messages
    r = mock_server.get(f"/bot{FAKE_TOKEN}/getUpdates")
    assert len(r.json()["result"]) >= 2

    # Reset
    r = mock_server.post("/debug/reset")
    assert r.status_code == 200

    # Vérifier que le buffer est vide
    r = mock_server.get(f"/bot{FAKE_TOKEN}/getUpdates")
    assert len(r.json()["result"]) == 0


def test_get_updates_respects_offset(mock_server):
    """getUpdates avec offset ne retourne que les messages plus récents."""
    mock_server.post("/debug/reset")

    mock_server.post(f"/bot{FAKE_TOKEN}/sendMessage", json={"chat_id": 1, "text": "msg1"})
    mock_server.post(f"/bot{FAKE_TOKEN}/sendMessage", json={"chat_id": 1, "text": "msg2"})
    mock_server.post(f"/bot{FAKE_TOKEN}/sendMessage", json={"chat_id": 1, "text": "msg3"})

    # Récupérer le 2e update_id
    r = mock_server.get(f"/bot{FAKE_TOKEN}/getUpdates")
    updates = r.json()["result"]
    assert len(updates) == 3
    second_id = updates[1]["update_id"]

    # Offset = second_id → ne doit retourner que msg3
    r = mock_server.get(f"/bot{FAKE_TOKEN}/getUpdates", params={"offset": second_id})
    remaining = r.json()["result"]
    assert len(remaining) == 1
    assert remaining[0]["message"]["text"] == "msg3"
