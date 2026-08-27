from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.backend.config import FRONTEND_URL, ENVIRONMENT
from src.backend.limiter import limiter
from src.backend.routers import auth as auth_router
from src.backend.routers import posts as posts_router
from src.backend.routers import ai as ai_router
from src.backend.routers import media as media_router
from src.backend.routers import handoff as handoff_router

app = FastAPI(title="Calendo API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [FRONTEND_URL]
if ENVIRONMENT == "development":
    origins += [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic's default 422 body is a list of machine-readable error dicts, which
# the frontend can only render as "[object Object]". Flatten it into a single
# readable sentence under the same `detail` key every other error path uses.
_FIELD_LABELS = {
    "name": "Name",
    "email": "Email",
    "password": "Password",
    "new_password": "Password",
}


def _humanize_error(error: dict) -> str:
    location = [part for part in error.get("loc", ()) if part != "body"]
    field = str(location[-1]) if location else ""
    label = _FIELD_LABELS.get(field) or (field.replace("_", " ").capitalize() or "Request")
    error_type = error.get("type", "")
    ctx = error.get("ctx") or {}
    message = error.get("msg", "is invalid")

    if error_type == "missing":
        return f"{label} is required"
    if error_type == "string_too_short":
        return f"{label} must be at least {ctx.get('min_length')} characters"
    if error_type == "string_too_long":
        return f"{label} must be {ctx.get('max_length')} characters or less"
    if field in ("email",) and error_type.startswith("value_error"):
        return "Please enter a valid email address"
    if error_type.startswith("value_error"):
        # Our own validators raise ValueError; pydantic prefixes the message.
        return message.split("Value error, ", 1)[-1]
    return f"{label}: {message}"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = [_humanize_error(error) for error in exc.errors()]
    # De-duplicate while preserving order.
    seen: dict[str, None] = {}
    for message in messages:
        seen.setdefault(message, None)
    return JSONResponse(
        status_code=422,
        content={"detail": ". ".join(seen) or "Invalid request"},
    )


app.include_router(auth_router.router)
app.include_router(posts_router.router)
app.include_router(ai_router.router)
app.include_router(media_router.router)
app.include_router(handoff_router.router)


@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}
