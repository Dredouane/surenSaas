from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from supabase import create_client
from datetime import datetime, timedelta
from uuid import UUID
import jwt
import hashlib
import time

from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.core.logging import get_logger, log_auth_attempt

# Logger pour ce module
logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Lazy initialization of Supabase client
_supabase_client = None

def get_supabase():
    """Récupère le client Supabase avec gestion d'erreurs."""
    global _supabase_client
    
    if _supabase_client is None:
        try:
            logger.debug("Initialisation du client Supabase...")
            
            if not settings.supabase_url or not settings.supabase_service_key:
                logger.error("Configuration Supabase manquante")
                raise HTTPException(
                    status_code=500, 
                    detail="Configuration Supabase manquante. Vérifiez les variables d'environnement."
                )
            
            _supabase_client = create_client(settings.supabase_url, settings.supabase_service_key)
            logger.info("✅ Client Supabase initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur initialisation Supabase: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erreur connexion Supabase: {str(e)}"
            )
    
    return _supabase_client

# Cookie settings
COOKIE_NAME = "session_token"
COOKIE_MAX_AGE = 60 * 60  # 1 heure (3600 secondes)

def create_session_token(user_id: str, email: str, org_id: str, org_slug: str, role: str) -> str:
    """Crée un JWT pour la session."""
    try:
        payload = {
            "sub": user_id,
            "email": email,
            "org_id": org_id,
            "org_slug": org_slug,
            "role": role,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1)  # 1 heure
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        logger.debug(f"Token créé pour {email}")
        return token
    except Exception as e:
        logger.error(f"Erreur création token pour {email}: {e}")
        raise

def set_session_cookie(response: Response, token: str):
    """Set le cookie httpOnly."""
    is_production = settings.environment == "production"
    
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/"
    )
    logger.debug(f"Cookie de session défini (secure={is_production}, samesite=lax)")

class AuthenticationError(HTTPException):
    """Exception personnalisée pour les erreurs d'authentification."""
    def __init__(self, detail: str, redirect_to_login: bool = False):
        super().__init__(status_code=401, detail=detail)
        self.redirect_to_login = redirect_to_login

def get_current_user_from_cookie(request: Request):
    """Récupère l'utilisateur depuis le cookie."""
    token = request.cookies.get(COOKIE_NAME)
    
    if not token:
        logger.warning("Cookie de session manquant")
        raise AuthenticationError("Session invalide", redirect_to_login=True)
    
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        logger.debug(f"Token décodé pour {payload.get('email')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expiré - redirection vers login requise")
        raise AuthenticationError("Session expirée", redirect_to_login=True)
    except jwt.InvalidTokenError as e:
        logger.error(f"Token invalide: {e}")
        raise AuthenticationError("Session invalide", redirect_to_login=True)

