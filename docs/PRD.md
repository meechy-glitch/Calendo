# Calendo — Product Requirements Document
> Content Calendar App for Creative Brands, Agencies & Startups

---

## Overview
A full-stack content planning tool for creative brands, agencies, and startups to plan, schedule, and manage social media posts across multiple platforms. Built with FastAPI + PostgreSQL backend and React frontend. Deployed on Render. Beta tested with influencers.

---

## App Name
**Calendo** — working name for the beta. Can be changed before public launch.

---

## Target Users
- Social media managers at creative agencies
- Brand managers at streetwear/lifestyle brands
- Startup marketing teams
- Freelance content creators
- Influencer beta testers

---

## User Stories

### Auth
- As a user, I can register with my email and password
- As a user, I can log in and receive a JWT access token
- As a user, I can log out and my session is cleared
- As a user, I can only see my own posts
- As a user, I am automatically redirected to login if my session expires

### Posts
- As a user, I can create a post with a title, caption, platform, scheduled date, and status
- As a user, I can view all my posts on a monthly calendar
- As a user, I can click a date on the calendar to create a post for that day
- As a user, I can click an existing post to view, edit, or delete it
- As a user, I can filter the calendar by platform
- As a user, I can export the current month's posts as a CSV file

---

## Data Models

### User
| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| email | string | Unique, required |
| hashed_password | string | bcrypt hash |
| created_at | datetime | Auto-generated |
| updated_at | datetime | Auto-updated on change |

### Post
| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| user_id | int | FK to users table |
| title | string | Required, max 100 chars |
| caption | string | Optional, max 2200 chars |
| platform | enum | Instagram, X, TikTok, LinkedIn |
| scheduled_date | date | YYYY-MM-DD, required |
| status | enum | Draft, Scheduled, Published |
| created_at | datetime | Auto-generated |
| updated_at | datetime | Auto-updated on change |

---

## Features

### 1. Authentication
- Register: email + password
  - Password minimum 8 characters
  - Returns 400 if email already registered
- Login: returns JWT access token + expiry
  - Token lifetime: 7 days
  - No refresh token for v1 — user re-logs in after expiry
  - Token stored in localStorage on frontend
  - On 401 response from any endpoint → clear token + redirect to /login
- Rate limiting on auth endpoints: max 10 requests/minute per IP via slowapi
- CORS configured to allow only the frontend domain in production

### 2. Post Management (CRUD)
- Create, read, update, delete posts
- All endpoints scoped to the authenticated user
- Users cannot access or modify other users' posts (403 Forbidden)
- Partial updates supported on PUT (only send changed fields)

### 3. Calendar View
- Monthly grid (Mon–Sun column headers)
- Posts appear on their scheduled date as colored chips
- Platform color coding:
  - Instagram → `#833AB4` Purple
  - X → `#888888` Gray
  - TikTok → `#FE2C55` Red
  - LinkedIn → `#0A66C2` Blue
- Status visual distinction on chips:
  - Draft → dashed border on chip
  - Scheduled → solid chip (default)
  - Published → chip has a checkmark icon + reduced opacity (0.6)
- Click empty date → open Create Post modal (date pre-filled)
- Click post chip → open Edit Post modal (all fields pre-filled)
- Quick status toggle: right-click or long-press a chip to cycle Draft → Scheduled → Published without opening modal
- "Today" button in navbar — jumps back to current month and selects today's date
- Calendar auto-refreshes after every create, edit, or delete (re-fetches from API)
- Loading state: skeleton calendar shown while posts are fetching
- Empty state: "No posts scheduled — click a date to get started"

### 4. Mobile Calendar View (iOS-style)
- Compact monthly grid at top with platform color dots below each date
- Selected date highlighted with `#E1306C` filled circle
- Today's date shows subtle ring when not selected
- Bottom half: scrollable list of posts for selected date
- Each post item shows:
  - Colored left border bar in platform color
  - Post title and platform name
  - Status badge (Draft/Scheduled/Published)
  - Tap to open Edit Post modal
- Quick status toggle: swipe right on a post item to mark as Published
- Floating `+` button in `#E1306C` to create post for selected date
- Empty state: "No posts — tap + to add one"
- "Today" button in navbar resets to current month and selects today

### 5. Platform Filter
- Toggle buttons for each platform above the calendar (desktop only)
- All platforms active by default
- Frontend-only filter — no API call on toggle

### 6. Quick Status Toggle
- Desktop: right-click a post chip → context menu with status options (Draft / Scheduled / Published)
- Mobile: swipe right on a post list item → marks as Published instantly
- Both call PUT /posts/{id} with updated status
- Calendar auto-refreshes after status change

### 7. Today Button
- Appears in the Navbar next to the month display
- Clicking it resets the calendar to the current month
- Highlights today's date with the `#E1306C` accent circle
- Works on both desktop and mobile views

### 8. CSV Export
- "Export Month" button in header
- Downloads CSV of all posts for the currently viewed month
- CSV columns: Title, Caption, Platform, Scheduled Date, Status
- Filename format: `calendo-posts-YYYY-MM.csv`
- Triggered via GET /posts/export/csv?month=YYYY-MM

