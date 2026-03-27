"""
Service de stockage de fichiers temporaire.

Stockage local dans /tmp pour l'instant.
À remplacer plus tard par S3 ou autre provider.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from app.core.logging import get_logger

logger = get_logger(__name__)


class FileStorageService:
    """
    Service de stockage de fichiers temporaire.
    
    Pour l'instant, stocke les fichiers dans /tmp.
    À remplacer par un vrai service S3/Storage cloud plus tard.
    """
    
    def __init__(self, base_path: str = "/tmp/surensaas"):
        """
        Initialise le service de stockage.
        
        Args:
            base_path: Chemin de base pour le stockage temporaire
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 FileStorageService initialisé: {self.base_path}")
    
    async def store_file(
        self, 
        file_data: bytes, 
        filename: str,
        org_id: Optional[str] = None
    ) -> str:
        """
        Stocke un fichier temporairement.
        
        Args:
            file_data: Données binaires du fichier
            filename: Nom du fichier
            org_id: ID de l'organisation (pour isolation)
            
        Returns:
            Chemin local du fichier stocké
        """
        # Créer un sous-dossier par org si spécifié
        if org_id:
            target_dir = self.base_path / org_id
        else:
            target_dir = self.base_path / "general"
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Ajouter timestamp pour éviter collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_filename = f"{timestamp}_{filename}"
        
        file_path = target_dir / safe_filename
        
        # Écrire le fichier
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"💾 Fichier stocké: {file_path} ({len(file_data)} bytes)")
        
        return str(file_path)
    
    def get_file(self, file_path: str) -> Optional[bytes]:
        """
        Récupère un fichier.
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            Données binaires ou None si fichier inexistant
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.warning(f"⚠️ Fichier non trouvé: {file_path}")
            return None
        
        with open(path, 'rb') as f:
            return f.read()
    
    def delete_file(self, file_path: str) -> bool:
        """
        Supprime un fichier.
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            True si supprimé, False sinon
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"🗑️ Fichier supprimé: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Erreur suppression fichier {file_path}: {e}")
            return False
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Nettoie les fichiers vieux de plus de X heures.
        
        Args:
            max_age_hours: Âge maximum des fichiers en heures
            
        Returns:
            Nombre de fichiers supprimés
        """
        deleted_count = 0
        max_age = timedelta(hours=max_age_hours)
        now = datetime.now()
        
        try:
            for org_dir in self.base_path.iterdir():
                if org_dir.is_dir():
                    for file_path in org_dir.iterdir():
                        if file_path.is_file():
                            # Vérifier l'âge du fichier
                            stat = file_path.stat()
                            file_age = now - datetime.fromtimestamp(stat.st_mtime)
                            
                            if file_age > max_age:
                                file_path.unlink()
                                deleted_count += 1
                                logger.debug(f"🧹 Fichier nettoyé: {file_path}")
            
            logger.info(f"🧹 Nettoyage terminé: {deleted_count} fichiers supprimés")
            
        except Exception as e:
            logger.error(f"❌ Erreur nettoyage fichiers: {e}")
        
        return deleted_count
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Retourne les informations d'un fichier.
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            Dictionnaire avec infos ou None
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            stat = path.stat()
            
            return {
                "path": str(path),
                "filename": path.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération info fichier: {e}")
            return None


# Singleton
file_storage_service = FileStorageService()
