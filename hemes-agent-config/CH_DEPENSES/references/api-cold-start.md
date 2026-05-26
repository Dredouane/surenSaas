# Stratégie Cold Start — API SurenSaaS (Cloud Run)

L'API SurenSaaS tourne sur Google Cloud Run, qui met le conteneur en veille
après inactivité. Un premier appel peut prendre jusqu'à 30s (cold start).

## Règle : Warm-up paresseux

**Avant tout appel métier** (POST /depenses, /pointages/upsert, /operations),
faire UN appel warm-up par session :

```bash
curl -s -X POST \
  "https://test-surensaas-back-REDACTED-ew.a.run.app/api/v1/tools/chantiers/list" \
  -H "X-API-Key: $TOOLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"org_id\":\"$SURE_ORG_ID\"}" \
  --connect-timeout 10 --max-time 30
```

## Séquence type

```
1. POST /chantiers/search (WARM-UP + recherche, 30s timeout)
   ↓  (si timeout → réessayer immédiatement, le conteneur est en train de démarrer)
2. POST /depenses (ou autre, 15s timeout suffit après warm-up)
```

## Timeouts recommandés

| Contexte | --connect-timeout | --max-time |
|---|---|---|
| Premier appel de la session (cold start probable) | 10s | 30s |
| Appels suivants (conteneur chaud) | 5s | 15s |

## Environnement

Ces variables sont dans `~/.hermes/.env` :
- `TOOLS_API_KEY` → header `X-API-Key`
- `SURE_ORG_ID` → `org_id` dans tous les payloads
