"""Pydantic models for multi-step E2E test scenarios."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Backward-compat types used by judge.py and engine.py ──────────────


class JudgeVerdict(BaseModel):
    """Verdict returned by the LLM judge (judge.py).

    Attributes:
        score: 1 = pass, 0 = fail.
        reason: Explanation from the judge LLM.
    """
    score: int = Field(ge=0, le=1)
    reason: str = ""


class ScenarioJudge(BaseModel):
    """Judge configuration for old-style scenarios (engine.py compat)."""
    prompt: str = ""
    expected_verdict: str = "pass"


class Step(BaseModel):
    """A single interaction step in a multi-turn E2E scenario.

    Attributes:
        type: 'text' for a text message, 'callback' for clicking an inline button.
        content: Text content to send, or button label text to click.
        judge_prompt: Scenario description the judge uses to evaluate correctness.
        expected_verdict: Whether the bot is expected to pass or fail this step.
    """
    type: Literal["text", "callback", "document", "photo"]
    mode: Literal["sync", "async"] = "sync"
    content: str
    caption: str = ""
    judge_prompt: str = ""
    expected_verdict: Literal["pass", "fail"] = "pass"


class Scenario(BaseModel):
    """A complete multi-step end-to-end test scenario.

    Attributes:
        test_case: Unique identifier for the test case.
        description: Human-readable description of what is being tested.
        tags: List of tags for test categorization / filtering.
        steps: Ordered list of interaction steps (text or callback).
    """
    test_case: str
    description: str = ""
    tags: list[str] = []
    steps: list[Step]


class Verdict(BaseModel):
    """Result of evaluating a bot reply against a step's judge prompt.

    Attributes:
        score: 1 = pass, 0 = fail.
        reason: Explanation from the judge LLM (or mock).
        step_index: Index of the step this verdict corresponds to.
    """
    score: int = Field(ge=0, le=1)
    reason: str = ""
    step_index: int = 0

    @property
    def passed(self) -> bool:
        """Return True if the verdict score is 1 (pass)."""
        return self.score == 1
