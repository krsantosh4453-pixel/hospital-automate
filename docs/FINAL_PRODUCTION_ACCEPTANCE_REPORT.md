# Final Production Acceptance Report — 2026-11-19 (Prompt 5)

Supersedes `PRODUCTION_READINESS_AUDIT_2026-11-18.md` as the current status. That audit stays as history.

## Decision

**READY FOR STAGING ONLY. NOT READY FOR REAL PATIENTS.**

- **Engineering:** every automated suite passes, including the mobile live tests against a real server (sections 3–5), and the load and concurrency tests (section 10).
- **Real patients are blocked by items that engineering cannot finish alone (section 11):**
  1. staging rehearsal on a real host;
  2. real provider credentials (Twilio, email, STT/LLM, Google);
  3. clinical safety sign-off;
  4. penetration test and DPDP assessment;
  5. the mobile upload keystore.
- **iOS is BLOCKED.** No build has succeeded, because this Mac lacks the iOS platform component (section 7).

## Scope and method

- **Revision:** branch `ui/redesign-2026-10-25`, HEAD `7466cf7`, plus this session's uncommitted changes (listed below).
- **Not done:** nothing was staged, committed, pushed, merged or deployed.
- **Data:** synthetic only (`seed_demo`, scratch fixtures, `example.test` hosts).
- **Where it ran:** the project folder is iCloud-synced, so every suite ran in a `git archive HEAD` scratch copy with the changed files copied in. Before this report was written, `cmp` confirmed that the project files match the tested copies byte for byte.
- **Toolchain:**
  - Python 3.12 venv from `backend/requirements-lock.txt`; `npm ci`;
  - throwaway PostgreSQL 17 and Redis in the scratchpad;
  - Flutter 3.47.9; Xcode 26.6.
- **Other sessions' work:**
  - Their uncommitted files were not touched: `backend/config/settings/base.py`, `backend/users/auth_backends.py`, `backend/users/test_staff_login_identifier.py`, plus the untracked items listed in the 2026-11-18 audit.
  - Those files are **not** included in any result below.
  - The shared Android emulator was running another session's debug build, so it was not used (section 6).

Legend:
- **COMPLETE:** implemented and done.
- **VERIFIED:** proven by a run in this session.
- **TESTED:** covered by automated tests, but not exercised end to end here.
- **NOT VERIFIED:** not run.
- **BLOCKED:** needs something outside engineering.
- **NOT IMPLEMENTED:** does not exist.

### Changes made in this session (uncommitted)

| File | Change |
|---|---|
| `src/assets/i18n/loadHindiPages.js` (new) | Loads `hiPages.js` on demand and caches it; a failed load can be retried |
| `src/assets/context/LanguageProvider.jsx` | No static import of `hiPages.js`. The Hindi shell text stays bundled. Page text loads when Hindi is chosen (or was saved) |
| `src/__tests__/hindiLazyLoad.test.jsx` (new) | English never evaluates the Hindi module; switching or a saved choice loads it. This test failed against the old provider |
| `src/__tests__/hindiPages.test.jsx` | Preloads the dictionary before rendering |
| `hospital-automate-mobile/lib/**`, `test/**` (36 files) | `dart format lib test` only (layout, no code change) |
| `hospital-automate-mobile/test/live/ai_scribe_live_test.dart` | Also: uploads a real M4A header (see section 5) |
| `docs/LOAD_TEST.md`, `docs/README.md`, this report | Documentation |

## 1. Completed functionality

The module table in `PRODUCTION_READINESS_AUDIT_2026-11-18.md` (section A) is unchanged. No module was added or removed in this session.

New in this session:
- **COMPLETE / VERIFIED:** Hindi page text is lazy-loaded (section 9).
- **COMPLETE / VERIFIED:** the mobile code is formatted. `dart format --set-exit-if-changed lib test` now passes, so the mobile CI format step will pass once this is committed.
- **VERIFIED:** the mobile live tests ran against a real server for all six modules, 51 of 51 passing (section 5).

## 2. Remaining incomplete functionality

- **BLOCKED:**
  - real Twilio/email/STT/LLM/Google credentials;
  - the CNN image model (no validated model or dataset; the server reports it `blocked`, and the live test asserts this);
  - the iOS build;
  - the mobile upload keystore.
- **NOT IMPLEMENTED:**
  - a staff notification inbox in the mobile app;
  - a release (signed) mobile CI job (the CI builds a debug APK only).
