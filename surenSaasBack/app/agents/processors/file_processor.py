"""
Processeurs de fichiers pour l'extraction.

Gère le téléchargement, l'encodage et l'optimisation des fichiers.
"""

import os
import base64
from pathlib import Path
from typing import Union, Optional
from io import BytesIO

import httpx
from PIL import Image

from app.core.logging import get_logger

logger = get_logger(__name__)


class FileProcessor:
    """
    Processeur de fichiers pour préparer les documents avant extraction.
    
    Gère :
    - Téléchargement depuis URL
    - Encodage base64
    - Optimisation images
    - Validation formats
    """
    
    # Tailles max (Gemini Flash 1.5 supporte jusqu'à 20MB par fichier)
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
    MAX_IMAGE_DIMENSION = 4096  # pixels
    
    # Formats supportés
    SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    SUPPORTED_DOCUMENTS = {'.pdf'}
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def download_from_url(self, url: str) -> bytes:
        """
        Télécharge un fichier depuis une URL.
        
        Args:
            url: URL du fichier
            
        Returns:
            Données binaires du fichier
        """
        try:
            logger.info(f"⬇️  Téléchargement: {url}")
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.content
            
            if len(data) > self.MAX_FILE_SIZE:
                raise ValueError(
                    f"Fichier trop gros: {len(data) / 1024 / 1024:.1f}MB "
                    f"(max: {self.MAX_FILE_SIZE / 1024 / 1024}MB)"
                )
            
            logger.info(f"✅ Téléchargé: {len(data)} bytes")
            return data
            
        except Exception as e:
            logger.error(f"❌ Erreur téléchargement: {e}")
            raise
    
    def encode_base64(self, data: bytes) -> str:
        """
        Encode des données en base64.
        
        Args:
            data: Données binaires
            
        Returns:
            Chaîne base64
        """
        return base64.b64encode(data).decode('utf-8')
    
    def decode_base64(self, encoded: str) -> bytes:
        """
        Décode une chaîne base64.
        
        Args:
            encoded: Chaîne base64
            
        Returns:
            Données binaires
        """
        return base64.b64decode(encoded)
    
    def optimize_image(
        self,
        image_data: bytes,
        max_size: Optional[tuple] = None,
        quality: int = 85
    ) -> bytes:
        """
        Optimise une image pour réduire la taille.
        
        Args:
            image_data: Données binaires de l'image
            max_size: Taille max (width, height)
            quality: Qualité JPEG (1-100)
            
        Returns:
            Données optimisées
        """
        try:
            img = Image.open(BytesIO(image_data))
            
            # Convertir en RGB si nécessaire
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Redimensionner si nécessaire
            if max_size:
                img.thumbnail(max_size, Image.LANCZOS)
            elif max(img.size) > self.MAX_IMAGE_DIMENSION:
                ratio = self.MAX_IMAGE_DIMENSION / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.LANCZOS)
            
            # Sauvegarder optimisé
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            optimized_data = output.read()
            
            logger.info(
                f"🖼️  Image optimisée: {len(image_data)} → {len(optimized_data)} bytes "
                f"({len(optimized_data)/len(image_data)*100:.1f}%)"
            )
            
            return optimized_data
            
        except Exception as e:
            logger.warning(f"⚠️  Optimisation image échouée, utilisation originale: {e}")
            return image_data
    
    def validate_file(self, file_path: Union[str, Path]) -> tuple:
        """
        Valide un fichier (format, taille).
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            (est_valide: bool, message: str, mime_type: str)
        """
        path = Path(file_path)
        
        if not path.exists():
            return False, f"Fichier non trouvé: {file_path}", ""
        
        # Vérifier l'extension
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_IMAGES and ext not in self.SUPPORTED_DOCUMENTS:
            return False, f"Format non supporté: {ext}", ""
        
        # Vérifier la taille
        size = path.stat().st_size
        if size > self.MAX_FILE_SIZE:
            return False, (
                f"Fichier trop gros: {size / 1024 / 1024:.1f}MB "
                f"(max: {self.MAX_FILE_SIZE / 1024 / 1024}MB)"
            ), ""
        
        # Déterminer le type MIME
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        mime_type = mime_types.get(ext, 'application/octet-stream')
        
        return True, "OK", mime_type
    
    def get_file_info(self, file_path: Union[str, Path]) -> dict:
        """
        Retourne les informations d'un fichier.
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            Dictionnaire avec infos
        """
        path = Path(file_path)
        
        if not path.exists():
            return {"error": "Fichier non trouvé"}
        
        stat = path.stat()
        
        info = {
            "path": str(path.absolute()),
            "name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "modified": stat.st_mtime,
        }
        
        # Si image, ajouter dimensions
        if path.suffix.lower() in self.SUPPORTED_IMAGES:
            try:
                with Image.open(path) as img:
                    info["dimensions"] = img.size
                    info["mode"] = img.mode
            except Exception as e:
                info["image_error"] = str(e)
        
        return info
    
    async def prepare_for_extraction(
        self,
        source: str,
        optimize: bool = True
    ) -> tuple:
        """
        Prépare un fichier pour l'extraction.
        
        Args:
            source: URL ou chemin local
            optimize: Optimiser les images
            
        Returns:
            (données binaires, mime_type)
        """
        # Déterminer si c'est une URL ou un chemin local
        if source.startswith(('http://', 'https://')):
            data = await self.download_from_url(source)
            # Déterminer le type depuis l'URL
            ext = Path(source).suffix.lower()
            mime_types = {
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
            }
            mime_type = mime_types.get(ext, 'application/octet-stream')
        else:
            # Chemin local
            is_valid, message, mime_type = self.validate_file(source)
            if not is_valid:
                raise ValueError(message)
            
            with open(source, 'rb') as f:
                data = f.read()
        
        # Optimiser si image
        if optimize and mime_type.startswith('image/'):
            data = self.optimize_image(data)
        
        return data, mime_type
    
    async def close(self):
        """Ferme le client HTTP."""
        await self.client.aclose()
