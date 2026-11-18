# Production Readiness, Security, Testing and Release Audit — 2026-11-18 (Prompt 10)

Supersedes `RELEASE_CANDIDATE_AUDIT_2026-11-03.md` as the current status.

Revision: branch `ui/redesign-2026-10-25`, HEAD `b0846a5`, plus the uncommitted fixes listed in section C. Nothing was staged, committed, pushed, merged or deployed. Every run used synthetic data only (`seed_demo`, test fixtures, `example.test` hosts).

Starting state: `git status --short` showed only untracked files belonging to other sessions or the user (`.claude/`, `.ua/`, `reports/database-view.html`, `backend/db.sqlite3.backup-2026-11-03-before-migrate`, `backend/patients/tests 2.py`). None of them was touched.

How it was run: the project folder is iCloud-synced, so every command ran in a `git archive HEAD` scratch copy:
- The uncommitted fixes were copied in and byte-compared with `cmp`.
- Python 3.12 venv built from `backend/requirements-lock.txt`; `npm ci`.
- Throwaway PostgreSQL 17 on 127.0.0.1:55433.
- Flutter 3.47.9 with Android Studio's JBR.

The user's own PostgreSQL on port 5432 and another session's server on port 8137 were left alone.

## J. Decision: **CONDITIONALLY READY**

- **Engineering:** no Critical or High defect remains open that is known or was found in this audit. The one backend High found here (S-H1) and the mobile release-signing High (M-1) were fixed; S-H1 has a test that failed before the fix. All automated suites pass (section F).
- **Not production ready for real patients until these are met:**
  1. Staging rehearsal on a real host with its domain and CA certificate (L1).
  2. Real provider credentials exercised end to end: Twilio Verify OTP, email, STT/LLM, Google sign-in (L2).
  3. Clinical safety sign-off (L4).
  4. Penetration test and DPDP privacy assessment (L5).
  5. A mobile upload keystore before any store release (M-1 below).

Items 1–4 carry over unchanged from `KNOWN_LIMITATIONS.md` and `RELEASE_CANDIDATE_AUDIT_2026-11-03.md`. None of them can be completed by engineering alone, and none was invented or simulated here.

## A. Master table

Legend: **VERIFIED** = an automated test or a run in this audit proves it. **TESTED** = covered by automated tests, but not exercised end to end in this audit. **NOT VERIFIED** = not run. **BLOCKED** = needs something outside engineering.

| Module | Implementation | API integration (web / mobile) | Tests (backend `def test_` count; mobile tests) | Risk | Status |
|---|---|---|---|---|---|
| Auth (staff, patient, OTP, sessions) | Done | Yes / Yes | users 71 + security_tests 380 (shared); mobile auth 54 | Medium: OTP only with mocked Twilio (L2); low findings S-L1/L2/L4 | VERIFIED (mock OTP); real OTP BLOCKED |
| Patients | Done | Yes / Yes | 68; mobile patient 26 | Low | VERIFIED |
| Appointments | Done | Yes / Yes | 39 | Low | VERIFIED (booking race on PostgreSQL) |
| Queue / encounters | Done | Yes / Yes | 40 | Low | VERIFIED |
| Doctor / consultation (clinical) | Done | Yes / Yes | doctors 5, clinical 105; mobile doctor 40 | Low | VERIFIED |
| Nursing / MAR | Done | Yes / Yes | nurses 5 + `test_mar_safety`; mobile nursing 36 | Medium: awaits clinical sign-off | VERIFIED (Playwright `nurse-mar`) |
| Pharmacy | Done | Yes / Yes | 43; mobile 29 | Low (S-L3 only for legacy hospital-less medicines) | VERIFIED (dispense race on PostgreSQL) |
| Laboratory | Done | Yes / Yes | 16; mobile 30 | Low | VERIFIED (Playwright `laboratory`) |
| Billing | Done | Yes / Yes | 40; mobile 33 | Low | VERIFIED (Playwright `opd-to-bill`, `advance-payment`) |
| Emergency | Done | Yes / Yes | 12; mobile operations 55 (shared with IPD and hospital) | Low | VERIFIED (Playwright `emergency`) |
| IPD | Done | Yes / Yes | 14 + bed race tests | Low | VERIFIED (Playwright `ipd-bed`) |
| Hospital / departments / services | Done | Yes / Yes | hospital 32, hospital_services 13 | Low (S-L5) | VERIFIED (Playwright `hospital-services`, `procurement`) |
| Notifications | In-app done; SMS/WhatsApp need credentials | Yes / Yes | 40 | Medium (L2) | In-app VERIFIED; external channels BLOCKED |
| AI scribe | Done (consent, STT, LLM draft, doctor approval) | Yes / Yes | ai_scribe 40, ai_advanced 6; mobile 21; live test exists | Medium: real provider never run | TESTED with mock providers; real provider BLOCKED |
| CNN image prediction | Not built (no model, dataset or approved use) | `GET /api/ai/capabilities/` reports it blocked | — | — | BLOCKED |
| Audit / break-glass / consent | Done | Yes / partial (consent opens "not in this app version") | audit 9, consent 10 | Medium: awaits clinical sign-off | VERIFIED (Playwright `break-glass`) |

