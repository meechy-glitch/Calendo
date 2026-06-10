from __future__ import annotations
import os
from openai import AsyncOpenAI
from src.backend.config import GROQ_API_KEY, LLM_MODEL

_groq_client: AsyncOpenAI | None = None


def _get_groq_client() -> AsyncOpenAI:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
    return _groq_client


async def complete(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    tool_choice: str = "auto",
) -> dict:
    client = _get_groq_client()
    m = model or LLM_MODEL
    kwargs: dict = {
        "model": m,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice
    try:
        response = await client.chat.completions.create(**kwargs)
    except Exception as e:
        # Groq returns 400 tool_use_failed when the model outputs text instead of a tool call.
        # The model's actual generation is recoverable from the error body.
        body = getattr(e, "body", None) or {}
        if isinstance(body, dict) and body.get("code") == "tool_use_failed":
            text = body.get("failed_generation", "")
            return {"text": text, "tool_calls": [], "finish_reason": "stop"}
        raise
    choice = response.choices[0]
    msg = choice.message
    return {
        "text": msg.content,
        "tool_calls": msg.tool_calls or [],
        "finish_reason": choice.finish_reason,
    }
