import json
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.backend import crud, models, schemas
from src.backend.auth import get_current_user
from src.backend.config import GROQ_API_KEY
from src.backend.database import get_db
from src.backend.limiter import limiter

router = APIRouter(prefix="/ai", tags=["ai"])

VALID_PLATFORMS = {"instagram", "x", "tiktok", "linkedin"}

_PLATFORM_CAPTION_INSTRUCTIONS = {
    "instagram": (
        "Write warm, engaging Instagram captions. Be conversational and relatable. "
        "Include 3-5 relevant hashtags at the end. Use emoji naturally throughout."
    ),
    "x": (
        "Write punchy, direct tweets for X (Twitter). Each caption MUST be under 280 characters. "
        "Be concise, sharp, and engaging. No hashtags unless they add value."
    ),
    "tiktok": (
        "Write casual, hooky TikTok captions. Open with a strong hook. "
        "Use trending, authentic language. Keep it fun and relatable. "
        "Optionally include 2-3 relevant hashtags."
    ),
    "linkedin": (
        "Write professional LinkedIn captions. Business tone, no emoji. "
        "Focus on insights, value, or a compelling story. End with a question or call to action."
    ),
}

_PLATFORM_REWRITE_INSTRUCTIONS = {
    "instagram": "Warm, emoji-rich, 3-5 hashtags, conversational.",
    "x": "Punchy, under 280 characters, no filler.",
    "tiktok": "Casual, hooky, authentic, trending language.",
    "linkedin": "Professional, no emoji, insight-driven.",
}

MAX_CHAT_ITERATIONS = 6

_CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_today",
            "description": "Get the current date and the user's timezone.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_posts",
            "description": "List the user's scheduled posts for a given month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "Month in YYYY-MM format"},
                    "platform": {
                        "type": "string",
                        "enum": ["instagram", "x", "tiktok", "linkedin"],
                        "description": "Filter by platform",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["draft", "scheduled", "published"],
                        "description": "Filter by status",
                    },
                },
                "required": ["month"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_post",
            "description": "Create a new scheduled post.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "caption": {"type": "string"},
                    "platform": {"type": "string", "enum": ["instagram", "x", "tiktok", "linkedin"]},
                    "scheduled_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "scheduled_time": {"type": "string", "description": "HH:MM (optional)"},
                    "notes": {"type": "string"},
                },
                "required": ["title", "caption", "platform", "scheduled_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_post",
            "description": "Update fields of an existing post.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer"},
                    "title": {"type": "string"},
                    "caption": {"type": "string"},
                    "platform": {"type": "string", "enum": ["instagram", "x", "tiktok", "linkedin"]},
                    "scheduled_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "scheduled_time": {"type": "string"},
                    "status": {"type": "string", "enum": ["draft", "scheduled", "published"]},
                    "notes": {"type": "string"},
                },
                "required": ["post_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_post",
            "description": "Reschedule a post to a new date and optional time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer"},
                    "scheduled_date": {"type": "string", "description": "New date in YYYY-MM-DD format"},
                    "scheduled_time": {"type": "string", "description": "New time in HH:MM format (optional)"},
                },
                "required": ["post_id", "scheduled_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bulk_create_posts",
            "description": "Create multiple posts at once, e.g. to plan a full week.",
            "parameters": {
                "type": "object",
                "properties": {
                    "posts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "caption": {"type": "string"},
                                "platform": {
                                    "type": "string",
                                    "enum": ["instagram", "x", "tiktok", "linkedin"],
                                },
                                "scheduled_date": {"type": "string", "description": "YYYY-MM-DD"},
                                "scheduled_time": {"type": "string"},
                                "notes": {"type": "string"},
                            },
                            "required": ["title", "caption", "platform", "scheduled_date"],
                        },
                    }
                },
                "required": ["posts"],
            },
        },
    },
]


# ── Pydantic input models for tool validation ──────────────────────────────

class _ListPostsArgs(BaseModel):
    month: str
    platform: Optional[str] = None
    status: Optional[str] = None


