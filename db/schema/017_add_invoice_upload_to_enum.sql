-- 017_add_invoice_upload_to_enum.sql
-- Ajoute 'invoice_upload' à l'enum telegram_interaction_type

-- Note: PostgreSQL ne permet pas d'ajouter une valeur à un enum directement
-- sans recréer le type. Mais on peut utiliser ALTER TYPE ... ADD VALUE

DO $$
BEGIN
    -- Vérifier si la valeur existe déjà
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'invoice_upload' 
        AND enumtypid = 'telegram_interaction_type'::regtype
    ) THEN
        -- Ajouter la valeur à l'enum
        ALTER TYPE telegram_interaction_type ADD VALUE 'invoice_upload';
        
        RAISE NOTICE 'Valeur invoice_upload ajoutée à telegram_interaction_type';
    ELSE
        RAISE NOTICE 'Valeur invoice_upload existe déjà';
    END IF;
END $$;

-- Alternative: Si la valeur ne peut pas être ajoutée (conflit),
-- on peut créer un nouveau type et migrer les données
-- Mais ALTER TYPE ADD VALUE est plus simple si la DB n'a pas encore de données

COMMENT ON TYPE telegram_interaction_type IS 
'Types d''interactions Telegram:
- message_received: Message reçu
- command_received: Commande reçue (/start, etc.)
- button_clicked: Bouton cliqué
- file_received: Fichier reçu (photo, PDF)
- invoice_upload: Upload de facture (spécifique)
- workflow_started: Workflow démarré
- workflow_step: Étape de workflow
- workflow_completed: Workflow terminé
- workflow_failed: Workflow échoué
- notification_sent: Notification envoyée
- error: Erreur';
