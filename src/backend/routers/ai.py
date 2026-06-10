import base64
import json
import boto3
from datetime import date, datetime
from typing import Optional, Union
from pydantic import BaseModel, field_validator, model_validator
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session

from src.backend import crud, models, schemas
from src.backend.auth import get_current_user
from src.backend.config import GROQ_API_KEY, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
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
            "name": "save_memory",
            "description": (
                "Save a durable fact, preference, or summary about the user. "
                "Call when the user explicitly says 'remember that…' OR when you learn something "
                "clearly durable: their brand, recurring campaigns, tone preferences, ongoing projects, "
                "key decisions. Do NOT save one-off task details, questions, or conversation trivia."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The fact, preference, or summary to remember",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["fact", "preference", "summary"],
                        "description": "Category of memory",
                    },
                },
                "required": ["content", "type"],
            },
        },
    },
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
                        "anyOf": [
                            {"type": "string", "enum": ["instagram", "x", "tiktok", "linkedin"]},
                            {"type": "null"},
                        ],
                        "description": "Filter by platform (omit or null for all)",
                    },
                    "status": {
                        "anyOf": [
                            {"type": "string", "enum": ["draft", "scheduled", "published"]},
                            {"type": "null"},
                        ],
                        "description": "Filter by status (omit or null for all)",
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
                    "post_id": {
                        "anyOf": [{"type": "integer"}, {"type": "string"}],
                        "description": "ID of the post to update",
                    },
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
                    "post_id": {
                        "anyOf": [{"type": "integer"}, {"type": "string"}],
                        "description": "ID of the post to reschedule",
                    },
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
            "name": "bulk_reschedule_posts",
            "description": (
                "Reschedule multiple posts to new dates in one call. "
                "Use this whenever moving several posts at once, e.g. 'move June posts to July' "
                "or 'shift next week to the following week'. "
                "First call list_posts to get post IDs, then call this with all posts in one shot."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reschedules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "post_id": {
                                    "anyOf": [{"type": "integer"}, {"type": "string"}],
                                    "description": "ID of the post to reschedule",
                                },
                                "scheduled_date": {"type": "string", "description": "New date in YYYY-MM-DD format"},
                                "scheduled_time": {"type": "string", "description": "New time in HH:MM format (optional)"},
                            },
                            "required": ["post_id", "scheduled_date"],
                        },
                    }
                },
                "required": ["reschedules"],
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

class _SaveMemoryArgs(BaseModel):
    content: str
    type: str


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
    post_id: Union[int, str]
    title: Optional[str] = None
    caption: Optional[str] = None
    platform: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("post_id", mode="before")
    @classmethod
    def coerce_post_id(cls, v):
        try:
            return int(v)
        except (TypeError, ValueError):
            raise ValueError(f"post_id must be an integer, got {v!r}")


class _RescheduleArgs(BaseModel):
    post_id: Union[int, str]
    scheduled_date: str
    scheduled_time: Optional[str] = None

    @field_validator("post_id", mode="before")
    @classmethod
    def coerce_post_id(cls, v):
        try:
            return int(v)
        except (TypeError, ValueError):
            raise ValueError(f"post_id must be an integer, got {v!r}")


class _BulkRescheduleArgs(BaseModel):
    reschedules: list[_RescheduleArgs]


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


class CaptionFromImageRequest(BaseModel):
    media_asset_id: int
    platform: Optional[str] = None


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


def _downscale_image(image_bytes: bytes, mime_type: Optional[str]) -> tuple[bytes, str]:
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > 1568:
        scale = 1568 / long_edge
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    out_fmt = "JPEG"
    out_mime = "image/jpeg"
    if mime_type == "image/png":
        out_fmt, out_mime = "PNG", "image/png"
    elif mime_type == "image/webp":
        out_fmt, out_mime = "WEBP", "image/webp"
    if img.mode in ("RGBA", "P") and out_fmt == "JPEG":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format=out_fmt)
    return buf.getvalue(), out_mime


def _get_memories_text(db: Session, user_id: int) -> str:
    memories = crud.get_memories(db, user_id, limit=50)
    if not memories:
        return ""
    lines = [f"- [{m.type}] {m.content}" for m in memories]
    return "\n\nWhat you remember about this user:\n" + "\n".join(lines)