- **NOT VERIFIED:**
  - the release APK started on a device;
  - sign-in from a release build against an HTTPS host (section 6);
  - Dart dependency vulnerability scan (no scanner available);
  - the backend SQLite suite (only the PostgreSQL suite was run, which is the production engine).
- See `KNOWN_LIMITATIONS.md` for the full list carried from earlier audits.

## 3. Backend verification

| Check | Command | Result |
|---|---|---|
| Django system check | `manage.py check` (testing settings) | **VERIFIED:** no issues |
| Migrations | `makemigrations --check --dry-run` | **VERIFIED:** no changes detected |
| Full suite on PostgreSQL 17 | `TEST_DATABASE_URL=… REQUIRE_ROW_LOCK_TESTS=1 manage.py test --noinput` | **VERIFIED: 1216 tests OK, 0 skipped** (83 s). The row-lock and concurrency tests ran |

## 4. Frontend verification

| Check | Result |
|---|---|
| Vitest `npx vitest run` | **VERIFIED:** 35 files, 128 tests passed (125 before + 3 new) |
| ESLint `npx eslint .` | **VERIFIED:** 0 errors, 11 warnings (the same 11 as on 2026-11-18; none in changed files) |
| Production build `npx vite build` | **VERIFIED:** OK (sizes in section 9) |
| Browser check of the production build (`vite preview`) | **VERIFIED:** see section 9 |
| `npm audit` (production and all dependencies) | **VERIFIED:** 0 vulnerabilities |

## 5. Flutter verification

| Check | Result |
|---|---|
| `dart format --set-exit-if-changed lib test` | Before: 36 files changed. After `dart format lib test`: **0 changed (VERIFIED)** |
| `flutter analyze` | **VERIFIED:** No issues found |
| `flutter test` (whole suite) | **VERIFIED:** 441 passed, 51 skipped. The skipped ones are the opt-in live tests, run separately below. That is 7 more tests than on 2026-11-18 (434), from other sessions' commits |

**Mobile live integration: VERIFIED, 51 of 51.**

How it ran:
- **Server:** a real Django server (`config.settings.e2e`, SQLite, `seed_demo`, random synthetic password) on 127.0.0.1:8163. The listening PID was confirmed to be this session's scratch venv.
- **Fixtures:** one scratch ORM script made each module's fixture JSON (`HMS_LIVE_DOCTOR_SEED`, `HMS_LIVE_AI_SEED`, `HMS_LIVE_WARD_SEED`, `HMS_LIVE_OPS_SEED`), plus the patient fixtures.
- **Code under test:** the app's real `ApiClient` and repositories. No fake repositories were used, and fake-repository tests are not counted here.

| Suite | Covers | Result |
|---|---|---|
| `patient_live_test.dart` | Email sign-in; idempotent booking; own prescriptions, labs (unreleased hidden), invoice balance 600 after a 400 payment; marking a notification read; other patients and hospitals refused; every endpoint 401 after sign-out | 6/6 |
| `doctor_live_test.dart` | Queue, vitals, notes, diagnosis, prescription, lab order on a synthetic visit; cross-patient refusal | 9/9 |
| `ai_scribe_live_test.dart` | Consent required, recording upload, queued transcription and drafting (mock STT/LLM), another doctor cannot see or approve, approval writes a clinical note | 5/5 (after the test fix below) |
| `lab_billing_live_test.dart` | Full lab workflow, invoice, payments, refund rules, role refusals | 10/10 |
| `nursing_pharmacy_live_test.dart` | Ward scope (other ward refused), vitals, nursing note, MAR dose, dispense with stock change | 6/6 |
| `ops_live_test.dart` | ER register, triage, notes, discharge; IPD bed allocation (double allocation refused), discharge rules; other hospital refused | 15/15 |

**AI scribe defect (test, not product).**
- **What failed:** the first AI scribe run got HTTP 400 on `stop_recording`.
- **Why:** since commit `51572f0` (S-L6), the server checks that uploaded bytes really are the declared audio container. The live test still uploaded the text `synthetic-audio-bytes` as `.m4a`. The server was right.
- **Fix:** the test now sends the same synthetic M4A header (`ftyp` box) that the backend tests use. The re-run passed 5/5.

## 6. Android release status

