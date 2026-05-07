# Calendo

Content calendar app for creative brands, agencies & startups.

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (or use SQLite for development)

### Backend

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, SECRET_KEY (min 32 chars), FRONTEND_URL

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn src.backend.main:app --reload --port 8000
```

API will be available at http://localhost:8000. Docs at http://localhost:8000/docs.

### Frontend

```bash
cd src/frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:5173.

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

### Running Tests

```bash
# From project root, with venv activated
pytest tests/ -v
```

Tests use SQLite in-memory database — no PostgreSQL required for testing.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key (min 32 chars) |
| `ENVIRONMENT` | `development` or `production` |
| `FRONTEND_URL` | Frontend URL for CORS (e.g. `http://localhost:5173`) |
| `JWT_EXPIRE_DAYS` | JWT token expiry in days (default: 7) |

## Deployment

Defined in `render.yaml`. Three Render services:

1. **Web Service** — FastAPI backend
2. **Static Site** — React frontend (built from `src/frontend/dist`)
3. **PostgreSQL** — Managed database (free tier)

Deploy by connecting the GitHub repo to Render and using the Blueprint deploy option.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, python-jose, passlib, slowapi
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, shadcn/ui
- **Database**: PostgreSQL (production), SQLite (tests)
- **Hosting**: Render
