import re

with open('app/api/emails.py', 'r') as f:
    content = f.read()

# Remplacer la fonction require_capability par une version très simple
old_require_capability = '''# TODO: Implémenter require_capability quand le système de capabilities sera migré
def require_capability(capability: str):
    """Vérifie que l'utilisateur a la capability requise."""
    from fastapi import HTTPException
    # Pour l'instant, autoriser tout
    def _check():
        return {"id": "test-user", "role": "admin"}
    return _check'''

new_require_capability = '''# TODO: Implémenter require_capability quand le système de capabilities sera migré
def require_capability(capability: str):
    """Dépendance temporaire pour les capabilities."""
    async def _require_capability():
        # Pour l'instant, permissif - retourner un utilisateur mock
        return {"id": "test-user", "role": "admin", "org_id": "test"}
    return _require_capability'''

content = content.replace(old_require_capability, new_require_capability)

# Supprimer get_current_user car il n'est pas utilisé
old_get_current_user = '''def get_current_user():
    """Récupère l'utilisateur courant."""
    return {"id": "test-user", "role": "admin"}'''

new_get_current_user = '''# get_current_user n'est plus utilisé dans ce fichier
# def get_current_user():
#     """Récupère l'utilisateur courant."""
#     async def _get_current_user():
#         return {"id": "test-user", "role": "admin", "org_id": "test"}
#     return _get_current_user'''

content = content.replace(old_get_current_user, new_get_current_user)

with open('app/api/emails.py', 'w') as f:
    f.write(content)

print("Patch simple appliqué.")
