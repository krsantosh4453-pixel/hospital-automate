# Hospital Management System (HMS)

A comprehensive hospital management system built with React (Vite) frontend and Django REST Framework backend, designed for multi-hospital deployments with strict data isolation.

**Current Status (2026-10-10): Development — Not Production Ready**

---

## 1. Project Overview

### What the Project Does

The Hospital Management System provides a digital platform for hospital operations. **Status varies significantly by module** — see Module Status table below for actual implementation state.

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, Vite 8, React Router 7, Tailwind CSS 4 |
| **Backend** | Django 5.2, Django REST Framework 3.15 |
| **Database** | PostgreSQL 16 (production), SQLite (development) |
| **Cache/Queue** | Redis 7, Celery 5 |
| **Authentication** | JWT (SimpleJWT), Google OAuth 2.0, Patient OTP (SMS/Email) |
| **API Documentation** | DRF Spectacular (OpenAPI 3), Swagger UI, ReDoc |
| **Containerization** | Docker, Docker Compose |
| **Reverse Proxy** | Nginx |
| **Monitoring** | Health checks, structured JSON logging, Sentry (optional) |

### API Architecture

- **RESTful API** with JSON request/response
- **JWT Authentication** — Access tokens (15 min), Refresh tokens (7 days, rotating)
- **Hospital-scoped endpoints** — All data isolated by `hospital` query parameter or header
- **ViewSets + Routers** — Standard DRF patterns for CRUD + custom actions
- **OpenAPI 3 Schema** — Auto-generated at `/api/schema/`, Swagger at `/api/docs/`, ReDoc at `/api/redoc/`

### Authentication Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Authentication Flow                       │
├─────────────────────────────────────────────────────────────────┤
│  Staff Login          │  Patient Login                          │
│  ─────────────        │  ─────────────                          │
│  POST /api/auth/      │  1. Request OTP (phone/email)           │
│    staff/login/       │     POST /api/auth/patient/otp/request/ │
│  → {access, refresh,  │  2. Verify OTP                          │
│    user, roles,       │     POST /api/auth/patient/otp/verify/  │
│    hospitals}         │  → {access, refresh, patient}           │
│                       │                                         │
│  Google OAuth         │  Patient Email/Password                 │
│  POST /api/auth/      │  POST /api/auth/patient/login/          │
│    google/            │  → {access, refresh, patient}           │
└─────────────────────────────────────────────────────────────────┘
```

- **Staff** — Username/password + Google OAuth, returns roles and hospital memberships
- **Patients** — OTP (SMS/Email), email/password, or token login
- **Hospital Isolation** — Staff must have `StaffHospitalMembership` for target hospital

### Major Hospital Modules — Actual Implementation Status

| Module | Backend App | Frontend Pages | Status | Notes |
|--------|-------------|----------------|--------|-------|
| **Core Auth** | users, hospital | StaffLogin, HospitalSelection | ✅ ACTIVE | JWT, RBAC, hospital isolation implemented |
| **Patients** | patients | Patients, PatientDashboard, Patient* | ✅ ACTIVE | Full CRUD, hospital-scoped |
| **Doctors** | doctors | Doctors | ✅ ACTIVE | Full CRUD, hospital-scoped |
| **Appointments** | appointments | Appointments | ✅ ACTIVE | Full CRUD, hospital-scoped |
| **Queue/Encounters** | encounters | Queue, Consultation, QueueToken | ✅ ACTIVE | Queue token issuance, state transitions |
| **Clinical** | clinical | Prescription, Vitals, Diagnoses, Notes | ✅ ACTIVE | Visit-scoped clinical records |
| **IPD** | ipd | IPD, Admissions, Beds, Discharge | ✅ ACTIVE | Admissions, bed allocation, discharge workflow |
| **Emergency** | emergency | Emergency | ✅ ACTIVE | Triage, visits, orders, medications |
| **Pharmacy** | pharmacy, procurement | Pharmacy, Inventory, Compounder | ✅ ACTIVE | Inventory, sales, procurement (PO/GRN) |
| **Laboratory** | laboratory | Laboratory | ✅ ACTIVE | Test ordering, results, status workflow |
| **Blood Bank** | bloodbank | BloodBank | ✅ ACTIVE | Inventory, requests, transactions (hospital FK added) |
| **Billing** | billing | Billing, Reports | ✅ ACTIVE | Invoices, payments, insurance claims |
| **Nursing** | nurses | Nurses | ⚠️ PARTIAL | Nurse CRUD ✅; Clinical workflows (vitals, assessments, MAR, orders) use **MOCK DATA** — not connected to clinical visit APIs |
| **AI Scribe** | ai_scribe | AIScribe | ⚠️ MOCK/DEMO | Full pipeline structure exists but STT/LLM providers are **development mocks only** — no production API keys configured |
| **Notifications** | notifications | (Integrated) | ⚠️ BACKEND ONLY | In-app Notification model exists; SMS/WhatsApp/Email providers NOT IMPLEMENTED; no event-driven notifications |
| **Audit** | audit | (Backend only) | ✅ ACTIVE | Audit logs, AI interactions — read-only API |
| **Reports** | reports | Reports | ⚠️ STUB | Backend stubbed, no real report generation; frontend UI only |
| **Admin** | (Django admin + users) | AdminDashboard, Users, Roles, Hospitals, Departments, Permissions | ✅ ACTIVE | Full admin UI |
| **FHIR** | fhir | — | ❌ UNMOUNTED | App exists, routes commented in urls.py |
| **HL7** | hl7 | — | ❌ UNMOUNTED | App exists, routes commented in urls.py |
| **ABDM** | abdm | — | ❌ UNMOUNTED | App exists, routes commented in urls.py |
| **Consent** | consent | Consent (UI) | ❌ UNMOUNTED | UI exists, backend unmounted |
| **Documents** | documents | Documents (UI) | ❌ UNMOUNTED | UI exists, backend unmounted |

**Status Legend:**
- ✅ **ACTIVE** — Fully implemented, mounted, tested
- ⚠️ **PARTIAL** — Partially implemented, some endpoints/models missing
- ⚠️ **MOCK/DEMO** — Uses mock/demo data, not production-ready
- ⚠️ **BACKEND ONLY** — Backend implemented, no frontend integration
- ⚠️ **STUB** — Minimal implementation, placeholder only
- ❌ **UNMOUNTED** — Code exists but not included in URL routing
- ❌ **NOT IMPLEMENTED** — No code exists

## 2. AI/ML Features — Current Status

> **IMPORTANT:** The audit reports AI/ML at 22% completion. The following clarifies what exists vs. what is claimed.

### ✅ IMPLEMENTED: AI Medical Scribe (Mock/Demo Pipeline)

The AI Scribe module exists as a **complete mock/demo pipeline** with:
- Database models: `ConsultationSession`, `ConversationTranscript`, `AIConsultationDraft`, `DoctorReview`, `ClinicalExtractionSchema`, `AIPromptTemplate`
- REST API endpoints at `/api/ai/` (consultation-sessions, transcripts, drafts, reviews, schemas, prompts)
- Frontend page: `AIScribe.jsx` with recording UI
- Audio upload → Transcript → AI Draft → Doctor Review → Clinical Note workflow
- **Provider abstraction** for STT (Whisper, Google, Azure) and LLM (OpenAI, Anthropic, Local)
- **Prompt versioning** and schema validation for reproducibility

**However:** The AI provider integration is **mocked**. No actual OpenAI/Anthropic API calls are made in the current codebase. The `AI_SCRIBE_API_KEY` environment variable is defined but not consumed by working provider code.

### ❌ NOT IMPLEMENTED

| Feature | Status | Notes |
|---------|--------|-------|
| **CNN Imaging AI** | Not present | No computer vision models, no DICOM handling, no imaging endpoints |
| **RAG/Embeddings/Vector DB** | Not present | No pgvector, no embedding generation, no retrieval pipeline |
| **Production AI Scribe** | Mock only | Pipeline structure exists but providers are stubbed |
| **ML Forecasting** | Partial | `backend/reports/forecasting.py` exists but not wired to API |

### 📋 Documented in Settings (Base Config)

The following AI-related settings exist in `config/settings/base.py` but are **not fully implemented**:

```python
AI_SCRIBE_ENABLED = True
AI_SCRIBE_PROVIDER = 'openai'  # openai, anthropic, local
AI_SCRIBE_MODEL = 'gpt-4'
AI_SCRIBE_MAX_TOKENS = 4000
AI_SCRIBE_TEMPERATURE = 0.1

