-- ============================================================================
-- Migration 022 : Hermès Email V2 - Cycle de vie + email_ai_analysis
-- ============================================================================

-- 1. Type ENUM pour le cycle de vie
DO $$ BEGIN
    CREATE TYPE email_processing_status AS ENUM (
        'NEW',
        'READY_FOR_AI',
        'PENDING_VALIDATION',
        'PROCESSED',
        'REJECTED',
        'FAILED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Statut dans email_threads
ALTER TABLE email_threads
  ADD COLUMN IF NOT EXISTS status email_processing_status DEFAULT 'NEW',
  ADD COLUMN IF NOT EXISTS detected_chantier_id UUID REFERENCES chantiers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_email_threads_status ON email_threads(status);
CREATE INDEX IF NOT EXISTS idx_email_threads_status_chantier ON email_threads(status, detected_chantier_id);

-- 3. Table email_ai_analysis (propositions Hermès)
CREATE TABLE IF NOT EXISTS email_ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_thread_id UUID REFERENCES email_threads(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    detected_urgency VARCHAR(20) CHECK (detected_urgency IN ('LOW', 'MEDIUM', 'HIGH')),
    proposed_actions JSONB DEFAULT '[]'::jsonb,
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    validated_at TIMESTAMP WITH TIME ZONE,
    validated_by UUID REFERENCES auth.users(id),
    rejected_reason TEXT,
    raw_llm_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_ai_analysis_thread ON email_ai_analysis(email_thread_id);
CREATE INDEX IF NOT EXISTS idx_email_ai_analysis_analyzed ON email_ai_analysis(analyzed_at);

-- 4. Migration des statuts existants (email.processing_status → email_threads.status)
-- Les emails en 'vectorized' deviennent 'READY_FOR_AI' si le chantier est trouvé
UPDATE email_threads et
SET status = 'READY_FOR_AI',
    detected_chantier_id = et.chantier_id
FROM emails e
WHERE e.gmail_thread_id = et.gmail_thread_id
  AND e.processing_status = 'vectorized'
  AND et.chantier_id IS NOT NULL
  AND et.status = 'NEW';
