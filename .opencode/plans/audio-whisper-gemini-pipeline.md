# Plan — Pipeline Audio "Whisper + Gemini"

## Goal
Ajouter un pipeline audio en 2 étapes :
1. **Whisper** (via OpenRouter) : blob audio → texte brut
2. **Gemini** (Vertex AI) : texte brut → JSON structuré `{task_id, percentage, status, observation}`

Chaque étape loggée séparément dans `logs_agents` pour monitoring de latence et d'erreur.

## Constraints & Preferences
- Whisper via OpenRouter (API compatible OpenAI) : `POST https://openrouter.ai/api/v1/audio/transcriptions`
- Clé : `SUREN_OPEN_ROUTER_API_KEY` (dans `.bashrc`, secrète déploy)
- Gemini structuration : même Vertex AI que le reste (gemini-2.5-flash)
- Nouvel endpoint dédié : `POST /api/v1/tma/transcribe-and-structure`
- Logging séparé (2 lignes dans `logs_agents`) avec `agent_type: whisper_transcription` et `agent_type: gemini_structuration`
- Frontend : VoiceRecorder adapté pour appeler le nouvel endpoint
- Appliquer le TDD Cycle (RED → GREEN → REFACTOR)

## Progress
### In Progress
- Plan élaboré et validé

### Done
- (nothing yet)

### Blocked
- (none)

## Key Decisions
- OpenRouter au lieu de Groq (déjà une clé SUREN_OPEN_ROUTER_API_KEY)
- Whisper large-v3 uniquement (pas de fallback)
- Pas de service layer pour Whisper — simple fonction asynchrone (comme transcribe_with_gemini existant)
- AgentWrapper n'est pas utilisé ici (logging direct via audit_service.log_agent pour la transparence)
- Le renommage de `transcribe_with_gemini` en `transcribe_gemini_multimodal` préserve la compatibilité des imports existants

## Files
- `surenSaasBack/app/core/config.py` — ajouter `open_router_api_key: str`, `whisper_model: str`
- `surenSaasBack/app/services/whisper_service.py` — créer : `transcribe_with_whisper()`
- `surenSaasBack/app/services/transcribe_service.py` — modifier : renommage + `transcribe_pipeline()` + `gemini_structured_extraction()`
- `surenSaasBack/app/api/tma.py` — modifier : ajouter POST `/transcribe-and-structure`
- `surenSaasBack/tests/test_whisper_service.py` — créer
- `surenSaasBack/tests/test_transcribe_pipeline.py` — créer
- `surenSaasBack/tests/test_tma_transcribe_and_structure_api.py` — créer
- `surenSaasFront/app/(tma)/mini-app/components/VoiceRecorder.tsx` — modifier
- `DOMAIN_LANGUAGE.md` — modifier (déjà fait)
- `.opencode/plans/audio-whisper-gemini-pipeline.md` — créer (ce fichier)
