# CampusArena — College Events & Hackathon Platform

> An Unstop-style, full-stack college events management platform built with Django 6. Enables event discovery, team formation, real-time registration tracking, in-team messaging, and skill-based team matching.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [App Modules](#3-app-modules)
4. [Data Models](#4-data-models)
5. [URL Structure](#5-url-structure)
6. [User Roles & Permissions](#6-user-roles--permissions)
7. [Tech Stack](#7-tech-stack)
8. [Project Structure](#8-project-structure)
9. [Getting Started (Local Development)](#9-getting-started-local-development)
10. [Environment Variables](#10-environment-variables)
11. [Running with Docker](#11-running-with-docker)
12. [Running Tests](#12-running-tests)
13. [Settings Overview](#13-settings-overview)
14. [Security](#14-security)
15. [Future Enhancements](#15-future-enhancements)

---

## 1. Project Overview

**CampusArena** is a web application for college students and faculty to:

- **Browse and discover** all college events — hackathons, workshops, coding contests, design jams, quizzes, paper presentations, and more.
- **Register** for events individually or as part of a team.
- **Form teams** with smart tech-stack matching — users specify their skills (Frontend, Backend, ML/AI, DevOps, UI/UX, Mobile, etc.) ensuring diverse skill sets.
- **Manage join requests** — team creators can approve or decline incoming requests from other students.
- **Receive in-app notifications** for join requests, announcements, and reminders.
- **Event organizers** can create, manage, and publish events with custom registration forms, multi-round timelines, prize structures, and announcements.

---

## 2. Architecture

CampusArena follows a **monolithic Django application** structure with a clear separation of concerns using the **Controller → Service → Repository → Model** pattern.

```
Request
  └─► URL Router (gdgProject/urls.py)
        └─► View (Controller)
              └─► Service Layer (business logic, transactions)
                    └─► Repository Layer (DB queries)
                          └─► Django ORM / Model
```

**Key patterns used:**

| Pattern | Where |
|---|---|
| Service Layer | `team/services.py` — `TeamJoinRequestService` |
| Repository Layer | `team/services.py` — `TeamRepository` |
| Soft Delete | `Event.is_deleted`, `Team.is_deleted` with custom managers |
| Custom Managers | `ActiveEventManager`, `AllEventManager`, `ActiveTeamManager` |
| Global Error Handling | `core/middleware/ErrorHandlerMiddleware` |
| Structured Exceptions | `core/exceptions.py` — `AppError` hierarchy |
| Structured Logging | `core/logging/` — JSON formatter for prod, verbose for dev |
| DTOs (Data Transfer Objects) | `JoinRequestResult` dataclass in `team/services.py` |

---

## 3. App Modules

The project is divided into **8 Django apps**, each with a single responsibility:

| App | Responsibility |
|---|---|
| `core` | Shared infrastructure — exceptions, middleware, logging, base views |
| `events` | Event discovery, listing, detail pages (public-facing) |
| `eventManagement` | Organizer-facing — create, edit, publish, archive events |
| `registration` | User event registration (individual & team) |
| `team` | Team creation, membership, join requests, in-team chat |
| `users` | Authentication — login, register, profile, logout |
| `dashboard` | Authenticated user dashboard — my events, my teams, pending requests |
| `notification` | In-app notification system |

### `core`

- **`core/exceptions.py`** — Custom exception hierarchy (`AppError`, `NotFoundError`, `PermissionDeniedError`, `ValidationError`, `ConflictError`)
- **`core/middleware/`** — `ErrorHandlerMiddleware` maps `AppError` subtypes to structured JSON or HTML error responses, and logs all unhandled 500s with a unique `request_id`
- **`core/logging/`** — Custom JSON formatter for production log pipelines and a verbose formatter for development
- **`core/views.py`** — `/health/` endpoint for container health checks

### `events`

Public-facing event browsing. Views currently use in-memory stub data (wired to the `Event` model as development progresses). Renders:
- Homepage with featured events and event grid
- Event detail page
- Category/filter browsing

### `eventManagement`

Organizer-only event management (create, edit, publish, manage rounds, announcements, view registrations).

### `registration`

Records a participant's registration for an event — supports both **individual** and **team** registration types, with statuses: `pending → confirmed → cancelled / submitted`.

### `team`

Full team lifecycle:
- **Create** a team for an event
- **Join** via join requests (approve / decline / cancel)
- **In-team chat** (ChatMessage model, POST handled server-side)
- **Tech stack coverage** — visual indicator of which roles are filled

### `users`

- Email + password registration with profile creation
- Login with "remember me" and `?next=` redirect support
- `UserProfile` model extending Django's `auth.User` (one-to-one)
- Skills stored as comma-separated tags with a `skills_list` property

### `dashboard`

Authenticated hub showing:
- Registered events
- Own teams
- Pending join requests (sent & received)
- Notification center

### `notification`

Generic notification model using a `GenericForeignKey` (`ContentType` + `target_id`) so one model can point at any object (Event, Team, JoinRequest). Supports types: `join_request`, `announcement`, `reminder`, `system`.

---

## 4. Data Models

### `Event` (`events/models.py`)

Core entity for the platform. Supports a full state machine:

```
draft → published → registration_open → registration_closed → ongoing → completed
      ↘ cancelled (from any mutable state)
      ↘ archived  (soft-delete)
```

| Field | Type | Notes |
|---|---|---|
| `slug` | SlugField | Unique, URL-safe identifier |
| `title` | CharField | Indexed |
| `category` | TextChoices | hackathon, workshop, coding_contest, quiz, paper_presentation, design_challenge, ideathon, case_study, cultural, sports, other |
| `mode` | TextChoices | online, offline, hybrid |
| `participation_type` | TextChoices | individual, team, both |
| `status` | TextChoices | draft, published, registration_open, registration_closed, ongoing, completed, cancelled, archived |
| `registration_start/end` | DateTimeField | Registration window |
| `event_start/end` | DateTimeField | Event window |
| `submission_deadline` | DateTimeField | Optional |
| `venue` / `platform_link` | CharField / URLField | For offline/online modes |
| `capacity` | PositiveIntegerField | Max participants or teams |
| `min_team_size` / `max_team_size` | PositiveSmallIntegerField | Team-based events |
| `prize_pool` / `prize_1st/2nd/3rd` | DecimalField / CharField | Prize details |
| `registration_fee` | DecimalField | 0 = free |
| `participation_certificate` / `merit_certificate` | BooleanField | Certificate availability |
| `organizer` | ForeignKey → User | Event creator |
| `is_deleted` | BooleanField | Soft-delete flag |

**Custom Managers:**
- `Event.objects` — `ActiveEventManager` (excludes `is_deleted=True`)
- `Event.all_objects` — `AllEventManager` (includes soft-deleted, for admin)

### `EventRound` (`events/models.py`)

Represents a phase/round within an event (e.g., Screening, Semi-Final, Final).

### `UserProfile` (`users/models.py`)

One-to-one extension of Django's `auth.User`:

| Field | Type |
|---|---|
| `phone` | CharField |
| `college` / `branch` / `year` | CharField / PositiveSmallIntegerField |
| `bio` | TextField (500 chars) |
| `github` / `linkedin` | URLField |
| `skills` | CharField (comma-separated) |
| `email_verified` | BooleanField |

Properties: `skills_list` (returns a Python list), `year_display` (e.g., "2nd Year").

### `Team` (`team/models.py`)

| Field | Notes |
|---|---|
| `event` | FK → Event |
| `name` | Unique per event |
| `leader` | FK → User (PROTECT, unique per event) |
| `status` | open, closed, disbanded |
| `is_deleted` | Soft-delete |

Properties: `member_count`, `is_full`, `spots_available`.

### `TeamMembership` (`team/models.py`)

Through model for Team ↔ User M2M with roles:
`frontend`, `backend`, `fullstack`, `mobile`, `uiux`, `ml_ai`, `data`, `devops`, `pm`, `other`

### `JoinRequest` (`team/models.py`)

State machine: `pending → approved | declined | cancelled`

### `ChatMessage` (`team/models.py`)

In-team messages scoped to a Team, with timestamps.

### `Registration` (`registration/models.py`)

| Field | Notes |
|---|---|
| `event` | FK → Event |
| `user` | FK → User |
| `type` | individual or team |
| `team` | FK → Team (required when type=team) |
| `status` | pending, confirmed, cancelled, submitted |

DB-level check constraint: `type='team'` requires `team IS NOT NULL`.

### `Notification` (`notification/models.py`)

Generic notification using Django's `ContentType` framework:

| Field | Notes |
|---|---|
| `user` | Recipient |
| `type` | join_request, announcement, reminder, system |
| `actor` | FK → User who triggered it (nullable) |
| `target_ct` + `target_id` + `target` | GenericForeignKey — points at any object |
| `read` | BooleanField, indexed |

---

## 5. URL Structure

| Prefix | App | Description |
|---|---|---|
| `/` | `events` | Homepage, event listing, event detail |
| `/auth/` | `users` | Login, register, logout, profile |
| `/dashboard/` | `dashboard` | User dashboard |
| `/teams/` | `team` | Team management, join requests, chat |
| `/organizer/` | `eventManagement` | Organizer event tools |
| `/registration/` | `registration` | Event registration flows |
| `/notifications/` | `notification` | Notification list & mark-read |
| `/admin/` | Django admin | Full admin site |
| `/health/` | `core` | Health check endpoint |

---

## 6. User Roles & Permissions

| Role | Access |
|---|---|
| **Super Admin** | Full platform control — all events, users, settings, analytics |
| **Event Organizer** | Create & manage own events, custom form builder, view registrations, send announcements, approve/reject registrations |
| **Participant** | Browse events, register (solo or team), create teams, send/accept join requests, in-team chat, personal dashboard |
| **Guest (Visitor)** | Read-only event browsing — must log in to register or interact |

---

## 7. Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | Django 6.x |
| **Language** | Python 3.12 |
| **Database (dev)** | SQLite |
| **Database (prod)** | PostgreSQL 16 |
| **Cache (prod)** | Redis 7 |
| **DB Driver** | psycopg (v3, binary) |
| **Static Files** | WhiteNoise (production) |
| **Containerisation** | Docker (multi-stage), Docker Compose |
| **WSGI Server** | Gunicorn |
| **Config Management** | python-decouple (`.env` files) |
| **Image Handling** | Pillow |
| **Testing** | pytest-django, coverage, factory-boy |
| **Linting / Formatting** | Ruff, Black, isort |
| **Security Scanning** | Bandit, Safety |

---

## 8. Project Structure

```
GDG/
├── Dockerfile                  # Multi-stage production Docker image
├── docker-compose.yml          # Django + PostgreSQL + Redis stack
├── requirements.txt            # Python dependencies
├── PROJECT_SPECIFICATION.txt   # Full feature & design specification
└── gdgProject/                 # Django project root
    ├── manage.py
    ├── db.sqlite3              # Dev SQLite database
    ├── core/                   # Shared infrastructure
    │   ├── exceptions.py       # AppError hierarchy
    │   ├── views.py            # Health check view
    │   ├── middleware/         # ErrorHandlerMiddleware
    │   ├── logging/            # JSON + verbose log formatters
    │   └── tests/              # Baseline test suite (unit, integration, permission)
    ├── events/                 # Public event browsing (models + views + urls)
    ├── eventManagement/        # Organizer event management
    ├── registration/           # Event registration models & views
    ├── team/                   # Team models, service layer, views
    │   └── services.py         # TeamJoinRequestService + TeamRepository
    ├── users/                  # Auth views + UserProfile model
    ├── dashboard/              # Authenticated user dashboard
    ├── notification/           # In-app notification model & views
    ├── templates/              # Global HTML templates (Jinja2/DTL)
    │   ├── base.html
    │   ├── 404.html / 500.html
    │   └── {app}/              # Per-app template directories
    ├── static/
    │   ├── css/style.css
    │   └── js/main.js, theme.js
    └── gdgProject/             # Django settings & WSGI/ASGI
        ├── urls.py             # Root URL config
        ├── settings/
        │   ├── base.py         # Shared settings
        │   ├── dev.py          # SQLite, console email, verbose logging
        │   ├── prod.py         # PostgreSQL, Redis, SMTP, HSTS, WhiteNoise
        │   └── test.py         # Test-specific overrides
        ├── wsgi.py
        └── asgi.py
```

---

## 9. Getting Started (Local Development)

### Prerequisites

- Python 3.12+
- Git

### Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd GDG

# 2. Create and activate a virtual environment
python3 -m venv env
source env/bin/activate       # Linux / macOS
# env\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file in the project root
cp .env.example .env          # if .env.example exists, otherwise create manually
# (see Environment Variables section below)

# 5. Run database migrations
cd gdgProject
python manage.py migrate --settings=gdgProject.settings.dev

# 6. Create a superuser
python manage.py createsuperuser --settings=gdgProject.settings.dev

# 7. Start the development server
python manage.py runserver --settings=gdgProject.settings.dev
```

The app will be available at `http://localhost:8000`.

---

## 10. Environment Variables

Create a `.env` file in the project root (`GDG/`). At minimum for development:

```env
DJANGO_SETTINGS_MODULE=gdgProject.settings.dev
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (dev uses SQLite by default — no DB vars needed)
# For PostgreSQL:
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=campusarena
# DB_USER=campusarena
# DB_PASSWORD=your-db-password
# DB_HOST=localhost
# DB_PORT=5432
```

For **production**, additionally set:

```env
DJANGO_SETTINGS_MODULE=gdgProject.settings.prod
DEBUG=False
SECRET_KEY=<strong-random-secret>
ALLOWED_HOSTS=yourdomain.com

DB_ENGINE=django.db.backends.postgresql
DB_NAME=campusarena
DB_USER=campusarena
DB_PASSWORD=<strong-password>
DB_HOST=db
DB_PORT=5432

REDIS_URL=redis://redis:6379/0

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## 11. Running with Docker

The `docker-compose.yml` spins up three services: **Django (web)**, **PostgreSQL (db)**, and **Redis (redis)**.

```bash
# Build and start all services
docker compose up --build

# Run migrations inside the container
docker compose exec web python manage.py migrate

# Create a superuser
docker compose exec web python manage.py createsuperuser

# Stop all services
docker compose down

# Stop and remove volumes (clears DB data)
docker compose down -v
```

The app will be available at `http://localhost:8000`.

**Docker image details:**
- Multi-stage build (builder → runtime) using `python:3.12-slim`
- Static files collected at build time via `collectstatic`
- Runs as a non-root `app` user for security
- PostgreSQL healthcheck ensures DB is ready before the web container starts

---

## 12. Running Tests

```bash
# From the gdgProject/ directory with the venv active
cd gdgProject

# Run all tests
pytest --ds=gdgProject.settings.test

# Run with coverage
coverage run -m pytest --ds=gdgProject.settings.test
coverage report

# Run a specific test file
pytest core/tests/test_baseline.py --ds=gdgProject.settings.test -v
```

### Test Strategy

The project follows a three-archetype **test pyramid**:

| Type | Example | Description |
|---|---|---|
| **Unit** | `TestTeamJoinRequestServiceUnit` | Service layer tested in complete isolation using mocks — no DB, fast execution |
| **Integration** | *(in `test_baseline.py`)* | Views + DB wired together using Django's `TestCase` with a real (test) database |
| **Permission** | *(in `test_baseline.py`)* | Validates role-based access control — unauthenticated, wrong-role, and correct-role scenarios |

---

## 13. Settings Overview

Settings are split into a layered hierarchy:

| Module | Use Case |
|---|---|
| `settings/base.py` | Shared across all environments — installed apps, middleware, templates, password validators, internationalization |
| `settings/dev.py` | Overrides for local development — SQLite, console email backend, in-memory cache, verbose logging, CSRF relaxation |
| `settings/prod.py` | Production hardening — PostgreSQL, Redis cache, SMTP email, HSTS, secure cookies, WhiteNoise for static files, JSON logging |
| `settings/test.py` | Test-specific overrides — fast password hashing, in-memory SQLite |

Switch environments via the `DJANGO_SETTINGS_MODULE` environment variable.

---

## 14. Security

- **`DEBUG=False`** enforced in production settings
- **HSTS** enabled with 1-year max-age, including subdomains and preload
- **Secure cookies** — `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `HTTPONLY` flags set
- **SSL redirect** — `SECURE_SSL_REDIRECT=True` in production
- **Content security** — `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_BROWSER_XSS_FILTER`
- **CSRF protection** — Django's built-in CSRF middleware active
- **Non-root Docker user** — container runs as `app` system user
- **Password validation** — minimum 10 characters, common password check, numeric-only check
- **DB-level constraints** — `UniqueConstraint` and `CheckConstraint` on critical business rules (e.g., team registration requires a team FK)
- **Atomic requests** — `ATOMIC_REQUESTS=True` wraps every request in a DB transaction
- **Dependency scanning** — `bandit` (SAST) and `safety` (CVE checks) in the dev toolchain

---

## 15. Future Enhancements

Based on the project specification, the following features are planned or partially implemented:

- **Real-time updates** — WebSocket-based live stats for participant counts, team openings, and announcements (Django Channels / ASGI)
- **In-team real-time messaging** — Upgrade current HTTP-POST chat to WebSocket-based messaging
- **Custom registration form builder** — Dynamic field creation by organizers (text, dropdown, file upload, etc.)
- **Email verification** — OTP or verification link on user registration
- **Smart team matching** — Algorithm to suggest teams based on skill-set complementarity
- **Event announcements** — Organizer-to-registrant broadcast notifications
- **Celery + Redis task queue** — Async email sending, scheduled status transitions, reminders
- **REST API** — Django REST Framework for mobile/SPA clients
- **Analytics dashboard** — Event organizer stats (registrations over time, team distribution, skill coverage)
- **Certificate generation** — Automated PDF participation/merit certificates
- **Multi-round management** — Organizer-controlled round progression with elimination tracking
- **Full-text search** — Elasticsearch or PostgreSQL `tsvector` for event search
