import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/calendo")
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-min32chars")
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
JWT_EXPIRE_DAYS: int = int(os.getenv("JWT_EXPIRE_DAYS", "7"))
RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