### 9. Beta Feedback
- Floating "Send Feedback" button in bottom-right corner
- Opens a modal with a textarea
- Submits to a Tally or Google Form (external link, no backend needed)

---

## Backend API

### Auth Endpoints
| Method | Path | Auth | Status Codes |
|--------|------|------|--------------|
| POST | /auth/register | No | 201 Created, 400 Email taken, 422 Validation error |
| POST | /auth/login | No | 200 OK + token, 401 Invalid credentials |

### Post Endpoints
| Method | Path | Auth | Status Codes |
|--------|------|------|--------------|
| GET | /posts | Yes | 200 OK |
| POST | /posts | Yes | 201 Created, 422 Validation error |
| GET | /posts/{id} | Yes | 200 OK, 404 Not found |
| PUT | /posts/{id} | Yes | 200 OK, 404 Not found, 403 Forbidden |
| DELETE | /posts/{id} | Yes | 204 No content, 404 Not found, 403 Forbidden |
| GET | /posts/export/csv | Yes | 200 OK (CSV file), 400 Missing month param |
| GET | /health | No | 200 OK — Render health check |

### Query Params
- `GET /posts` — supports `?month=YYYY-MM` to filter by month
- `GET /posts/export/csv` — requires `?month=YYYY-MM`

### Error Response Format
All errors return consistent JSON:
```json
{
  "detail": "Human readable error message"
}
```

---

## Frontend Screens & Components

### Screens
| Path | Description |
|------|-------------|
| `/` | Redirect to `/dashboard` if logged in, else `/login` |
| `/login` | Login form, link to register |
| `/register` | Register form, link to login |
| `/dashboard` | Protected — redirects to `/login` if no valid token |

### Route Protection
- `ProtectedRoute` component wraps `/dashboard`
- Checks for JWT in localStorage on mount
- On 401 from any API call → clear localStorage + redirect to `/login`

### Mobile Responsiveness
- Desktop (≥768px): full 7-column monthly grid with post chips (`CalendarGrid`)
- Mobile (<768px): iOS Calendar-style layout (`CalendarMobile`)
  - Compact monthly grid at top with platform color dots below each date
  - Selected date highlighted with `#E1306C` filled circle
  - Today's date shows a subtle ring when not selected
  - Bottom half shows scrollable list of posts for selected date
  - Each post item shows colored left border bar, title, platform, status badge
  - Floating `+` button in `#E1306C` to create post for selected date
  - Empty state: "No posts — tap + to add one"
- Swap between components using a `useMediaQuery` hook or Tailwind `md:` breakpoint

### Components
| Component | Description |
|-----------|-------------|
| `ProtectedRoute` | Guards authenticated routes |
| `Navbar` | App name, month display, Today button, user email, logout |
| `CalendarGrid` | Desktop: full monthly grid with post chips, prev/next navigation |
| `CalendarMobile` | Mobile: iOS-style compact grid + selected day post list |
| `CalendarCell` | Single day cell — date number + post chips (desktop only) |
| `PostChip` | Colored chip showing post title, platform color coded (desktop only) |
| `PlatformFilter` | Toggle buttons for each platform (desktop only) |
| `PostModal` | Create/edit form — title, caption, platform, date, status |
| `ExportButton` | Triggers CSV download for current month |
| `FeedbackButton` | Floating button bottom-right, opens feedback modal |
| `LoadingSkeleton` | Shown while calendar posts are loading |
| `EmptyState` | Shown when no posts exist for current month (desktop) |
| `ErrorToast` | Shows API error messages to the user |

### Frontend State
- Auth: JWT token + user email in localStorage
- Calendar: current month, active platform filters, posts array
- Modal: open/closed, mode (create/edit), pre-filled data
- No external state library — React useState + useContext

### Local Dev Proxy
`vite.config.js` proxies `/api` → `http://localhost:8000` during development to avoid CORS issues locally.

---

## File Structure
```
content-calendar/
├── src/
│   ├── backend/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── auth.py
│   │   ├── config.py
│   │   └── routers/
│   │       ├── auth.py
│   │       └── posts.py
│   └── frontend/
│       ├── index.html
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── package.json
│       ├── tailwind.config.ts
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   ├── auth.ts
│       │   └── posts.ts
│       ├── hooks/
│       │   └── useMediaQuery.ts
│       └── components/
│           ├── ProtectedRoute.tsx
│           ├── Navbar.tsx
│           ├── CalendarGrid.tsx
│           ├── CalendarMobile.tsx
│           ├── CalendarCell.tsx
│           ├── PostChip.tsx
│           ├── PlatformFilter.tsx
│           ├── PostModal.tsx
│           ├── ExportButton.tsx
│           ├── FeedbackButton.tsx
│           ├── LoadingSkeleton.tsx
│           ├── EmptyState.tsx
│           └── ErrorToast.tsx
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_posts.py
├── .env.example
├── render.yaml
├── requirements.txt
└── README.md
```

---