def clear_session_cookie(response: Response):
    """Supprime le cookie de session."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax"
    )
    logger.debug("Cookie de session supprimé")

# Schémas Pydantic
class EmailCheckRequest(BaseModel):
    email: EmailStr

class EmailCheckResponse(BaseModel):
    authorized: bool
    exists: bool
    org_id: str | None = None
    org_slug: str | None = None
    org_name: str | None = None
    role: str | None = None
    message: str | None = None

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    org_id: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Routes
@router.get("/session")
async def check_session(request: Request):
    """Vérifie si la session est valide (pour le middleware Next.js)."""
    try:
        user = get_current_user_from_cookie(request)
        logger.info(f"Session vérifiée pour {user.get('email')}")
        return {
            "user_id": user["sub"],
            "email": user["email"],
            "org_id": user["org_id"],
            "org_slug": user["org_slug"],
            "role": user["role"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur vérification session: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Session invalide")

@router.post("/check-email", response_model=EmailCheckResponse)
@rate_limit(max_requests=10, window=60)
async def check_email(request: Request, data: EmailCheckRequest):
    """
    Vérifie si l'utilisateur peut se connecter ou s'inscrire.
    
    Workflow:
    1. Vérifier si l'utilisateur existe déjà → Si oui, LOGIN (exists=true)
    2. Sinon, vérifier s'il est pre-authorized → Si oui, SIGNUP (exists=false)
    3. Sinon → Refuser l'accès
    """
    start_time = time.time()
    logger.info(f"🔍 Vérification email: {data.email}")
    
    try:
        # ÉTAPE 1: Vérifier si l'utilisateur existe déjà (dans la table users - accessible avec ANON key)
        user_exists = False
        org_id = None
        org_slug = None
        org_name = None
        role = None
        
        try:
            # Chercher d'abord dans users (accessible avec ANON key)
            user_result = get_supabase().table('users') \
                .select('id, org_id, role') \
                .eq('email', data.email) \
                .maybe_single() \
                .execute()
            
            if user_result.data:
                user_exists = True
                org_id = user_result.data.get('org_id')
                role = user_result.data.get('role')
                logger.info(f"✅ Utilisateur trouvé dans table users: {data.email} → Proposer LOGIN")
        except Exception as e:
            logger.warning(f"Erreur vérification table users: {e}")
        
        # Si pas trouvé dans users, essayer auth.users (nécessite SERVICE key)
        if not user_exists:
            try:
                users_list = get_supabase().auth.admin.list_users()
                for user in users_list:
                    if user.email == data.email:
                        user_exists = True
                        org_id = user.user_metadata.get('org_id') if user.user_metadata else None
                        logger.debug(f"✅ Utilisateur trouvé dans auth.users: {user.id}")
                        break
            except Exception as e:
                logger.debug(f"Impossible de vérifier auth.users (normal avec ANON key): {e}")
        
        # Récupérer le org_slug depuis les organisations si on a un org_id
        if org_id:
            try:
                org_result = get_supabase().table('organizations') \
                    .select('slug, name') \
                    .eq('id', org_id) \
                    .maybe_single() \
                    .execute()
                if org_result.data:
                    org_slug = org_result.data.get('slug')
                    org_name = org_result.data.get('name')
            except Exception as e:
                logger.warning(f"Erreur récupération org: {e}")
        
        # Si utilisateur existe et a les infos org → Autoriser LOGIN
        if user_exists and org_id:
            duration = (time.time() - start_time) * 1000
            log_auth_attempt(logger, data.email, True, org_id=org_id)
            logger.info(f"✅ LOGIN autorisé pour {data.email} en {duration:.2f}ms")
            
            return EmailCheckResponse(
                authorized=True,
                exists=True,
                org_id=org_id,
                org_slug=org_slug or '',
                org_name=org_name or '',
                role=role or 'user'
            )
        
        # ÉTAPE 2: L'utilisateur n'existe pas, vérifier s'il est pre-authorized
        logger.debug(f"Recherche dans pre_authorized_emails pour {data.email}")
        
        pre_auth_result = get_supabase().table('pre_authorized_emails') \
            .select('*, organizations!inner(slug, name)') \
            .eq('email', data.email) \
            .eq('is_active', True) \
            .maybe_single() \
            .execute()
        
        pre_auth = pre_auth_result.data if hasattr(pre_auth_result, 'data') else pre_auth_result
        
        if pre_auth:
            # Utilisateur pre-authorized mais pas encore créé → Proposer SIGNUP
            org_data = pre_auth.get('organizations', {})
            duration = (time.time() - start_time) * 1000
            
            log_auth_attempt(logger, data.email, True, org_id=pre_auth.get('org_id'))
            logger.info(f"✅ SIGNUP autorisé pour {data.email} en {duration:.2f}ms")
            
            return EmailCheckResponse(
                authorized=True,
                exists=False,
                org_id=pre_auth.get('org_id'),
                org_slug=org_data.get('slug'),
                org_name=org_data.get('name'),
                role=pre_auth.get('role')
            )
        
        # ÉTAPE 3: Ni existant, ni pre-authorized → Refuser
        logger.warning(f"Email non autorisé: {data.email}")
        log_auth_attempt(logger, data.email, False, error="Email non pré-autorisé")
        return EmailCheckResponse(
            authorized=False,
            exists=False,
            message="Cet email n'est pas autorisé. Contactez votre administrateur."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(
            f"❌ Erreur vérification email {data.email}: {str(e)}",
            extra={"duration_ms": duration},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )

@router.post("/signup")
@rate_limit(max_requests=5, window=60)
async def signup(request: Request, data: SignupRequest, response: Response):
    """Crée un nouvel utilisateur avec cookie session."""
    start_time = time.time()
    logger.info(f"📝 Tentative signup: {data.email}")
    
    try:
        if len(data.password) < 8:
            logger.warning(f"Mot de passe trop court pour {data.email}")
            raise HTTPException(
                status_code=400,
                detail="Le mot de passe doit contenir au moins 8 caractères"
            )
        
        # Vérifier pre_authorized_emails
        logger.debug(f"Vérification pre_auth pour {data.email}")
        pre_auth = get_supabase().table('pre_authorized_emails') \
            .select('*') \
            .eq('email', data.email) \
            .eq('org_id', data.org_id) \
            .eq('is_active', True) \
            .single() \
            .execute()
        
        if not pre_auth.data:
            logger.warning(f"Signup refusé - email non pré-autorisé: {data.email}")
            raise HTTPException(status_code=403, detail="Email non autorisé")
        
        # Créer l'utilisateur via Supabase Auth avec métadonnées
        logger.info(f"Création utilisateur Supabase: {data.email}")
        try:
            auth_response = get_supabase().auth.sign_up({
                "email": data.email,
                "password": data.password,
                "options": {
                    "data": {
                        "org_id": data.org_id,
                    }
                }
            })
        except Exception as auth_error:
            logger.error(f"Erreur création auth Supabase: {auth_error}")
            raise HTTPException(status_code=400, detail=f"Erreur création compte: {str(auth_error)}")
        
        user_id = auth_response.user.id
        logger.info(f"✅ Utilisateur créé dans auth: {user_id}")
        
        # Confirmer automatiquement l'email (pour environnement de test)
        # En production, vous voudrez peut-être garder la confirmation par email
        try:
            logger.debug(f"Confirmation automatique de l'email pour {data.email}")
            admin_supabase = get_supabase()
            # Utiliser l'API admin pour confirmer l'email
            admin_supabase.auth.admin.update_user_by_id(
                user_id,
                {"email_confirm": True}
            )
            logger.info(f"✅ Email confirmé automatiquement pour {data.email}")
        except Exception as confirm_error:
            logger.warning(f"Impossible de confirmer l'email automatiquement: {confirm_error}")
            # On continue quand même, l'utilisateur devra confirmer via email
        
        # Vérifier si le profil a été créé par le trigger
        profile_check = get_supabase().table('users').select('*').eq('id', user_id).execute()
        
        if not profile_check.data:
            # Créer le profil manuellement si le trigger n'a pas fonctionné
            logger.warning(f"Trigger n'a pas créé le profil, création manuelle pour {user_id}")
            try:
                # Récupérer le role depuis pre_authorized_emails
                pre_auth_role = pre_auth.data.get('role') if pre_auth.data else None
                
                get_supabase().table('users').insert({
                    'id': user_id,
                    'email': data.email,
                    'org_id': data.org_id,
                    'role': pre_auth_role,  # Transférer le role depuis pre_authorized_emails
                }).execute()
                logger.info(f"✅ Profil créé manuellement avec role: {pre_auth_role}")
            except Exception as profile_error:
                logger.error(f"Erreur création profil: {profile_error}")
                # On continue quand même, l'utilisateur auth est créé
        
        # Mettre à jour pre_authorized_emails
        get_supabase().table('pre_authorized_emails') \
            .update({'used_at': datetime.utcnow().isoformat()}) \
            .eq('email', data.email) \
            .execute()
        
        # Créer la session
        token = create_session_token(
            user_id,
            data.email,
            data.org_id,
            pre_auth.data['organizations']['slug'] if 'organizations' in pre_auth.data else '',
            pre_auth.data['role']
        )
        
        set_session_cookie(response, token)
        duration = (time.time() - start_time) * 1000
        
        log_auth_attempt(logger, data.email, True, org_id=data.org_id)
        logger.info(f"✅ Signup réussi pour {data.email} en {duration:.2f}ms")
        
        return {"success": True, "message": "Compte créé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(
            f"❌ Erreur signup {data.email}: {str(e)}",
            extra={"duration_ms": duration},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'inscription: {str(e)}")

@router.post("/login")
@rate_limit(max_requests=5, window=60)
async def login(request: Request, data: LoginRequest, response: Response):
    """Connecte un utilisateur existant."""
    start_time = time.time()
    logger.info(f"🔑 Tentative login: {data.email}")
    
    try:
        # Authentification Supabase
        logger.debug(f"Authentification Supabase pour {data.email}")
        try:
            auth_response = get_supabase().auth.sign_in_with_password({
                "email": data.email,
                "password": data.password,
            })
        except Exception as auth_error:
            logger.warning(f"Échec authentification pour {data.email}: {auth_error}")
            log_auth_attempt(logger, data.email, False, error=str(auth_error))
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
        
        user_id = auth_response.user.id
        logger.info(f"✅ Authentification réussie: {user_id}")
        
        # Récupérer les infos utilisateur depuis auth_response ou la table users
        org_id = None
        org_slug = ''
        role = 'user'
        
        # D'abord essayer de récupérer depuis user_metadata
        if auth_response.user.user_metadata:
            org_id = auth_response.user.user_metadata.get('org_id')
            role = auth_response.user.user_metadata.get('role', 'user')
        
        # Ensayer de récupérer depuis la table users (si l'utilisateur y est)
        try:
            user_data = get_supabase().table('users') \
                .select('org_id, role, organizations(slug)') \
                .eq('id', user_id) \
                .maybe_single() \
                .execute()
            
            if user_data.data:
                org_id = user_data.data.get('org_id', org_id)
                role = user_data.data.get('role', role)
                org_slug = user_data.data.get('organizations', {}).get('slug', '') if user_data.data.get('organizations') else ''
                logger.info(f"✅ Infos utilisateur récupérées depuis table users")
            else:
                logger.warning(f"Utilisateur {user_id} non trouvé dans table users, utilisation metadata")
                # Récupérer org_slug depuis organizations si on a un org_id
                if org_id:
                    try:
                        org_data = get_supabase().table('organizations') \
                            .select('slug') \
                            .eq('id', org_id) \
                            .maybe_single() \
                            .execute()
                        if org_data.data:
                            org_slug = org_data.data.get('slug', '')
                    except Exception as org_error:
                        logger.warning(f"Erreur récupération org: {org_error}")
        except Exception as e:
            logger.warning(f"Erreur récupération user_data: {e}, utilisation metadata")
        
        if not org_id:
            logger.error(f"org_id manquant pour {user_id}")
            raise HTTPException(status_code=500, detail="Configuration utilisateur incomplète")
        
        # Créer la session
        token = create_session_token(
            user_id,
            data.email,
            org_id,
            org_slug,
            role
        )
        
        set_session_cookie(response, token)
        duration = (time.time() - start_time) * 1000
        
        log_auth_attempt(logger, data.email, True, org_id=org_id)
        logger.info(f"✅ Login réussi pour {data.email} en {duration:.2f}ms")
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(
            f"❌ Erreur login {data.email}: {str(e)}",
            extra={"duration_ms": duration},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Erreur lors de la connexion: {str(e)}")

@router.post("/logout")
async def logout(response: Response):
    """Déconnecte l'utilisateur."""
    logger.info("Déconnexion")
    response.delete_cookie(COOKIE_NAME)
    return {"success": True}


# ============================================================================
# DÉPENDANCES FASTAPI
# ============================================================================

def get_current_user(request: Request) -> dict:
    """
    Dépendance FastAPI pour récupérer l'utilisateur courant.
    
    Usage:
        @router.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            return {"user_id": current_user["sub"]}
    """
    return get_current_user_from_cookie(request)


def get_org_id_from_user(current_user: dict = Depends(get_current_user)) -> UUID:
    """
    Dépendance FastAPI pour récupérer l'org_id de l'utilisateur courant.
    
    Usage:
        @router.get("/items")
        async def list_items(org_id: UUID = Depends(get_org_id_from_user)):
            ...
    """
    from uuid import UUID
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=401, detail="Organisation non définie")
    try:
        return UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="org_id invalide")
