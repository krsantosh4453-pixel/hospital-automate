# Mobile App Complete Audit: Hospital Healthcare Automation

| | |
|---|---|
| Audit date | 2026-11-10 |
| Branch | `ui/redesign-2026-10-25` (HEAD `cf06720`) |
| Scope | Flutter app in `mobile/` only. The React web app (`src/`) and Django backend (`backend/`) are referenced only where the mobile app depends on them. |
| Method | Read every mobile source, test and platform file; ran the analyzer, the tests and an Android build; read backend routing and auth from git. No source code changed. |
| Audit type | Read-only. The only file created is this report. |

---

## Section 1: Executive Summary

| Item | Finding |
|---|---|
| Project | `hms_mobile` ("Hospital Management mobile app"), `mobile/` |
| Framework | Flutter 3.47.9 (stable), Dart 3.13.7 |
| Current status | **Foundation scaffold only.** The app has one diagnostic screen that calls the backend's public `GET /health/` and shows whether the backend answered. There is no login, no navigation, and no hospital feature of any kind. |
| Size | 5 Dart source files (196 lines) and 3 test files (159 lines) |
| Overall completion | **≈ 2.5 %** (weighting in Section 17) |
| Functional (user-facing) completion | **0 %**. None of the 103 checklist features exist in the app. |
| Production readiness | **Not ready.** Release builds are signed with the debug key, there is no HTTPS or production configuration, and the app source is not under version control (see C-1). |

The audit-critical finding is about the repository, not the features: **`mobile/lib/` is git-ignored** by the root `.gitignore` (line 39, a Python `lib/` rule). The mobile scaffold is staged in the index but not committed, and `lib/` is not in the stage. Committing as-is would store the platform shells and tests but none of the app code. The tests would then fail on a fresh clone.

---

## Section 2: Technology Stack

All of these were verified from files or from command output.

| Area | Technology / version | Evidence |
|---|---|---|
| Framework | Flutter 3.47.9 stable, framework rev `c197ca5199` | `flutter --version`, `mobile/.metadata` |
| Language | Dart 3.13.7; SDK constraint `^3.13.7` | `flutter --version`, `mobile/pubspec.yaml` |
| HTTP client | `dio` ^5.11.1 | `pubspec.yaml` |
| Icons | `cupertino_icons` 1.0.9 (2.0.0 available) | `flutter pub outdated` |
| Lints | `flutter_lints` ^6.0.0 | `pubspec.yaml`, `analysis_options.yaml` |
| State management | None. Uses `StatefulWidget` + `FutureBuilder` only | `lib/features/backend_status/backend_status_screen.dart` |
| Navigation | None. A single `home:` widget, no routes | `lib/app.dart` |
| Local storage / DB | None | no storage packages in `pubspec.yaml` |
| Secure storage | None | same |
| Localization | None (no `flutter_localizations`, no ARB files) | same |
| Android build | AGP 9.1.0, Kotlin plugin 2.4.0, Gradle 9.3.1, Java/JVM target 17, compile/min/target SDK = Flutter defaults | `android/settings.gradle.kts`, `android/app/build.gradle.kts`, `gradle-wrapper.properties` |
| Android toolchain on host | SDK 36.1.0, platform android-36, Android Studio JBR (OpenJDK 25) | `flutter doctor` |
| iOS project | Deployment target 15.0, bundle id `com.hospitalautomate.hmsMobile`, automatic signing, no team set, UIScene lifecycle | `ios/Runner.xcodeproj/project.pbxproj`, `ios/Runner/Info.plist` |
| iOS toolchain on host | Xcode 26.6 present; **CocoaPods not installed; simulator runtimes unavailable** | `flutter doctor` |
| Architecture | Feature-first folders: `lib/core/config`, `lib/core/network`, `lib/features/backend_status` | directory listing |
| Backend target | Django REST at `<origin>/api/v1` (URL built in code but never called); health at `<origin>/health/` | `lib/core/config/api_config.dart` |
| Environment config | `--dart-define=API_ORIGIN=…`, validated as http(s). Defaults: `http://10.0.2.2:8000` (Android), `http://localhost:8000` (iOS). No flavors, no staging/production profiles | `api_config.dart` |
| Testing | `flutter_test`: 3 files, 12 tests | `mobile/test/` |
| CI | **None for mobile.** `.github/workflows/ci.yml` has no Flutter steps | `git grep flutter .github` → no match |

---

## Section 3: Complete Module-Wise Status

