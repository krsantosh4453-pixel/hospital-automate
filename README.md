# Hospital Management System (HMS)

Multi-hospital management system: React (Vite) frontend, Django REST Framework backend, strict per-hospital data isolation.

**Status (2026-10-25): CONDITIONALLY_READY_AFTER_LISTED_ACTIONS for a defined pilot scope. Not complete against the full requirements.** See [`docs/FINAL_PRODUCTION_READINESS_REPORT.md`](docs/FINAL_PRODUCTION_READINESS_REPORT.md) for the verdict, its conditions and the coverage figures, and [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) for what does not exist yet.

---

## 1. Project Overview

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, Vite 8, React Router 7, Tailwind CSS 4 |
| **Backend** | Django 6.0, Django REST Framework 3.18, SimpleJWT |
| **Database** | PostgreSQL 16 (production), SQLite (development and tests) |
| **Cache/Queue** | Redis 7, Celery 5 |
| **Authentication** | Staff: password + SMS OTP (Twilio Verify). Patients: mobile/email OTP, password, Google |
| **API Documentation** | drf-spectacular: `/api/schema/`, `/api/docs/`, `/api/redoc/`; route table in `docs/API_DOCUMENTATION.md` |
| **Deployment** | Docker Compose, nginx |

Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Data model: [`docs/DATABASE.md`](docs/DATABASE.md).

## 2. Module Status

Taken from [`docs/REQUIREMENTS_TRACEABILITY.md`](docs/REQUIREMENTS_TRACEABILITY.md) (116 requirement rows): 42 verified, 24 implemented, 23 partial, 23 missing, 3 blocked, 1 not applicable.

| Module | Status |
|---|---|
| Tenancy, roles, staff auth, audit | Verified by tests |
| Patient registration and portal, consent, record sharing | Working; no proxy/caregiver access |
| Appointments, OPD queue, consultation, prescriptions | Working; no ICD-10 search or structured EMR sections |
| Laboratory | Working order → sample → result → release; no printing |
| Pharmacy | Ledgered stock and dispensing; **no drug-interaction checking** |
| IPD, nursing, MAR, discharge | Working; discharge requires a finalized summary |
| Billing | Server-side Decimal totals, append-only idempotent payments, refunds; no advance payments or PDF |
| AI scribe | Draft → clinician approval only; needs a real STT/LLM provider (mocks are disabled in production) |
| Notifications | In-app with consent and delivery log; SMS/WhatsApp need credentials; no voice workflow |
| Reports | Server-side KPIs |
| FHIR, HL7, ABDM | Code present, **not mounted** |
| Interface language | English / Hindi (navigation and patient menu) |

AI output is always labelled **"AI Draft — Pending Review"** until a linked doctor approves it.

---

## 3. Quick Start Guide

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 20+ | Frontend build tooling |
| npm | 10+ | Package manager |
| PostgreSQL | 16+ | Production database |
| Redis | 7+ | Cache, Celery broker |
| Docker | 24+ | Containerization (optional) |
| Git | 2.40+ | Version control |

### Clone Repository

```bash
git clone <repository-url>
cd hospital-automate
```

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env with your values (see docs/ENVIRONMENT.md)

# Run migrations
python manage.py migrate

# Create superuser (optional, for Django admin)
python manage.py createsuperuser

# Create staff user (if management command exists)
# python manage.py create_staff_user --username admin --password <pwd> --role Admin

# Start development server
python manage.py runserver 0.0.0.0:8000
```

**Backend runs at:** `http://localhost:8000`
**API Base URL:** `http://localhost:8000/api`
**Admin:** `http://localhost:8000/admin/` (or `ADMIN_URL` from env)
**API Docs:** `http://localhost:8000/api/docs/` (Swagger), `http://localhost:8000/api/redoc/` (ReDoc)
**Health Checks:** `http://localhost:8000/health/`, `/health/live/`, `/health/ready/`

### Frontend Setup