## B. Functional integration

- **Workflows:** run through the Playwright suite against `seed_demo` data, a real Django server (e2e settings) and the Vite app (section E).
- **Mobile:** every built module talks to the same `/api/v1/` routes. Its repository and screen tests run against fakes. The per-module live tests in `hospital-automate-mobile/test/live/` (patient, doctor, lab/billing, nursing/pharmacy, ops, AI scribe) were not re-run in this audit: they need a seeded server plus per-module fixture JSON, and other sessions held the usual ports. Their last passing runs are recorded in `MOBILE_APP_COMPLETE_AUDIT.md` and the session notes. Status: NOT VERIFIED in this audit.
- **Unbuilt mobile modules:** patient consent, radiology, inventory and reports open an honest "not in this app version" screen. Nothing on mobile is faked.

## C. Security

### Fixed in this audit (uncommitted)

| ID | Severity | Finding | Fix | Evidence |
|---|---|---|---|---|
| S-H1 | **High** | An Admin or Manager of hospital A could invite an email that hospital B had already invited, where the person had not yet set a password. `StaffInviteView` returned a fresh set-password link for that account to A's admin, who could then take over B's staff account and role. | `backend/users/staff_invite.py`: an account with no password and a membership at another hospital is refused (400). No link is issued. | `users.test_staff_invite.StaffInviteTests.test_pending_invite_at_another_hospital_cannot_be_taken_over`. Before the fix: `201` with `invite_url` in the body. |
| S-M1 | Medium (clinical integrity) | Any clinical staff member in the hospital and care scope could PATCH, PUT or DELETE an AI-scribe transcript, which is the input to the AI draft. They could POST forged doctor-review rows (`action=approved`, any `doctor`). Any doctor could create or DELETE another doctor's draft, including an approved one. | `backend/ai_scribe/views.py`: transcripts and reviews are read-only. Drafts keep GET and their POST workflow actions (generate, review, approve, reject, regenerate), but plain create, edit and delete answer 405. Neither the web nor the mobile client used those methods. | `security_tests.test_ai_scribe_safety.AIScribeSafetyTests.test_transcripts_reviews_and_drafts_cannot_be_written_directly`. Before the fix: `[200, 400, 204, 201, 201, 400, 204]`. After: all `405`. |
| M-1 | **High** (release) | The Android release build was signed with the public debug key (Flutter template). | `android/app/build.gradle.kts`: the release build signs with the upload key from the git-ignored `android/key.properties`. Without that file it stops with an explanation. Debug signing needs an explicit `ORG_GRADLE_PROJECT_hmsAllowDebugReleaseSigning=true` and is for local test builds only. | Release build without a key: refused ("Release signing: create android/key.properties …"). With the opt-in: `app-release.apk` built. **No keystore was created:** the hospital must create its own upload key. |
| M-2 | Medium | AI-scribe audio (`scribe-<ts>.m4a`, patient voice) stayed in the app cache after upload. | `ScribeRecorder.discard`, called in a `finally` after the upload attempt (`scribe_recorder.dart`, `scribe_screen.dart`). `record`'s `cancel()` already deletes its own file. | `test/features/ai/ai_screens_test.dart` asserts that the recording is discarded. |
| M-3 | Medium | A release build without `--dart-define=APP_ENV` silently used the development origin (`http://10.0.2.2:8000`). | `ApiConfig.resolve(releaseBuild: kReleaseMode)` refuses the development environment in release builds. | `test/core/config/api_config_test.dart` "a release build refuses the development environment". |
| M-4 | Medium | `android:allowBackup` defaulted to true. | `allowBackup="false"` and `fullBackupContent="false"`. | `aapt2 dump xmltree` of the built release APK shows both `=false`. |
| C-1 | Config | `.env.production.example` set `AI_SCRIBE_MODEL=gpt-4`, which has no JSON-schema output and would break the scribe. The LLM/STT base URL, timeout and STT keys, `ABDM_ABHA_BASE_URL` (required when ABDM is on) and `TRUSTED_PROXY_COUNT` were missing. The comment said FHIR and ABDM were "not mounted". | Corrected, with blank values only. | `config/settings/base.py:480-497`, `production.py:437-442`. |