Feature counts follow the checklist in the audit brief. A feature is counted once, in the module where it first appears. "Completed" means a working end-to-end flow in the **mobile app**. Backend-only support doesn't count.

| Module | Total Features | Completed | Partial | Mock | Broken | Missing | Completion % |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0. Mobile foundation (infrastructure, not in checklist) | 12 | 0 | 5 | 0 | 0 | 7 | 25 % |
| A. Authentication & User Management | 13 | 0 | 0 | 0 | 0 | 13 | 0 % |
| B. Patient Management | 8 | 0 | 0 | 0 | 0 | 8 | 0 % |
| C. Appointment Management | 11 | 0 | 0 | 0 | 0 | 11 | 0 % |
| D. Doctor Module | 10 | 0 | 0 | 0 | 0 | 10 | 0 % |
| E. Nursing Module | 10 | 0 | 0 | 0 | 0 | 10 | 0 % |
| F. Pharmacy Module | 8 | 0 | 0 | 0 | 0 | 8 | 0 % |
| G. Laboratory Module | 6 | 0 | 0 | 0 | 0 | 6 | 0 % |
| H. Billing & Payments | 7 | 0 | 0 | 0 | 0 | 7 | 0 % |
| I. Emergency & IPD | 7 | 0 | 0 | 0 | 0 | 7 | 0 % |
| J. Notifications & Communication | 7 | 0 | 0 | 0 | 0 | 7 | 0 % |
| K. AI & Smart Healthcare | 8 | 0 | 0 | 0 | 0 | 8 | 0 % |
| L. Additional Healthcare Features | 8 | 0 | 0 | 0 | 0 | 8 | 0 % |
| **Checklist modules A–L total** | **103** | **0** | **0** | **0** | **0** | **103** | **0 %** |

No feature is mock, broken, or partial, because no feature screen exists. There is no fake data anywhere in `lib/`.

---

## Section 4: Feature-Level Audit

### 4.1 What exists (foundation layer)

| Feature | Screen/File | Backend API | Database | UI Status | Functionality | Completion % |
|---|---|---|---|---|---|---:|
| Flutter project scaffold (Android + iOS shells) | `mobile/` | n/a | n/a | n/a | Analyzer clean; Android debug APK builds; iOS not built | 80 % |
| Backend origin config | `lib/core/config/api_config.dart` `ApiConfig.fromEnvironment`, `resolveOrigin` | n/a | n/a | n/a | Rejects bad URLs, strips trailing slash, per-platform default. Unit tested (6 tests). No flavors or prod HTTPS profile | 80 % |
| HTTP client | `lib/main.dart` (`Dio` with 10 s connect/receive timeouts) | n/a | n/a | n/a | No interceptors: no auth header, token refresh, `X-Hospital-ID`, request id, retry or error envelope | 40 % |
| Backend health check | `lib/core/network/backend_health.dart` `BackendHealth.check` | `GET /health/` (`backend/config/health.py` `HealthCheckView.basic`, returns `{"status":"healthy","service":"hms-backend"}`) | none | n/a | Request/response shape matches the backend. Handles HTTP 400 (ALLOWED_HOSTS), other codes, timeouts, connection errors. Tested with a fake adapter (4 tests). **Not run against a live backend in this audit** | 80 % |
| Backend status screen | `lib/features/backend_status/backend_status_screen.dart` | uses the health check above | none | Diagnostic only: origin, spinner, result icon, "Check again" | Loading, success, error and retry covered by 2 widget tests | 80 % |
| Theming | `lib/app.dart` (`ColorScheme.fromSeed(teal)`) | n/a | n/a | Material 3 seed theme only; no design tokens matching the web redesign; no dark theme | n/a | 20 % |
| Navigation / routing | none | n/a | n/a | missing | missing | 0 % |
| State management | none beyond `setState` | n/a | n/a | missing | missing | 0 % |
| Auth session + token storage | none | n/a | n/a | missing | missing | 0 % |
| Secure local storage | none | n/a | n/a | missing | missing | 0 % |
| Localization (English/Hindi) | none | n/a | n/a | missing | missing | 0 % |
| Mobile CI pipeline / crash reporting | none | n/a | n/a | missing | missing | 0 % |

Foundation average: (80+80+40+80+80+20+0+0+0+0+0+0) / 12 = **38 %** if the status screen counts separately. Counting the health check and its screen as one item (11 items): (80+80+40+80+20+0×6)/11 ≈ **27 %**. This report uses the conservative **25 %**, because the screen is a developer diagnostic, not product UI.

