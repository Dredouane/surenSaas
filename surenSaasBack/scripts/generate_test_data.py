#!/usr/bin/env python3
"""
Script de génération de données de test pour la webapp.
À exécuter après avoir créé un utilisateur et une organisation.
"""

import os
import sys
from datetime import datetime, timedelta
from supabase import create_client
import random
import uuid
from typing import Optional

# Configuration depuis les variables d'environnement
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def get_supabase():
    """Récupère le client Supabase."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Variables d'environnement SUPABASE_URL et SUPABASE_SERVICE_KEY requises")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def generate_test_data(org_id: str, created_by: str, company_id: Optional[str] = None):
    """Génère des données de test pour une organisation."""
    supabase = get_supabase()
    
    print(f"🚀 Génération de données de test pour l'org {org_id}")
    
    # Récupérer une company_id si non fournie
    if not company_id:
        companies = supabase.table('companies').select('id').eq('org_id', org_id).limit(1).execute()
        if companies.data:
            company_id = companies.data[0]['id']
            print(f"📋 Company trouvée: {company_id}")
        else:
            print("❌ Aucune company trouvée pour cette organisation")
            print("Vous devez d'abord créer une company ou fournir un company_id en argument")
            sys.exit(1)
    
    # Vérifier que le created_by (user_id) existe dans la table users
    try:
        user_check = supabase.table('users').select('id').eq('id', created_by).maybe_single().execute()
        if not user_check.data:
            raise Exception("User not found")
        print(f"👤 User validé: {created_by}")
    except:
        # Essayer de récupérer un user existant de l'org
        print(f"⚠️  User {created_by} non trouvé, recherche d'un user valide...")
        users = supabase.table('users').select('id').eq('org_id', org_id).limit(1).execute()
        if users.data:
            created_by = users.data[0]['id']
            print(f"👤 User trouvé automatiquement: {created_by}")
        else:
            print(f"❌ Aucun user trouvé pour l'org {org_id}")
            print("Veuillez créer un utilisateur d'abord")
            sys.exit(1)
    
    # 1. Créer des clients
    clients_data = [
        {
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "name": "Construction Dupont SA",
            "email": "contact@dupont-construction.fr",
            "phone": "+33 1 42 56 78 90",
            "address": "15 Rue de la Paix, 75002 Paris",
            "siret": "12345678900012",
            "notes": "Client régulier - Paiement sous 30 jours",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "name": "Bâtiment Martin & Fils",
            "email": "devis@martin-batiment.fr",
            "phone": "+33 4 91 23 45 67",
            "address": "45 Avenue du Prado, 13008 Marseille",
            "siret": "98765432100021",
            "notes": "Nouveau client - Prospect important",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "name": "Entreprise Bernard SARL",
            "email": "contact@bernard-sarl.com",
            "phone": "+33 3 20 45 67 89",
            "address": "8 Place de la République, 59000 Lille",
            "siret": "45678912300034",
            "notes": "Client fidèle depuis 2020",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "name": "Gros Oeuvre Morel",
            "email": "facturation@morel-go.fr",
            "phone": "+33 5 56 78 90 12",
            "address": "120 Rue de Bordeaux, 33000 Bordeaux",
            "siret": "78912345600045",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "name": "Travaux Publics Petit",
            "email": "admin@tp-petit.fr",
            "phone": "+33 2 40 56 78 90",
            "address": "56 Boulevard des Anglais, 44000 Nantes",
            "siret": "32165498700056",
            "notes": "Spécialisé en travaux publics",
            "created_at": datetime.utcnow().isoformat()
        }
    ]
    
    # Insérer les clients
    result = supabase.table('clients').insert(clients_data).execute()
    client_ids = [c['id'] for c in result.data]
    print(f"✅ {len(client_ids)} clients créés")
    
    # 2. Créer des factures (statuts valides selon l'ENUM invoice_status)
    statuses = ['brouillon', 'en_attente_validation', 'validee', 'en_traitement_comptable', 'rejetee', 'archivee']
    invoice_data = []
    
    for i in range(20):
        client_id = random.choice(client_ids)
        status = random.choice(statuses)
        total = round(random.uniform(500, 15000), 2)
        ht = round(total / 1.2, 2)
        vat = round(total - ht, 2)
        
        days_ago = random.randint(0, 90)
        issue_date = (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        due_date = (datetime.utcnow() - timedelta(days=days_ago) + timedelta(days=30)).strftime('%Y-%m-%d')
        
        invoice = {
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "company_id": company_id,
            "created_by": created_by,
            "invoice_number": f"FAC-2024-{str(i+1).zfill(3)}",
            "supplier_name": random.choice([
                "Fournitures BTP Plus",
                "Matériaux de Construction SA",
                "Équipements Pro Build",
                "Location Matériel BTP",
                "Services Techniques Industriels"
            ]),
            "amount_ttc": total,
            "amount_ht": ht,
            "vat_amount": vat,
            "vat_rate": 20.0,
            "status": status,
            "invoice_date": issue_date,
            "due_date": due_date,
            "description": f"Facture pour travaux de {random.choice(['maçonnerie', 'électricité', 'plomberie', 'charpente', 'fondations'])}",
            "client_id": client_id,
            "created_at": (datetime.utcnow() - timedelta(days=days_ago)).isoformat(),
            "updated_at": (datetime.utcnow() - timedelta(days=random.randint(0, days_ago))).isoformat()
        }
        
        # Ajouter des dates de validation pour les factures validées
        if status in ['validee', 'en_traitement_comptable', 'archivee']:
            invoice['validated_by'] = created_by
            invoice['validated_at'] = (datetime.utcnow() - timedelta(days=random.randint(0, days_ago))).isoformat()
        
        invoice_data.append(invoice)
    
    # Insérer les factures
    result = supabase.table('invoices').insert(invoice_data).execute()
    invoice_ids = [inv['id'] for inv in result.data]
    print(f"✅ {len(invoice_ids)} factures créées")
    
    # 3. Créer des entrées dans l'historique des statuts
    history_data = []
    for inv_id in invoice_ids:
        # Chaque facture a au moins une entrée "brouillon"
        history_data.append({
            "invoice_id": inv_id,
            "org_id": org_id,
            "previous_status": None,
            "new_status": "brouillon",
            "changed_by": created_by,
            "changed_by_telegram": False,
            "change_reason": "Création automatique - données de test"
        })
    
    supabase.table('invoice_status_history').insert(history_data).execute()
    print(f"✅ Historique des statuts créé")
    
    print(f"\n🎉 Données de test générées avec succès!")
    print(f"   - {len(client_ids)} clients")
    print(f"   - {len(invoice_ids)} factures")
    
    return {
        "clients_count": len(client_ids),
        "invoices_count": len(invoice_ids)
    }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_test_data.py <org_id> <user_id> [company_id]")
        print("Example: python generate_test_data.py <your-org-uuid> <your-user-uuid> <your-company-uuid>")
        sys.exit(1)
    
    org_id = sys.argv[1]
    user_id = sys.argv[2]
    company_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    generate_test_data(org_id, user_id, company_id)
