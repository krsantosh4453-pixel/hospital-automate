# Hospital Automate — mobile app

Flutter app (`hms_mobile`, Android id `com.hospitalautomate.hms_mobile`) for patients and hospital staff. It talks to the same Django REST API as the web app; it has no database or backend of its own.

| Part of the repository | Folder |
|------------------------|--------|
| Mobile app (this folder) | `hospital-automate-mobile/` |
| Web app (React + Vite) | repository root: `src/`, `package.json` |
| Backend API (Django + DRF) | `backend/` |

## 1. Architecture

Feature-first. Each feature keeps its data layer (models + repository over the API) next to its screens. App-wide plumbing lives in `core/`, reusable UI in `shared/`.

```
lib/
├── main.dart                  # Wires config, API client, session, auth, repositories; runs HmsApp
├── app.dart                   # MaterialApp.router, theme, localization
├── core/
│   ├── app_scope.dart         # AppServices: dependency container passed down the tree
│   ├── config/                # ApiConfig (API_ORIGIN), AppEnvironment (APP_ENV), AppInfo
│   ├── network/               # ApiClient (Dio; bearer, X-Hospital-ID, X-Request-ID; token refresh),
│   │                          #   ApiException, BackendHealth, paged results
│   ├── security/              # SessionController, SecureTokenStore (flutter_secure_storage)
│   ├── routing/               # GoRouter: routes and role-aware redirects
│   ├── localization/          # LocaleController (English / Hindi), l10n helpers
│   └── theme/                 # Colours, spacing, typography, shadows, ThemeData
├── features/
│   ├── auth/                  # Staff and patient sign-in, registration, devices; AuthService, repository
│   ├── dashboard/             # Role homes (guest, patient, staff), stats
│   ├── patient/               # Patient portal: appointments, booking, queue, prescriptions,
│   │                          #   lab results, bills, documents, notifications, profile
│   ├── doctor/                # Doctor: appointments, queue board, patient search and records,
│   │                          #   consultation, orders, prescriptions, lab
│   ├── navigation/            # App shell, header, sidebar, nav config (same paths as the web app)
│   ├── backend_status/        # Backend health screen
│   └── system/                # Settings; ModuleScreen for modules not built on mobile yet
├── shared/                    # Widgets (buttons, cards, fields, states, headers), polling
└── l10n/                      # app_en.arb, app_hi.arb; generated/ is committed
test/                          # Unit and widget tests; test/live/ runs against a real backend (opt-in)
assets/fonts/                  # Inter (OFL), the web app's typeface
android/  ios/                 # Platform projects
```

Why there is no top-level `services/`, `models/`, `repositories/` or `providers/` folder: each repository and its models belong to one feature (for example `features/patient/data/patient_repository.dart`), so they stay with that feature. Cross-cutting services (API client, token store, session, health check) are in `core/`. State lives in `ChangeNotifier` controllers (`SessionController`, `LocaleController`, `DashboardController`) handed down through `AppServices`, so a separate `providers/` package would only hold re-exports.

## 2. Requirements

- Flutter 3.47.9 stable (Dart 3.13.7). CI pins the same version in `.github/workflows/mobile.yml`.
- Android: Android Studio or the command-line tools, SDK platform 36, JDK 17 or newer (Android Studio's bundled JBR works).
- iOS: Xcode with an iOS simulator runtime, and CocoaPods (macOS only).
- A running backend (section 5).

```bash
flutter doctor
```

## 3. Run the app

Run every command from this folder.

```bash
cd hospital-automate-mobile
```

```bash
flutter pub get
```

Android emulator. It reaches the host machine at `10.0.2.2`, which is the default origin:

```bash
flutter run -d emulator-5554
```

iOS simulator. The default origin is `http://localhost:8000`:

```bash
flutter run -d "iPhone 16"
```

A physical phone on the same Wi-Fi as the backend:

```bash
flutter run --dart-define=API_ORIGIN=http://192.168.1.20:8000
```

Android debug APK:

```bash
flutter build apk --debug
```

## 4. Tests

```bash
flutter analyze
```

```bash
flutter test
```

The tests in `test/live/` are skipped unless you point them at a throwaway test backend. Never point them at a server with real patients.

```bash
HMS_LIVE_ORIGIN=http://127.0.0.1:8137 HMS_LIVE_PASSWORD=<seed password> flutter test test/live/patient_live_test.dart
```

The doctor live test also needs `HMS_LIVE_DOCTOR_SEED` (a JSON file describing a fresh visit and queue token); see the comments at the top of `test/live/doctor_live_test.dart`.

There is no `integration_test/` package yet. The live tests above are the end-to-end checks against a real server.

CI (`.github/workflows/mobile.yml`) runs `flutter gen-l10n` (the generated files must be committed), a `dart format` check, `flutter analyze`, `flutter test` and an Android debug build.

## 5. API and backend connection

- The Django backend in `../backend/` is the only source of truth. Start it as the root `README.md` describes; use `python manage.py runserver 0.0.0.0:8000` so emulators and phones can reach it.
- REST base: `<origin>/api/v1/`. Health check: `<origin>/health/`.
- Auth: JWT access and refresh tokens from the backend's staff and patient login endpoints. Tokens are kept with `flutter_secure_storage` (iOS Keychain, first unlock, this device only; Android uses the plugin's default Keystore-backed storage). An expired access token is refreshed through the same client.
- Every request carries `Authorization: Bearer …`, `X-Hospital-ID` (the hospital the user is acting in) and `X-Request-ID`.
- The app hides routes a role may not open (GoRouter redirects, sidebar config), but the server enforces the permissions.

