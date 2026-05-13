"""
tradenexus/config.py

Loads environment configuration — direct Python port of the TS getAiClient()
and model constant logic in geminiService.ts.
"""

import os
from dotenv import load_dotenv

# Load .env from the project root (one level up from this package)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Copy .env.example to .env and fill in your key."
        )
    return key


DEFAULT_MODEL: str = os.getenv("GEMINI_DEFAULT_MODEL", "gemma-4-31b-it")
GROUNDING_MODEL: str = os.getenv("GEMINI_GROUNDING_MODEL", "gemma-4-31b-it")
THINKING_BUDGET: int = int(os.getenv("GEMINI_THINKING_BUDGET", "0"))


def build_thinking_config(model: str) -> dict:
    """
    Port of buildThinkingConfig() from geminiService.ts.

    Different model families use different thinking config formats:
      - Gemma 4 / Gemini 3 : thinkingLevel  ("high" | "medium" | "low" | "minimal")
      - Gemini 2.5          : thinkingBudget (0 = off, -1 = dynamic, N = token budget)
    """
    if THINKING_BUDGET <= 0:
        return {}
    if model.startswith("gemma-4"):
        return {"thinking_config": {"thinking_level": "high"}}
    if model.startswith("gemini-3"):
        return {"thinking_config": {"thinking_level": "low"}}
    return {"thinking_config": {"thinking_budget": THINKING_BUDGET}}