FHIR_ENABLED = True        # Not implemented (URLs commented)
HL7_ENABLED = True         # Not implemented (URLs commented)
ABDM_ENABLED = True        # Not implemented (URLs commented)
```

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

```bash
# Configure production environment
cp .env.example .env
# Edit .env with production values (SECRETS!)

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

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
VITE_API_BASE_URL=http://localhost:8000/api
AI_SCRIBE_ENABLED=False  # Disable if no API key
```

**Production requires:** `DJANGO_SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `EMAIL_*`, `SENTRY_DSN`, `BACKUP_ENCRYPTION_KEY`.

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
# Backend
cd backend
python manage.py test

# Frontend
npm test  # if configured
```

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

See **`docs/DEPLOYMENT.md`** for complete deployment guide covering:
- Docker Compose (single server)
- Kubernetes
- Cloud providers (AWS/GCP/Azure)
- Database setup, SSL, Nginx, monitoring

---

## 8. Security

See **`docs/SECURITY_AUDIT_CHECKLIST.md`** for production security checklist.

Key security features implemented:
- JWT with rotating refresh tokens, blacklisting
- Hospital-level data isolation (enforced in ViewSets via HospitalScopedViewSet)
- Role-based access control (RBAC) with 11 staff roles + Patient
- Rate limiting (DRF throttling + custom middleware on auth endpoints)
- Audit logging on all data modifications (AuditLog, AIInteraction models)
- Secure headers (HSTS, CSP, X-Frame-Options, etc.) in production settings
- File upload validation, private media protection (documents app)

**Known Security Gaps:**
- Password reset endpoints NOT IMPLEMENTED (throttle configured but no views)
- Account lockout after failed login attempts NOT IMPLEMENTED
- Frontend role hiding is UI-only — NOT a security boundary
- FHIR/HL7/ABDM endpoints unmounted but config flags enabled
- Some serializers may still allow mass assignment (verify with SECURITY_FINDINGS.md)

**Production Deployment Requires:**
- `DEBUG=False`, strong `DJANGO_SECRET_KEY`, `JWT_SECRET_KEY`
- PostgreSQL with SSL, Redis with TLS
- HTTPS enforcement, HSTS, secure cookies
- `python manage.py check --deploy` passes with 0 issues

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