class _PostArgs(BaseModel):
    title: str
    caption: str
    platform: str
    scheduled_date: str
    scheduled_time: Optional[str] = None
    notes: Optional[str] = None


class _UpdatePostArgs(BaseModel):
    post_id: int
    title: Optional[str] = None
    caption: Optional[str] = None
    platform: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class _RescheduleArgs(BaseModel):
    post_id: int
    scheduled_date: str
    scheduled_time: Optional[str] = None


class _BulkCreateArgs(BaseModel):
    posts: list[_PostArgs]


# ── Request/Response bodies ────────────────────────────────────────────────

class CaptionRequest(BaseModel):
    idea: str
    platform: str
    brand_voice: Optional[str] = None

    @field_validator("idea")
    @classmethod
    def validate_idea(cls, v: str) -> str:
        if len(v) < 3 or len(v) > 500:
            raise ValueError("idea must be 3–500 characters")
        return v


class RewriteRequest(BaseModel):
    caption: str
    target_platforms: list[str]


class ChatMessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn]
    timezone: Optional[str] = "UTC"


# ── Helpers ────────────────────────────────────────────────────────────────

def _require_groq() -> None:
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="AI features not configured (missing GROQ_API_KEY)")


def _get_brand_voice_text(db: Session, user_id: int) -> str:
    bv = db.query(models.BrandVoice).filter(models.BrandVoice.user_id == user_id).first()
    if not bv:
        return ""
    parts: list[str] = []
    if bv.tone:
        parts.append(f"Tone: {bv.tone}")
    if bv.dos:
        parts.append(f"Do: {bv.dos}")
    if bv.donts:
        parts.append(f"Don't: {bv.donts}")
    if bv.sample_posts:
        parts.append(f"Sample posts: {bv.sample_posts}")
    return "\n\nBrand voice:\n" + "\n".join(parts) if parts else ""


