from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app.include_router(auth_router.router)
app.include_router(posts_router.router)
app.include_router(ai_router.router)
app.include_router(media_router.router)
app.include_router(handoff_router.router)


@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}
