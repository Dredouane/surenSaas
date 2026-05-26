#!/usr/bin/env python3
"""
Backfill les embeddings des chantiers existants dans chantier_embeddings.

Usage:
    python scripts/backfill_chantier_embeddings.py

Prérequis :
    - Variables d'environnement chargées (SUPABASE_URL, SUPABASE_SERVICE_KEY)
    - Vertex AI configuré (text-embedding-004)
"""

import asyncio
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from dotenv import load_dotenv
    for env_file in [".env.prod", ".env.test", ".env"]:
        full_path = os.path.join(project_root, env_file)
        if os.path.exists(full_path):
            load_dotenv(full_path, override=False)
            break
except ImportError:
    pass


async def main():
    from app.api.auth import get_supabase
    from app.services.emails.embedding_service import embedding_service

    sb = get_supabase()

    # Récupérer tous les chantiers (pas de limite de statut pour le backfill)
    chantiers = sb.table("chantiers")\
        .select("id, org_id, nom, ref, adresse")\
        .execute()

    if not chantiers.data:
        print("Aucun chantier trouvé dans la base.")
        return

    print(f"Indexation de {len(chantiers.data)} chantier(s)...")

    success = 0
    errors = 0

    for c in chantiers.data:
        text = f"Chantier : {c['nom']}. Référence : {c.get('ref','')}. Adresse : {c.get('adresse','')}."
        try:
            vector = await embedding_service.generate_embedding(text)

            # Supprimer les anciens embeddings (re-indexation propre)
            sb.table("chantier_embeddings") \
              .delete() \
              .eq("chantier_id", c["id"]) \
              .execute()

            # Insérer le nouvel embedding
            sb.table("chantier_embeddings").insert({
                "org_id": c["org_id"],
                "chantier_id": c["id"],
                "content_chunk": text,
                "embedding": vector,
                "chunk_index": 0,
                "chunk_total": 1,
            }).execute()

            print(f"  ✓ {c['nom']} (ref: {c.get('ref','?')})")
            success += 1

        except Exception as e:
            print(f"  ✗ {c['nom']}: {e}")
            errors += 1

    print(f"\nTerminé : {success} succès, {errors} erreurs sur {len(chantiers.data)} chantier(s)")


if __name__ == "__main__":
    asyncio.run(main())
