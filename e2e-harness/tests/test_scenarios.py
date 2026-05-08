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
import time
from pathlib import Path

import pytest

from engine import SessionRunner
from provider import load_scenario

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
BACKEND_HEALTH_URL = os.getenv("BACKEND_HEALTH_URL", "http://localhost:8080/health")


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


def _wait_for_backend(timeout: float = 60.0) -> bool:
    """Poll /health until the backend responds 200, or return False."""
    import httpx

    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(BACKEND_HEALTH_URL, timeout=5.0)
            if resp.status_code == 200:
                logger.info("Backend ready after %.1fs", timeout - (deadline - time.monotonic()))
                return True
        except Exception as exc:
            last_error = str(exc)
        time.sleep(3)
    logger.warning("Backend not reachable within %.0fs: %s", timeout, last_error)
    return False


# ═════════════════════════════════════════════════════════════════════════════
# The actual test
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
def test_scenario(scenario, tg_mock_client) -> None:
    """Run a multi-step scenario end-to-end via SessionRunner.

    Steps:
    1. Skip if backend is unreachable.
    2. Create a SessionRunner and run all steps.
    3. Assert each step's verdict matches its expected_verdict.
    """
    # ── Wait for backend ─────────────────────────────────────────────
    if not _wait_for_backend(timeout=60.0):
        pytest.skip("Backend did not become reachable within 60s — skipping E2E test")

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