## 6. Environment configuration

Set at build time with `--dart-define`:

| Key | Values | Default |
|-----|--------|---------|
| `APP_ENV` | `development`, `staging`, `production` | `development` |
| `API_ORIGIN` | scheme, host and port, no path | Android `http://10.0.2.2:8000`, other platforms `http://localhost:8000` (development only) |
| `GOOGLE_SERVER_CLIENT_ID` | the backend's `GOOGLE_CLIENT_ID` (a Google **Web** OAuth client ID) | the web app's client ID |

Staging and production builds need an `https://` `API_ORIGIN`; without one the app refuses to start. The localhost defaults apply only to development.

```bash
flutter build apk --dart-define=APP_ENV=production --dart-define=API_ORIGIN=https://hms.example.org
```

### Google sign-in

The app asks Google for an ID token issued to the backend's Web client (`GOOGLE_SERVER_CLIENT_ID`) and sends it to `POST /api/v1/auth/google/`, which checks it with Google. Patients only: staff accounts are refused there, as on the web. Google only issues the token to a registered app, so in the same Google Cloud project as that Web client:

1. **Android**: create an OAuth client of type *Android* with package `com.hospitalautomate.hms_mobile` and the SHA-1 of every key that signs the app (`keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android` for debug builds; the upload/Play signing key for releases).
2. **iOS** (not set up yet): create an *iOS* client for the bundle ID, then add `GIDClientID` and its reversed-client-ID URL scheme to `ios/Runner/Info.plist`.

Until that is done the button stays, and pressing it says Google sign-in is not set up for this app.

Plain `http://` works only in development: the Android debug manifest allows cleartext traffic, and iOS allows only local networking (`NSAllowsLocalNetworking`).

## 7. Supported features

- Staff sign-in (password, SMS code, SMS password reset); patient sign-in by mobile OTP, token/ID, email (with email verification and the "Verify using Email" fallback), Google, and family/caregiver view-only access; patient registration, signed-in device list, sign-out.
- Hospital context: the acting hospital is sent with every request.
- Role homes for guests, patients and staff.
- Patient portal: appointments and booking, live queue, prescriptions, lab results, bills, documents, notifications, profile.
- Doctor: appointments, queue board (Call Next), patient search and records, consultation (vitals, diagnoses, notes, orders), prescriptions, lab.
- English and Hindi; phone, tablet and landscape layouts.
- Backend health screen.

## 8. Known limitations

- Sidebar modules without a mobile screen open a "not in this app version" screen (for example patient consent, radiology, inventory and reports). So does a built module opened by a role it is not built for. Nursing, pharmacy, laboratory, billing, emergency, IPD, hospital management and the AI scribe are built (2026-11-18).
- No push notifications; screens load from the API, and the queue screens poll.
- No offline cache.
- Release signing (2026-11-18): a release build reads the upload key from `android/key.properties` (git-ignored; fields listed in `android/app/build.gradle.kts`) and stops if it is missing. No upload keystore exists yet, so the hospital must create one before publishing. For a local test build only, `ORG_GRADLE_PROJECT_hmsAllowDebugReleaseSigning=true` signs with the debug key. A release build also refuses to start unless it was built with `--dart-define=APP_ENV=staging|production` and an `https://` `API_ORIGIN`.
- The app keeps no Android backup (`allowBackup="false"`). AI scribe recordings are deleted from the device after the upload attempt.
- iOS has not been built on the development machine yet (no simulator runtime or CocoaPods installed).
