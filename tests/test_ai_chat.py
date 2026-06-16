import json
import os
import re
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


def test_delete_posts_requires_confirmation(client, auth_headers):
    """First delete turn must show which posts will go and ask for confirmation — nothing is deleted."""
    r = client.post("/posts", json={
        "title": "My July Post", "caption": "Summer content",
        "platform": "instagram", "scheduled_date": "2026-07-15",
    }, headers=auth_headers)
    assert r.status_code == 201
    post_id = r.json()["id"]

    call_count = 0

    async def fake_llm(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            tc = _make_tool_call("tc-list", "list_posts", {"month": "2026-07"})
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        if call_count == 2:
            # Call delete_posts WITHOUT confirm — backend should return a preview
            tc = _make_tool_call("tc-del", "delete_posts", {"post_ids": [post_id]})
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        return {
            "text": (
                "I found 1 post in July: 'My July Post' (2026-07-15). "
                "Shall I delete it? Reply yes to confirm."
            ),
            "tool_calls": [],
            "finish_reason": "stop",
        }

    with patch("src.backend.llm.complete", new=fake_llm):
        r = client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "delete my July posts"}]},
            headers=auth_headers,
        )

    assert r.status_code == 200
    data = r.json()

    assert data["changes"] == [], f"No posts should be deleted without confirmation, got {data['changes']}"
    reply = data["assistant_reply"]
    assert "?" in reply or "confirm" in reply.lower(), (
        f"Assistant should ask for confirmation, got: {reply!r}"
    )

    db = TestingSessionLocal()
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    db.close()
    assert post is not None, "Post must NOT be deleted until the user confirms"


def test_delete_posts_confirmed_removes_from_db(client, auth_headers):
    """When delete_posts is called with confirm=true, rows are hard-deleted and changes are reported."""
    r1 = client.post("/posts", json={
        "title": "July Post A", "caption": "Caption A",
        "platform": "instagram", "scheduled_date": "2026-07-10",
    }, headers=auth_headers)
    r2 = client.post("/posts", json={
        "title": "July Post B", "caption": "Caption B",
        "platform": "x", "scheduled_date": "2026-07-20",
    }, headers=auth_headers)
    assert r1.status_code == r2.status_code == 201
    id_a, id_b = r1.json()["id"], r2.json()["id"]

    call_count = 0

    async def fake_llm(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            tc = _make_tool_call("tc-del", "delete_posts", {
                "post_ids": [id_a, id_b],
                "confirm": True,
            })
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        return {
            "text": "Done — I've deleted 2 posts from July.",
            "tool_calls": [],
            "finish_reason": "stop",
        }

    with patch("src.backend.llm.complete", new=fake_llm):
        r = client.post(
            "/ai/chat",
            json={"messages": [
                {"role": "user", "content": "delete my July posts"},
                {"role": "assistant", "content": "Found 2 July posts. Shall I delete them?"},
                {"role": "user", "content": "yes, go ahead"},
            ]},
            headers=auth_headers,
        )

    assert r.status_code == 200
    data = r.json()

    deleted_ids = {c["id"] for c in data["changes"] if c.get("type") == "deleted"}
    assert id_a in deleted_ids, f"Post A should be in deleted changes; got {data['changes']}"
    assert id_b in deleted_ids, f"Post B should be in deleted changes; got {data['changes']}"

    db = TestingSessionLocal()
    post_a = db.query(models.Post).filter(models.Post.id == id_a).first()
    post_b = db.query(models.Post).filter(models.Post.id == id_b).first()
    db.close()
    assert post_a is None, "Post A must be gone from the database after confirmed deletion"
    assert post_b is None, "Post B must be gone from the database after confirmed deletion"


def test_no_raw_json_in_chat_reply(client, auth_headers):
    """A JSON tool-call payload leaked as text must never be forwarded to the user."""
    raw_json_blob = '[{"name":"update_post","parameters":{"post_id":1,"title":"oops"}}]'

    async def fake_llm_leaks_json(messages, **kwargs):
        return {"text": raw_json_blob, "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.llm.complete", new=fake_llm_leaks_json):
        r = client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "update post 1 title"}]},
            headers=auth_headers,
        )

    assert r.status_code == 200
    reply = r.json()["assistant_reply"]
    assert reply != raw_json_blob, "Raw JSON blob must not be the assistant reply"
    assert not reply.strip().startswith("[{"), "Reply must not start with a JSON array of objects"
    assert '"name"' not in reply, "Reply must not contain raw tool-call JSON fields"


