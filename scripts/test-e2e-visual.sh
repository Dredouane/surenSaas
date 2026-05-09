#!/bin/bash
# 🎬 Lancer les tests E2E avec visualisation
# 
# Ce script propose 3 modes pour voir les tests :
# 1. Mode UI (interface graphique) - RECOMMANDÉ
# 2. Mode headed (voir le navigateur)
# 3. Rapport HTML (après exécution)

set -e

echo "🎬 Visualisation des Tests E2E"
echo "=============================="
echo ""
echo "Choisissez un mode:"
echo ""
echo "1️⃣  Mode UI (RECOMMANDÉ)"
echo "   Interface graphique pour voir et contrôler les tests"
echo "   Permet de rejouer, debugguer, inspecter"
echo ""
echo "2️⃣  Mode Headed"
echo "   Voir le navigateur Firefox exécuter les tests"
echo "   Rapide mais pas interactif"
echo ""
echo "3️⃣  Générer Rapport HTML"
echo "   Voir le rapport détaillé après exécution"
echo "   Avec screenshots et vidéos"
echo ""
echo "4️⃣  Mode Debug (step-by-step)"
echo "   S'arrête à chaque ligne pour inspection"
echo ""
echo "q) Quitter"
echo ""

read -p "Votre choix (1-4): " choice

cd surenSaasFront

case $choice in
  1)
    echo ""
    echo "🚀 Lancement Mode UI..."
    echo "   Une fenêtre va s'ouvrir dans votre navigateur"
    echo ""
    npm run test:e2e:ui
    ;;
  2)
    echo ""
    echo "🚀 Lancement Mode Headed..."
    echo "   Vous allez voir Firefox exécuter les tests"
    echo ""
    npx playwright test e2e/01-auth/login.spec.ts --headed
    ;;
  3)
    echo ""
    echo "📊 Génération du rapport HTML..."
    echo ""
    # D'abord exécuter les tests
    npm run test:e2e:local || true
    # Puis ouvrir le rapport
    npm run test:e2e:report
    ;;
  4)
    echo ""
    echo "🐛 Lancement Mode Debug..."
    echo "   Le test s'arrêtera à chaque ligne"
    echo "   Utilisez les touches:"
    echo "     n = next (ligne suivante)"
    echo "     s = step into"
    echo "     c = continue"
    echo "     q = quit"
    echo ""
    npx playwright test e2e/01-auth/login.spec.ts --debug
    ;;
  *)
    echo "Au revoir!"
    exit 0
    ;;
esac
