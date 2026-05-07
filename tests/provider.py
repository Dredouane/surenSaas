"""YAML scenario loader for the E2E test harness.

Loads multi-step test scenarios from YAML files and validates them
against the ``Scenario`` model.
"""

from pathlib import Path

import yaml

from tests.models import Scenario


def load_scenario(yaml_path: str) -> Scenario:
    """Load a YAML scenario file and return a validated ``Scenario`` model.

    Args:
        yaml_path: Path to the YAML file (absolute or relative).

    Returns:
        A validated ``Scenario`` instance.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        ValidationError: If the YAML content does not match the ``Scenario`` schema.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {yaml_path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Scenario(**raw)
