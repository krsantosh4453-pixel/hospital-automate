# Security hardening and findings register — 2026-11-19

Follows up the open findings of [PRODUCTION_READINESS_AUDIT_2026-11-18.md](PRODUCTION_READINESS_AUDIT_2026-11-18.md) (S-L1 to S-L8 and the mobile review).

**This is an internal engineering review.** It does not replace an independent penetration test or a legal privacy assessment. Nothing here is a statement of compliance.

Status: all changes are uncommitted on `ui/redesign-2026-10-25`.

## 1. Backend findings S-L1 to S-L8

| ID | Finding | Status | Fix | Regression test |
|---|---|---|---|---|
| S-L1 | Patient password sign-in had a per-address rate limit only, with no per-account lockout. | **Fixed** | `users/views.py` `patient_email_login` / `patient_token_login`: 5 wrong passwords lock the account for 15 min. The lock counts across email and mobile-number sign-in, and staff and patient sign-in share one account counter. When a mobile number matches several family accounts, each of them is charged. | `PatientLockoutTests` (4 tests) |
| S-L2 | The staff lockout key was the typed identifier, so the username and the email of one account had separate budgets. | **Fixed** | `users/security.py` `staff_login_keys`: the identifier is resolved to every matching account (username or email, case-insensitive), and failures count against each account and against the identifier. The account key includes the join time, so a reused id never inherits a lock. A password reset clears that account's lock. | `StaffLockoutPerAccountTests` (3 tests) |
| S-L3 | A medicine with no hospital (legacy rows) skipped the hospital check in sales and dispensing. | **Fixed** | `pharmacy/views.py` `_check_batch` and `pharmacy/serializers.py`: stock with no hospital is refused ("assign it before dispensing"). `MedicineViewSet.perform_create` refuses new stock that would have no hospital. | `LegacyMedicineIsolationTests` (2 tests) |
| S-L4 | Registration and staff-invite messages revealed whether an email or mobile number had an account. | **Fixed (residual noted)** | Registration gives one message whether the email or the mobile is taken (`REGISTRATION_UNAVAILABLE`). The invite gives one message (`EMAIL_NOT_INVITABLE`) for a patient's email, another hospital's pending invite, and another hospital's inactive profile. Mobile error mapping and en/hi strings updated. | `EnumerationTests` (2), `test_stage1a_patient_registration`, mobile `auth_errors_test` |
| S-L5 | The security overview showed a staff member's sign-ins and devices from every hospital they work at. | **Fixed** | `hospital/security_overview.py`: history and alerts include only audit rows recorded for this hospital or for no hospital. Sessions, history and alerts cover active members only. The client-chosen `device_id` (a cross-tenant correlator, unused by the UI) is no longer returned. | `SecurityOverviewScopeTests` |
| S-L6 | Audio upload trusted the client `Content-Type`. | **Fixed** | New `ai_scribe/audio_validation.py`: the file's first bytes must be a WAV, MP3, MP4/M4A, Ogg or WebM signature and must match the declared type. The stored file gets a server-chosen name and extension (`consultation-<id>-<uuid>.<ext>`), so client names such as `../../evil.html` never reach storage or logs. | `AudioSignatureUnitTests`, `AudioUploadValidationTests` (3) |
| S-L7 | A staff invite re-activated a legacy self-signup profile (`is_active_staff=False`) with its self-chosen password. | **Fixed** | `users/staff_invite.py` `_readmit_legacy_profile`: the old password is discarded, every session is revoked, and the person must set a password from the invitation link. The event is audited (`users.staff.legacy_readmitted`). An inactive profile with a membership at another hospital is refused. | `LegacyProfileReactivationTests` (2) |
| S-L8 | Any doctor could create, edit or delete platform-wide extraction schemas and prompt templates (nothing reads them). | **Fixed** | `ai_scribe/views.py`: both viewsets are read-only (`GET` only, tenant-global reads for hospital staff). Platform superusers manage the rows in the Django admin. | `AIConfigurationWriteTests` |