### Open (not fixed; none Critical or High)

From the backend review:
- **S-L1:** patient password sign-in has a per-address rate limit (5/min) but no per-account lockout.
- **S-L2:** the staff lockout key is the typed identifier, so a username and an email for the same account have separate counters.
- **S-L3:** a medicine with no hospital (legacy rows; `Medicine.hospital` is nullable) skips the batch hospital check in dispensing.
- **S-L4:** account enumeration messages in registration and staff invite.
- **S-L5:** the security overview shows a staff member's sign-ins and devices from every hospital they work at.
- **S-L6:** audio upload trusts the client `Content-Type` (no magic-byte check; media is not served publicly in production).
- **S-L7:** a staff invite reactivates a legacy profile with `is_active_staff=False`. No current code sets that flag to False, so only legacy self-signup accounts are affected.
- **S-L8:** `ai/extraction-schemas/` and `ai/prompt-templates/` accept a doctor's POST and create global rows that nothing reads.

From the mobile review:
- No `FLAG_SECURE` or app-switcher protection on PHI screens.
- No explicit R8 minify, shrink or obfuscation.
- The iOS Google sign-in `Info.plist` entries were not checked.
- iOS has never been built.

**Verified secure in this audit:**
- Tenancy base (`HospitalScopedViewSet` fails closed; cross-hospital foreign keys refused on write; the every-endpoint tenancy tests pass).
- Billing advances and payments: row locks and idempotency.
- Dispensing: `select_for_update` and a guarded `F()` stock update.
- Bed allocation: row lock.
- Cookie auth: CSRF check on cookie writes, httpOnly and Secure flags.
- Refresh rotation with reuse revocation.
- Twilio webhook signature check.
- No SSRF: LLM/STT URLs come from settings only.
- No raw SQL, `extra()` or `eval` in the audited code.
- Mobile tokens are in `flutter_secure_storage` and cleared on sign-out.
- No HTTP body or header logging on mobile, and only in debug builds.
- Cleartext traffic is allowed in debug only.

**Supply chain:**
- `pip-audit -r requirements-lock.txt`: "No known vulnerabilities found".
- `npm audit --omit=dev`: 4 High, all one advisory (picomatch ReDoS, GHSA-fc5q-39xc-vjpf) reached through Vite. Vite is build-time tooling and is not shipped to browsers, so the risk is Low. The offered fix (`--force`, downgrading Vite) is breaking and was not applied.
- Secret scan of tracked files (OpenAI/AWS/Twilio/Google/GitHub key patterns and private-key headers): no matches.

**Deployment checks:** `manage.py check --deploy` under `config.settings.production` with synthetic values reports "System check identified no issues (0 silenced)". The only warning is the expected `AI_SCRIBE_API_KEY not set`.

## D. Database and PostgreSQL

- `makemigrations --check`: "No changes detected".
- All 38 migrations added since the 2026-11-03 audit were checked:
  - none contains `RemoveField`, `DeleteModel` or `RunSQL`;
  - the four data migrations reverse as no-ops;
  - the two that add uniqueness constraints (`appointments/0007`, `patients/0011`) refuse to run while duplicates exist.
- No migration was applied to any real database. The user's database file and backup were not touched.
- Full suite on PostgreSQL 17 with `REQUIRE_ROW_LOCK_TESTS=1`: 1135 tests OK, 0 skipped. The concurrency and row-lock tests ran instead of skipping.

## E. End-to-end workflows (synthetic)

- **Setup:** Playwright 1.64.1, all 15 spec files, the installed Google Chrome (`channel: chrome`, via a scratch-only config override; no browser download), e2e settings, `seed_demo`.
- **First run:** 30 passed and 2 timed out at the fixed 30 s limit (`hospital-services` ambulance/leave, `procurement` store purchase order). The machine was heavily loaded after the Android builds.
- **Re-run:** both spec files with `--timeout=90000`, 5/5 passed. The two tests took 7.8 s and 5.4 s, so the timeouts came from the environment, not a defect.

