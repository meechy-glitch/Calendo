import json
import os
os.environ.setdefault("GROQ_API_KEY", "test-key-for-tests")

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.backend import models
from tests.conftest import TestingSessionLocal


def _make_tool_call(call_id: str, name: str, args: dict) -> MagicMock:
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(args)
    return tc


def test_chat_tool_choice_is_always_auto(client, auth_headers):
    """tool_choice must be 'auto' on every turn — the required-first-turn forcing was removed."""
    captured_kwargs: list[dict] = []

    async def capture(messages, **kwargs):
        captured_kwargs.append(kwargs)
        return {"text": "Sure, what topic should these posts cover?", "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.llm.complete", new=capture):
        r = client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "plan 3 Instagram posts for next week"}]},
            headers=auth_headers,
        )

    assert r.status_code == 200
    assert len(captured_kwargs) >= 1
    for kwargs in captured_kwargs:
        assert kwargs.get("tool_choice") == "auto", (
            f"Expected tool_choice='auto', got {kwargs.get('tool_choice')!r}"
        )


def test_chat_no_post_created_when_llm_asks_questions(client, auth_headers):
    """When LLM responds with a clarifying question (no tool call), no changes are recorded."""
    text_result = {
        "text": "What topic should these posts be about?",
        "tool_calls": [],
        "finish_reason": "stop",
    }

    with patch("src.backend.llm.complete", new=AsyncMock(return_value=text_result)):
        r = client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "plan 3 Instagram posts"}]},
            headers=auth_headers,
        )

    assert r.status_code == 200
    data = r.json()
    assert data["changes"] == [], "No posts should be created when LLM asks a clarifying question"
    assert "?" in data["assistant_reply"], "LLM should have asked a question"


def test_bulk_reschedule_actually_moves_posts(client, auth_headers):
    """bulk_reschedule_posts tool execution persists new dates to the DB."""
    r1 = client.post("/posts", json={
        "title": "June Post 1", "caption": "Caption one",
        "platform": "instagram", "scheduled_date": "2026-06-05",
    }, headers=auth_headers)
    r2 = client.post("/posts", json={
        "title": "June Post 2", "caption": "Caption two",
        "platform": "instagram", "scheduled_date": "2026-06-20",
    }, headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    post1_id = r1.json()["id"]
    post2_id = r2.json()["id"]

    call_count = 0

    async def fake_llm(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            tc = _make_tool_call("tc-list", "list_posts", {"month": "2026-06"})
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        if call_count == 2:
            tc = _make_tool_call("tc-bulk", "bulk_reschedule_posts", {
                "reschedules": [
                    {"post_id": post1_id, "scheduled_date": "2026-07-05"},
                    {"post_id": post2_id, "scheduled_date": "2026-07-20"},
                ]
            })
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        return {
            "text": "Done — I've moved your 2 June posts to July.",
            "tool_calls": [],
            "finish_reason": "stop",
        }

    with patch("src.backend.llm.complete", new=fake_llm):
        r = client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "move my June posts to July"}]},
            headers=auth_headers,
        )

    assert r.status_code == 200
    data = r.json()
    assert len(data["changes"]) == 2, "Two posts should have been rescheduled"
    assert "July" in data["assistant_reply"]

    db = TestingSessionLocal()
    p1 = db.query(models.Post).filter(models.Post.id == post1_id).first()
    p2 = db.query(models.Post).filter(models.Post.id == post2_id).first()
    db.close()
    assert str(p1.scheduled_date) == "2026-07-05", f"Post 1 date: {p1.scheduled_date}"
    assert str(p2.scheduled_date) == "2026-07-20", f"Post 2 date: {p2.scheduled_date}"


def test_system_prompt_contains_clarify_and_no_placeholder_rules(client, auth_headers):
    """System prompt must instruct the model to ask questions and forbid placeholder titles."""
    captured: list[list[dict]] = []

    async def capture_messages(messages, **kwargs):
        captured.append(messages)
        return {"text": "What topic?", "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.llm.complete", new=capture_messages):
        client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "plan some posts"}]},
            headers=auth_headers,
        )

    assert captured, "llm.complete should have been called"
    system_content = captured[0][0]["content"]
    assert "Post 1" in system_content, "System prompt must mention 'Post 1' in the no-placeholder rule"
    assert "NEVER" in system_content, "System prompt must use NEVER for the no-placeholder rule"
    assert "clarif" in system_content.lower() or "question" in system_content.lower(), (
        "System prompt must instruct model to ask clarifying questions"
    )
    assert "ANTI-HALLUCINATION" in system_content, "Anti-hallucination rule must still be present"
