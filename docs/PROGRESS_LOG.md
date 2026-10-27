# Production-readiness work — progress log

Branch: `audit/production-readiness-2026-10-24` (rollback tag `baseline-before-readiness-audit-2026-10-24` = commit e58280c).

## How to run checks here (important)

The project sits on an iCloud-synced Desktop; many `__pycache__`/log files are
"dataless" (evicted), so Python blocks reading them. Always run with an
out-of-tree bytecode cache:

```
cd backend
export PYTHONPYCACHEPREFIX=/tmp/hms-pycache
../backend_env/bin/python manage.py check --settings=config.settings.testing
../backend_env/bin/python manage.py makemigrations --check --dry-run --settings=config.settings.testing
../backend_env/bin/python -W ignore manage.py test --settings=config.settings.testing
```

Never `grep -r` into `backend/venv` (evicted files hang); use `--exclude-dir=venv`.

## Done (commit order)

1. e2d7f4d tenant isolation (25 leaking endpoints), per-hospital roles, audit service
2. 1299a51 staff OTP challenge, lockout, password reset, prod compose/Celery app
3. 7044390 AI scribe safety (mock providers gated, approval bypass closed, broken imports)
4. 9bcd125 billing service (Decimal, payments/refunds/idempotency), stock ledger
5. 0de1e42 E2E workflow fixes (queue issue 500, lab, discharge finalize)
6. bd66f90 private documents, nginx routing/CORS/media
7. 7178cf4 consent forms + record sharing, hospital directory

## Next

- Frontend: HospitalsContext/Navbar mock hospitals -> API; PatientConsent page;
  remove fake clinical data (Nurses, laboratory, Home, Queue, Appointments,
  doctors, Patients, PrescriptionContext); admin pages; reports.
- Backend: staff management API (approve pending staff, memberships).
- i18n (Hindi/English) minimal.
- Docs: docs/*.md set + final report.

## Session 1 stopped here (usage limit) — 2026-10-25

Also done after the list above: staff admin API (52ec7d8), real hospitals + consent UI
(aa1be1f), API contract fixes + notification consent/history (383a297), MAR safety fix
(4fe06b9). Uncommitted-then-committed in the final commit: Nurses page wired to API (no
mock data), laboratory page wired to the real lab workflow (removed auto "Normal" results),
demo fallbacks emptied in doctors/Appointments/Queue/Patients/Home, StaffLogin password
fallback when OTP is not configured, Vite watch/proxy config. These frontend changes were
built/linted only partially (iCloud made the machine very slow) — run `npm run build` and
`npm run lint` first, then browser-check Nurses and Laboratory with real data.

Still to do: PrescriptionContext (keeps rejected prescriptions locally), reports page,
admin Users/Roles/Departments pages (Users API exists at /api/users/), Hindi/English
i18n, docs/*.md report set + final readiness report. Recommend moving the repo out of
iCloud Drive (Desktop sync makes Python/Node hang).

## Session 2 — 2026-10-25 (completed)

All items above are done: prescriptions (cd2ce85), admin pages (c37552f), reports (dc69688),
Hindi/English (094683b), page crash fixes found by browsing the build (199310c), patient
portal hospital selection (80ee2b5), backup script verified on PostgreSQL 16 (dfe1e82),
invoice N+1 (d9010df), dependency upgrades + lock file (08301e9), `.env.example` (fd3ff71),
and the full docs set ending in `docs/FINAL_PRODUCTION_READINESS_REPORT.md`
(verdict: CONDITIONALLY_READY_AFTER_LISTED_ACTIONS). Remaining work is listed in
`docs/KNOWN_LIMITATIONS.md`. The `backend_env` venv is partly evicted by iCloud; build a
fresh venv outside iCloud from `backend/requirements-lock.txt`.