| Item | Finding | Status |
|---|---|---|
| Production API configuration | `ApiConfig.resolve`: a release build must be `APP_ENV=staging/production`, which requires `API_ORIGIN`, and it must be `https://`. Cleartext is allowed only in `src/debug/AndroidManifest.xml` | VERIFIED (code review + unit tests) |
| Signing guard | Release build with no `key.properties` and no opt-in: **refused** ("Release signing: create android/key.properties…") | VERIFIED |
| Upload keystore handling | Tested with a throwaway test keystore (`CN=THROWAWAY TEST KEY - NOT FOR DISTRIBUTION`, 2-day validity), created only in the scratchpad copy. The APK was signed by it (apksigner). The key and `key.properties` were deleted afterwards. No hospital key was generated | VERIFIED (mechanism only) |
| Signed release APK | `flutter build apk --release --dart-define=APP_ENV=production --dart-define=API_ORIGIN=https://hms.example.test`: **built, 65.0 MB**, versionCode 1 / 1.0.0, targetSdk 36. Signed v2 with the debug key via the explicit local opt-in, so **not distributable** | VERIFIED (build) |
| Manifest | `allowBackup=false`, `fullBackupContent=false`, `dataExtractionRules` excludes every domain from cloud backup and device transfer. Not debuggable, no cleartext flag | VERIFIED (aapt2 dump of the release APK) |
| Permissions | INTERNET, RECORD_AUDIO (scribe, after consent), USE_BIOMETRIC and USE_FINGERPRINT (transitive from `androidx.biometric:1.1.0`, normal-level, no prompt), DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION | VERIFIED. Declare the two biometric permissions in Play's data-safety review, or remove them with `tools:node="remove"` if unused |
| Secure storage | Tokens in `flutter_secure_storage` (Android Keystore; iOS Keychain `first_unlock_this_device`). Only the language and an install marker are in SharedPreferences | TESTED (unit tests + code review) |
| App start and sign-in (release build) | Not installed. The only emulator was running another session's debug build in the foreground, and replacing it would disrupt that work. A release build can only reach an HTTPS host, so sign-in needs staging. The same sign-in code passed in the live tests | **NOT VERIFIED** |

### Play Store release checklist

- [ ] Hospital creates its upload key. Store it outside the repo and fill `android/key.properties` (git-ignored). Enrol in Play App Signing.
- [ ] Set `versionCode` / `versionName` in `pubspec.yaml` (currently 1 / 1.0.0); increase it for every upload.
- [ ] Build an app bundle: `flutter build appbundle --release --obfuscate --split-debug-info=<private dir> --dart-define=APP_ENV=production --dart-define=API_ORIGIN=https://<real host>`. Keep the symbols private.
- [ ] Remove the leftover template comment `TODO: Specify your own unique Application ID` in `android/app/build.gradle.kts`. Confirm `com.hospitalautomate.hms_mobile` is final; it cannot change after the first upload.
- [ ] Install the signed build on a real device (and a low-RAM one). Check start, sign-in against staging, scribe recording consent, sign-out, and that reinstall or backup restore does not carry tokens.
- [ ] Play Console:
  - data-safety form (health data, audio, biometric permissions);
  - privacy policy URL;
  - content rating;
  - target audience;
  - health apps declaration;
  - test track before production.
- [ ] Optional: add a release CI job that reads the upload key from CI secrets.

## 7. iOS release status: **BLOCKED (not production ready)**

| Item | Finding |
|---|---|
| Build attempt | `flutter build ios --release --no-codesign …`: the Swift Package Manager dependencies resolved (GoogleSignIn 10.1.0, AppAuth 3.0.0 and others). Then the build **failed**: `xcodebuild: error: … Found no destinations for the scheme 'Runner' and action build.` Xcode 26.6 has the iOS 26.5 SDK, but not the iOS platform component (`xcrun simctl list runtimes` is empty) |
| Fix (user action) | `xcodebuild -downloadPlatform iOS` (several GB; about 20 GB is free on this Mac), then re-run the build. CocoaPods is not needed: the project uses Swift Package Manager |
| Signing | `CODE_SIGN_STYLE = Automatic` with no `DEVELOPMENT_TEAM`. Needs an Apple Developer account, a team, an App ID `com.hospitalautomate.hmsMobile` and provisioning. **BLOCKED** |
| Google Sign-In | `Info.plist` reads `GIDClientID` and the reversed-client-id URL scheme from `ios/Flutter/GoogleSignIn.xcconfig` (git-ignored, optional include). Only the `.example` exists, so the values are empty, and per the code the app then hides Google sign-in on iOS. Needs this deployment's iOS OAuth client. **BLOCKED** |
| Permissions and privacy text | `NSMicrophoneUsageDescription` present and accurate (scribe records only after patient consent). No other privacy-sensitive keys. A privacy manifest (`PrivacyInfo.xcprivacy`) for the app target was not found. **NOT VERIFIED** whether the SDKs' own manifests cover the required-reason APIs |
| Network | ATS allows only `NSAllowsLocalNetworking` (no arbitrary loads). HTTPS is enforced in code for staging and production |
| Secure storage | Keychain, `first_unlock_this_device` (not migrated to other devices) |
| Deployment target | iOS 15.0 |
| Device testing | **NOT VERIFIED** (no build) |