**Residual on S-L4:** registration still answers 400 when the email or mobile is taken, so a caller can still learn that *some* account uses those details. The route is rate limited (5 per 5 min per address). Fully closing it needs an "accepted, check your email" flow that emails the existing owner. That is a product change, and it has to handle families who share one mobile number. The invite still says "already staff at this hospital", which the admin can see in their own staff list anyway.

**Lockout trade-off (S-L1/S-L2):** anyone who knows an identifier can lock that account for 15 minutes (denial of service). Mitigations: the per-address rate limits, the password reset path, and audit events `auth.staff_login.locked` / `auth.patient_login.locked` for monitoring.

## 2. Mobile findings

| # | Item | Status | Change / evidence |
|---|---|---|---|
| 1 | `FLAG_SECURE` on PHI screens | **Fixed (Android)** | `MainActivity.kt` sets `FLAG_SECURE` on the window in non-debuggable builds, which blocks screenshots, screen recording and the recents thumbnail. Debug builds leave it off for development and emulator screenshots. iOS has no OS screenshot block (see 2). |
| 2 | App-switcher snapshots | **Fixed (both)** | `lib/core/security/privacy_cover.dart` covers the whole app whenever it is not `resumed`. It is wrapped around the router in `app.dart`. Test: `mobile_hardening_test.dart` "covers patient data…". **Not verified on an iOS device:** iOS has never been built. |
| 3 | R8 minify / shrink / obfuscation | **Fixed** | `build.gradle.kts` release: `isMinifyEnabled`, `isShrinkResources`, `proguard-android-optimize.txt` and `proguard-rules.pro`. Dart obfuscation is a build flag: `flutter build apk --release --obfuscate --split-debug-info=<private dir>`. See section 4b for the build result. |
| 4 | iOS Google Sign-In `Info.plist` | **Fixed (config); unverified on device** | It had no `GIDClientID` and no reversed-client-id URL scheme, so the Google iOS SDK would raise at sign-in. Added both from build settings (`ios/Flutter/GoogleSignIn.xcconfig`, git-ignored, with an `.example`). The Dart side takes `GOOGLE_IOS_CLIENT_ID` and hides Google sign-in on iOS when it is not set, instead of crashing. Tests: "PluginGoogleIdentity on iOS". |
| 5 | Token storage and sign-out | **Verified; one gap fixed** | Tokens are in Keystore/Keychain (`first_unlock_this_device`), never SharedPreferences, and are cleared on sign-out (cleanup failures still clear tokens). **Gap:** iOS keeps Keychain items after the app is deleted, so a reinstall resumed the old session. Fixed: `forgetSessionFromPreviousInstall` clears stored tokens on an install's first start. Existing users are signed out once after this update. |
| 6 | Local cache, audio files, deletion | **Verified; one gap fixed** | Audio is deleted after upload (M-2). **Gap:** a recording interrupted by a crash or app kill stayed in the temp dir. Fixed: `deleteLeftoverRecordings` runs at start-up and at every sign-out. No other files are written; record lists live in memory and are cleared by sign-out cleanups. |
| 7 | HTTPS and production origin | **Verified (no change)** | `ApiConfig.resolve` refuses `http://` for staging and production, and refuses the development environment in release builds (`api_config_test.dart`). Android release keeps the default cleartext block (cleartext only in `src/debug`). iOS ATS allows only local networking. No certificate pinning (R-3). |
| 8 | Backup restrictions and manifest | **Fixed** | `allowBackup="false"` was already set. On Android 12+ that does not stop device-to-device transfer, so `dataExtractionRules` (`res/xml/data_extraction_rules.xml`) now exclude every domain from cloud backup and device transfer. Manifest permissions: INTERNET, RECORD_AUDIO only. |

## 3. Changed files

Backend:
- `users/security.py`
- `users/views.py`
- `users/staff_invite.py`
- `pharmacy/views.py`
- `pharmacy/serializers.py`
- `hospital/security_overview.py`
- `ai_scribe/views.py`
- `ai_scribe/audio_validation.py` (new)

