-- 999_cleanup_user_org_membership.sql
-- Nettoyage : Suppression de user_org_membership et mise à jour des policies
-- À exécuter après avoir vérifié que tout fonctionne avec users.role

-- 1. Supprimer les anciennes RLS policies sur user_org_membership
DROP POLICY IF EXISTS "user_read_own_memberships" ON public.user_org_membership;
DROP POLICY IF EXISTS "Users can view own memberships" ON public.user_org_membership;
DROP POLICY IF EXISTS "Enable read access for users in same org" ON public.user_org_membership;

-- 2. Désactiver RLS sur user_org_membership (optionnel - peut être supprimé plus tard)
ALTER TABLE public.user_org_membership DISABLE ROW LEVEL SECURITY;

-- 3. Vérifier que users.role existe et a les bonnes valeurs
-- Ajouter la contrainte CHECK si elle n'existe pas
DO $$
BEGIN
    -- Vérifier si la contrainte existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints 
        WHERE constraint_name = 'users_role_check'
    ) THEN
        -- Ajouter la contrainte
        ALTER TABLE public.users 
        ADD CONSTRAINT users_role_check 
        CHECK (role IS NULL OR role IN ('admin', 'user'));
    END IF;
END $$;

-- 4. Ajouter RLS policies sur users pour sécurité
-- Désactiver temporairement pour éviter les erreurs si elles existent déjà
DROP POLICY IF EXISTS "users_select_own" ON public.users;
DROP POLICY IF EXISTS "users_update_own" ON public.users;

-- Policy SELECT : Un user voit son propre profil
CREATE POLICY "users_select_own" ON public.users
    FOR SELECT USING (
        id = auth.uid() OR 
        org_id IN (SELECT org_id FROM public.users WHERE id = auth.uid())
    );

-- Policy UPDATE : Un user modifie son propre profil
CREATE POLICY "users_update_own" ON public.users
    FOR UPDATE USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- 5. Commentaire explicatif
COMMENT ON TABLE public.user_org_membership IS 'DEPRECATED - Utiliser users.role directement. Table conservée temporairement pour référence.';
COMMENT ON TABLE public.users IS 'Profils utilisateurs avec org_id et role directement';

-- 6. S'assurer que tous les utilisateurs ont un role défini
-- Mettre à jour les NULL en 'user'
UPDATE public.users SET role = 'user' WHERE role IS NULL;

SELECT 'Nettoyage terminé. user_org_membership est maintenant DEPRECATED.' AS status;