## 8. Security status

| Check | Result |
|---|---|
| `pip-audit -r backend/requirements-lock.txt` | **VERIFIED:** no known vulnerabilities |
| `npm audit` | **VERIFIED:** 0 vulnerabilities |
| gitleaks 8 over git history (209 commits) and the working tree | 25 history hits and 22 tree hits, all rule `generic-api-key`. Each was reviewed and **all are false positives**: synthetic test passwords and idempotency-key constants in test files, the phrase `getAllRows(_api, …)` in Dart, and a docs table row. No real secret was found |
| Tracked secret files | **VERIFIED:** none. Only `.env.example` and `.env.production.example` are tracked; `key.properties`, `*.jks` and `*.keystore` are git-ignored |
| Dart dependencies | No vulnerability scanner available: **NOT VERIFIED**. `flutter pub outdated` lists 12 locked upgrades |
| Earlier findings | S-H1, M-1 and S-L1…S-L8 are fixed at HEAD. The live AI scribe run confirmed S-L6 (audio content check) works against a real server |
| Penetration test, DPDP assessment | **BLOCKED** (external) |

**New finding R-1 (Medium, availability):**
- **What happens:** in the production configuration, DRF throttle counters, sessions and the default cache all use Redis through `django_redis` with no fail-open setting. While Redis was stopped, **every API request returned HTTP 500**. Service recovered by itself on the first request after Redis returned. No data was lost or corrupted.
- **Options (your decision; nothing was changed):**
  - (a) accept it, with Redis restart policy and alerting (as now);
  - (b) let throttles fail open when Redis is down (`DJANGO_REDIS_IGNORE_EXCEPTIONS`). This trades away rate limiting during an outage, which also guards sign-in and OTP.
- **Related:** during a database outage the API returns 500, not 503. The health endpoint's behaviour during an outage was not checked.

## 9. Performance comparison (web bundle)

| | Before (HEAD `7466cf7`) | After | Change |
|---|---|---|---|
| Main chunk `index-*.js` | 656.48 kB (178.76 kB gzip) | **462.51 kB (131.26 kB gzip)** | −194 kB (−29.5 %); gzip −47.5 kB (−26.6 %) |
| Hindi page dictionary | inside the main chunk | separate `hiPages-*.js`, 194.38 kB (47.72 kB gzip), fetched only for Hindi | — |

The browser check below used the production build through `vite preview`.

**English user:**
- 1 script loaded;
- no `hiPages` request;
- `lang="en"`.

**Switching to हिंदी:**
- `hiPages-DqNTUwXj.js` was fetched once (49,181 bytes transferred);
- the page title, buttons and navigation turned Hindi;
- `lang="hi"`.

**Reload with Hindi saved:** Hindi is restored, and the chunk is fetched once.

**Switching back to English:** English text returns, and `hms_language=en` is saved.

**Console:** the only errors were 401s from signed-out API calls, which are expected.

**Unchanged by design:**
- `LanguageProvider` API (`language`, `setLanguage`, `t`);
- `t()` with `{placeholders}`;
- English fallback for unknown text;
- shell text wins over page text.

While the page dictionary downloads, shell text is Hindi and page text shows in English for a moment.

**Still open:** the main chunk is still larger than the 310 kB measured on 2026-11-03. The rest of the growth was not investigated.

## 10. Load-test results

**Setup:**
- **Server:** gunicorn 26.2.0, 4 sync workers (as in `docker-compose.prod.yml`).
- **Database:** PostgreSQL 17 (`CONN_MAX_AGE=60`).
- **Cache:** Redis with production-style `django_redis` settings.
- **Hardware:** the same 8 GB Mac as 2026-11-08.
- **Data:** `seed_demo`, 200 synthetic patients and 30 synthetic portal logins.
- **Throttles:** off for capacity runs and on for the outage runs.

