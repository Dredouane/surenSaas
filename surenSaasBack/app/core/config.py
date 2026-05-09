from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Configuration de l'application."""
    model_config = SettingsConfigDict(
        # Ne pas utiliser env_file car on charge manuellement depuis .env.test/.env.prod
        env_file=None,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Environment (détermine les préfixes à utiliser)
    environment: str = "development"
    
    # Supabase (peut être partagé ou préfixé)
    supabase_url: str = ""
    supabase_service_key: str = ""
    
    # JWT (devrait être différent par environnement)
    jwt_secret: str = ""
    
    # CORS - format: "http://localhost:3000,https://..."
    allowed_origins: str = "http://localhost:3000"
    
    # Organisation (préfixée TEST_ORG_ID ou PROD_ORG_ID)
    org_id: str = ""
    org_slug: str = ""
    
    # Telegram Construction Bots (préfixés TEST_ ou PROD_)
    telegram_construction_bot_token: str = ""
    telegram_construction_bot_username: str = ""
    
    # Telegram API URL (pour pointer vers le Local Bot API Server en test)
    telegram_api_url: str = "https://api.telegram.org"
    
    def model_post_init(self, __context) -> None:
        """Charge les variables d'environnement (préfixées ou non)."""
        env = self.environment.lower()
        
        # Mapping des variables avec fallback
        var_mappings = [
            # ... autres mappings ...
            ("telegram_api_url", [
                "TELEGRAM_API_URL",
            ]),
            ("supabase_url", [
                "SUPABASE_URL",
            ]),
            # ...
        ]
        # (J'ajoute juste le champ au settings et je le mappe)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"  # Modèle recommandé pour Vertex AI
    gemini_location: str = "europe-west1"  # Région Vertex AI
    gcp_project_id: str = ""  # Projet GCP pour Vertex AI
    
    # Secrétaire IA (préfixés TEST_ ou PROD_)
    secretariat_model: str = "gemini-2.5-flash-lite"  # Modèle pour la Secrétaire IA
    
    # App
    app_name: str = "SurenSaaS API"
    debug: bool = False

    # TMA (Telegram Mini App)
    tma_host: str = ""
    tma_extraction_model: str = "gemini-2.5-flash-lite"  # Modèle rapide pour les extractions TMA

    # LLM Provider (gemini ou deepseek)
    llm_provider: str = "gemini"
    deepseek_api_key: str = ""

    # OpenRouter (Whisper transcription)
    open_router_api_key: str = ""
    whisper_model: str = "whisper-large-v3"

    # Cloudflare R2 Configuration (S3-Compatible)
    # Mêmes credentials pour test et prod (isolation par folder)
    r2_endpoint_url: str = ""       # SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT
    r2_access_key_id: str = ""      # SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID
    r2_secret_access_key: str = ""  # SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY
    r2_token: str = ""              # SUREN_GED_CLOUDFLARE_TOKEN
    r2_bucket_name: str = ""        # SUREN_GED_CLOUDFLARE_BUCKET_NAME
    
    def model_post_init(self, __context) -> None:
        """Charge les variables d'environnement (préfixées ou non)."""
        env = self.environment.lower()
        
        # Mapping des variables avec fallback
        # Format: (nom_attribut, [liste des noms de variables possibles])
        var_mappings = [
            ("supabase_url", [
                "SUPABASE_URL",
            ]),
            ("supabase_service_key", [
                f"{env}_supabase_service_key",  # TEST_SUPABASE_SERVICE_KEY
                "supabase_service_key",          # SUPABASE_SERVICE_KEY (GCP)
            ]),
            ("jwt_secret", [
                f"{env}_jwt_secret",
                "jwt_secret",
            ]),
            ("org_id", [
                f"{env}_org_id",
                "org_id",
            ]),
            ("org_slug", [
                f"{env}_org_slug",
                "org_slug",
            ]),
            ("telegram_construction_bot_token", [
                f"{env}_telegram_construction_bot_token",
                "telegram_construction_bot_token",
            ]),
            ("telegram_construction_bot_username", [
                f"{env}_telegram_construction_bot_username",
                "telegram_construction_bot_username",
            ]),
            ("telegram_api_url", [
                "TELEGRAM_API_URL",
            ]),
            ("gemini_api_key", [
                f"{env}_google_gemini_credentials_b64",
                "google_gemini_credentials_b64",
                "GOOGLE_API_KEY",
            ]),
            ("gcp_project_id", [
                f"{env}_gcp_project_id",
                "gcp_project_id",
                "GOOGLE_CLOUD_PROJECT",
                "GCP_PROJECT",
            ]),
            ("secretariat_model", [
                f"{env}_vertex_ai_secretariat_model",
                "vertex_ai_secretariat_model",
            ]),
            ("allowed_origins", [
                "ALLOWED_ORIGINS",
            ]),
            ("tma_host", [
                "TMA_HOST",
                "tma_host",
            ]),
            ("tma_extraction_model", [
                "TMA_EXTRACTION_MODEL",
                "tma_extraction_model",
            ]),
            # Cloudflare R2 (SUREN_GED_CLOUDFLARE_* pour local, R2_* pour GCP)
            ("r2_endpoint_url", [
                "SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT",
                "R2_ENDPOINT_URL",
            ]),
            ("r2_access_key_id", [
                "SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID",
                "R2_ACCESS_KEY_ID",
            ]),
            ("r2_secret_access_key", [
                "SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY",
                "R2_SECRET_ACCESS_KEY",
            ]),
            ("r2_token", [
                "SUREN_GED_CLOUDFLARE_TOKEN",
                "R2_TOKEN",
            ]),
            ("r2_bucket_name", [
                "SUREN_GED_CLOUDFLARE_BUCKET_NAME",
                "R2_BUCKET_NAME",
            ]),
            # OpenRouter / Whisper
            ("open_router_api_key", [
                "SUREN_OPEN_ROUTER_API_KEY",
                "open_router_api_key",
            ]),
            ("whisper_model", [
                "WHISPER_MODEL",
                "whisper_model",
            ]),
            ("llm_provider", [
                "LLM_PROVIDER",
            ]),
            ("deepseek_api_key", [
                "DEEPSEEK_API_KEY",
                "SUREN_DEEP_SEEK_API_KEY",
            ]),
        ]
        
        for attr_name, env_var_names in var_mappings:
            value = None
            used_var = None
            
            # Chercher dans l'ordre des priorités
            for env_var_name in env_var_names:
                env_value = os.getenv(env_var_name.upper())
                if env_value and env_value.strip():
                    value = env_value
                    used_var = env_var_name.upper()
                    break
            
            if value:
                setattr(self, attr_name, value)
                print(f"   {attr_name}: [CHARGÉ depuis {used_var}]")
            elif getattr(self, attr_name):
                print(f"   {attr_name}: [DÉFINI par défaut]")
            else:
                print(f"   {attr_name}: [NON DÉFINI]")
    
    def is_deepseek(self) -> bool:
        """Retourne True si le provider LLM est DeepSeek."""
        return self.llm_provider.lower() == "deepseek"

    def get_allowed_origins(self) -> List[str]:
        """Parse la liste des origines depuis la string."""
        if not self.allowed_origins:
            return ["http://localhost:3000"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    def is_configured(self) -> bool:
        """Vérifie que la configuration minimale est présente."""
        return bool(self.supabase_url and self.supabase_service_key and self.jwt_secret)


# Singleton pattern - créé à la première utilisation
_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    """Récupère les settings (singleton)."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
        # Log pour debug
        print(f"🔧 Settings initialisés:")
        print(f"   ENVIRONMENT: {_settings_instance.environment}")
        print(f"   Configuré: {_settings_instance.is_configured()}")
    return _settings_instance


# Compatibilité ascendante - les modules qui importent 'settings' directement
# obtiendront l'instance au moment de l'import
settings = get_settings()