async def _execute_tool(
    tool_name: str,
    args: dict,
    db: Session,
    user_id: int,
    changes: list[dict],
    timezone: str,
) -> str:
    if tool_name == "save_memory":
        try:
            a = _SaveMemoryArgs(**args)
        except Exception as e:
            return json.dumps({"error": str(e)})
        valid_types = {"fact", "preference", "summary"}
        mem_type = a.type if a.type in valid_types else "fact"
        _, was_saved = crud.save_memory(db, user_id, a.content, mem_type)
        if was_saved:
            return json.dumps({"saved": True, "content": a.content, "type": mem_type})
        return json.dumps({"saved": False, "reason": "duplicate"})

    if tool_name == "get_today":
        return json.dumps({"date": str(date.today()), "timezone": timezone})

    if tool_name == "list_posts":
        try:
            a = _ListPostsArgs(**args)
        except Exception as e:
            return json.dumps({"error": str(e)})
        # Coerce empty strings sent by the model to None
        platform_filter = a.platform or None
        status_filter = a.status or None
        posts = crud.get_posts(db, user_id, a.month)
        if platform_filter:
            posts = [p for p in posts if p.platform.value == platform_filter]
        if status_filter:
            posts = [p for p in posts if p.status.value == status_filter]
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
        change_entry: dict = {"type": "updated", "id": a.post_id}
        if a.scheduled_date is not None:
            change_entry["new_date"] = a.scheduled_date
        changes.append(change_entry)
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
        changes.append({"type": "updated", "id": a.post_id, "new_date": a.scheduled_date})
        return json.dumps({"rescheduled": {"id": a.post_id, "new_date": a.scheduled_date}})

    if tool_name == "bulk_reschedule_posts":
        try:
            a = _BulkRescheduleArgs(**args)
        except Exception as e:
            return json.dumps({"error": str(e)})
        rescheduled: list[dict] = []
        errors: list[dict] = []
        for item in a.reschedules:
            try:
                sched_date = date.fromisoformat(item.scheduled_date)
            except ValueError as e:
                errors.append({"post_id": item.post_id, "error": str(e)})
                continue
            item_update: dict = {"scheduled_date": sched_date}
            if item.scheduled_time is not None:
                item_update["scheduled_time"] = item.scheduled_time
            result = crud.update_post(db, item.post_id, schemas.PostUpdate(**item_update), user_id)
            if result == "not_found":
                errors.append({"post_id": item.post_id, "error": "Post not found"})
            elif result == "forbidden":
                errors.append({"post_id": item.post_id, "error": "Not authorized"})
            else:
                changes.append({"type": "updated", "id": item.post_id, "new_date": item.scheduled_date})
                rescheduled.append({"id": item.post_id, "new_date": item.scheduled_date})
        return json.dumps({"rescheduled": rescheduled, "errors": errors})

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
    memories_text = _get_memories_text(db, user.id)
    system_msg = {
        "role": "system",
        "content": (
            "You are Calendo AI, an expert social media content calendar assistant. "
            f"Today is {date.today()}. User's timezone: {timezone}. "
            "Use the provided tools to read and modify the user's posts. "
            "Never expose or assume the user's internal ID. "
            "CONTENT CREATION RULE: When a user asks you to plan, create, or schedule posts "
            "but does NOT specify a topic, theme, or actual content direction, you MUST ask "
            "1-3 concise clarifying questions first — e.g. what topic or theme, what goal or tone, "
            "whether they have specific ideas. If no platform is specified, ask for it. "
            "Do NOT call create_post or bulk_create_posts until you have real content direction. "
            "NEVER create placeholder titles like 'Post 1', 'Post 2', 'Post 3', or posts with "
            "generic/empty captions. Every post must have a meaningful title and a full caption "
            "tailored to the platform, using the user's brand voice and the content they described. "
            "ANTI-HALLUCINATION RULE: You MUST call a tool for any request to create, update, "
            "reschedule, or move posts. NEVER claim to have created, updated, or moved posts "
            "unless you actually called the appropriate tool during this turn. "
            "For bulk moves (e.g. 'move June posts to July'): call list_posts first to get IDs "
            "and current dates, then call bulk_reschedule_posts with all posts in a single call, "
            "computing the equivalent date in the destination month for each post "
            "(e.g. June 5 → July 5, June 20 → July 20). "
            "MEMORY: Use save_memory to store durable user facts — brand details, recurring campaigns, "
            "tone preferences, ongoing projects, key decisions. Call it when the user says "
            "'remember that…' AND proactively when you learn something clearly durable. "
            "Do NOT save one-off task details or trivial information. "
            "IMPORTANT: After using any tool, always respond in natural, conversational English. "
            "Never output raw JSON, tool results, or structured data directly to the user. "
            "Instead, summarise what you did in plain language, for example: "
            "'I've scheduled 3 Instagram posts for next week: Monday — \"Morning routine\", "
            "Wednesday — \"Product spotlight\", Friday — \"Weekend vibes\".' "
            "Be friendly, concise, and specific about what was created, updated, or found."
            f"{bv_text}"
            f"{memories_text}"
        ),
    }
    messages: list[dict] = [system_msg] + messages_in
    changes: list[dict] = []

    for i in range(MAX_CHAT_ITERATIONS):
        result = await llm.complete(messages, tools=_CHAT_TOOLS, max_tokens=2048, tool_choice="auto")

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


