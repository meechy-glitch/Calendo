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
        kwargs["tool_choice"] = "auto"
    response = await client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    msg = choice.message
    return {
        "text": msg.content,
        "tool_calls": msg.tool_calls or [],
        "finish_reason": choice.finish_reason,
    }