async def _execute_tool(
    tool_name: str,
    args: dict,
    db: Session,
    user_id: int,
    changes: list[dict],
    timezone: str,
) -> str:
    if tool_name == "get_today":
        return json.dumps({"date": str(date.today()), "timezone": timezone})

    if tool_name == "list_posts":
        try:
            a = _ListPostsArgs(**args)
        except Exception as e:
            return json.dumps({"error": str(e)})
        posts = crud.get_posts(db, user_id, a.month)
        if a.platform:
            posts = [p for p in posts if p.platform.value == a.platform]
        if a.status:
            posts = [p for p in posts if p.status.value == a.status]
        return json.dumps([
            {
                "id": p.id,
                "title": p.title,
                "platform": p.platform.value,
                "scheduled_date": str(p.scheduled_date),
                "scheduled_time": p.scheduled_time,
                "status": p.status.value,
            }
            for p in posts[:50]
        ])

    if tool_name == "create_post":
        try:
            a = _PostArgs(**args)
        except Exception as e:
            return json.dumps({"error": str(e)})
        try:
            sched_date = date.fromisoformat(a.scheduled_date)
            platform = models.PlatformEnum(a.platform)
        except ValueError as e:
            return json.dumps({"error": str(e)})
        post = crud.create_post(
            db,
            schemas.PostCreate(
                title=a.title,
                caption=a.caption,
                platform=platform,
                scheduled_date=sched_date,
                scheduled_time=a.scheduled_time,
                notes=a.notes,
            ),
            user_id,
        )
        changes.append({"type": "created", "id": post.id})
        return json.dumps({"created": {"id": post.id, "title": post.title}})

    if tool_name == "update_post":
        try:
            a = _UpdatePostArgs(**args)
        except Exception as e:
            return json.dumps({"error": str(e)})
        update_data: dict = {}
        if a.title is not None:
            update_data["title"] = a.title
        if a.caption is not None:
            update_data["caption"] = a.caption
        if a.platform is not None:
            try:
                update_data["platform"] = models.PlatformEnum(a.platform)
            except ValueError:
                return json.dumps({"error": f"Unknown platform: {a.platform}"})
        if a.scheduled_date is not None:
            try:
                update_data["scheduled_date"] = date.fromisoformat(a.scheduled_date)
            except ValueError as e:
                return json.dumps({"error": str(e)})
        if a.scheduled_time is not None:
            update_data["scheduled_time"] = a.scheduled_time
        if a.status is not None:
            try:
                update_data["status"] = models.StatusEnum(a.status)
            except ValueError:
                return json.dumps({"error": f"Unknown status: {a.status}"})
        if a.notes is not None:
            update_data["notes"] = a.notes
        result = crud.update_post(db, a.post_id, schemas.PostUpdate(**update_data), user_id)
        if result == "not_found":
            return json.dumps({"error": "Post not found"})
        if result == "forbidden":
            return json.dumps({"error": "Not authorized"})
        changes.append({"type": "updated", "id": a.post_id})
        return json.dumps({"updated": {"id": a.post_id}})

    if tool_name == "reschedule_post":
        try:
            a = _RescheduleArgs(**args)
        except Exception as e:
            return json.dumps({"error": str(e)})
        try:
            sched_date = date.fromisoformat(a.scheduled_date)
        except ValueError as e:
            return json.dumps({"error": str(e)})
        update_data = {"scheduled_date": sched_date}
        if a.scheduled_time is not None:
            update_data["scheduled_time"] = a.scheduled_time
        result = crud.update_post(db, a.post_id, schemas.PostUpdate(**update_data), user_id)
        if result == "not_found":
            return json.dumps({"error": "Post not found"})
        if result == "forbidden":
            return json.dumps({"error": "Not authorized"})
        changes.append({"type": "updated", "id": a.post_id})
        return json.dumps({"rescheduled": {"id": a.post_id, "new_date": a.scheduled_date}})

    if tool_name == "bulk_create_posts":
        try:
            a = _BulkCreateArgs(**args)
        except Exception as e:
            return json.dumps({"error": str(e)})
        created: list[dict] = []
        for p in a.posts:
            try:
                sched_date = date.fromisoformat(p.scheduled_date)
                platform = models.PlatformEnum(p.platform)
            except ValueError as e:
                return json.dumps({"error": f"Invalid input for '{p.title}': {e}"})
            post = crud.create_post(
                db,
                schemas.PostCreate(
                    title=p.title,
                    caption=p.caption,
                    platform=platform,
                    scheduled_date=sched_date,
                    scheduled_time=p.scheduled_time,
                    notes=p.notes,
                ),
                user_id,
            )
            changes.append({"type": "created", "id": post.id})
            created.append({"id": post.id, "title": post.title})
        return json.dumps({"created": created})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