@router.post("/transcribe")
@limiter.limit("10/hour")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    import io
    _require_groq()
    MAX_SIZE = 5 * 1024 * 1024
    content = await audio.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Audio file too large (max 5 MB)")
    from src.backend import llm
    client = llm._get_groq_client()
    filename = audio.filename or "recording.webm"
    mime = audio.content_type or "audio/webm"
    try:
        result = await client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=(filename, io.BytesIO(content), mime),
        )
        return {"text": result.text}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription error: {exc}")


@router.get("/memory")
def list_memories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.MemoryResponse]:
    return crud.get_memories(db, current_user.id, limit=200)


@router.delete("/memory/{memory_id}")
def delete_memory(
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    result = crud.delete_memory(db, current_user.id, memory_id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True}


@router.delete("/memory")
def clear_all_memories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    count = crud.clear_memories(db, current_user.id)
    return {"cleared": count}


@router.post("/caption-from-image")
@limiter.limit("15/hour")
async def caption_from_image(
    request: Request,
    body: CaptionFromImageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    _require_groq()
    if body.platform and body.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {body.platform}")

    asset = db.query(models.MediaAsset).filter(
        models.MediaAsset.id == body.media_asset_id,
        models.MediaAsset.user_id == current_user.id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    try:
        r2 = boto3.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        obj = r2.get_object(Bucket=R2_BUCKET, Key=asset.storage_key)
        image_bytes = obj["Body"].read()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch image from storage: {exc}")

    try:
        image_bytes, out_mime = _downscale_image(image_bytes, asset.mime_type)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process image: {exc}")

    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{out_mime};base64,{b64}"

    bv_text = _get_brand_voice_text(db, current_user.id)
    platform_hint = f" for {body.platform}" if body.platform else ""

    system = (
        "You are an expert social media copywriter with vision capabilities.\n"
        "Analyze the attached image and write 3 captions.\n"
        "Respond ONLY with valid JSON, no prose, no markdown fences:\n"
        '{"suggested_platform":"instagram|x|tiktok|linkedin",'
        '"captions":["caption1","caption2","caption3"],'
        '"alt_text":"short accessibility description"}'
        f"{bv_text}"
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": f"Write 3 captions for this image{platform_hint}. Return JSON only."},
            ],
        },
    ]

    from src.backend import llm
    try:
        result = await llm.complete(messages, max_tokens=1024)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    text = result["text"] or ""
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {}

    suggested = parsed.get("suggested_platform", "")
    if suggested not in VALID_PLATFORMS:
        suggested = body.platform or "instagram"

    captions = parsed.get("captions", [])
    if not isinstance(captions, list):
        captions = []

    return {
        "suggested_platform": suggested,
        "captions": captions[:3],
        "alt_text": parsed.get("alt_text", ""),
    }
