# Load test and rate limits (P1-08)

## Re-run (2026-11-19, final acceptance)

Same machine, gunicorn 26.2.0 with 4 sync workers, throwaway PostgreSQL 17, a local Redis configured like production (`django_redis`, no fail-open), `seed_demo` plus 200 synthetic patients and 30 synthetic portal logins. Details and raw figures: `docs/FINAL_PRODUCTION_ACCEPTANCE_REPORT.md`, section 10.

| Scenario | Result |
|---|---|
| Staff mix as below, 50 clients, 60 s, throttles off | **9,975 requests, 166 req/s, 0 errors**; p50 302 ms, p95 372 ms, p99 441 ms, max 622 ms. 1,986 registrations, every UHID unique |
| 30 portal patients, no think time, 30 s | 18,164 requests, 605 req/s, 0 errors; p95 87 ms |
| 30 portal patients, 1 s think time, 30 s | 900 requests, 0 errors; p95 23 ms |
| 20 patients book the same slot at once | 1 booked (201), 19 refused (409 "slot was just booked"); 1 row |
| 12 dispenses at once against 5 units | 5 dispensed, 7 refused ("Insufficient stock"); stock 0; ledger IN 5 / OUT 5 |
| 10 bed allocations at once for one bed | 1 allocated, 9 refused (400); one active allocation |
| Redis stopped for 15 s (production throttles on) | **every API request returned 500** while Redis was down; recovered by itself on the first request after Redis returned |
| PostgreSQL stopped for 15 s | every API request returned 500; recovered by itself |

Redis is therefore a hard dependency for the whole API in production, not only for caching (finding R-1 in the acceptance report). Keep its restart policy and monitoring in place until that is decided.


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
