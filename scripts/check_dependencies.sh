#!/bin/bash
# Script de vérification des dépendances

echo "🔍 Vérification des dépendances..."
echo ""

# Vérifier httpx
echo "📦 httpx:"
pip show httpx | grep -E "Version:|Requires:"
echo ""

# Vérifier supabase
echo "📦 supabase:"
pip show supabase | grep -E "Version:|Requires:"
echo ""

# Vérifier google-genai
echo "📦 google-genai:"
pip show google-genai 2>/dev/null | grep -E "Version:|Requires:" || echo "   ❌ Non installé"
echo ""

# Vérifier les conflits
echo "🔍 Vérification des conflits:"
if pip check 2>&1 | grep -q "No broken requirements"; then
    echo "   ✅ Aucun conflit détecté"
else
    echo "   ⚠️ Conflits détectés:"
    pip check 2>&1
fi
echo ""

# Tester l'import de Gemini
echo "🧪 Test d'import Gemini:"
python3 << 'PYTHON'
try:
    from app.agents.generic_extractor import create_invoice_extractor
    print("   ✅ Gemini import OK")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
PYTHON

echo ""
echo "✅ Vérification terminée!"