## F. Automated suites

| Suite | Command | Result |
|---|---|---|
| Django check | `manage.py check` | no issues |
| Django, SQLite (baseline, HEAD) | `manage.py test --parallel 4` | 1135 OK, 29 skipped |
| Django, PostgreSQL 17 (baseline, HEAD) | `TEST_DATABASE_URL=… REQUIRE_ROW_LOCK_TESTS=1 manage.py test` | 1135 OK, 0 skipped |
| Django targeted after fixes | `test ai_scribe ai_advanced security_tests users config` | 526 OK, 21 skipped |
| Django, SQLite (final, with fixes) | as above, plus `makemigrations --check` ("No changes detected") | **1137 OK, 29 skipped** (2 new tests) |
| Django, PostgreSQL 17 (final, with fixes) | as above, `REQUIRE_ROW_LOCK_TESTS=1` | **1137 OK, 0 skipped** |
| React unit (Vitest) | `npx vitest run` | 34 files, 125 tests passed |
| ESLint | `npx eslint .` | 0 errors, 11 warnings |
| React production build | `npm run build` | OK. Main chunk 656 kB (179 kB gzip); see G |
| Flutter analyze | `flutter analyze` | No issues found |
| Flutter tests | `flutter test` | All tests passed: 434, 51 skipped (opt-in live tests) |
| Android debug APK | `flutter build apk --debug` | built |
| Android release APK | `flutter build apk --release --dart-define=APP_ENV=production --dart-define=API_ORIGIN=https://hms.example.test` with the debug-signing opt-in | built, 64.9 MB, targetSdk 36. The first attempt was killed (font subsetter exit -9, out of memory on the 8 GB Mac); a lone retry succeeded |
| Release build without a keystore | same, no opt-in | refused by the new guard, as designed |
| `dart format --set-exit-if-changed` | as in `.github/workflows/mobile.yml` | **Fails at HEAD:** 36 files need formatting (35 predate this audit; `scribe_screen.dart` was already unformatted). The mobile CI "Check formatting" step will fail until `dart format lib test` is run and committed. Not done here, because it rewrites other sessions' files. |

## G. Performance (verified problems only)

- **Web main bundle:** the main chunk grew from 310 kB (2026-11-03) to 656 kB (179 kB gzip). The cause is `src/assets/i18n/hiPages.js` (206 kB of Hindi text), which `LanguageProvider` imports eagerly, so English users download it too. Recommendation: load the Hindi dictionary only when Hindi is selected. Not changed here, because it alters how `t()` starts up on every page.
- **Backend:** no new verified problem. The suites run quickly (1135 tests in 21 s on SQLite with 4 processes, 77 s on PostgreSQL). Load figures in `LOAD_TEST.md` were not re-measured.

## H. Deployment preparation (configuration and documentation only)

- `docker-compose.prod.yml`, `backend/entrypoint.sh` and production settings were reviewed:
  - only the web container migrates;
  - the database, Redis and Gunicorn are bound to 127.0.0.1;
  - production refuses to start without its secrets;
  - DEBUG is forced off;
  - HSTS, Secure cookies and CSP are on;
  - mock AI providers are disallowed.
- `.env.production.example` corrected (C-1).
- Mobile release:
  - the signing guard is in place (M-1);
  - the release environment guard is in place (M-3);
  - the README now describes both.
- **Mobile CI** builds only a debug APK. A release job needs the upload key as a CI secret. Not added: there is no key, and no credentials were invented.
- Nothing was purchased, created in a cloud, published or deployed.

## I. Documentation updated

- This report.
- `hospital-automate-mobile/README.md` "Known limitations": built modules, release signing, backup and audio deletion.
- `.env.production.example`.

## Not verified / blocked (summary)

**NOT VERIFIED in this audit:**
- the mobile live tests against a seeded server;
- an iOS build;
- staging on a real host;
- load test figures;
- iOS Google sign-in configuration.

**BLOCKED (outside engineering):**
- real Twilio, email, STT/LLM and Google credentials;
- the clinical safety sign-off;
- the pentest and the DPDP assessment;
- the mobile upload keystore;
- CNN (no validated model or dataset).
