# Stockage de Fichiers - Cloudflare R2

Documentation complète du service de stockage de fichiers basé sur Cloudflare R2 (S3-compatible).

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Service de stockage](#service-de-stockage)
5. [API Endpoints](#api-endpoints)
6. [Frontend](#frontend)
7. [Sécurité](#sécurité)
8. [Déploiement](#déploiement)
9. [Troubleshooting](#troubleshooting)

---

## Vue d'ensemble

### Pourquoi Cloudflare R2 ?

- **S3-compatible** : Utilise la même API AWS S3
- **Pas de frais de sortie** : Contrairement à AWS S3
- **Pricing simple** : $0.015/GB/mois pour le stockage
- **Edge caching** : Distribution mondiale via le réseau Cloudflare
- **Isolation environnements** : Dossiers `test/` et `prod/` dans le même bucket

### Principes

| Principe | Implémentation |
|----------|----------------|
| **Full R2** | Plus de stockage local `/tmp` - tout passe par R2 |
| **Isolation** | Un dossier par environnement (`test/`, `prod/`) |
| **Hiérarchie** | `{env}/org/{org_id}/{type}/{id}/{filename}` |
| **Sécurité** | URLs signées (1h) avec vérification org_id |
| **Unification** | Mêmes credentials pour test et prod |

---

## Architecture

### Structure du Bucket

```
Bucket: [configurable via SUREN_GED_CLOUDFLARE_BUCKET_NAME]

├── test/                                    # Environnement TEST
│   └── org/{org_id}/
│       ├── emails/{email_id}/
│       │   └── 20250115_143022_123456_facture.pdf
│       ├── invoices/{invoice_id}/
│       ├── ao/{ao_id}/
│       └── telegram/
│
└── prod/                                    # Environnement PRODUCTION
│   └── org/{org_id}/
│       ├── emails/{email_id}/
│       ├── invoices/{invoice_id}/
│       ├── ao/{ao_id}/
│       └── telegram/
```

### Flux de données

```
┌─────────────┐     Upload      ┌─────────────┐
│   Client    │ ───────────────>│   Backend   │
│  (Frontend) │                 │  (FastAPI)  │
└─────────────┘                 └──────┬──────┘
                                       │
                                       │ boto3
                                       │
                                       ▼
                               ┌───────────────┐
                               │  Cloudflare   │
                               │      R2       │
                               └───────┬───────┘
                                       │
                                       │ URL signée
                                       │
┌─────────────┐     Download    ┌──────▼──────┐
│   Client    │ <───────────────│   Backend   │
│  (Frontend) │   (Redirect 302)│  (FastAPI)  │
└─────────────┘                 └─────────────┘
```

### Diagramme de séquence - Upload

```
Client          Backend         R2
  │               │              │
  │── File ──────>│              │
  │               │── put_object─>│
  │               │              │
  │               │<── Key ──────│
  │               │              │
  │<── storage_path ─────────────│
  │               │              │
  │── Save to DB ───────────────>│
  │   (storage_path)             │
```

### Diagramme de séquence - Download

```
Client          Backend         R2
  │               │              │
  │── GET /download/{path} ────>│
  │               │              │
  │               │── Verify ────│
  │               │   org_id     │
  │               │              │
  │               │── generate ──│
  │               │   presigned  │
  │               │   URL        │
  │               │              │
  │<── 302 Redirect ─────────────│
  │   (to R2)                    │
  │               │              │
  │── Direct to R2 URL ─────────>│
  │               │              │
  │<── File content ─────────────│
```

---

## Configuration

### Variables d'environnement (.bashrc)

Ajoutez ces variables dans votre `~/.bashrc` (mêmes valeurs pour test et prod) :

```bash
# ============================================
# CLOUDFLARE R2 - GED (Gestion Electronique Documents)
# Mêmes credentials pour test et prod (isolation par folder)
# ============================================

export SUREN_GED_CLOUDFLARE_TOKEN="votre-token-cloudflare"
export SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID="votre-access-key"
export SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY="votre-secret-key"
export SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT="https://votre-account.r2.cloudflarestorage.com"
export SUREN_GED_CLOUDFLARE_BUCKET_NAME="votre-bucket-name"
```

**Note** : Ces variables sont utilisées telles quelles sans préfixe TEST_/PROD_. L'isclusion entre environnements se fait via le préfixe de dossier (`test/` vs `prod/`).

### Configuration Backend (config.py)

```python
class Settings(BaseSettings):
    # ... autres champs ...
    
    # Cloudflare R2 Configuration
    r2_endpoint_url: str = ""      # SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT
    r2_access_key_id: str = ""     # SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID
    r2_secret_access_key: str = "" # SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY
    r2_token: str = ""             # SUREN_GED_CLOUDFLARE_TOKEN
    r2_bucket_name: str = ""        # SUREN_GED_CLOUDFLARE_BUCKET_NAME
```

### Configuration R2 (Dashboard Cloudflare)

1. Créer un bucket R2 dans le dashboard Cloudflare
2. Créer un API Token avec les permissions :
   - `Object Read & Write` sur le bucket
3. Récupérer les credentials :
   - Access Key ID
   - Secret Access Key
   - S3 Endpoint URL

---

## Service de stockage

### FileStorageService

Le service est un singleton qui initialise un client S3 (boto3) configuré pour R2.

#### Initialisation

```python
from app.services.file_storage_service import file_storage_service

# Le service est initialisé automatiquement avec les credentials R2
# Si les credentials sont manquants, une erreur est levée au démarrage
```

#### Méthodes principales

##### `store_file(file_data: bytes, filename: str, org_id: str, folder: str = "general") -> str`

Stocke un fichier sur R2.

**Paramètres :**
- `file_data` : Données binaires du fichier
- `filename` : Nom original du fichier
- `org_id` : ID de l'organisation (obligatoire)
- `folder` : Dossier logique (emails, invoices, ao, telegram, general)

**Retour :**
- Clé S3 complète (ex: `test/org/xxx/invoices/20250115_143022_123456_facture.pdf`)

**Exemple :**
```python
storage_path = await file_storage_service.store_file(
    file_data=pdf_content,
    filename="facture.pdf",
    org_id="REDACTEDORG",
    folder="invoices"
)
# Sauvegarder storage_path en base de données
```

##### `get_file(key: str) -> Optional[bytes]`

Récupère un fichier depuis R2.

**Note** : Cette méthode est rarement utilisée directement. Préférez les URLs signées pour le download.

##### `get_presigned_url(key: str, expires: int = 3600, filename: Optional[str] = None) -> str`

Génère une URL signée pour téléchargement.

**Paramètres :**
- `key` : Clé S3 du fichier (storage_path depuis la DB)
- `expires` : Durée de validité en secondes (défaut: 3600 = 1h)
- `filename` : Nom de fichier pour le header Content-Disposition

**Retour :**
- URL signée complète (ex: `https://xxx.r2.cloudflarestorage.com/[bucket_name]/...?X-Amz-Algorithm=...`)

**Exemple :**
```python
url = await file_storage_service.get_presigned_url(
    key="test/org/xxx/invoices/20250115_143022_123456_facture.pdf",
    filename="facture_client.pdf",
    expires=3600
)
```

##### `delete_file(key: str) -> bool`

Supprime un fichier de R2.

**Retour :**
- `True` si supprimé avec succès
- `False` si le fichier n'existe pas ou erreur

---

## API Endpoints

### Endpoint générique

#### `GET /api/v1/{org}/files/download`

Endpoint générique de téléchargement par storage_path.

**Query Parameters :**
- `storage_path` (required) : Chemin de stockage R2 complet
- `filename` (optional) : Nom de fichier pour le téléchargement

**Headers requis :**
- `Cookie` : Session token (authentification)

**Réponses :**
- `302 Redirect` : Redirection vers l'URL signée R2
- `403 Forbidden` : L'utilisateur n'a pas accès à ce fichier (mauvais org_id)
- `404 Not Found` : Fichier inexistant

**Exemple :**
```bash
curl -L "https://api.example.com/api/v1/suren-societe/files/download?storage_path=test%2Forg%2Fxxx%2Finvoices%2F20250115_143022_123456_facture.pdf" \
  -H "Cookie: session_token=xxx"
```

### Emails - Pièces jointes

#### `GET /api/v1/{org}/emails/{email_id}/attachments/{attachment_id}/download`

Télécharge une pièce jointe d'email.

**Réponses :**
- `302 Redirect` : Vers l'URL signée R2
- `404 Not Found` : Pièce jointe inexistante
- `403 Forbidden` : Email dans une autre organisation

**Exemple frontend :**
```typescript
// Ouvre dans un nouvel onglet (le navigateur gère le téléchargement)
window.open(
  `/api/v1/${orgSlug}/emails/${emailId}/attachments/${attachmentId}/download`,
  '_blank'
);
```

### Factures

#### `GET /api/v1/{org}/invoices/{invoice_id}/download`

Télécharge le fichier original d'une facture.

**Réponses :**
- `302 Redirect` : Vers l'URL signée R2
- `404 Not Found` : Facture ou fichier inexistant

---

## Frontend

### Hook useFileDownload

```typescript
import { useState } from 'react';

export function useFileDownload() {
  const [downloading, setDownloading] = useState(false);
  
  const downloadFile = async (storagePath: string, filename?: string) => {
    setDownloading(true);
    try {
      const response = await fetch(
        `/api/v1/${orgSlug}/files/download?storage_path=${encodeURIComponent(storagePath)}`,
        { redirect: 'follow' }
      );
      
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'download';
      a.click();
      window.URL.revokeObjectURL(url);
      
    } finally {
      setDownloading(false);
    }
  };
  
  return { downloadFile, downloading };
}
```

### Composant AttachmentList

```typescript
interface Attachment {
  id: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  storage_path: string;
}

export function AttachmentList({ 
  attachments, 
  emailId, 
  orgSlug 
}: { 
  attachments: Attachment[];
  emailId: string;
  orgSlug: string;
}) {
  const handleDownload = (att: Attachment) => {
    window.open(
      `/api/v1/${orgSlug}/emails/${emailId}/attachments/${att.id}/download`,
      '_blank'
    );
  };

  return (
    <div className="attachments space-y-2">
      {attachments.map(att => (
        <button
          key={att.id}
          onClick={() => handleDownload(att)}
          className="flex items-center gap-2 p-2 rounded hover:bg-gray-100"
        >
          <FileIcon mimeType={att.mime_type} />
          <span className="text-sm">{att.filename}</span>
          <span className="text-xs text-gray-500">
            ({formatBytes(att.file_size_bytes)})
          </span>
        </button>
      ))}
    </div>
  );
}
```

---

## Sécurité

### Isolation des organisations

Chaque fichier est stocké avec un préfixe `org/{org_id}/`.
L'API vérifie systématiquement que l'utilisateur authentifié a le droit d'accéder à ce org_id.

```python
# Vérification dans l'endpoint
default_prefix = f"{environment}/org/{current_user['org_id']}/"
if not storage_path.startswith(expected_prefix):
    raise HTTPException(status_code=403, detail="Accès non autorisé")
```

### URLs signées

Les URLs de téléchargement sont signées et expirent après 1 heure (configurable).
Une URL signée ne peut pas être modifiée sans invalider la signature.

### Permissions requises

| Action | Permission |
|--------|------------|
| Upload | Capability associée au module (ex: `invoices:write`) |
| Download | Capability associée au module (ex: `emails:read`) |
| Delete | Capability `admin` ou owner du fichier |

### CORS

Le bucket R2 doit avoir une configuration CORS autorisant les origines frontend :

```xml
<CORSConfiguration>
  <CORSRule>
    <AllowedOrigin>https://app.surensaas.com</AllowedOrigin>
    <AllowedOrigin>https://test-app.surensaas.com</AllowedOrigin>
    <AllowedOrigin>http://localhost:3000</AllowedOrigin>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedHeader>*</AllowedHeader>
    <MaxAgeSeconds>3600</MaxAgeSeconds>
  </CORSRule>
</CORSConfiguration>
```

---

## Déploiement

### Prérequis

1. **Cloudflare R2 configuré** :
   - Bucket créé
   - API Token généré
   - Credentials récupérés

2. **Variables dans ~/.bashrc** :
   ```bash
   export SUREN_GED_CLOUDFLARE_TOKEN="xxx"
   export SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID="xxx"
   export SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY="xxx"
   export SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT="xxx"
   ```

3. **Scripts de déploiement mis à jour** (voir section Scripts)

### Déploiement Test

```bash
./scripts/deploy_back_test.sh
```

Les credentials R2 sont automatiquement injectés via GCP Secret Manager.

### Déploiement Production

```bash
./scripts/deploy_back_prod.sh
```

Confirmation requise (`prod`).

### Développement local

```bash
./scripts/run-local-back_test.sh
```

Le script charge automatiquement les credentials depuis `~/.bashrc`.

---

## Troubleshooting

### Erreur : "Credentials R2 manquants"

**Symptôme :** Le backend refuse de démarrer avec une erreur sur les credentials R2.

**Solution :**
1. Vérifier que les variables sont définies dans `~/.bashrc`
2. Sourcer le fichier : `source ~/.bashrc`
3. Vérifier : `echo $SUREN_GED_CLOUDFLARE_TOKEN`

### Erreur : "NoSuchKey" lors du download

**Symptôme :** Le fichier existe en base de données mais pas sur R2.

**Causes possibles :**
- Fichier uploadé avant la migration vers R2 (ancien stockage /tmp)
- Fichier supprimé manuellement du bucket
- Clé S3 incorrecte en base de données

**Solution :**
- Si fichier ancien : le réimporter
- Vérifier la clé S3 dans la DB : `SELECT storage_path FROM email_attachments WHERE id = 'xxx'`

### Erreur : "AccessDenied" sur R2

**Symptôme :** Le client S3 reçoit une erreur 403 d'AWS/R2.

**Causes possibles :**
- Credentials incorrects
- Token expiré
- Permissions insuffisantes sur le bucket

**Solution :**
1. Vérifier les credentials dans le dashboard Cloudflare
2. Régénérer un API Token si nécessaire
3. Vérifier les permissions du token (Object Read & Write)

### Lenteur sur les uploads

**Symptôme :** Les uploads sont lents (> 5s pour des fichiers < 1MB).

**Causes possibles :**
- Région R2 éloignée
- Pas de connexion keep-alive

**Solution :**
- Vérifier l'endpoint utilisé (eu, us, apac)
- Activer le keep-alive dans boto3 (déjà configuré)
- Considérer l'upload par chunks pour les gros fichiers

### Coûts R2

**Surveillance :**
- Dashboard Cloudflare > R2 > Metrics
- Facturation : ~$0.015/GB/mois de stockage
- Pas de frais de sortie (contrairement à S3)

**Optimisations :**
- Lifecycle policies pour les fichiers temporaires
- Compression avant upload si pertinent

---

## Références

- [Documentation Cloudflare R2](https://developers.cloudflare.com/r2/)
- [API S3 Compatible](https://developers.cloudflare.com/r2/api/s3/api/)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---

## Changelog

| Date | Version | Changement |
|------|---------|------------|
| 2025-01-15 | 1.0.0 | Migration Full R2 - Suppression du stockage local |
