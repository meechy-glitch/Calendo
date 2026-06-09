# Calendo — Responsive UX Redesign (frontend only)

Restructure the Calendo dashboard for clarity on BOTH mobile and desktop. FRONTEND-ONLY —
do NOT touch the backend, API endpoints, data shapes, or database. Preserve ALL existing
functionality; only reorganize presentation. Next.js 14 (App Router, TS, Tailwind,
shadcn/ui). Design mobile-first, then adapt to desktop at the md breakpoint.

## Design tokens (keep these)
- bg #0F0F0F, surface #1A1A1A, accent #E1306C, text #F5F5F5, muted #888888, border #2A2A2A.
- Platform colors: Instagram #833AB4, X #888888, TikTok #FE2C55, LinkedIn #0A66C2.

## Guiding principles
- Structure over pile-up: each concern gets its own home, not one long scroll.
- One clear priority per screen; lead with the action, not the data.
- Restraint with the accent: solid pink = ONE primary action per screen. Everything else
  neutral/outlined. Platform colors do the categorization.
- Hierarchy through size and spacing, not more borders.
- KEEP what works: the desktop month grid with platform-colored post chips is good — retain
  its quality, only declutter the chrome around it.

## Change 1 — Responsive navigation (the core change)
Remove the three floating pill buttons (Brand Voice, Notifications, AI Assistant) entirely —
they float over and overlap the calendar/content. Replace with a single responsive nav with
four destinations:
  - **Today** — Ready-to-post queue + what's due today (default destination).
  - **Calendar** — month grid + selected-day detail + platform filters + stats + Export Month.
  - **Assistant** — the chat assistant (ChatPanel), full-screen/main-area.
  - **Settings** — Brand Voice + Notification preferences (lead reminder toggle) + Logout.

Responsive placement:
  - **Mobile (< md):** fixed BOTTOM TAB BAR. Active tab in accent, others muted. lucide-react
    icons. Carry the ready-count badge on the Today tab.
  - **Desktop (>= md):** fixed LEFT SIDEBAR with the same four destinations stacked
    vertically, main content to the right. Active item in accent.

Keep the "+" create-post action in the top header on both (single primary action).

## Change 2 — Consolidate the assistant entry points
There are currently TWO ways into the assistant (the floating "AI Assistant" pill AND a
floating chat bubble bottom-right). Remove both floating elements. The Assistant nav
destination is the single entry point.

## Change 3 — Today-first
Make **Today** the default destination. Lead with "what do I post today?" — the
Ready-to-post queue (reuse existing ReadyQueue / PostNowModal) as the hero, the single most
urgent/overdue post visually larger than the rest. Calendar is the second destination.

## Change 4 — Accent discipline
Audit accent (#E1306C). It's currently on the +, selected date, every "Post now" border, the
banner stripe, and the ready-queue border at once. Reduce to: solid accent for the single
primary action only (the + ; and "Post now" on the single most-urgent post). Other "Post now"
buttons outlined/neutral. Remove decorative accent borders from container cards. Use platform
colors (not pink) for post dots/chips/labels.

## Change 5 — Collapse redundant "today" surfaces
There are overlapping "today" representations: the daily banner ("All done for today" /
"You have N posts going out today"), the selected-day detail, and the Ready-to-post queue.
Remove the standalone daily banner. The Ready-to-post queue (Today destination) conveys it
better. Keep the selected-day detail only inside the Calendar destination.

## Change 6 — De-duplicate the month label
"June 2026" currently appears twice (a top-center pill and the calendar heading with prev/
next arrows). Keep ONE month indicator with navigation (the calendar heading). Remove the
redundant top-center pill, or repurpose that space — don't show the month twice.

## Change 7 — Redesign the stats block
Current stats read like a debug log ("Instagram: 11, X: 5, TikTok: 4, LinkedIn: 4, Total:
24, Published: 5, Scheduled: 4, Draft: 15"). Replace with 3 glanceable stat tiles
(**Scheduled**, **Drafts**, **This month** total) at the top of the Calendar destination; on
desktop lay them in a row. Put the per-platform breakdown in a compact secondary row of
small platform-colored dots + counts, skipping any platform with 0.

## Change 8 — Spacing & hierarchy
Consistent vertical rhythm between cards (no equal-weight edge-to-edge stacking). The
most-urgent post larger than the rest. All scrollable content gets bottom padding (mobile)
or left padding (desktop) so nothing hides behind the tab bar / sidebar.

## Constraints
- NO backend/API/data-shape/migration changes.
- NO feature removed — caption AI, image caption, voice mic buttons, brand voice,
  notifications, export, filters, post CRUD all still work, just relocated.
- Keep voice mic buttons where they are (chat input + post idea field).
- Must be clean and usable at 390px (mobile) AND ~1440px (desktop).

## Delivery
- No backend changes, no migrations.
- Verify on both a 390px and a 1440px viewport: nav renders correctly for each, Today is the
  default, nothing is hidden behind nav, month shown once, and every existing feature is
  reachable.
- Give me the git add/commit/push commands when done.