def test_move_june_to_august_lists_then_reschedules_with_real_ids(client, auth_headers):
    """'Move my June posts to August' — list silently, bulk_reschedule with REAL ids,
    no confirmation gate, and no post IDs leaked into the reply."""
    r1 = client.post("/posts", json={
        "title": "Summer kickoff", "caption": "Caption one",
        "platform": "instagram", "scheduled_date": "2026-06-05",
    }, headers=auth_headers)
    r2 = client.post("/posts", json={
        "title": "Mid-month promo", "caption": "Caption two",
        "platform": "instagram", "scheduled_date": "2026-06-20",
    }, headers=auth_headers)
    assert r1.status_code == r2.status_code == 201
    post1_id, post2_id = r1.json()["id"], r2.json()["id"]

    seen_reschedule_ids: list = []
    call_count = 0

    async def fake_llm(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Model must list first to discover the real IDs
            tc = _make_tool_call("tc-list", "list_posts", {"month": "2026-06"})
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        if call_count == 2:
            # Pull the real IDs straight out of the list_posts tool result
            tool_msg = next(m for m in reversed(messages) if m.get("role") == "tool")
            listed = json.loads(tool_msg["content"])
            ids = [p["id"] for p in listed]
            seen_reschedule_ids.extend(ids)
            tc = _make_tool_call("tc-bulk", "bulk_reschedule_posts", {
                "reschedules": [
                    {"post_id": ids[0], "scheduled_date": "2026-08-05"},
                    {"post_id": ids[1], "scheduled_date": "2026-08-20"},
                ]
            })
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        return {
            "text": (
                "Done — I moved both posts into August: "
                "\"Summer kickoff\" and \"Mid-month promo\" are now scheduled for August."
            ),
            "tool_calls": [],
            "finish_reason": "stop",
        }

    with patch("src.backend.llm.complete", new=fake_llm):
        r = client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "Move my June posts to August"}]},
            headers=auth_headers,
        )

    assert r.status_code == 200
    data = r.json()

    # Real IDs were used (the ones we created), not fabricated 123/456/789
    assert set(seen_reschedule_ids) == {post1_id, post2_id}
    assert 123 not in seen_reschedule_ids and 456 not in seen_reschedule_ids

    # Reschedule happened immediately — no confirmation gate, changes present this turn
    assert len(data["changes"]) == 2, f"Both posts should move in one shot, got {data['changes']}"

    # Posts actually moved in the DB
    db = TestingSessionLocal()
    p1 = db.query(models.Post).filter(models.Post.id == post1_id).first()
    p2 = db.query(models.Post).filter(models.Post.id == post2_id).first()
    db.close()
    assert str(p1.scheduled_date) == "2026-08-05"
    assert str(p2.scheduled_date) == "2026-08-20"

    # No post IDs leaked into the reply (standalone numeric tokens)
    import re
    reply = data["assistant_reply"]
    for pid in (post1_id, post2_id):
        assert not re.search(rf"\b{pid}\b", reply), (
            f"Post ID {pid} must not appear in reply: {reply!r}"
        )
    assert "August" in reply or "Aug" in reply


def test_reschedule_intent_forces_tool_choice_required_first_turn(client, auth_headers):
    """A move/reschedule request must force tool_choice='required' on the first iteration."""
    client.post("/posts", json={
        "title": "Existing", "caption": "c", "platform": "instagram",
        "scheduled_date": "2026-06-08",
    }, headers=auth_headers)

    choices: list = []
    call_count = 0

    async def fake_llm(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        choices.append(kwargs.get("tool_choice"))
        if call_count == 1:
            tc = _make_tool_call("tc-list", "list_posts", {"month": "2026-06"})
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        if call_count == 2:
            tool_msg = next(m for m in reversed(messages) if m.get("role") == "tool")
            ids = [p["id"] for p in json.loads(tool_msg["content"])]
            tc = _make_tool_call("tc-bulk", "bulk_reschedule_posts", {
                "reschedules": [{"post_id": ids[0], "scheduled_date": "2026-07-08"}],
            })
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        return {"text": "Moved \"Existing\" to July.", "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.llm.complete", new=fake_llm):
        r = client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "move my June post to July"}]},
            headers=auth_headers,
        )

    assert r.status_code == 200
    assert choices[0] == "required", f"First turn must force a tool call, got {choices[0]!r}"
    assert choices[1] == "auto", "Later turns must relax back to 'auto'"