## Tech Stack
| Layer | Tech |
|-------|------|
| Backend | FastAPI, Python 3.10 |
| Database | PostgreSQL via SQLAlchemy + psycopg2 |
| Migrations | Alembic |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Rate limiting | slowapi |
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Testing | pytest, httpx |
| Dev server | uvicorn --reload + Vite dev server |
| Hosting | Render (web service + static site + managed PostgreSQL) |

---

## Security
- Passwords hashed with bcrypt via passlib
- JWT signed with `SECRET_KEY` env var — never hardcoded
- All post endpoints validate resource ownership (403 if mismatch)
- Rate limiting on `/auth/register` and `/auth/login` — 10 req/min per IP
- CORS: production allows only `FRONTEND_URL` domain
- `.env` never committed — `.env.example` provided
- `SECRET_KEY` minimum 32 characters, randomly generated

---

## Environment Variables

### `.env.example`
```
DATABASE_URL=postgresql://user:password@localhost:5432/calendo
SECRET_KEY=your-secret-key-minimum-32-chars
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173
JWT_EXPIRE_DAYS=7
```

### Render Dashboard Variables
```
DATABASE_URL        → Render internal Postgres connection string
SECRET_KEY          → randomly generated 64-char hex string
ENVIRONMENT         → production
FRONTEND_URL        → https://your-frontend.onrender.com
JWT_EXPIRE_DAYS     → 7
```

---

## Render Deployment

### Services
1. **Web Service** — FastAPI backend
   - Build: `pip install -r requirements.txt && alembic upgrade head`
   - Start: `uvicorn src.backend.main:app --host 0.0.0.0 --port $PORT`
   - Health check: `GET /health`

2. **Static Site** — React frontend
   - Build: `cd src/frontend && npm install && npm run build`
   - Publish directory: `src/frontend/dist`
   - Rewrite rule: `/* → /index.html` (React Router support)

3. **PostgreSQL** — Render managed database (free tier)
   - `DATABASE_URL` auto-injected into web service env

### `render.yaml`
Defines all three services as infrastructure-as-code for reproducible deploys.

---

## Testing

### Backend (`/tests`)
| File | Coverage |
|------|----------|
| `conftest.py` | Test DB setup, test client, auth headers fixture |
| `test_auth.py` | Register success, duplicate email 400, login success, wrong password 401, missing fields 422 |
| `test_posts.py` | Create, read all, read one, update, delete, 404 on missing, 403 on wrong user, CSV export, month filter |

### Frontend
- Not included in v1 beta
- Add Playwright e2e tests before public launch

---

## Color Scheme
| Token | Hex | Usage |
|-------|-----|-------|
| Background | `#0F0F0F` | Page background |
| Surface | `#1A1A1A` | Cards, modals, calendar cells |
| Primary accent | `#E1306C` | Buttons, active states, links |
| Text primary | `#F5F5F5` | Headings, body text |
| Text muted | `#888888` | Placeholders, secondary labels |
| Border | `#2A2A2A` | Dividers, cell borders |

### Platform Colors
| Platform | Hex | Color |
|----------|-----|-------|
| Instagram | `#833AB4` | Purple |
| X | `#888888` | Gray |
| TikTok | `#FE2C55` | Red |
| LinkedIn | `#0A66C2` | Blue |

---

## Acceptance Criteria
- [ ] User can register with email + password (min 8 chars)
- [ ] Duplicate email returns 400
- [ ] User can login and receive JWT
- [ ] Wrong password returns 401
- [ ] JWT protects all post endpoints
- [ ] Expired/missing token redirects to /login
- [ ] User can create, read, update, delete their own posts
- [ ] User cannot access another user's posts (403)
- [ ] Desktop: calendar renders correctly with posts on correct dates
- [ ] Desktop: posts are color coded by platform
- [ ] Desktop: status distinction visible on chips (dashed/solid/checkmark)
- [ ] Desktop: platform filter works (no API call)
- [ ] Desktop: right-click chip shows status context menu
- [ ] Mobile: iOS-style calendar renders with platform dots
- [ ] Mobile: tapping a date shows that day's posts below
- [ ] Mobile: floating + button creates post for selected date
- [ ] Mobile: swipe right marks post as Published
- [ ] Today button resets calendar to current month and highlights today
- [ ] Calendar auto-refreshes after create, edit, delete, or status change
- [ ] Loading skeleton shown while fetching
- [ ] Empty state shown when no posts for the month
- [ ] CSV export downloads correctly
- [ ] Feedback button opens feedback form
- [ ] All backend tests passing
- [ ] Alembic migrations run cleanly
- [ ] CORS configured correctly for production
- [ ] App deploys to Render (backend + frontend + database)
- [ ] Health check returns 200
- [ ] Environment variables configured in Render dashboard

---

## Out of Scope (v1 Beta)
- Social media API integration (actual posting to platforms)
- Team/collaboration features
- Notifications or reminders
- Mobile app
- Image/media upload
- Password reset flow
- Email verification
- Frontend tests
- Analytics or usage tracking
- Week view
- Drag and drop rescheduling
- Bulk actions (mark all as published, delete all drafts etc.)