"""
Parametrized pytest that reads all YAML scenario files from ``tests/scenarios/``
and runs each as an end-to-end blackbox test using the multi-step SessionRunner.

For each scenario:
1. Parse the YAML into a ``Scenario`` model via ``load_scenario()``.
2. Execute all steps via ``SessionRunner.run_scenario()``.
3. Assert that every step's verdict matches its ``expected_verdict``.

Test IDs in pytest output are the YAML filenames (e.g. ``scenario_depense``).
"""

import logging
import os
from pathlib import Path

import pytest

from tests.engine import SessionRunner
from tests.provider import load_scenario

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
BACKEND_HEALTH_URL = os.getenv("BACKEND_HEALTH_URL", "http://localhost:8080/health")
HEALTH_CHECK_TIMEOUT = 5.0


# ═════════════════════════════════════════════════════════════════════════════
# Dynamic parametrization
# ═════════════════════════════════════════════════════════════════════════════


def pytest_generate_tests(metafunc):
    """Dynamic parametrization: one test ID per scenario YAML file."""
    if "scenario" in metafunc.fixturenames:
        scenario_paths = sorted(SCENARIOS_DIR.glob("*.yaml"))
        scenarios = [load_scenario(str(p)) for p in scenario_paths]
        ids = [p.stem for p in scenario_paths]
        metafunc.parametrize("scenario", scenarios, ids=ids)


# ═════════════════════════════════════════════════════════════════════════════
# Health check helper
# ═════════════════════════════════════════════════════════════════════════════


def _backend_is_reachable() -> bool:
    """Return True if the backend health endpoint responds 200."""
    try:
        import httpx

        resp = httpx.get(
            BACKEND_HEALTH_URL,
            timeout=HEALTH_CHECK_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception as exc:
        logger.info("Backend health check failed: %s", exc)
        return False


# ═════════════════════════════════════════════════════════════════════════════
# The actual test
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
def test_scenario(scenario, tg_mock_client, judge_client) -> None:
    """Run a multi-step scenario end-to-end via SessionRunner.

    Steps:
    1. Skip if backend is unreachable.
    2. Create a SessionRunner and run all steps.
    3. Assert each step's verdict matches its expected_verdict.
    """
    # ── Skip check ────────────────────────────────────────────────────
    if not _backend_is_reachable():
        pytest.skip("Backend is not reachable — skipping E2E test")

    logger.info(
        "🚀 Running scenario [%s]: %s",
        scenario.test_case,
        scenario.description,
    )

    # ── Run all steps via SessionRunner ───────────────────────────────
    runner = SessionRunner(mock_client=tg_mock_client)
    verdicts = runner.run_scenario(scenario)

    # ── Assert each verdict ───────────────────────────────────────────
    for v in verdicts:
        step = scenario.steps[v.step_index]
        expected_pass = step.expected_verdict == "pass"

        if expected_pass:
            assert v.passed, (
                f"Step {v.step_index} [{step.type}]: expected PASS but got FAIL. "
                f"Reason: {v.reason}"
            )
        else:
            assert not v.passed, (
                f"Step {v.step_index} [{step.type}]: expected FAIL but got PASS. "
                f"Reason: {v.reason}"
            )

    logger.info("✅ Scenario [%s] — all %d step(s) passed expected verdicts",
                 scenario.test_case, len(verdicts))
