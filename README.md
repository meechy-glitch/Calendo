# Calendo

Content calendar for social media teams. Plan, schedule and track posts across Instagram, X, TikTok and LinkedIn from one place.

## Live
- Frontend: https://calendo-omega.vercel.app
- Backend: https://calendo-api.onrender.com

## Tech Stack
- **Backend:** FastAPI, PostgreSQL, SQLAlchemy, Alembic, JWT auth, bcrypt
- **Frontend:** Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Database:** Supabase (PostgreSQL)
- **Deployment:** Vercel (frontend), Render Docker (backend)

## Features
- Auth with JWT (register, login, password reset)
- Post scheduling across Instagram, X, TikTok and LinkedIn
- Multi-platform posting — create one post across multiple platforms at once
- Desktop monthly calendar grid with platform color coding
- Mobile iOS-style calendar view
- Draft → Scheduled → Published workflow
- Platform filter, CSV export, analytics summary
- Daily summary banner showing today's scheduled posts
- Published posts locked as read-only
- Demo account with sample posts

## Local Development

### Backend
```bash
cd into project root
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.backend.main:app --reload --port 8000
```

### Frontend
```bash
cd src/frontend
npm install
npm run dev
```

### Environment Variables
Create a `.env` file in the project root:
```
DATABASE_URL=your_postgresql_url
SECRET_KEY=your_secret_key
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
JWT_EXPIRE_DAYS=7
RESEND_API_KEY=your_resend_api_key
```
