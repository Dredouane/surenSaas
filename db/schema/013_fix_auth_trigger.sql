-- 013_fix_auth_trigger.sql
-- Correction du trigger on_auth_user_created pour rendre org_id optionnel

-- Supprimer l'ancien trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS public.handle_new_user();

-- Créer la nouvelle fonction avec org_id optionnel
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Insérer dans users seulement si org_id est présent dans les métadonnées
    -- ou si l'utilisateur existe déjà dans pre_authorized_emails
    INSERT INTO public.users (id, email, org_id)
    SELECT 
        NEW.id,
        NEW.email,
        COALESCE(
            (NEW.raw_user_meta_data->>'org_id')::uuid,
            (SELECT org_id FROM public.pre_authorized_emails WHERE email = NEW.email AND is_active = true LIMIT 1)
        )
    WHERE COALESCE(
        (NEW.raw_user_meta_data->>'org_id')::uuid,
        (SELECT org_id FROM public.pre_authorized_emails WHERE email = NEW.email AND is_active = true LIMIT 1)
    ) IS NOT NULL;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Recréer le trigger
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Ajouter un commentaire
COMMENT ON FUNCTION public.handle_new_user() IS 'Crée automatiquement le profil utilisateur avec org_id optionnel';
