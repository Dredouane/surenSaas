"""
Service de stockage de fichiers - Cloudflare R2 (S3-Compatible).

Stockage full cloud sans dépendance au filesystem local.
Utilise boto3 pour communiquer avec l'API S3 de Cloudflare R2.

Structure des dossiers:
    {environment}/org/{org_id}/{folder}/{timestamp}_{filename}
    
    Ex: test/org/xxx/invoices/20250115_143022_123456_facture.pdf
"""

import mimetypes
from datetime import datetime
from typing import Optional
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class FileStorageService:
    """
    Service de stockage de fichiers sur Cloudflare R2.
    
    Cette implémentation utilise boto3 pour stocker/récupérer des fichiers
    sur R2 via l'API S3-compatible. Il n'y a plus de stockage local.
    
    Attributes:
        s3_client: Client boto3 configuré pour R2
        bucket_name: Nom du bucket R2
        environment: Environnement courant (test/production)
    """
    
    def __init__(self):
        """Initialise le service avec les credentials R2."""
        self.settings = get_settings()
        self.environment = self.settings.environment.lower()
        
        # Vérifier que les credentials sont configurés
        self._validate_credentials()
        
        # Initialiser le client S3 pour R2
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.settings.r2_endpoint_url,
            aws_access_key_id=self.settings.r2_access_key_id,
            aws_secret_access_key=self.settings.r2_secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'  # R2 n'utilise pas de régions
        )
        self.bucket_name = self.settings.r2_bucket_name
        
        logger.info(f"📁 FileStorageService initialisé (R2)")
        logger.info(f"   Bucket: {self.bucket_name}")
        logger.info(f"   Environnement: {self.environment}")
        logger.info(f"   Endpoint: {self.settings.r2_endpoint_url}")
    
    def _validate_credentials(self):
        """Vérifie que tous les credentials R2 sont configurés."""
        required = [
            ('r2_endpoint_url', self.settings.r2_endpoint_url),
            ('r2_access_key_id', self.settings.r2_access_key_id),
            ('r2_secret_access_key', self.settings.r2_secret_access_key),
        ]
        
        missing = [name for name, value in required if not value]
        
        if missing:
            error_msg = (
                f"❌ Credentials Cloudflare R2 manquants: {', '.join(missing)}\n"
                f"Veuillez configurer les variables dans ~/.bashrc:\n"
                f"  - SUREN_GED_CLOUDFLARE_TOKEN\n"
                f"  - SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID\n"
                f"  - SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY\n"
                f"  - SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _build_key(self, org_id: str, folder: str, filename: str) -> str:
        """
        Construit la clé S3 avec préfixe environment.
        
        Format: {env}/org/{org_id}/{folder}/{timestamp}_{filename}
        
        Args:
            org_id: ID de l'organisation
            folder: Dossier logique (emails, invoices, ao, telegram, general)
            filename: Nom original du fichier
            
        Returns:
            Clé S3 complète
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_filename = f"{timestamp}_{filename}"
        return f"{self.environment}/org/{org_id}/{folder}/{safe_filename}"
    
    def _get_content_type(self, filename: str) -> str:
        """Déduit le Content-Type depuis l'extension du fichier."""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'
    
    async def store_file(
        self, 
        file_data: bytes, 
        filename: str,
        org_id: Optional[str] = None,
        folder: str = "general"
    ) -> str:
        """
        Stocke un fichier sur R2.
        
        Args:
            file_data: Données binaires du fichier
            filename: Nom original du fichier
            org_id: ID de l'organisation (obligatoire)
            folder: Dossier logique (emails, invoices, ao, telegram, general)
            
        Returns:
            Clé S3 complète (à sauvegarder en base de données)
            
        Raises:
            ValueError: Si org_id est manquant
            ClientError: Si erreur lors de l'upload
        """
        if not org_id:
            raise ValueError("org_id est obligatoire pour le stockage R2")
        
        key = self._build_key(org_id, folder, filename)
        content_type = self._get_content_type(filename)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type
            )
            
            logger.info(f"💾 Fichier stocké sur R2: {key} ({len(file_data)} bytes)")
            return key
            
        except ClientError as e:
            logger.error(f"❌ Erreur upload R2: {e}")
            raise
    
    async def get_file(self, key: str) -> Optional[bytes]:
        """
        Récupère un fichier depuis R2.
        
        Args:
            key: Clé S3 du fichier
            
        Returns:
            Données binaires du fichier ou None si inexistant
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, 
                Key=key
            )
            return response['Body'].read()
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"⚠️ Fichier non trouvé sur R2: {key}")
                return None
            logger.error(f"❌ Erreur récupération fichier R2: {e}")
            raise
    
    async def get_presigned_url(
        self, 
        key: str, 
        expires: int = 3600,
        filename: Optional[str] = None
    ) -> str:
        """
        Génère une URL signée pour téléchargement.
        
        L'URL signée permet d'accéder au fichier directement sur R2
        sans passer par l'API backend. Elle expire après un certain temps.
        
        Args:
            key: Clé S3 du fichier
            expires: Durée de validité en secondes (défaut: 3600 = 1h)
            filename: Nom du fichier pour le header Content-Disposition
            
        Returns:
            URL signée complète
        """
        params = {
            'Bucket': self.bucket_name,
            'Key': key
        }
        
        if filename:
            # Permet au navigateur de suggérer ce nom lors du téléchargement
            params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires
            )
            
            logger.debug(f"🔗 URL signée générée pour {key} (expire dans {expires}s)")
            return url
            
        except ClientError as e:
            logger.error(f"❌ Erreur génération URL signée: {e}")
            raise
    
    async def delete_file(self, key: str) -> bool:
        """
        Supprime un fichier de R2.
        
        Args:
            key: Clé S3 du fichier
            
        Returns:
            True si supprimé avec succès, False sinon
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name, 
                Key=key
            )
            logger.info(f"🗑️ Fichier supprimé de R2: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Erreur suppression fichier R2 {key}: {e}")
            return False
    
    async def file_exists(self, key: str) -> bool:
        """
        Vérifie si un fichier existe sur R2.
        
        Args:
            key: Clé S3 du fichier
            
        Returns:
            True si le fichier existe
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def get_file_info(self, key: str) -> Optional[dict]:
        """
        Retourne les informations d'un fichier sur R2.
        
        Args:
            key: Clé S3 du fichier
            
        Returns:
            Dictionnaire avec infos ou None si fichier inexistant
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return {
                "key": key,
                "size_bytes": response.get('ContentLength', 0),
                "size_mb": round(response.get('ContentLength', 0) / 1024 / 1024, 2),
                "content_type": response.get('ContentType', 'unknown'),
                "last_modified": response.get('LastModified').isoformat() if response.get('LastModified') else None,
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            logger.error(f"❌ Erreur récupération info fichier R2: {e}")
            return None


# Singleton instance
file_storage_service = FileStorageService()