### 4.2 Checklist features (modules A–L)

Every row below is **0 % – Not implemented in the mobile app.** The "Backend API" column says whether the Django backend registers routes for that area (read from `backend/*/urls.py` at HEAD). It does not mean those endpoints were exercised in this audit.

| Module | Features (all missing in mobile) | Screen/File | Backend routes present (HEAD) | Database | Completion % |
|---|---|---|---|---|---:|
| A. Auth | Login, registration, OTP verification, forgot password, role-based access, patient / doctor / admin / nurse / compounder / receptionist auth, session management, logout | none | Yes: `backend/users/urls.py`: `staff/login/`, `staff/login/otp/{start,verify,resend}/`, `patient/otp/{request,verify}/`, `patient/email-otp/*`, `patient/login/`, `register/`, `password/reset/{,confirm/}`, `token/refresh/`, `sessions/`, `sessions/<id>/revoke/`, `logout-all/`, `staff/logout/`, `me/contexts/`, `proxy/*` (family access) | backend only | 0 % |
| B. Patient | Registration, profile, personal info, medical history, search, records, multi-hospital selection, dashboard | none | Yes: router `patients`, `patient-hospitals`; `auth/patient/me/`, `auth/me/contexts/`; `clinical/`, `encounters/`, `documents/` | backend only | 0 % |
| C. Appointments | Book, select doctor, select department, schedule, cancel, reschedule, token, queue, wait estimate, status tracking, notifications | none | Yes: router `appointments`, `doctors`; `hospital/`, `services/` | backend only | 0 % |
| D. Doctor | Dashboard, patient list, consultation, history, clinical notes, diagnosis, prescription, follow-up, availability, consultation completion | none | Yes: `clinical/` (13 routes), `encounters/`, router `doctors` | backend only | 0 % |
| E. Nursing | Dashboard, assignments, vitals (BP, temperature, pulse, SpO₂), nursing notes, medication administration (MAR), monitoring | none | Yes: `nurses/` (9 routes, incl. assessments, notes, care tasks, MAR per `config/urls.py` comment) | backend only | 0 % |
| F. Pharmacy | Medicine search, details, prescription view, dispensing, stock, inventory, billing, procurement | none | Yes: router `pharmacy`, `pharmacy-sales`, `compounder`; `procurement/` (12 routes) | backend only | 0 % |
| G. Laboratory | Test requests, scheduling, sample collection, results, report view, report upload | none | Yes: router `laboratory`; `laboratory/` (6 routes) | backend only | 0 % |
| H. Billing | Patient billing, invoice, payment processing, history, outstanding, refunds, receipts | none | Yes: `billing/` (6 routes) | backend only | 0 % |
| I. Emergency & IPD | Emergency registration, tracking, bed availability, admission, discharge, transfer, IPD monitoring | none | Yes: `emergency/` (6), `ipd/` (6), `ai/discharge/` | backend only | 0 % |
| J. Notifications | Push, SMS, reminders, OTP notifications, doctor / patient notifications, history | none | Partly: `notifications/` (7 routes). `NOTIFICATION_CHANNELS` lists `push` and production settings name a `firebase` provider, but a grep of non-test backend code found **no push-sending implementation and no device-token model** | backend only | 0 % |
| K. AI | AI consultation, voice-to-text, transcription, clinical summaries, prescription assist, image analysis, CNN features, recommendations | none | Partly: `ai/` (`ai_scribe`, 7 routes), `ai/discharge/`. Image analysis / CNN not audited on backend | backend only | 0 % |
| L. Additional | Blood bank, medical documents, consent, audit logs, hospital management, multilingual (Hindi/English), ABDM, FHIR/HL7 | none | Yes: `bloodbank/`, `documents/`, `consent/`, `audit/`, `hospital/`, `abdm/`, `fhir/`, `terminology/` | backend only | 0 % |

Procurement is listed under both F and L in the brief. It is counted once, under F.

---

## Section 5: Completed Features

**No checklist feature is complete.**

At the foundation level, these pieces are implemented and tested, but none of them is a hospital feature:

1. **API origin configuration**: `ApiConfig.resolveOrigin` (`lib/core/config/api_config.dart:32`). 6 passing unit tests.
2. **Backend health probe**: `BackendHealth.check` (`lib/core/network/backend_health.dart:19`). 4 passing tests with a fake HTTP adapter.
3. **Backend status screen with retry**: `BackendStatusScreen` (`lib/features/backend_status/backend_status_screen.dart:8`). 2 passing widget tests.

