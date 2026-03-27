-- 005_auth_triggers.sql
-- Triggers pour automatiser la création de membership au signup

-- Trigger function : créer membership quand un user s'inscrit
CREATE OR REPLACE FUNCTION create_user_membership()
RETURNS TRIGGER AS $$
BEGIN
    -- Créer le membership à partir de pre_authorized_emails
    INSERT INTO user_org_membership (user_id, org_id, role)
    SELECT 
        NEW.id,
        pae.org_id,
        pae.role
    FROM pre_authorized_emails pae
    WHERE pae.email = NEW.email
    AND pae.is_active = true;
    
    -- Marquer l'invitation comme utilisée
    UPDATE pre_authorized_emails 
    SET used_at = NOW() 
    WHERE email = NEW.email;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Supprimer le trigger s'il existe déjà
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Créer le trigger au signup
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION create_user_membership();

COMMENT ON FUNCTION create_user_membership() IS 'Crée automatiquement le membership org au signup';
