# NE-ES School Management System - Backend

FastAPI + Pydantic v2 + SQLAlchemy 2.x REST backend for the NE-ES private
school management platform. It provides authentication (JWT), student
enrolment, academic management (classes & subjects) and school branding /
UI-configuration endpoints.

## Stack

- [FastAPI](https://fastapi.tiangolo.com/) (modern async web framework)
- [Pydantic v2](https://docs.pydantic.dev/) (validation / serialization)
- [SQLAlchemy 2.x](https://www.sqlalchemy.org/) (ORM, typed `Mapped` models)
- [PyJWT](https://pyjwt.readthedocs.io/) (access tokens)
- SQLite by default; any SQLAlchemy-supported database (Postgres, MySQL) via `DATABASE_URL`

## Project layout

```
schoolmanager/
├── app/
│   ├── api/               # Routers: auth, students, academics, management (+ deps)
│   ├── core/              # Settings + security (password hash, JWT)
│   ├── db/                # DeclarativeBase, engine/session, init & seeding
│   ├── models/            # ORM models: identity, academics, management
│   ├── schemas/           # Pydantic models (requests/responses)
│   ├── services/          # Business logic used by the routers
│   └── main.py            # FastAPI app, router registration, health check
├── requirements.txt
└── .gitignore
```

All `__init__.py` files use **static, explicit imports** - there are no
dynamic loader loops or `pkgutil`/`importlib` tricks anywhere.

## Setup & run

```bash
# 1. Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. (optional) configuration via environment variables - see .env.example
cp .env.example .env

# 3. Run the server (SQLite DB + seed data are created automatically)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs: http://127.0.0.1:8000/docs
Alternative docs (ReDoc): http://127.0.0.1:8000/redoc
Health check: http://127.0.0.1:8000/

## Default seed credentials

On first startup the app creates the database tables and seeds a default
private school plus an administrator account (both configurable via env vars):

| Field    | Default value |
|----------|---------------|
| username | `admin`       |
| password | `admin123`    |
| school   | `NE-ES Academy` (code `NEES`) |

> **Change the default admin password and `SECRET_KEY` before any real deployment.**

## API overview

| Method | Path                          | Description                                    | Auth |
|--------|-------------------------------|------------------------------------------------|------|
| GET    | `/`                           | Health check                                   | -    |
| POST   | `/auth/login`                 | Log in with username/email + password → JWT    | -    |
| GET    | `/auth/me`                    | Current user profile                           | ✔    |
| GET    | `/students/`                  | List students (`?school_id=`)                  | ✔    |
| POST   | `/students/`                  | Enrol a new student (unique `student_number`)  | ✔    |
| GET    | `/students/{id}`              | Get a student by ID                            | ✔    |
| GET    | `/academics/classes`          | List school classes                            | ✔    |
| POST   | `/academics/classes`          | Create a school class                          | ✔    |
| GET    | `/academics/classes/{id}`     | Get a class by ID                              | ✔    |
| GET    | `/academics/subjects`         | List subjects                                  | ✔    |
| POST   | `/academics/subjects`         | Create a subject                               | ✔    |
| GET    | `/academics/subjects/{id}`    | Get a subject by ID                            | ✔    |
| GET    | `/management/settings`        | School UI config (colors/branding) - public    | -    |
| PUT    | `/management/settings`        | Update UI config (colors validated `#RRGGBB`)  | ✔    |
| GET    | `/management/settings/school` | School profile                                 | -    |
| POST   | `/management/settings/logo`   | School logo upload (placeholder)               | ✔    |
| POST   | `/management/settings/photos` | Photo upload (placeholder)                     | ✔    |

Protected routes expect `Authorization: Bearer <access_token>`.

## Configuration (`app/core/config.py`)

| Env var                    | Default                                              |
|----------------------------|------------------------------------------------------|
| `APP_NAME`                 | `NE-ES School Management System`                     |
| `APP_VERSION`              | `1.0.0`                                              |
| `DEBUG`                    | `false`                                              |
| `DATABASE_URL`             | `sqlite:///<repo>/schoolmanager.db`                  |
| `SECRET_KEY`               | `dev-only-secret-change-me-in-production`            |
| `TOKEN_ALGORITHM`          | `HS256`                                              |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440`                                            |
| `DEFAULT_SCHOOL_NAME`      | `NE-ES Academy`                                      |
| `DEFAULT_ADMIN_USERNAME`   | `admin`                                              |
| `DEFAULT_ADMIN_PASSWORD`   | `admin123`                                           |

## Development notes

- Passwords are hashed with PBKDF2-HMAC-SHA256 (per-user random salt) - never
  stored in plain text.
- Model/schema registries live in `app/models/__init__.py` and
  `app/schemas/__init__.py` with static imports so tooling can rely on `__all__`.
- Photo endpoints are deliberate placeholders: they validate the payload and
  return the target path. Implement real storage inside
  `app/services/management.store_photo()` (S3 / local `uploads/` folder).