Each of these stops short of 100 % because none was exercised against a running backend on an emulator or device during this audit.

---

## Section 6: Partially Completed Features

Only foundation items are partial:

| Item | Implemented | Remaining |
|---|---|---|
| HTTP client (`lib/main.dart:12`) | Dio instance with timeouts | Auth interceptor (Bearer access token), refresh-token rotation via `auth/token/refresh/`, `X-Hospital-ID` tenancy header, `Idempotency-Key` for writes (backend CORS allows both), error envelope parsing, retry/backoff, request logging that never logs PHI |
| Environment config | `API_ORIGIN` dart-define with validation | Dev/staging/prod flavors; enforce `https://` outside debug; separate Android `applicationId` / iOS bundle per flavor |
| Theming (`lib/app.dart:16`) | Material seed colour | Design tokens matching the web redesign, dark mode, typography scale, accessibility checks (text scale, contrast) |
| Project scaffold | Android + iOS shells; Android debug build passes | Release signing, iOS build verification, app icons/branding (default Flutter icons), README (still the Flutter template) |

---

## Section 7: Mock and Non-Functional Features

- **No mock data, placeholder lists, or simulated workflows exist** in `mobile/lib/`.
- The only screen, `BackendStatusScreen`, is a **developer diagnostic**. Its own doc comment says "First screen of the foundation build: proves the app reaches the backend." It isn't a product screen.
- Test doubles (`_FakeAdapter` in `test/core/network/backend_health_test.dart`, injected `checkHealth` closures in `test/widget_test.dart`) exist only in tests. That's correct.

---

## Section 8: Broken Features and Bugs

No compilation errors (analyzer: "No issues found!") and no failing tests. The issues found are configuration and repository problems:

| ID | Severity | File / location | Function / class | Description | Recommended fix |
|---|---|---|---|---|---|
| C-1 | **Critical** | `.gitignore:39` (root) | n/a | The Python rule `lib/` also matches `mobile/lib/`. `git check-ignore -v mobile/lib/main.dart` → `.gitignore:39:lib/`. The mobile scaffold is staged (`git status` shows `A` on 68 files) but **all 5 app source files are ignored**. A commit would leave tests importing `package:hms_mobile/app.dart` with no source, so a fresh clone fails. | Anchor the Python rule (for example `/lib/`, `backend/**/lib/`) or add `!mobile/lib/` after it. Re-stage `mobile/lib/` before committing. |
| H-1 | High | `mobile/android/app/build.gradle.kts:36` | `buildTypes.release` | Release builds are signed with the **debug keystore** (Flutter template TODO). They can't be published, and anyone with the debug key could sign an "update". | Create an upload keystore stored outside the repo; read it via `key.properties` (git-ignored) or CI secrets; enable Play App Signing. |
| H-2 | High | `backend/config/settings/development.py:34` (HEAD) | `ALLOWED_HOSTS` | At HEAD, `10.0.2.2` is not allowed, so the Android emulator's health check gets **HTTP 400** (the app shows the ALLOWED_HOSTS hint). A fix adding `10.0.2.2` and `DEV_EXTRA_ALLOWED_HOSTS` is in the working tree but **uncommitted and unstaged**. | Commit the existing working-tree change together with the mobile scaffold. |
| M-1 | Medium | `mobile/android/gradle.properties:1` | `org.gradle.jvmargs=-Xmx8G -XX:MaxMetaspaceSize=4G` | Gradle may claim 8 GB of heap on a Mac with 8 GB RAM. The debug build took **433 s**. Heavy swapping like this has made the emulator lose network before. | Lower to about `-Xmx3g -XX:MaxMetaspaceSize=1g` and measure again. |
| M-2 | Medium | `mobile/lib/main.dart:11` | `main` → `ApiConfig.fromEnvironment` | An invalid `API_ORIGIN` throws `ArgumentError` before `runApp`, so the app closes on launch with no on-screen explanation. Acceptable for a dev build, wrong for release. | Validate in CI/build scripts per flavor, or catch it and show a configuration error screen. |
| M-3 | Medium | `mobile/lib/core/config/api_config.dart:19-20` | defaults | Defaults are plain `http://`. The release Android manifest correctly blocks cleartext and iOS ATS allows only local networking, so a release build without an `https://` `API_ORIGIN` will **fail every request**. Nothing enforces a production origin. | Production flavor with a required `https://` origin; fail the build when it's missing. |
| L-1 | Low | `android/app/build.gradle.kts:8,19` vs `ios/…/project.pbxproj:386` | ids | Android id `com.hospitalautomate.hms_mobile`, iOS id `com.hospitalautomate.hmsMobile`. Inconsistent naming; the Android file still has the template "TODO: Specify your own unique Application ID". | Pick final store identifiers now; they can't change after publishing. |
| L-2 | Low | `mobile/README.md` | n/a | Still the Flutter template text. No instructions for `API_ORIGIN`, the emulator address, or backend setup. | Document run, test and build commands and the backend prerequisites. |
| L-3 | Low | `ios/Runner/Info.plist:62-74` | orientations | Landscape allowed on phone; no layout work done for it. | Decide on portrait-only for phones or test landscape. |
| L-4 | Low | `mobile/flutter_01.log` (ignored by `*.log`) | n/a | Crash log written by `flutter analyze` during this audit when iCloud timed out reading `android/local.properties` (see Section 14). Not a code defect. | Delete it if you like; it's ignored by git. |
| U-1 | Unverified | `lib/core/network/backend_health.dart:21` | `check` | If a proxy returns a non-JSON body (an HTML error page), `get<Map<String,dynamic>>` may raise an error that isn't a `DioException` and escape the `catch`. Not reproduced. | Add a test with an HTML body; catch the type error or request `ResponseType.plain` and parse. |

