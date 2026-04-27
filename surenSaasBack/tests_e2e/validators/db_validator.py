from datetime import datetime, timedelta
from typing import Optional


class DBValidator:
    def __init__(self, supabase, org_id: str):
        self.supabase = supabase
        self.org_id = org_id

    def assert_operation_created(
        self,
        source: str,
        since: Optional[datetime] = None,
        statut: str = "en_attente",
    ) -> dict:
        if since is None:
            since = datetime.utcnow() - timedelta(seconds=30)

        result = (
            self.supabase.table("chantier_operations_htl")
            .select("*")
            .eq("org_id", self.org_id)
            .eq("source", source)
            .eq("statut", statut)
            .gte("created_at", since.isoformat())
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        assert result.data, (
            f"No chantier_operations_htl row found with "
            f"org_id={self.org_id}, source='{source}', statut='{statut}' since {since}"
        )
        return result.data[0]

    def assert_document_created(
        self,
        candidature_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> dict:
        if since is None:
            since = datetime.utcnow() - timedelta(seconds=30)

        query = (
            self.supabase.table("ao_documents")
            .select("*")
            .eq("org_id", self.org_id)
            .gte("created_at", since.isoformat())
            .order("created_at", desc=True)
        )
        if candidature_id:
            query = query.eq("candidature_id", candidature_id)

        result = query.limit(1).execute()

        assert result.data, (
            f"No ao_document row found with "
            f"org_id={self.org_id} since {since}"
        )
        return result.data[0]

    def assert_depense_created(
        self,
        chantier_id: str,
        since: Optional[datetime] = None,
    ) -> dict:
        if since is None:
            since = datetime.utcnow() - timedelta(seconds=30)

        result = (
            self.supabase.table("chantier_depenses")
            .select("*")
            .eq("org_id", self.org_id)
            .eq("chantier_id", chantier_id)
            .gte("created_at", since.isoformat())
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        assert result.data, (
            f"No chantier_depenses row found for "
            f"chantier_id={chantier_id}, org_id={self.org_id} since {since}"
        )
        return result.data[0]

    def assert_tache_created(
        self,
        chantier_id: str,
        since: Optional[datetime] = None,
        statut: str = "en_attente",
    ) -> dict:
        if since is None:
            since = datetime.utcnow() - timedelta(seconds=30)

        result = (
            self.supabase.table("chantier_taches")
            .select("*")
            .eq("org_id", self.org_id)
            .eq("chantier_id", chantier_id)
            .eq("statut", statut)
            .gte("created_at", since.isoformat())
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        assert result.data, (
            f"No chantier_taches row found for "
            f"chantier_id={chantier_id}, org_id={self.org_id}, statut='{statut}' since {since}"
        )
        return result.data[0]