```bash
cd hospital-automate  # project root

# Install dependencies
npm install

# Start development server
npm run dev
```

**Frontend runs at:** `http://localhost:5173` (proxies `/api` to `http://localhost:8000`)

### Available Frontend Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run lint` | Run ESLint |
| `npm test` | Run frontend unit tests (Vitest) |
| `npm run preview` | Preview production build |

### Running with Docker Compose (Development)

```bash
# From project root
docker-compose -f docker-compose.dev.yml up -d

# Backend: http://localhost:8000
# Frontend: http://localhost:5173
# PostgreSQL: localhost:5432
# Redis: localhost:6379
```

### Running with Docker Compose (Production)

Follow **`docs/DEPLOYMENT.md`**. In short: fill `.env` (compose variables) and `.env.production` (Django; copy `.env.production.example`), put TLS files in `./ssl/`, then:

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

The backend container migrates and collects static files on start. Never run `down -v` on production: it deletes the database volume.

---

## 4. Environment Variables

See **`docs/ENVIRONMENT.md`** for complete documentation of all environment variables.

**Quick Reference — Required for Development:**

```bash
# .env (development)
DJANGO_ENV=development
DJANGO_SECRET_KEY=django-insecure-dev-key-change-in-production
DATABASE_URL=postgres://hms_user:hms_password@localhost:5432/hms_dev
REDIS_URL=redis://localhost:6379/0
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
VITE_API_BASE_URL=/api
AI_SCRIBE_ENABLED=False  # Disable if no API key
```

**Production requires** (startup fails without them): `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DATABASE_URL`, `REDIS_URL`, `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`, `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`, `GOOGLE_CLIENT_ID`, and Twilio Verify credentials. See `docs/DEPLOYMENT.md`.

---

## 5. Project Structure

```
hospital-automate/
├── backend/                    # Django project
│   ├── config/                 # Django settings, URLs, WSGI/ASGI
│   │   ├── settings/
│   │   │   ├── base.py         # Shared settings
│   │   │   ├── development.py  # Dev overrides
│   │   │   ├── production.py   # Prod overrides
│   │   │   └── testing.py      # Test overrides
│   │   ├── urls.py             # Root URL configuration
│   │   └── ...
│   ├── users/                  # Authentication, staff profiles
│   ├── patients/               # Patient registration, documents
│   ├── hospital/               # Hospital, Department, Ward, Room, Bed
│   ├── doctors/                # Doctor management
│   ├── appointments/           # Appointment scheduling
│   ├── encounters/             # Visits, QueueTokens, DoctorSchedule
│   ├── clinical/               # Vitals, Notes, Diagnoses, Prescriptions
│   ├── ipd/                    # Admissions, Bed management, Discharge
│   ├── emergency/              # Emergency visits, Triage
│   ├── pharmacy/               # Medicine inventory, Sales
│   ├── procurement/            # Suppliers, PO, GRN, Stock transactions
│   ├── laboratory/             # Lab tests, Samples, Results
│   ├── bloodbank/              # Blood inventory, Requests, Transactions
│   ├── billing/                # Invoices, Payments, Insurance claims
│   ├── nurses/                 # Nurses, Assessments, MAR, Care tasks
│   ├── notifications/          # Notifications, Consent, OTP
│   ├── audit/                  # Audit logs, AI interactions
│   ├── ai_scribe/              # AI Medical Scribe (mock/demo)
│   ├── reports/                # Analytics, Forecasting
│   ├── abdm/                   # ABDM/ABHA integration (stub)
│   ├── interoperability/       # FHIR mappings (stub)
│   └── manage.py
│
├── src/                        # React frontend (Vite)
│   ├── pages/                  # Page components
│   │   ├── admin/              # Admin pages
│   │   ├── patient/            # Patient portal pages
│   │   └── *.jsx               # Staff pages
│   ├── components/             # Reusable components
│   ├── layouts/                # Layout wrappers
│   ├── assets/context/         # React Context providers
│   ├── services/               # API service layer
│   ├── utils/                  # Utilities
│   ├── App.jsx                 # Routes & providers
│   └── main.jsx                # Entry point
│
├── docs/                       # Documentation (this folder)
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── API.md
│   ├── ENVIRONMENT.md
│   ├── DEPLOYMENT.md
│   ├── DISASTER_RECOVERY.md
│   ├── ROLLBACK_STRATEGY.md
│   └── SECURITY_AUDIT_CHECKLIST.md
│
├── .env.example                # Environment template (Stage 7)
├── docker-compose.dev.yml      # Dev Docker Compose
├── docker-compose.prod.yml     # Prod Docker Compose
├── nginx.conf                  # Dev Nginx config
├── nginx.prod.conf             # Prod Nginx config
├── vite.config.js              # Vite config
├── package.json                # Frontend dependencies
└── README.md                   # This file
```

