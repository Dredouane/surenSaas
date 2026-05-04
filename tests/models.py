"""Pydantic models for Telegram E2E blackbox test scenarios."""

from pydantic import BaseModel, Field
from typing import Literal


class ScenarioMedia(BaseModel):
    """Represents a piece of media sent by the test user.

    Attributes:
        type: Media type — text, voice, photo, or document.
        content: Text content for 'text' type, file path for others.
    """
    type: Literal["text", "voice", "photo", "document"]
    content: str


class ScenarioInput(BaseModel):
    """The Telegram update payload that triggers a bot interaction.

    Attributes:
        chat_id: Telegram chat identifier for the test user.
        from_user: Telegram user dict (id, first_name, is_bot, …).
        media: The media (text / voice / photo / document) being sent.
    """
    chat_id: int = 999999
    from_user: dict = Field(default_factory=lambda: {
        "id": 999999,
        "first_name": "Test",
        "is_bot": False,
    })
    media: ScenarioMedia


class ScenarioJudge(BaseModel):
    """Configuration for the LLM-based judge that evaluates the bot reply.

    Attributes:
        model: Gemini model identifier (default: gemini-2.0-flash).
        prompt: Scenario description the judge uses to evaluate correctness.
        expected_verdict: Whether the bot is expected to pass or fail.
    """
    model: str = "gemini-2.0-flash"
    prompt: str
    expected_verdict: Literal["pass", "fail"] = "pass"


class Scenario(BaseModel):
    """A complete end-to-end test scenario.

    Attributes:
        test_case: Unique identifier for the test case.
        description: Human-readable description of what is being tested.
        tags: List of tags for test categorization / filtering.
        input: The Telegram input that triggers the scenario.
        judge: Judge configuration to evaluate the bot's response.
    """
    test_case: str
    description: str = ""
    tags: list[str] = []
    input: ScenarioInput
    judge: ScenarioJudge


class JudgeVerdict(BaseModel):
    """Result of evaluating a bot reply against a scenario.

    Attributes:
        score: 1 = pass, 0 = fail.
        reason: Explanation from the judge LLM (or mock).
    """
    score: Literal[0, 1]
    reason: str
