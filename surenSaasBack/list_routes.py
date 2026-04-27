import sys
sys.path.insert(0, '.')

from app.main import app

print("Toutes les routes enregistrées dans l'application:")
print("=" * 80)

routes_by_path = {}

for route in app.routes:
    path = route.path
    methods = sorted(route.methods)
    if path not in routes_by_path:
        routes_by_path[path] = []
    routes_by_path[path].extend(methods)

# Afficher par ordre alphabétique de chemin
for path in sorted(routes_by_path.keys()):
    methods = sorted(set(routes_by_path[path]))
    print(f"{' '.join(methods):20} {path}")

print("\n" + "=" * 80)
print("Routes contenant 'emails':")
print("=" * 80)
for path in sorted(routes_by_path.keys()):
    if 'emails' in path:
        methods = sorted(set(routes_by_path[path]))
        print(f"{' '.join(methods):20} {path}")

print("\n" + "=" * 80)
print("Routes contenant '/sync':")
print("=" * 80)
for path in sorted(routes_by_path.keys()):
    if '/sync' in path:
        methods = sorted(set(routes_by_path[path]))
        print(f"{' '.join(methods):20} {path}")
