#!/usr/bin/env bash
# =============================================================================
# setup-clean.sh — Reconstruction propre des environnements SurenSaas
# Usage : bash scripts/setup-clean.sh [--e2e-only] [--backend-only] [--help]
#
# ATTENTION : Supprime et recrée les venv. Arrête les processus en cours.
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/surenSaasBack"
E2E_DIR="$ROOT_DIR/e2e-harness"

BACKEND_VENV="$BACKEND_DIR/venv"
E2E_VENV="${VIRTUAL_ENV:-/home/redouane/dev/AI-ERA/venv-e2e}"

PYTHON="python3.10"

# ── Flags ──────────────────────────────────────────────────────────────────
DO_BACKEND=true
DO_E2E=true

for arg in "$@"; do
    case "$arg" in
        --backend-only) DO_E2E=false ;;
        --e2e-only)     DO_BACKEND=false ;;
        --help)
            echo "Usage: $0 [--backend-only] [--e2e-only] [--help]"
            exit 0
            ;;
    esac
done

# ── Vérifications préalables ───────────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
    echo "❌ $PYTHON introuvable. Installe Python 3.10+."
    exit 1
fi

# ── Arrêt des processus en cours ───────────────────────────────────────────
echo "⏳ Arrêt des processus liés..."
for name in "uvicorn" "mock_telegram"; do
    if pgrep -f "$name" &>/dev/null; then
        echo "   → Arrêt de $name..."
        pkill -f "$name" 2>/dev/null || true
        sleep 1
    fi
done

# ── Backend ─────────────────────────────────────────────────────────────────
if $DO_BACKEND; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Backend : $BACKEND_VENV"
    echo "═══════════════════════════════════════════════════════════════"

    if [ -d "$BACKEND_VENV" ]; then
        echo "   → Suppression de l'ancien venv..."
        rm -rf "$BACKEND_VENV"
    fi

    echo "   → Création du venv..."
    "$PYTHON" -m venv "$BACKEND_VENV"

    echo "   → Vérification include-system-site-packages = false..."
    VENV_CFG="$BACKEND_VENV/pyvenv.cfg"
    if grep -q "include-system-site-packages = true" "$VENV_CFG" 2>/dev/null; then
        sed -i 's/include-system-site-packages = true/include-system-site-packages = false/' "$VENV_CFG"
        echo "     ✅ Corrigé → false"
    else
        echo "     ✅ Déjà false"
    fi

    echo "   → Installation des dépendances..."
    "$BACKEND_VENV/bin/pip" install --upgrade pip setuptools wheel --quiet
    "$BACKEND_VENV/bin/pip" install -r "$BACKEND_DIR/requirements.txt" --quiet

    echo "   ✅ Backend prêt."
fi

# ── E2E Harness ─────────────────────────────────────────────────────────────
if $DO_E2E; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  E2E Harness : $E2E_VENV"
    echo "═══════════════════════════════════════════════════════════════"

    if [ -d "$E2E_VENV" ]; then
        echo "   → Suppression de l'ancien venv..."
        rm -rf "$E2E_VENV"
    fi

    echo "   → Création du venv..."
    "$PYTHON" -m venv "$E2E_VENV"

    echo "   → Vérification include-system-site-packages = false..."
    VENV_CFG="$E2E_VENV/pyvenv.cfg"
    if grep -q "include-system-site-packages = true" "$VENV_CFG" 2>/dev/null; then
        sed -i 's/include-system-site-packages = true/include-system-site-packages = false/' "$VENV_CFG"
        echo "     ✅ Corrigé → false"
    else
        echo "     ✅ Déjà false"
    fi

    echo "   → Installation des dépendances..."
    "$E2E_VENV/bin/pip" install --upgrade pip setuptools wheel --quiet
    "$E2E_VENV/bin/pip" install -r "$E2E_DIR/requirements-e2e.txt" --quiet

    echo "   ✅ E2E Harness prêt."
fi

# ── Récapitulatif ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  RÉCAPITULATIF"
echo "═══════════════════════════════════════════════════════════════"
echo "  Python : $("$PYTHON" --version 2>&1)"
if $DO_BACKEND; then
    echo "  Backend venv : $BACKEND_VENV"
    echo "    → $( "$BACKEND_VENV/bin/pip" list --format=columns 2>/dev/null | wc -l ) packages installés"
fi
if $DO_E2E; then
    echo "  E2E venv     : $E2E_VENV"
    echo "    → $( "$E2E_VENV/bin/pip" list --format=columns 2>/dev/null | wc -l ) packages installés"
fi
echo ""
echo "✅ Terminé."