def test_fabricated_reschedule_success_is_overridden(client, auth_headers):
    """If the user asks to move posts but no write tool runs, a fake success is replaced."""
    client.post("/posts", json={
        "title": "Existing", "caption": "c", "platform": "instagram",
        "scheduled_date": "2026-06-08",
    }, headers=auth_headers)

    call_count = 0

    async def fake_llm(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Forced to call something — it lists, but then never reschedules
            tc = _make_tool_call("tc-list", "list_posts", {"month": "2026-06"})
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        # Fabricated success with no bulk_reschedule_posts call
        return {
            "text": "All done! I've moved your posts to July.",
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
    assert data["changes"] == [], "Nothing was actually moved"
    assert "wasn't able" in data["assistant_reply"].lower(), (
        f"Fabricated success must be overridden, got: {data['assistant_reply']!r}"
    )
    assert "moved" not in data["assistant_reply"].lower()


def test_id_language_stripped_from_reply(client, auth_headers):
    """Chain-of-thought 'I need to get their IDs first' language is scrubbed from the reply."""
    r1 = client.post("/posts", json={
        "title": "Launch", "caption": "c", "platform": "instagram",
        "scheduled_date": "2026-06-09",
    }, headers=auth_headers)
    post_id = r1.json()["id"]

    call_count = 0

    async def fake_llm(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            tc = _make_tool_call("tc-list", "list_posts", {"month": "2026-06"})
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        if call_count == 2:
            tc = _make_tool_call("tc-bulk", "bulk_reschedule_posts", {
                "reschedules": [{"post_id": post_id, "scheduled_date": "2026-07-09"}],
            })
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        return {
            "text": (
                "I need to get their IDs first. "
                "I've moved \"Launch\" to July."
            ),
            "tool_calls": [],
            "finish_reason": "stop",
        }

    with patch("src.backend.llm.complete", new=fake_llm):
        r = client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "reschedule my June post to July"}]},
            headers=auth_headers,
        )

    assert r.status_code == 200
    reply = r.json()["assistant_reply"]
    assert "ID" not in reply and "IDs" not in reply, f"ID language must be stripped: {reply!r}"
    assert "Launch" in reply and "July" in reply, "Result by title/date must remain"


