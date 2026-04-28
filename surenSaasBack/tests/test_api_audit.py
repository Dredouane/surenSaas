#!/usr/bin/env python3
"""
Tests unitaires pour les endpoints API Audit (monitoring admin).
Mock complet de Supabase. Validation directe des fonctions du routeur.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def make_result(data, count=None):
    """Crée un MagicMock avec .data et .count."""
    r = MagicMock()
    r.data = data
    r.count = count
    return r


class ChainMock:
    """Mock chaînable : toute méthode retourne self, execute() retourne un mock avec .data et .count."""
    def __init__(self, data=None, count=None):
        self._data = data
        self._count = count
        self.execute = MagicMock()
        self.execute.return_value = make_result(data, count)

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        if name in ('execute', '_data', '_count', 'side_effect'):
            raise AttributeError(name)
        return self


@pytest.fixture(autouse=True)
def mock_supabase_df():
    with patch("app.api.audit.get_supabase") as m:
        s = MagicMock()
        m.return_value = s
        yield s


class TestActivity:

    @pytest.mark.anyio
    async def test_list_paginated(self, mock_supabase_df):
        from app.api.audit import list_activity
        t = MagicMock()
        mock_supabase_df.table.return_value = t
        rows = [{"id": str(uuid4()), "action": "create", "table_name": "chantiers",
                 "org_id": "o1", "correlation_id": str(uuid4()),
                 "created_at": "2026-01-15T10:00:00+00:00",
                 "user_name": "Admin", "source_system": "api"}]
        t.select.return_value = ChainMock(rows, 1)

        r = await list_activity(None, {"user_id": "u1", "org_id": "o1", "role": "admin"},
                                page=1, page_size=25)

        assert r["total"] == 1
        assert len(r["items"]) == 1
        assert r["items"][0]["action"] == "create"

    @pytest.mark.anyio
    async def test_list_empty(self, mock_supabase_df):
        from app.api.audit import list_activity
        t = MagicMock()
        mock_supabase_df.table.return_value = t
        t.select.return_value = ChainMock([], 0)

        r = await list_activity(None, {"user_id": "u1", "org_id": "o1", "role": "admin"},
                                page=1, page_size=25)

        assert r["total"] == 0

    @pytest.mark.anyio
    async def test_list_pagination(self, mock_supabase_df):
        from app.api.audit import list_activity
        t = MagicMock()
        mock_supabase_df.table.return_value = t
        t.select.return_value = ChainMock(
            [{"id": str(uuid4()), "action": "update", "org_id": "o1",
              "correlation_id": str(uuid4()), "created_at": "2026-01-15T10:00:00+00:00"}], 25)

        r = await list_activity(None, {"user_id": "u1", "org_id": "o1", "role": "admin"},
                                page=2, page_size=10)

        assert r["page"] == 2
        assert r["page_size"] == 10
        assert r["total"] == 25

    @pytest.mark.anyio
    async def test_get_detail(self, mock_supabase_df):
        from app.api.audit import get_activity_detail
        aid = str(uuid4())
        t = MagicMock()
        mock_supabase_df.table.return_value = t
        s = MagicMock()
        e = MagicMock()
        sg = MagicMock()
        sg.execute.return_value = make_result({"id": aid, "action": "update"})
        e.single.return_value = sg
        e.eq.return_value = e
        s.eq.return_value = e
        t.select.return_value = s

        r = await get_activity_detail(aid, {"user_id": "u1", "org_id": "o1", "role": "admin"})

        assert r["id"] == aid


class TestAgents:

    @pytest.mark.anyio
    async def test_list_paginated(self, mock_supabase_df):
        from app.api.audit import list_agents
        t = MagicMock()
        mock_supabase_df.table.return_value = t
        rows = [{"id": str(uuid4()), "agent_type": "gemini_extraction",
                 "model": "gemini-2.5-flash", "status": "completed",
                 "org_id": "o1", "correlation_id": str(uuid4()),
                 "created_at": "2026-01-15T10:00:00+00:00"}]
        t.select.return_value = ChainMock(rows, 1)

        r = await list_agents({"user_id": "u1", "org_id": "o1", "role": "admin"},
                              page=1, page_size=25)

        assert r["total"] == 1
        assert r["items"][0]["agent_type"] == "gemini_extraction"

    @pytest.mark.anyio
    async def test_list_with_filters(self, mock_supabase_df):
        from app.api.audit import list_agents
        t = MagicMock()
        mock_supabase_df.table.return_value = t
        t.select.return_value = ChainMock([], 0)

        r = await list_agents({"user_id": "u1", "org_id": "o1", "role": "admin"},
                              page=1, page_size=25,
                              agent_type="gemini_chat", status="failed")

        assert r["total"] == 0

    @pytest.mark.anyio
    async def test_get_detail(self, mock_supabase_df):
        from app.api.audit import get_agent_detail
        aid = str(uuid4())
        t = MagicMock()
        mock_supabase_df.table.return_value = t
        s = MagicMock()
        e = MagicMock()
        sg = MagicMock()
        sg.execute.return_value = make_result({"id": aid, "agent_type": "custom"})
        e.single.return_value = sg
        e.eq.return_value = e
        s.eq.return_value = e
        t.select.return_value = s

        r = await get_agent_detail(aid, {"user_id": "u1", "org_id": "o1", "role": "admin"})

        assert r["id"] == aid


class TestCorrelations:

    @pytest.mark.anyio
    async def test_list(self, mock_supabase_df):
        from app.api.audit import list_correlations
        t = MagicMock()
        mock_supabase_df.table.return_value = t

        corr_id = str(uuid4())
        ch = ChainMock([{"correlation_id": corr_id}], 1)
        t.select.return_value = ch

        # Side effect pour les deux execute : le premier (logs_activity groupé),
        # le second (logs_agents count)
        ch.execute.side_effect = [
            make_result([{"correlation_id": corr_id}], 1),
            make_result([{"id": str(uuid4())}], 2),
        ]

        r = await list_correlations({"user_id": "u1", "org_id": "o1", "role": "admin"},
                                    page=1, page_size=25)

        assert r["total"] == 1

    @pytest.mark.anyio
    async def test_detail(self, mock_supabase_df):
        from app.api.audit import get_correlation_detail
        corr_id = str(uuid4())

        def mock_table_factory(name):
            m = MagicMock()
            s = MagicMock()
            e = MagicMock()
            o = MagicMock()
            o.execute.return_value = make_result([{"id": str(uuid4()), "action": "create",
                                                   "correlation_id": corr_id,
                                                   "org_id": "o1",
                                                   "created_at": "2026-01-15T10:00:00+00:00"}])
            e.order.return_value = o
            e.eq.return_value = e
            s.eq.return_value = e
            m.select.return_value = s
            return m

        mock_supabase_df.table.side_effect = [mock_table_factory("logs_activity"),
                                              mock_table_factory("logs_agents")]

        r = await get_correlation_detail(corr_id, {"user_id": "u1", "org_id": "o1", "role": "admin"})

        assert r["correlation_id"] == corr_id
        assert len(r["activites"]) == 1
        assert len(r["agents"]) == 1


class TestStats:

    @pytest.mark.anyio
    async def test_get(self, mock_supabase_df):
        from app.api.audit import get_stats
        t = MagicMock()
        mock_supabase_df.table.return_value = t
        s = MagicMock()
        eq = MagicMock()
        eq.execute.return_value = make_result([], 42)
        eq.eq.return_value = eq
        s.eq.return_value = eq
        s.order = MagicMock(return_value=eq)
        t.select.return_value = s

        rpc = MagicMock()
        rpc.execute.return_value = make_result([{"total_cost": 0.05}])
        mock_supabase_df.rpc.return_value = rpc

        r = await get_stats({"user_id": "u1", "org_id": "o1", "role": "admin"})

        assert r.total_activites == 42
        assert r.total_agents == 42


class TestSecurity:

    @pytest.mark.anyio
    async def test_list_activity_with_non_admin(self):
        from app.api.audit import list_activity
        t = MagicMock()
        from app.api.audit import get_supabase
        s = get_supabase()
        s.table.return_value = t
        t.select.return_value = ChainMock([], 0)

        r = await list_activity(None, {"user_id": "u1", "org_id": "o1", "role": "user"},
                                page=1, page_size=25)

        assert r["total"] == 0  # Un non-admin voit ses propres logs (org_id filtre)

