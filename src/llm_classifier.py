"""LLM-powered message classification for InboxIntel."""

import json
import os
from pathlib import Path
from typing import Literal

import yaml
from openai import OpenAI

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

MessageCategory = Literal[
    "EARLY_CHECKIN",
    "LATE_CHECKOUT",
    "SPECIAL_REQUEST",
    "MAINTENANCE_ISSUE",
    "GENERAL_QUESTION",
]


class ClassificationResult:
    def __init__(self, category: MessageCategory, confidence: float, summary: str):
        self.category = category
        self.confidence = confidence
        self.summary = summary

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "confidence": self.confidence,
            "summary": self.summary,
        }


def _load_prompt_template() -> str:
    prompts_file = Path(__file__).parent.parent / "config" / "prompts.yml"
    with open(prompts_file) as f:
        prompts_data = yaml.safe_load(f)
    return prompts_data["classification"]["system_prompt"]


_CLASSIFICATION_PROMPT: str | None = None


def _get_classification_prompt() -> str:
    global _CLASSIFICATION_PROMPT
    if _CLASSIFICATION_PROMPT is None:
        _CLASSIFICATION_PROMPT = _load_prompt_template()
    return _CLASSIFICATION_PROMPT


def classify_message(text: str) -> ClassificationResult:
    provider_config = config.LLM_PROVIDER.split(":")
    provider = provider_config[0]
    model = provider_config[1] if len(provider_config) > 1 else None

    if provider == "openai":
        return _classify_with_openai(text, model or "gpt-4-turbo")
    elif provider == "ollama":
        return _classify_with_ollama(text, model or "llama3")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _classify_with_openai(text: str, model: str) -> ClassificationResult:
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    prompt = _get_classification_prompt().format(message_text=text)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        result = json.loads(content)

        return ClassificationResult(
            category=result["category"],
            confidence=float(result["confidence"]),
            summary=result["summary"],
        )

    except Exception as e:
        logger.error(f"OpenAI classification failed: {e}")
        raise


def _classify_with_ollama(text: str, model: str) -> ClassificationResult:
    import requests

    ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    prompt = _get_classification_prompt().format(message_text=text)

    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=30,
        )
        response.raise_for_status()

        result_text = response.json()["response"]
        result = json.loads(result_text)

        return ClassificationResult(
            category=result["category"],
            confidence=float(result["confidence"]),
            summary=result["summary"],
        )

    except Exception as e:
        logger.error(f"Ollama classification failed: {e}")
        raise
