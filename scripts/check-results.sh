#!/usr/bin/env bash
# Affiche un résumé du dernier run des tests E2E.
set -euo pipefail

LOGS_DIR="$(cd "$(dirname "$0")/.." && pwd)/e2e-harness/logs"

# Trouver le dernier dossier horodaté
LAST_RUN=$(ls -td "$LOGS_DIR"/2* 2>/dev/null | head -1)

if [ -z "$LAST_RUN" ]; then
    echo "❌ Aucun rapport trouvé dans $LOGS_DIR"
    exit 1
fi

echo "============================================"
echo "  E2E Test Results — $(basename "$LAST_RUN")"
echo "============================================"
echo ""

for report in "$LAST_RUN"/*_report.md; do
    [ -f "$report" ] || continue
    SCENARIO=$(basename "$report" _report.md)
    STATUS=$(grep -E "^## Résultat final" "$report" | grep -q "✅" && echo "✅ PASS" || echo "❌ FAIL")
    # Chercher le premier FAIL pour la raison
    FIRST_FAIL=$(grep -E "❌ FAIL" -A2 "$report" | grep "Raison" | head -1 | sed 's/.*Raison du Juge : //' | head -c 120)
    if [ -z "$FIRST_FAIL" ]; then
        echo "  $SCENARIO : $STATUS"
    else
        echo "  $SCENARIO : $STATUS"
        echo "    ↳ $FIRST_FAIL..."
    fi
done

echo ""
echo "📝 Détails dans : $LAST_RUN"
