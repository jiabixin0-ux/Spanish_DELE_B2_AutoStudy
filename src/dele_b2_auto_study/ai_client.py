"""AI client for generating daily Spanish study lessons."""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI


class AIClientError(Exception):
    """Raised when the AI lesson generation client fails."""


def get_deepseek_client() -> "OpenAI":
    """Create a DeepSeek client using the OpenAI-compatible API."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise AIClientError("DEEPSEEK_API_KEY environment variable is required.")

    try:
        from openai import OpenAI

        return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    except ImportError as exc:
        raise AIClientError(
            "The openai package is required. Install dependencies from requirements.txt."
        ) from exc
    except Exception as exc:
        raise AIClientError(f"Failed to create DeepSeek client: {exc}") from exc


def generate_ai_lesson(prompt: str) -> str:
    """Generate a Markdown Spanish lesson from a prompt."""
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    client = get_deepseek_client()

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            max_tokens=6000,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一名西班牙语教学老师，擅长为中文母语者设计 "
                        "B1 巩固与 B2 过渡课程。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
    except AIClientError:
        raise
    except Exception as exc:
        raise AIClientError(f"Failed to generate AI lesson: {exc}") from exc

    if not content or not content.strip():
        raise AIClientError("DeepSeek returned an empty lesson response.")

    return content.strip()