Backend tests:
- `security_tests/test_security_hardening_2026_11.py` (new, 19 tests)
- `users/test_stage1a_patient_registration.py` (new message)
- `ai_scribe/test_scribe_workflow.py` and `security_tests/test_ai_scribe_safety.py`: test audio now carries real container headers, because a fake byte string is now (correctly) refused.

Mobile:
- `android/app/build.gradle.kts`
- `android/app/proguard-rules.pro` (new)
- `android/app/src/main/AndroidManifest.xml`
- `android/app/src/main/res/xml/data_extraction_rules.xml` (new)
- `MainActivity.kt`
- `ios/Runner/Info.plist`
- `ios/Flutter/{Debug,Release}.xcconfig`
- `ios/Flutter/GoogleSignIn.xcconfig.example` (new)
- `.gitignore`
- `lib/app.dart`
- `lib/main.dart`
- `lib/core/security/privacy_cover.dart` (new)
- `lib/core/security/token_store.dart`
- `lib/features/ai/data/scribe_recorder.dart`
- `lib/features/auth/google_identity.dart`
- `lib/features/auth/auth_errors.dart`
- `lib/l10n/app_{en,hi}.arb` (and the generated localizations)
- `test/core/security/mobile_hardening_test.dart` (new, 7 tests)
- `test/features/auth/auth_errors_test.dart`

Web: no change. The removed `device_id` was not used by `SecuritySettings.jsx`.

## 4. Evidence

All runs were in a clean `git archive` copy with the changed files overlaid, synthetic data, and no `.env`.

| Check | Before | After |
|---|---|---|
| `security_tests.test_security_hardening_2026_11` (19 tests) | **15 failures, 1 error.** Each finding reproduced: e.g. staff login 200 after 5 mixed failures; patient login 200 after 5 failures; legacy medicine sale 201; HTML uploaded as `audio/webm` accepted and stored as `consultation_audio/evil.html`; doctor POST to `/api/ai/schemas/` 201; other-hospital audit rows in the overview. | **19 passed** |
| Full Django suite (`manage.py test --parallel 4`, includes every `security_tests` module) | — | **1196 tests OK, 29 skipped.** The first run found one real problem in the new code (an account lock leaking across reused test ids); that is fixed by including the join time in the account key. |
| `flutter analyze` | — | No issues |
| `flutter test` | — | **441 passed, 51 skipped** (live tests need a backend) |
| React (`vitest`) | — | see section 4a |
| `pip-audit -r requirements-lock.txt` | — | No known vulnerabilities |
| `npm audit` (all and `--omit=dev`) | 4 High (picomatch, dev only) on 2026-11-18 | 0 vulnerabilities |
| Dart packages (`pubspec.lock`, 93 packages) against OSV | — | 0 advisories |
| Secret scan, tracked and new files (OpenAI, AWS, Twilio, Google API/OAuth secret, GitHub, Slack, private-key headers) | — | No matches. Git history: one hit, a test assertion string `"-----BEGIN PRIVATE KEY-----"`, not a key. `.env*.example` hold blanks only. |
| Android release build with R8 | — | see section 4b |

### 4a. React tests

`npx vitest run` after `npm ci`: **125 passed (125)**. No web source changed.

### 4b. Android release build

Command:

```
ORG_GRADLE_PROJECT_hmsAllowDebugReleaseSigning=true flutter build apk --release \
  --dart-define=APP_ENV=staging --dart-define=API_ORIGIN=https://staging.example.test \
  --obfuscate --split-debug-info=<scratch>/symbols
```

This was a local test build signed with the debug key. Real releases need `android/key.properties`.

