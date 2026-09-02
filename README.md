# Schoolmanager — NE-ES School Management System (backend)

FastAPI backend for the NE-ES School Management System: student records with
real photo uploads, plus the finance & fees module (fee structures, invoices,
payments, balances).

## Stack

| Concern    | Choice                                              |
| ---------- | --------------------------------------------------- |
| HTTP       | FastAPI (Pydantic v2 schemas)                        |
| ORM        | SQLAlchemy 2.0 (SQLite default, any URL via env)     |
| Money      | integer cents everywhere (no float rounding)         |
| QA         | `compileall`, `ruff`, `pytest` end-to-end (TestClient) |

## Layout

```
app/
  main.py              app factory: explicit router wiring, /static mount, error mapping
  core/                settings (env-overridable), engine/session factories, service errors
  models/              School, Student, FeeStructure, Invoice, Payment
  schemas/             Pydantic v2 request/response schemas
  services/            FileStorageService (uploads), ManagementService, FinanceService
  api/                 management + finance routers, deps.py wiring
  static/uploads/      avatars/ and logos/ live on disk here (contents git-ignored)
tests/                 50 end-to-end tests covering 200/201/400/404 (plus 413/422)
```

## Architecture rules (enforced by review + lint)

1. **Explicit static imports in every `__init__.py`** — packages re-export names
   with plain `from x import y` lines; no `importlib` loops or dynamic router
   discovery.
2. **Routers are wired only in `app/main.py`** via `app.include_router(...)`.
3. **Services own business logic** and raise typed `ServiceError`s
   (400/404/413/500); routes stay thin; a single exception handler in
   `create_app` converts them to JSON.
4. **Read schemas use `from_attributes`**; derived fields (balances, overdue
   flags, asset URLs) are composed in the service/schema layer.

## File storage (avatars & logos)

`app/services/storage.py` performs real file-system handling:

* magic-byte sniffing (PNG / JPEG / WebP / GIF only) — the client-declared
  `Content-Type` or filename is never trusted;
* hard size limit (default 2 MiB, `SCHOOLMGR_MAX_UPLOAD_BYTES`);
* generated names (`student-7_ab12cd34….png`) — the client filename never
  touches disk, so path traversal is structurally impossible;
* atomic writes (`tmp` + `os.replace`) into `app/static/uploads/<subdir>/`;
* replaced/removed photos are deleted from disk; files are served back at
  `/static/uploads/...` via the `StaticFiles` mount.

## Finance module

* `FeeStructure` — named, priced fee component per school (unique name per school).
* `Invoice` — one fee component per bill; `INV-<year>-<seq>` numbers; status
  `issued → partially_paid → paid`, plus `void`.
* `Payment` — immutable money-in records with `RCP-<year>-<seq>` receipts;
  overpayments and payments on settled/void invoices are rejected (HTTP 400).
* Balances are derived queries: per invoice (`/invoices/{id}/balance`) and
  per student (`/students/{id}/balance`, void invoices excluded, overdue count
  derived from due date + outstanding amount).

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

OpenAPI docs: `http://localhost:8000/docs` · Health: `GET /health`

### Key endpoints (prefix `/api/v1`)

| Method | Path                                   | Purpose                          |
| ------ | -------------------------------------- | -------------------------------- |
| POST   | `/management/schools`                  | create school                    |
| POST   | `/management/schools/{id}/logo`         | upload logo (multipart `file`)   |
| POST   | `/management/students`                  | create student                   |
| POST   | `/management/students/{id}/avatar`      | upload avatar (multipart `file`) |
| DELETE | `/management/students/{id}/avatar`      | remove avatar + file             |
| GET    | `/finance/fee-structures`               | list fee plan                    |
| POST   | `/finance/fee-structures`               | create fee                       |
| POST   | `/finance/invoices`                     | create invoice (fee or override) |
| POST   | `/finance/invoices/{id}/payments`       | record payment                   |
| GET    | `/finance/invoices/{id}/balance`        | invoice balance                  |
| GET    | `/finance/students/{id}/balance`        | aggregated student balance       |
| POST   | `/finance/invoices/{id}/void`           | void an untouched invoice        |

### Configuration (env)

| Variable                     | Default                       |
| ---------------------------- | ----------------------------- |
| `SCHOOLMGR_DATABASE_URL`     | `sqlite:///<repo>/data/schoolmanager.db` |
| `SCHOOLMGR_STATIC_ROOT`      | `app/static`                  |
| `SCHOOLMGR_MAX_UPLOAD_BYTES` | `2097152`                     |

## Verify

```bash
.venv/bin/python -m compileall -q app tests   # syntax
.venv/bin/ruff check app tests                # lint
.venv/bin/python -m pytest                    # end-to-end API tests
```
