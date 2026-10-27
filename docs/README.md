# Hospital Management System — Documentation Index

This directory contains the complete documentation for the Hospital Management System (HMS).

## Documentation Overview

| Document | Purpose |
|----------|---------|
| [Environment](ENVIRONMENT.md) | Environment variables, configuration, and secrets management for all deployment environments |
| [Architecture](ARCHITECTURE.md) | System architecture: frontend, backend, database, authentication, authorization, and deployment |
| [Database](DATABASE.md) | Database schema: models, relationships, indexes, and constraints |
| [API](API.md) | Complete API reference: endpoints, authentication, permissions, request/response schemas |
| [Roles & Permissions](ROLES_AND_PERMISSIONS.md) | Role definitions, permission classes, frontend/backend authorization separation |
| [User Guide](USER_GUIDE.md) | Role-based user workflows: login, navigation, available modules, limitations |
| [Module Status](MODULE_STATUS.md) | Module completion matrix: frontend, backend, API, database, integration, testing status |
| [AI/ML Status](AI_ML_STATUS.md) | AI/ML implementation audit: AI Scribe, STT, LLM, RAG, embeddings, vector DB status |
| [Testing](TESTING.md) | Testing system: backend, frontend, E2E, build, lint, CI/CD commands and current state |
| [Security](SECURITY.md) | Security architecture: auth, authorization, data protection, audit logging, known limitations |
| [Deployment](DEPLOYMENT.md) | Production deployment: Docker, Nginx, PostgreSQL, SSL, environment configuration |
| [Disaster Recovery](DISASTER_RECOVERY.md) | Backup, restore, and disaster recovery procedures |
| [Rollback Strategy](ROLLBACK_STRATEGY.md) | Deployment rollback procedures and criteria |

## Quick Start

### For Developers
1. Read [Architecture](ARCHITECTURE.md) to understand the system structure
2. Check [Environment](ENVIRONMENT.md) for local development setup
3. Review [API](API.md) for endpoint specifications
4. Run tests per [Testing](TESTING.md)

### For Operations
1. Review [Deployment](DEPLOYMENT.md) for production deployment steps
2. Check [Environment](ENVIRONMENT.md) for production variables
3. Read [Security](SECURITY.md) for security posture
4. Review [Disaster Recovery](DISASTER_RECOVERY.md) and [Rollback Strategy](ROLLBACK_STRATEGY.md)

### For Product/Clinical Teams
1. Read [User Guide](USER_GUIDE.md) for role-based workflows
2. Check [Module Status](MODULE_STATUS.md) for feature availability
3. Review [AI/ML Status](AI_ML_STATUS.md) for AI capabilities

## Version Information

- **Backend**: Django 5.2 + Django REST Framework 3.15
- **Frontend**: React 19 + Vite + Tailwind CSS 4
- **Database**: PostgreSQL (production), SQLite (development)
- **Authentication**: JWT (djangorestframework-simplejwt)
- **API Documentation**: drf-spectacular (OpenAPI 3)

## Repository Structure

```
hospital-automate/
├── backend/           # Django application
│   ├── config/        # Project settings, URLs, health checks
│   ├── users/         # Authentication, authorization, staff/patient management
│   ├── patients/      # Patient management
│   ├── doctors/       # Doctor management
│   ├── appointments/  # Appointment scheduling
│   ├── nurses/        # Nursing workflows, vitals, MAR, care tasks
│   ├── pharmacy/      # Medicine inventory, sales
│   ├── laboratory/    # Lab tests, samples, results
│   ├── clinical/      # Clinical notes, prescriptions, diagnoses
│   ├── encounters/    # Visits, queue tokens, doctor schedules
│   ├── hospital/      # Hospital, department, ward, bed management
│   ├── billing/       # Invoices, payments, insurance claims
│   ├── bloodbank/     # Blood inventory, requests, transactions
│   ├── ipd/           # Admissions, bed allocations, discharge
│   ├── emergency/     # Emergency visits, triage, orders
│   ├── procurement/   # Purchase orders, goods receipts, stock
│   ├── ai_scribe/     # AI Medical Scribe (STT + LLM)
│   ├── audit/         # Audit logging
│   ├── notifications/ # Notification system
│   ├── reports/       # Reports (stubbed)
│   └── ...            # Additional apps (fhir, hl7, abdm, consent, documents - unmounted)
├── src/               # React frontend
│   ├── pages/         # Page components (role-based)
│   ├── components/    # Reusable components (Sidebar, Navbar, etc.)
│   ├── services/      # API service layer
│   ├── assets/context/# React Context providers (Auth, Role, etc.)
│   └── layouts/       # Layout components
└── docs/              # This documentation
```

## Status Legend

Throughout documentation, components are labeled with status indicators:

| Status | Meaning |
|--------|---------|
| **ACTIVE** | Fully implemented and mounted |
| **PARTIAL** | Partially implemented |
| **MOCK** | Uses mock/demo data, not production-ready |
| **UNMOUNTED** | Code exists but not wired in URLs/router |
| **STUB** | Minimal implementation, placeholder |
| **PLANNED** | Designed but not implemented |
| **BROKEN** | Known non-functional |
| **NOT VERIFIED** | Status unknown, needs investigation |

## Contributing to Documentation

- Documentation must describe the **actual** repository state
- If something is unknown: write `UNKNOWN / NOT VERIFIED`
- If something is mock: write `MOCK`
- If something is unmounted: write `UNMOUNTED`
- If something is planned: write `PLANNED`
- If something is broken: write `BROKEN`
- Accuracy > completeness — never invent information

---

*Last updated: Stage 8 Documentation Completion*