| Scenario | Requests | Throughput | Errors | p50 / p95 / p99 / max (ms) |
|---|---|---|---|---|
| LOAD_TEST.md staff mix (80 % reads: patient search, appointments, queue, pharmacy stock and queue, bills, patient list; 20 % registrations), 50 clients, 60 s | 9,975 (7,989 × 200, 1,986 × 201) | **166.2 req/s** | **0** | 302 / 372 / 441 / 622 |
| 2026-11-08 baseline, same mix | 9,716 | 162 req/s | 0 | 301 / 368 / 497 / 636 |
| 30 portal patients, own records (me, appointments, prescriptions, invoices, labs, notifications, queue, documents), no think time, 30 s | 18,164 | 605.5 req/s | 0 | 44 / 87 / 98 / 150 |
| Same, 1 s think time | 900 | 30 req/s | 0 | 11 / 23 / 33 / 46 |

**Registration integrity:** 4,577 patient-hospital rows, 4,577 distinct UHIDs.

**A harness artefact, not a server error:** an earlier 50-client run showed 421 × 409. The cause was the harness: it seeded its random phone numbers by worker index, so it re-sent the numbers from a 10 s smoke run. The server's duplicate-mobile check refused them correctly. The table shows the re-run with unique seeds.

### Concurrency (all requests released together by a barrier)

| Race | Attempts | Outcome | Database after |
|---|---|---|---|
| Appointment: 20 patients book the same doctor, day and slot (capacity 1) | 20 | 1 × 201, 19 × 409 "This slot was just booked" | 1 appointment |
| Pharmacy: 12 prescriptions dispensed at once against 5 units | 12 | 5 × 201, 7 × 400 "Insufficient stock … Available: 0" | quantity 0; ledger IN 5 / OUT 5; 5 prescriptions dispensed |
| Bed: 10 admissions allocate the same free bed (nurse logins) | 10 | 1 × 201, 9 × 400 "not available (status: Occupied)" | 1 active allocation |

In an earlier bed run, half the logins were `demo.manager`. Those got 403, because the hospital manager role may not allocate beds. The other attempts still produced exactly one allocation.

### Interruption and recovery

The probe was one staff client polling every 0.25 s for 40–45 s, with the service stopped at about 10 s and restarted at about 25 s.

| Outage | During | After restart |
|---|---|---|
| Redis (production throttles on) | 58 / 58 × HTTP 500 | 200 from the first request; no restart of gunicorn |
| PostgreSQL (`pg_ctl stop -m fast`) | 58 / 58 × HTTP 500 | 200 from the first request; no restart of gunicorn |

### Not covered

These still need the staging host:
- nginx + TLS;
- a 100k-patient database;
- reports and AI under load;
- a 30-minute soak.

## 11. External dependencies (all BLOCKED for engineering)

| Dependency | Needed for |
|---|---|
| Staging host with domain and CA certificate | Staging rehearsal (`STAGING_DEPLOYMENT.md`); release-build sign-in on a device |
| Twilio Verify / SMS, email provider | Real OTP and notifications |
| STT and LLM provider credentials | AI scribe beyond the development mocks |
| Google OAuth clients (web, Android, iOS) | Google sign-in; iOS `GoogleSignIn.xcconfig` |
| Hospital's Android upload key and Play Console account | Distributable Android build |
| Apple Developer team, App ID, provisioning; iOS platform on this Mac | Any iOS build or TestFlight |
| Clinical safety officer | Clinical safety sign-off (`CLINICAL_SAFETY_REVIEW_PACK.md`) |
| Pentest vendor, DPDP assessor | Security and privacy sign-off |
| Validated CNN model and dataset | Image prediction (currently blocked by design) |

## 12. Final production readiness decision

| Target | Decision |
|---|---|
| Real patients (production) | **NOT READY:** blocked by section 11 (staging rehearsal, real providers, clinical sign-off, pentest/DPDP, upload key) |
| Staging with synthetic data | **READY:** all automated suites, live mobile tests, load and concurrency tests pass. Decide R-1 (Redis fail-closed) before go-live |
| Android store release | **BLOCKED:** needs the hospital's upload key, a device test of the signed build against staging, and Play Console setup (checklist in section 6) |
| iOS release | **BLOCKED:** no successful build (missing iOS platform), no signing team, no iOS Google client, no device test |

**Before committing:** the 36 formatted Dart files and the Hindi lazy-loading change are uncommitted. They should be committed together with the mobile CI format step in mind. Another session's uncommitted auth change (`base.py`, `auth_backends.py`) is separate and was not tested here.
