# Load test and rate limits (P1-08)

## Result (2026-11-08)

| | |
|---|---|
| Stack | gunicorn 26.2, 4 sync workers, PostgreSQL 16 (local, throwaway), Django settings without throttles |
| Data | `seed_demo` plus earlier synthetic records (about 80 patients, then +1,979 created by the test) |
| Load | 50 clients sending back to back for 60 s: 80 % reads (patient search, appointments, queue, pharmacy queue, stock, bills, patient list) and 20 % patient registrations |
| Throughput | **9,716 requests, 162 requests per second** |
| Errors | **0** (7,737 × 200, 1,979 × 201) |
| Latency | p50 **301 ms**, p95 **368 ms**, p99 **497 ms**, max 636 ms |

**How to read it:**
- The clients have no "think time". A person at a counter makes about one request every 5–10 seconds, so this machine has room for several hundred staff working at once.
- Registrations stayed correct under load: every UHID was unique (the sequence row lock, P0 work).

**Not covered yet** (repeat on the staging host):
- the real nginx + TLS path
- a larger database: 100,000+ patients and a year of visits, for index and query plans
- reports and AI endpoints
- a 30-minute soak for memory and connection leaks

## Rate limits after this test (production)

| Limit | Value | Why |
|---|---|---|
| Per signed-in user (DRF `user`) | **3,000 / hour** (was 1,000) | A page load costs 5–13 API calls, so a busy pharmacy or front desk can pass 1,000 in normal work |
| Anonymous (DRF `anon`) | 100 / hour per IP | Unchanged; only sign-in and public pages are anonymous |
| Patient phone OTP, family-access OTP | **5 / min per phone + 60 / min per IP** (was 5 / min per IP) | Indian mobile carriers put many users behind one IP (carrier-grade NAT) |
| Patient email OTP | **5 / min per email + 60 / min per IP** | Same reason |
| Staff sign-in | 5 / min per account + 60 / min per IP | Unchanged (already NAT-safe) |
| Twilio status callback | not throttled | Signed by Twilio; one call per message |

## Repeating the test

Use a throwaway database only, never real patient data:
1. Seed it with `manage.py seed_demo --password <synthetic>`.
2. Start gunicorn as in `docker-compose.prod.yml`.
3. Run 50 threads issuing the same mix for 60 s against it, and record the request count, status codes and p50/p95/p99.

Throttles must be off for a capacity test (the e2e settings do that). With them on, you measure the limits instead of the server.