Hard-coded credentials or secrets: **none found** in `mobile/`. No `.env`, keys, or tokens.

---

## Section 9: Missing Features

All **103** checklist features in modules A–L are missing from the mobile app (Section 4.2). Beyond the checklist, the mobile platform layer is also missing:

- Routing with role-aware guards
- An app-wide state management solution
- Bearer-token auth client with refresh rotation, and secure token storage (Keychain / Android Keystore)
- Hospital context selection (`auth/me/contexts/`) and the `X-Hospital-ID` header
- English/Hindi localization
- Offline behavior and caching policy for PHI (what may be stored on device, encryption, wipe on logout)
- Screenshot / app-switcher protection for clinical screens
- Biometric unlock, idle auto-lock
- Push notifications on both ends: mobile (FCM/APNs) and backend sending (no implementation found)
- Crash and performance reporting configured for PHI-safe payloads
- Mobile CI (analyze, test, build) and release pipeline (signing, store upload)
- Integration / end-to-end tests on emulator or device

---

## Section 10: Backend Integration Audit

| Check | Result | Evidence |
|---|---|---|
| Endpoints the mobile app calls | **1**: `GET /health/` | `lib/main.dart:15` |
| Matches backend? | Yes. Route exists (`backend/config/urls.py:123`); response keys `status`, `service` match `HealthCheckView.basic` | `backend/config/health.py:36-40` |
| `/api/v1/` versioned API | Exists on backend (`config/urls.py:138`, comment: "the versioned contract the mobile app uses"). Mobile builds `apiBaseUrl` but **never calls it** | `api_config.dart:26` |
| Auth model compatible with mobile? | **Yes, on the backend side.** `CookieJWTAuthentication` tries the `Authorization: Bearer` header first, then the cookie (`config/auth_cookies.py:69-90`). Cookies are used only when the client sends `X-Auth-Mode: cookie` (`auth_cookies.py:28`), so a mobile client gets tokens in the response body. JWT: 15-minute access, 7-day refresh, rotation on | `backend/config/settings/base.py:209-286` |
| Token handling in mobile | **Not implemented** | no auth code in `lib/` |
| Request/response models | None exist besides `HealthResult` | `lib/` |
| Loading / error states | Implemented for the health check only | `backend_status_screen.dart:41-60` |
| Role-based access in mobile | Not implemented. The backend enforces RBAC (recent commits `cc07990`, `cf06720`), and the mobile client must not try to replace that | git log |
| Emulator reachability | Blocked at HEAD by ALLOWED_HOSTS (H-2); fixed in uncommitted working tree | Section 8 |
| Live call performed in this audit | **No.** The backend wasn't started. Per my notes on this workspace, runserver in the iCloud-synced folder stalls, and an emulator run needs more RAM than was free | n/a |

**Integration level: 1 public, unauthenticated endpoint out of the backend's ~150+ routes, i.e. under 1 %.**

---

## Section 11: Android Readiness