- **Result:** `app-release.apk` built (60.4 MB) in 200 s. R8 ran with no missing-class errors, so the `-dontwarn` rules are enough.
- **R8:** `build/app/outputs/mapping/release/mapping.txt` has 101,959 lines, and plugin classes are renamed (e.g. `com.it_nomads.fluttersecurestorage.FlutterSecureStorage -> vi`).
- **Manifest** (`aapt2 dump xmltree` of the APK):
  - `allowBackup=false`, `fullBackupContent=false`, `dataExtractionRules=@xml/…`
  - no `debuggable`, no `usesCleartextTraffic`
  - permissions: INTERNET and RECORD_AUDIO from the app; USE_BIOMETRIC and USE_FINGERPRINT merged in from `flutter_secure_storage`, and unused
- **Dart:** obfuscated, with symbols written to `--split-debug-info` (`app.android-*.symbols`). Flutter warned that the ELF still has DWARF debug information and suggested `--strip`. Add it to the release command after checking that the symbol upload still works.
- **Not verified:** FLAG_SECURE at runtime (a screenshot or recents check on a device or emulator) and the privacy cover on a real device. The emulator was not started; this Mac's 8 GB of RAM has hung it before.

## 5. Findings register (open items after this work)

| ID | Severity | Item | Owner / next step |
|---|---|---|---|
| R-1 | Medium (process) | No independent penetration test yet. | Commission one against staging. Scope in section 6. |
| R-2 | Medium | iOS has never been built or run. The privacy cover, Google Sign-In and Keychain behaviour on iOS are unverified. | Build on a Mac with Xcode and a simulator, then test on a device. |
| R-3 | Low | No TLS certificate pinning in the mobile app. It relies on the OS trust store. | Decide with the hospital: pinning adds a certificate-rotation risk. |
| R-4 | Low | S-L4 residual: registration still distinguishes "taken" from "accepted". | Product decision (an email-confirmation flow). |
| R-5 | Low | Lockout can be used to lock an account for 15 minutes. | Monitor `auth.*.locked` audit events, and consider CAPTCHA or step-up after repeated locks. |
| R-6 | Low | `AUDIT_LOG_RETENTION_DAYS` defaults to 0 (keep forever), and there is no retention policy for consultation audio, documents or backups. | Set with counsel (see the DPDP preparation report). |
| R-7 | Info | The Google *web* client id is a constant in the mobile app (`google_identity.dart`). It is a public identifier, not a secret. | None; can be overridden per deployment. |
| R-8 | Info | Legacy medicines with no hospital can no longer be sold. | Before go-live, run a data check: `Medicine.objects.filter(hospital__isnull=True).count()`, and assign or retire those rows. |

## 6. Remaining penetration-test requirements

In addition to Part A of [PRIVACY_AND_PENTEST_PACK.md](PRIVACY_AND_PENTEST_PACK.md):

- **Authentication:**
  - try to bypass the per-account lockout (identifier variants, Unicode case folding, whitespace, a mobile number shared by family accounts)
  - lockout-based denial of service against known staff
  - the timing difference between existing and unknown accounts on `/api/auth/staff/login/` and `/api/auth/patient/login/` (password hashing runs only for existing accounts)
- **Enumeration:** registration, staff invite, password reset, OTP request and patient lookup.
- **Uploads:**
  - polyglot files with a valid audio header and a script body
  - oversized uploads (100 MB limit)
  - path and extension tricks
  - confirm `/media/` is never served
- **Tenancy:**
  - the security overview with a user who works at two hospitals
  - pharmacy sale and dispense of another hospital's stock or legacy stock
- **AI configuration:** confirm no write path to schemas or prompts outside the Django admin.
- **Mobile (Android APK and, once built, iOS IPA):**
  - static analysis (MobSF or equivalent)
  - check R8 obfuscation and that no secrets are in the bundle
  - screenshot and recents behaviour
  - backup and device-transfer extraction (`adb backup`, D2D)
  - rooted-device token extraction
  - traffic interception with a user-installed CA (no pinning, R-3)
  - deep links
  - the Google sign-in redirect
- **Infrastructure:** TLS configuration, headers, nginx, and exposure of the Django admin, on the real staging host.
