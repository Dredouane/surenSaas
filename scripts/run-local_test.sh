#!/bin/bash
# Lancer le backend ET frontend TEST en local (2 terminaux)

cd /home/redouane/dev/AI-ERA/surenSaas

echo "=========================================="
echo "🧹 Nettoyage initial..."
echo "=========================================="

# Tuer les processus existants sur les ports 3000 et 8080
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "  → Arrêt du processus sur port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

if lsof -ti:8080 > /dev/null 2>&1; then
    echo "  → Arrêt du processus sur port 8080..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
fi

sleep 1
echo "✅ Ports libérés"
echo ""

echo "=========================================="
echo "🚀 LANCEMENT COMPLET - TEST Environment"
echo "=========================================="
echo ""
echo "Cela va ouvrir:"
echo "  - Backend sur http://localhost:8080"
echo "  - Frontend sur http://localhost:3000"
echo ""
echo "Appuyez sur Entrée pour continuer..."
read

# Terminal 1: Backend
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "./scripts/run-local-back_test.sh; exec bash"
elif command -v xterm &> /dev/null; then
    xterm -hold -e "./scripts/run-local-back_test.sh" &
elif command -v konsole &> /dev/null; then
    konsole --new-tab -e "./scripts/run-local-back_test.sh" &
else
    echo "Ouverture du backend dans une nouvelle session..."
    echo "Dans un autre terminal, exécute: ./scripts/run-local-back_test.sh"
    echo ""
fi

# Attendre un peu que le backend démarre
sleep 3

# Terminal 2: Frontend
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "./scripts/run-local-front_test.sh; exec bash"
elif command -v xterm &> /dev/null; then
    xterm -hold -e "./scripts/run-local-front_test.sh" &
elif command -v konsole &> /dev/null; then
    konsole --new-tab -e "./scripts/run-local-front_test.sh" &
else
    echo "Dans un autre terminal, exécute: ./scripts/run-local-front_test.sh"
fi

echo ""
echo "✅ Services démarrés !"
echo "  Backend:  http://localhost:8080"
echo "  Frontend: http://localhost:3000"