| Item | Status | Evidence |
|---|---|---|
| `AndroidManifest.xml` (main) | OK for now: `INTERNET` permission; no cleartext in release; launcher activity exported (required) | `android/app/src/main/AndroidManifest.xml` |
| Debug manifest | `usesCleartextTraffic="true"` for local runserver, debug only | `android/app/src/debug/AndroidManifest.xml:9` |
| Permissions for future features | None declared yet (camera, microphone for AI scribe, notifications `POST_NOTIFICATIONS` for API 33+) | same |
| Gradle config | AGP 9.1.0, Kotlin 2.4.0, Gradle 9.3.1, Java 17. Template flags `android.newDsl=false`, `android.builtInKotlin=false` | `settings.gradle.kts`, `gradle.properties` |
| SDK levels | compile/min/target = Flutter defaults (exact numbers not printed in this audit) | `build.gradle.kts:9,22-23` |
| App signing | **Not ready**: debug key (H-1) | `build.gradle.kts:36` |
| Push config | **None**: no `google-services.json`, no Firebase plugin | file listing |
| Obfuscation / R8 / ProGuard | Not configured (defaults) | `build.gradle.kts` |
| **Debug build** | **VERIFIED**: `flutter build apk --debug` succeeded in 432.7 s; `app-debug.apk` 151 MB | Section 14 |
| Release build | **Not run** (would be signed with the debug key anyway) | n/a |
| On-device / emulator run | **NOT VERIFIED** in this audit | n/a |

**Android verdict:** compiles for debug; **not release-ready**.

---

## Section 12: iOS Readiness

| Item | Status | Evidence |
|---|---|---|
| `Info.plist` | Display name "Hospital Management"; ATS `NSAllowsLocalNetworking` only (good for release); UIScene manifest present; **no usage-description strings** (needed once camera, mic, photos or notifications are added) | `ios/Runner/Info.plist` |
| Bundle identifier | `com.hospitalautomate.hmsMobile` (differs in style from Android, L-1) | `project.pbxproj:386` |
| Deployment target | iOS 15.0 | `project.pbxproj:363,490,542` |
| Signing | Automatic style, **no `DEVELOPMENT_TEAM`**, so it can't sign for a device or the App Store | `project.pbxproj` |
| CocoaPods | **Not installed** on this Mac. No `Podfile` yet (not needed while the only package, `dio`, is pure Dart) | `flutter doctor` |
| Simulator | **Runtimes unavailable** ("Unable to get list of installed Simulator runtimes") | `flutter doctor` |
| iOS-specific dependencies | None | `pubspec.yaml` |
| Build verification | **BLOCKED / NOT VERIFIED.** No iOS build was attempted: no simulator runtime, no CocoaPods, no signing team, and limited disk (12 GB free) | n/a |
| Native tests | `RunnerTests/RunnerTests.swift` is the empty Xcode template | file |

**iOS verdict:** source configuration looks sane, but **readiness is NOT VERIFIED**. This report doesn't claim iOS builds.

---

## Section 13: Security, Performance and Reliability

| Risk | Severity | Notes |
|---|---|---|
| App source not version-controlled (C-1) | Critical | Loss of work; no review trail; CI impossible |
| Debug-key release signing (H-1) | High | Blocks store release; key compromise risk |
| No secure token storage design yet | High (when auth lands) | Tokens must live in Keychain/Keystore (for example `flutter_secure_storage`), never in `SharedPreferences`; refresh token rotation is already enforced by the backend |
| PHI on device | High (when features land) | Needs an explicit policy: no PHI in logs or crash reports, cache encryption, wipe on logout/revocation (backend already has `sessions/<id>/revoke/` and `logout-all/`), screenshot protection on clinical screens |
| HTTPS not enforced in config (M-3) | Medium | Platform defaults block cleartext in release, which protects data but breaks the app if misconfigured |
| Certificate pinning | Not present | Consider for production; weigh it against certificate rotation |
| Hardcoded secrets | None found | n/a |
| Gradle memory (M-1) | Medium | 433 s debug build on 8 GB RAM |
| APK size | Info | 151 MB is a normal debug size (JIT plus all ABIs); measure a release AAB later |
| Runtime performance / memory | Not measurable | The app has one trivial screen |
| Dependency health | Good | 1 direct dependency with a newer major version (`cupertino_icons` 2.0.0); a few locked transitive updates; no conflicts |

---

## Section 14: Testing Report

Commands actually executed (2026-11-09/10):