def test_plan_then_move_full_scenario(client, auth_headers):
    """Exact scenario: plan 3 IG posts → answer questions → 'move those to first week of july'
    must actually move them and reply by title/date with no ID language."""
    # Turn 1: vague plan request → model asks a clarifying question (no tool, no force)
    plan_choices: list = []

    async def ask_question(messages, **kwargs):
        plan_choices.append(kwargs.get("tool_choice"))
        return {
            "text": "Happy to! What topic or theme should these 3 posts cover?",
            "tool_calls": [],
            "finish_reason": "stop",
        }

    with patch("src.backend.llm.complete", new=ask_question):
        r = client.post("/ai/chat", json={"messages": [
            {"role": "user", "content": "plan 3 ig posts mon/wed/fri next week"},
        ]}, headers=auth_headers)
    assert r.status_code == 200
    assert "?" in r.json()["assistant_reply"], "Should ask a clarifying question"
    assert plan_choices[0] == "auto", "Plan request must NOT be forced (allows clarifying question)"

    # Turn 2: user answers → model creates the 3 posts
    async def create_three(messages, **kwargs):
        tc = _make_tool_call("tc-create", "bulk_create_posts", {"posts": [
            {"title": "Behind the scenes", "caption": "BTS look", "platform": "instagram", "scheduled_date": "2026-06-22"},
            {"title": "Product spotlight", "caption": "Our best seller", "platform": "instagram", "scheduled_date": "2026-06-24"},
            {"title": "Customer story", "caption": "Real results", "platform": "instagram", "scheduled_date": "2026-06-26"},
        ]})
        if not any(m.get("role") == "tool" for m in messages):
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        return {"text": "Scheduled 3 Instagram posts for Mon/Wed/Fri next week.", "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.llm.complete", new=create_three):
        r = client.post("/ai/chat", json={"messages": [
            {"role": "user", "content": "plan 3 ig posts mon/wed/fri next week"},
            {"role": "assistant", "content": "What topic?"},
            {"role": "user", "content": "behind the scenes, product spotlight, customer story"},
        ]}, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["changes"]) == 3

    db = TestingSessionLocal()
    created = db.query(models.Post).filter(models.Post.scheduled_date.in_(
        ["2026-06-22", "2026-06-24", "2026-06-26"]
    )).all()
    created_ids = sorted(p.id for p in created)
    db.close()
    assert len(created_ids) == 3

    # Turn 3: 'move those to first week of july' → forced, lists, reschedules, clean reply
    move_choices: list = []
    call_count = 0

    async def move_them(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        move_choices.append(kwargs.get("tool_choice"))
        if call_count == 1:
            tc = _make_tool_call("tc-list", "list_posts", {"month": "2026-06"})
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        if call_count == 2:
            tool_msg = next(m for m in reversed(messages) if m.get("role") == "tool")
            ids = [p["id"] for p in json.loads(tool_msg["content"])]
            july = ["2026-07-01", "2026-07-02", "2026-07-03"]
            tc = _make_tool_call("tc-bulk", "bulk_reschedule_posts", {
                "reschedules": [{"post_id": pid, "scheduled_date": d} for pid, d in zip(ids, july)],
            })
            return {"text": None, "tool_calls": [tc], "finish_reason": "tool_calls"}
        return {
            "text": (
                "Moved all three into the first week of July: \"Behind the scenes\", "
                "\"Product spotlight\" and \"Customer story\"."
            ),
            "tool_calls": [],
            "finish_reason": "stop",
        }

    with patch("src.backend.llm.complete", new=move_them):
        r = client.post("/ai/chat", json={"messages": [
            {"role": "user", "content": "plan 3 ig posts mon/wed/fri next week"},
            {"role": "assistant", "content": "What topic?"},
            {"role": "user", "content": "behind the scenes, product spotlight, customer story"},
            {"role": "assistant", "content": "Scheduled 3 posts."},
            {"role": "user", "content": "move those to first week of july"},
        ]}, headers=auth_headers)

    assert r.status_code == 200
    data = r.json()
    assert move_choices[0] == "required", "Move turn must force a tool call"
    assert len(data["changes"]) == 3, f"All 3 posts must move, got {data['changes']}"

    # Posts actually moved into the first week of July
    db = TestingSessionLocal()
    moved = db.query(models.Post).filter(models.Post.id.in_(created_ids)).all()
    moved_dates = sorted(str(p.scheduled_date) for p in moved)
    db.close()
    assert moved_dates == ["2026-07-01", "2026-07-02", "2026-07-03"], moved_dates

    # Reply references titles, contains no ID language and no raw IDs
    reply = data["assistant_reply"]
    assert "ID" not in reply and "IDs" not in reply
    assert "Behind the scenes" in reply
    for pid in created_ids:
        assert not re.search(rf"\b{pid}\b", reply), f"ID {pid} leaked: {reply!r}"


def test_system_prompt_enforces_id_privacy_and_no_confirmation_for_reschedule(client, auth_headers):
    """System prompt must forbid leaking IDs and restrict the confirmation gate to deletes."""
    captured: list[list[dict]] = []

    async def capture_messages(messages, **kwargs):
        captured.append(messages)
        return {"text": "Sure.", "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.llm.complete", new=capture_messages):
        client.post(
            "/ai/chat",
            json={"messages": [{"role": "user", "content": "move my posts"}]},
            headers=auth_headers,
        )

    assert captured, "llm.complete should have been called"
    system_content = captured[0][0]["content"]
    assert "ID PRIVACY" in system_content, "Prompt must contain the ID privacy rule"
    assert "NO CONFIRMATION GATE" in system_content, (
        "Prompt must state reschedule/create/update have no confirmation gate"
    )
    assert "Never invent" in system_content, "Prompt must forbid inventing post IDs"
    assert "list_posts FIRST" in system_content, "Prompt must require list_posts before rescheduling"


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