---

## 6. Development Workflow

### Code Style

- **Backend:** Black, isort, flake8 (configured in `pyproject.toml` if present)
- **Frontend:** ESLint 9 with React hooks plugin, Prettier (via Tailwind)

### Running Tests

```bash
cd backend
python manage.py check --settings=config.settings.testing
python manage.py test --settings=config.settings.testing   # 254 tests, 1 skipped
# Same suite on PostgreSQL (as CI does):
# TEST_DATABASE_URL=postgres://user:pass@localhost:5432/dbname python manage.py test --settings=config.settings.testing

cd ..
npm run lint     # 0 errors expected
npm test         # Vitest
npm run build
```

No `.env` is needed to run the tests. Results and coverage gaps: `docs/TEST_EXECUTION_REPORT.md`. If the repo sits in an iCloud-synced folder, run Python with `PYTHONPYCACHEPREFIX=/tmp/hms-pycache` or move the project out of iCloud (see `docs/OPERATIONS_RUNBOOK.md`). For a reproducible environment install `backend/requirements-lock.txt`.

### Database Migrations

```bash
# Create migration
python manage.py makemigrations <app_name>

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

### Adding a New Backend App

1. Create app: `python manage.py startapp <name>`
2. Add to `INSTALLED_APPS` in `config/settings/base.py`
3. Create models, serializers, views, URLs
4. Include URLs in `config/urls.py`
5. Run migrations

---

## 7. Deployment

See **`docs/DEPLOYMENT.md`** (Docker Compose, single server), **`docs/OPERATIONS_RUNBOOK.md`**, `docs/ROLLBACK_STRATEGY.md` and `docs/DISASTER_RECOVERY.md`. Backups: `backend/scripts/backup.py`, run from the host.

---

## 8. Security

Findings, fixes and open items: **`docs/SECURITY_AUDIT.md`**. Deployment checklist: `docs/SECURITY_AUDIT_CHECKLIST.md`.

- Hospital isolation is enforced server-side (fail-closed `HospitalScopedViewSet`, per-hospital roles), tested across 67 models.
- Staff sign-in: password, lockout, SMS OTP bound to the password step, OTP password reset.
- Every write is audited with previous values; patient documents are only served through an authenticated, audited API.
- Frontend role hiding is UI only; the server is the security boundary.
- **Open:** tokens are stored in `localStorage`; `backend/db.sqlite3` remains in git history.

---

## 9. Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/name`
3. Make changes with tests
4. Run lint/typecheck: `npm run lint` / backend linters
5. Submit PR with description

---

## 10. License

Proprietary — Internal Hospital Management System.

---

## 11. Support & Contacts

| Role | Contact |
|------|---------|
| Backend Team | backend@hospital.local |
| Frontend Team | frontend@hospital.local |
| DevOps | devops@hospital.local |
| Security | security@hospital.local |

---

*Documentation updated by audit: 2026-10-10. Previous: Stage 8 — Documentation & Project Knowledge Base (2026-10-06)*