| # | Command | Where | Result |
|---|---|---|---|
| 1 | `flutter --version` | `mobile/` | Flutter 3.47.9, Dart 3.13.7 |
| 2 | `flutter doctor` | `mobile/` | Flutter ✓, Android toolchain ✓, Xcode ! (no simulator runtimes, CocoaPods missing), Chrome ✓, connected devices ✓ (3), Network resources check crashed (4 m 30 s timeout) |
| 3 | `flutter analyze` | `mobile/` (iCloud folder) | **Tool crashed**: `FileSystemException: readInto failed … android/local.properties (Operation timed out, errno 60)`. iCloud file eviction, not a code issue |
| 4 | `flutter test --coverage` | `mobile/` | **12 / 12 passed** (`All tests passed!`) |
| 5 | `flutter pub outdated` | `mobile/` | `cupertino_icons` 1.0.9 → 2.0.0 available; 2 locked transitive upgrades |
| 6 | `flutter pub get && flutter analyze` | scratch copy outside iCloud | **No issues found!** (7.2 s) |
| 7 | `flutter build apk --debug` | scratch copy | **✓ Built** `app-debug.apk` (151,092,908 bytes) in 432.7 s |

Coverage (from `mobile/coverage/lcov.info`, run 4):

| File | Lines hit / found |
|---|---|
| `lib/app.dart` | 5 / 5 |
| `lib/core/config/api_config.dart` | 10 / 12 |
| `lib/core/network/backend_health.dart` | 18 / 19 |
| `lib/features/backend_status/backend_status_screen.dart` | 28 / 28 |
| **Total** | **61 / 64 (95.3 %)**. `lib/main.dart` isn't loaded by tests, so it isn't counted |

Test inventory:

| Type | Present | Notes |
|---|---|---|
| Unit tests | Yes, 10 | `api_config_test.dart` (6), `backend_health_test.dart` (4) |
| Widget tests | Yes, 2 | `widget_test.dart` |
| Integration tests (`integration_test/`) | **No** | n/a |
| API contract tests against a live backend | **No** | n/a |
| Auth / navigation tests | **No** | Features don't exist |
| Android instrumentation | **No** | n/a |
| iOS native tests | Template only | `RunnerTests.swift` |
| Emulator / device run | **Not performed** | n/a |
| iOS build | **Blocked** | Section 12 |
| Mobile CI | **None** | n/a |

Coverage of what exists is high. Coverage of the product is 0 %, because the product features aren't built yet.

---

## Section 15: Remaining Work with Priority

Effort is in developer-days for one experienced Flutter developer. These are planning estimates, not measurements.

| Priority | Task | Module | Estimated Effort | Dependencies |
|---|---|---|---|---|
| P0 | Fix root `.gitignore` so `mobile/lib/` is tracked; stage `lib/`; commit the scaffold | Repo | 0.25 d | none |
| P0 | Commit the `10.0.2.2` / `DEV_EXTRA_ALLOWED_HOSTS` dev-settings change | Backend dev config | 0.1 d | none |
| P0 | Decide the mobile product scope: patient app, staff app, or both; which roles first | Product | 1 d (decision) | none |
| P0 | Add mobile CI job: `flutter analyze`, `flutter test`, `flutter build apk --debug` | CI | 1 d | `.gitignore` fix |
| P1 | Pick and set up state management and routing with role guards | Foundation | 3 d | scope decision |
| P1 | API client: Bearer auth interceptor, refresh rotation (`auth/token/refresh/`), `X-Hospital-ID`, `Idempotency-Key`, error envelope, PHI-safe logging | Foundation | 4 d | routing/state |
| P1 | Secure token storage, logout, session revoke, idle lock, wipe on logout | A | 3 d | API client |
| P1 | Flavors (dev/staging/prod) with enforced `https://` origin; final app/bundle ids | Foundation | 2 d | none |
| P1 | Patient sign-in: mobile OTP / email OTP (`auth/patient/*`) | A | 3 d | API client |
| P1 | Staff sign-in with OTP (`auth/staff/login*`), password reset, hospital context switch (`auth/me/contexts/`) | A | 4 d | API client |
| P1 | English + Hindi localization scaffolding | L | 2 d | foundation |
| P1 | Release signing (Android upload key, iOS team/profiles), Play/App Store listings | Release | 3 d | ids decided |
| P1 | iOS toolchain on build machine (simulator runtime, CocoaPods) and first iOS build | iOS | 1–2 d | disk space |
| P1 | Patient core: profile, appointments (book/cancel/reschedule/status), lab reports, bills, prescriptions | B, C, G, H | 15–20 d | patient auth |
| P1 | PHI on-device policy, screenshot protection, crash reporting without PHI | Security | 3 d | foundation |
| P2 | Doctor: patient list, consultation, notes, diagnosis, prescription, follow-up | D | 15–20 d | staff auth, RBAC rules from backend |
| P2 | Nursing: assignments, vitals, notes, MAR | E | 10–15 d | staff auth |
| P2 | Push notifications: backend sending and device tokens (not implemented server-side), FCM/APNs on mobile | J | 6–8 d | backend work, signing |
| P2 | Integration tests on emulator against a seeded test backend | Testing | 4 d | first features |
| P2 | Pharmacy / lab staff / billing staff flows (if in mobile scope) | F, G, H | 15–25 d | scope decision |
| P3 | Emergency & IPD mobile views (bed board, admission, discharge) | I | 10–15 d | staff auth |
| P3 | AI scribe on mobile (microphone permission, upload, review) | K | 8–12 d | doctor module |
| P3 | Blood bank, documents, consent, ABDM flows on mobile | L | 10–20 d | scope decision |
| P3 | Biometric unlock, offline read cache, certificate pinning | Security | 5 d | auth |