async def _run_chat_loop(
    messages_in: list[dict],
    db: Session,
    user: models.User,
    timezone: str,
) -> tuple[str, list[dict]]:
    from src.backend import llm  # lazy — requires openai at runtime only
    bv_text = _get_brand_voice_text(db, user.id)
    system_msg = {
        "role": "system",
        "content": (
            "You are Calendo AI, an expert social media content calendar assistant. "
            f"Today is {date.today()}. User's timezone: {timezone}. "
            "Use the provided tools to read and modify the user's posts. "
            f"Never expose or assume the user's internal ID.{bv_text}"
        ),
    }
    messages: list[dict] = [system_msg] + messages_in
    changes: list[dict] = []

    for _ in range(MAX_CHAT_ITERATIONS):
        result = await llm.complete(messages, tools=_CHAT_TOOLS, max_tokens=2048)

        if not result["tool_calls"]:
            return result["text"] or "Done.", changes

        # Append assistant message (with tool_calls)
        assistant_msg: dict = {
            "role": "assistant",
            "content": result["text"],
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in result["tool_calls"]
            ],
        }
        messages.append(assistant_msg)

        # Execute each tool and append results
        for tc in result["tool_calls"]:
            try:
                tool_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}
            tool_result = await _execute_tool(
                tc.function.name, tool_args, db, user.id, changes, timezone
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_result,
            })

    # Max iterations exceeded — return last assistant text if any
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            return msg["content"], changes

    return "I've processed your request.", changes


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/caption")
@limiter.limit("20/hour")
async def generate_caption(
    request: Request,
    body: CaptionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    _require_groq()
    if body.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {body.platform}")

    from src.backend import llm  # lazy — requires openai at runtime only
    bv_text = _get_brand_voice_text(db, current_user.id)
    if body.brand_voice:
        bv_text = f"\n\nBrand voice override: {body.brand_voice}"

    platform_instructions = _PLATFORM_CAPTION_INSTRUCTIONS[body.platform]
    system = (
        f"You are an expert social media copywriter.\n"
        f"Platform: {body.platform}\n"
        f"{platform_instructions}{bv_text}\n\n"
        'Respond ONLY with valid JSON: {"captions": ["caption1", "caption2", "caption3"]}'
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Write 3 caption options for: {body.idea}"},
    ]
    try:
        result = await llm.complete(messages, max_tokens=1024)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    try:
        text = result["text"] or ""
        # Strip markdown code fences if present
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip())
        captions = parsed["captions"]
        if not isinstance(captions, list) or len(captions) == 0:
            raise ValueError("no captions")
    except Exception:
        # Fallback: split by newlines
        lines = [l.strip().lstrip("123.-) ") for l in (result["text"] or "").splitlines() if l.strip()]
        captions = lines[:3] if lines else ["Could not generate captions. Please try again."]

    return {"captions": captions[:3]}


@router.post("/rewrite")
async def rewrite_caption(
    body: RewriteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    _require_groq()
    from src.backend import llm  # lazy — requires openai at runtime only
    invalid = [p for p in body.target_platforms if p not in VALID_PLATFORMS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown platforms: {invalid}")

    bv_text = _get_brand_voice_text(db, current_user.id)
    platform_hints = "\n".join(
        f"- {p}: {_PLATFORM_REWRITE_INSTRUCTIONS[p]}" for p in body.target_platforms
    )
    system = (
        f"You are an expert social media copywriter.\n"
        f"Rewrite the caption for each requested platform.\n"
        f"Platform instructions:\n{platform_hints}{bv_text}\n\n"
        "Respond ONLY with valid JSON mapping platform name to rewritten caption. "
        'Example: {"instagram": "...", "x": "..."}'
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Original caption:\n{body.caption}\n\n"
                f"Rewrite for: {', '.join(body.target_platforms)}"
            ),
        },
    ]
    try:
        result = await llm.complete(messages, max_tokens=1024)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    try:
        text = result["text"] or ""
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        rewrites = json.loads(text.strip())
    except Exception:
        rewrites = {p: body.caption for p in body.target_platforms}

    return {"rewrites": rewrites}


@router.get("/brand-voice", response_model=schemas.BrandVoiceResponse)
def get_brand_voice(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> schemas.BrandVoiceResponse:
    bv = db.query(models.BrandVoice).filter(models.BrandVoice.user_id == current_user.id).first()
    if not bv:
        return schemas.BrandVoiceResponse()
    return bv


@router.put("/brand-voice", response_model=schemas.BrandVoiceResponse)
def upsert_brand_voice(
    body: schemas.BrandVoiceUpsert,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.BrandVoice:
    bv = db.query(models.BrandVoice).filter(models.BrandVoice.user_id == current_user.id).first()
    if bv:
        for key, value in body.model_dump(exclude_unset=True).items():
            setattr(bv, key, value)
        bv.updated_at = datetime.utcnow()
    else:
        bv = models.BrandVoice(user_id=current_user.id, **body.model_dump(exclude_unset=True))
        db.add(bv)
    db.commit()
    db.refresh(bv)
    return bv


@router.post("/chat")
@limiter.limit("30/hour")
async def chat(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    _require_groq()
    messages_in = [{"role": m.role, "content": m.content} for m in body.messages]
    tz = body.timezone or "UTC"
    try:
        reply, changes = await _run_chat_loop(messages_in, db, current_user, tz)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    return {"assistant_reply": reply, "changes": changes}
