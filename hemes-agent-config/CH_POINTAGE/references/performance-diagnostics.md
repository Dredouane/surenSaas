# Performance Diagnostics — Analyse de latence DeepSeek + outils

Méthode pour auditer précisément d'où vient la lenteur ressentie par l'utilisateur
sur les workflows Arev Chantiers. Permet de séparer :
- **Latence LLM** (DeepSeek) — cumul des temps de réponse API
- **Exécution outils** (execute_code, terminal, etc.) — mesuré par tool_executor
- **Cascade** — nombre d'allers-retours DeepSeek par message utilisateur

## Source des données

- **`~/.hermes/logs/agent.log`** — logs INFO avec timestamps précis
- **`~/.hermes/state.db`** — sessions, messages, tokens, coûts

## Extraction des latences API

Regex pour les appels API dans agent.log :

```
API call #N: model=X provider=Y in=TOK out=TOK total=TOK latency=X.Xs cache=HIT/TOTAL (PCT%)
```

Pattern Python :
```python
api_call_p = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO \[(\w+)\] agent.conversation_loop: '
    r'API call #(\d+): model=(\S+) provider=(\S+) '
    r'in=(\d+) out=(\d+) total=(\d+) latency=([\d.]+)s'
    r'(?: cache=(\d+)/(\d+) \((\d+)%\))?'
)
```

## Extraction des temps d'exécution outils

Regex pour les temps mesurés par tool_executor :

```python
all_tool_p = re.compile(r'tool (\w+) completed \(([\d.]+)s')
```

**Attention** : `clarify` affiche des temps longs (jusqu'à 600s) car il mesure
le temps utilisateur (réflexion avant clic), pas le temps système. L'exclure
des stats de performance machine.

## Extraction des délais utilisateur (message → réponse)

```python
resp_p = re.compile(
    r'response ready: platform=telegram chat=(\d+) time=([\d.]+)s api_calls=(\d+) response=(\d+) chars'
)
```

Le `time=` est le délai total entre réception du message et envoi de la réponse.

## Anatomie type d'un workflow lent (pointage v2, 7 appels API)

```
API #1 → skill_view(CH_POINTAGE)    →  0.2s outil + 12s DeepSeek
API #2 → execute_code(warmup)       →  4.5s outil + 19s DeepSeek
API #3 → execute_code(search)       →  3.8s outil + 19s DeepSeek
API #4 → execute_code(GET ress.)    →  4.1s outil + 13s DeepSeek
API #5 → matching LLM               →  0s outil   +  9s DeepSeek
API #6 → clarify()                  →  0s outil   + 14s DeepSeek
API #7 → execute_code(POST upsert)  →  4.0s outil + 24s DeepSeek
─────────────────────────────────────────────────────────
Total : 111s DeepSeek + 16.6s outils = 128s pour UN pointage
```

## Ratio réel DeepSeek vs outils

Sur 650 appels API analysés (8 sessions, mai 2026) :

| Composante | Temps cumulé | Part du temps actif |
|---|---|---|
| DeepSeek (LLM) | 7085s | **89%** |
| execute_code (SurenSaaS) | 211s | 2.6% |
| terminal | 483s | 6% |
| Autres (read, skill, patch…) | 197s | 2.4% |

**Le backend SurenSaaS n'est PAS le bottleneck.** La cascade d'appels DeepSeek
est responsable de 89% du temps.

## Distribution des latences DeepSeek

```
0-5s    : 24% des appels
5-10s   : 42% (le gros)
10-15s  : 13%
15-20s  : 9%
20-30s  : 7%
30-60s  : 4%
60s+    : 0.3%

Médiane : 7.4s | P95 : 29.3s
```

## Optimisation appliquée : fusion execute_code (v3)

Levier principal : réduire le nombre d'allers-retours DeepSeek.

**Avant** : warmup() → search_chantier() → list_ressources() = 3 execute_code = 3 appels DeepSeek
**Après** : prepare_pointage() = 1 execute_code = 1 appel DeepSeek

Fonctions fusionnées dans `api_helper.py` :
- `prepare_pointage(chantier_query, type)` → health_check + search + list
- `prepare_depense(chantier_query)` → health_check + search
- `prepare_tache(chantier_query)` → health_check + search
- `prepare_operation(chantier_query)` → health_check + search
- `prepare_avancement(chantier_query)` → health_check + search + list_situations

Gain estimé : 7→3 appels API par workflow, -65% de temps (128s→45s pour un pointage).

## Warmup : GET /health au lieu de POST /list

L'ancien `warmup()` faisait un POST lourd sur `/chantiers/list` (query DB, 5-25s).
Remplacé par `health_check()` → GET `/health` (pas de body, pas de DB, timeout 5s).
Intégré dans chaque `prepare_*()`, donc 0 appel DeepSeek supplémentaire.

## Vérification rapide

```bash
# Latences moyennes par session
grep -oP '\[(\w+)\].*latency=([\d.]+)s' ~/.hermes/logs/agent.log | ...

# Top 10 outils les plus lents
grep -oP 'tool (\w+) completed \(([\d.]+)s' ~/.hermes/logs/agent.log | ...
```
