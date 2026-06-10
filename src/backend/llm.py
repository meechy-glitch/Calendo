from __future__ import annotations
import json
import os
import types
from openai import AsyncOpenAI
from src.backend.config import GROQ_API_KEY, LLM_MODEL

_groq_client: AsyncOpenAI | None = None


def _parse_failed_generation(text: str) -> list:
    """Try to recover tool calls from a Groq tool_use_failed payload.

    Groq emits failed_generation as a JSON string like:
      [{"name": "update_post", "parameters": {...}}]
    Returns a list of SimpleNamespace objects with .id, .function.name,
    .function.arguments — same interface _run_chat_loop expects.
    """
    stripped = text.strip()
    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return []
    items = data if isinstance(data, list) else [data]
    calls = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        name = item.get("name") or (item.get("function") or {}).get("name")
        args = (
            item.get("parameters")
            or item.get("arguments")
            or (item.get("function") or {}).get("arguments")
            or {}
        )
        if not name:
            continue
        tc = types.SimpleNamespace(
            id=f"recovered-{i}",
            function=types.SimpleNamespace(
                name=name,
                arguments=json.dumps(args) if not isinstance(args, str) else args,
            ),
        )
        calls.append(tc)
    return calls


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
            raw = body.get("failed_generation", "")
            recovered = _parse_failed_generation(raw)
            if recovered:
                return {"text": None, "tool_calls": recovered, "finish_reason": "tool_calls"}
            # Failed generation not parseable — return nothing rather than leaking JSON
            return {"text": "", "tool_calls": [], "finish_reason": "stop"}
        raise
    choice = response.choices[0]
    msg = choice.message
    return {
        "text": msg.content,
        "tool_calls": msg.tool_calls or [],
        "finish_reason": choice.finish_reason,
    }