---

## Section 16: Development Roadmap

| Phase | Goal | Contents | Depends on |
|---|---|---|---|
| **0. Make it real** (1–2 days) | The scaffold is safe and reproducible | `.gitignore` fix and commit; dev ALLOWED_HOSTS commit; mobile CI; scope decision; README | none |
| **1. Platform foundation** (~2 weeks) | Every later screen can be built quickly and safely | State management + routing with role guards; API client and auth interceptor; secure storage; flavors and HTTPS; i18n (en/hi); design tokens matching the web redesign; PHI policy; first emulator run against a scratch backend | Phase 0 |
| **2. Authentication** (~1.5 weeks) | Real users can sign in | Patient OTP and email OTP; staff login + OTP; hospital context switch; sessions, logout, revoke; tests for each | Phase 1 |
| **3. First vertical slice** (~3–4 weeks) | One role fully usable end to end | Recommended: **patient app**. Profile, appointments, lab reports, bills, prescriptions; integration tests; internal Android test build | Phase 2 |
| **4. Release pipeline** (~1 week, can overlap 3) | Shippable to testers on both platforms | Android upload key; iOS toolchain, team and profiles; first iOS build; TestFlight / Play internal track | Phase 0 (ids), Phase 3 for content |
| **5. Staff modules** (~6–10 weeks) | Clinical roles on mobile | Doctor, then nursing (vitals, MAR), then pharmacy/lab/billing as scoped | Phase 2, backend RBAC |
| **6. Notifications** (~1.5 weeks) | Reminders and alerts | Backend push sender and device-token model, FCM/APNs integration | Phase 4 (signing) |
| **7. Advanced** (ongoing) | Parity extras | Emergency/IPD, AI scribe, blood bank, documents, consent, ABDM | Phase 5 |

Order rationale: version control and CI first, because nothing else is safe without them. Auth is the gate for every PHI screen. A single vertical slice shows the client architecture works before it gets copied to 10 modules. The backend already has the endpoints for phases 2–5, so mobile work isn't blocked on the server except for push notifications.

---

## Section 17: Final Completion Assessment

**Weighting method.** Foundation infrastructure is weighted 10 % and the 12 checklist modules 90 % (split by feature count, 103 features). Feature scores use the brief's 0/20/40/60/80/100 scale.

Overall = 0.10 × 25 % (foundation) + 0.90 × 0 % (modules) = **2.5 %**.

Excluded or unverified: iOS build (blocked), emulator/device run (not performed), live backend call (not performed), backend feature behavior (out of mobile scope; route presence only).

| Measure | Value |
|---|---|
| **Overall mobile completion** | **≈ 2.5 %** |
| Backend integration | **< 1 %** (1 public health endpoint; no `/api/v1/` call) |
| UI completion (product screens) | **0 %** (1 developer diagnostic screen) |
| Functional completion (checklist features) | **0 / 103 = 0 %** |
| Testing completion | Existing code: 95.3 % line coverage, 12/12 passing. Product testing: **0 %** |
| Android readiness | Debug build **verified**; release **not ready** (debug signing, no prod config) |
| iOS readiness | **BLOCKED / NOT VERIFIED** |
| Production readiness | **Not ready** |

**Bottom line.** What's done is a clean, well-tested connectivity scaffold, built on a backend that already supports mobile Bearer-token clients. Nothing is partially built, mocked, or broken, because none of the hospital features have been started. The next steps, in order: fix the `.gitignore` so the app code is actually tracked, commit, add CI, decide the mobile scope, then build the foundation (Phase 1) before any feature screens.
