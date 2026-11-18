# External provider integration status (2026-11-18)

Scope: Twilio Verify OTP, e-mail, AI scribe speech-to-text and LLM, Google Sign-In, notifications.
Rule applied throughout: a mocked response is not proof. Every PASS below comes from a live provider answer; anything without one is BLOCKED.

## 1. Status

| Provider | Engineering | Real-provider verification | Evidence |
|---|---|---|---|
| Twilio Verify (patient and staff SMS OTP) | Done (error codes mapped, phone numbers masked in logs, local attempt cap for patient SMS) | **BLOCKED**: the credentials Django loads are rejected | Root `.env` API key: Twilio HTTP 401, error 8001 on both the Account and the Verify Service fetch |
| Twilio Messaging (SMS/WhatsApp notifications) | Already implemented (codes-only errors, retryable 429/5xx, status callback) | **BLOCKED**: same rejected credentials; no sender configured | Same 401 / 8001 |
| E-mail (OTP, invite, notifications) | Done (console backend no longer counts as "sent" for notifications) | **BLOCKED**: no SMTP login configured; dev uses the console backend | `check_providers`: `MOCK email EMAIL_BACKEND is …console.EmailBackend` |
| AI scribe STT (Whisper API) | Already hardened: no mock in production, 120 s timeout, status-only error logs | **BLOCKED**: `AI_SCRIBE_STT_API_KEY` not set | `check_providers`: `MOCK stt only the development mock transcriber` |
| AI scribe LLM drafts | Already hardened: schema coercion, timeout, no mock in production | **BLOCKED**: `AI_SCRIBE_API_KEY` empty | `check_providers`: `MOCK llm only the development mock LLM` |
| Google Sign-In (web) | Backend verifies via Google `tokeninfo` (signature, `aud`, `iss`, `email_verified`) | **PASS** for client existence; an end-to-end sign-in still needs a human Google account | Google recognises `GOOGLE_CLIENT_ID` (`redirect_uri_mismatch` for the probe URI, so the client exists) |
| Google Sign-In (Android) | **Fixed**: the app shipped a client ID that does not exist | **BLOCKED** on device: needs the Android OAuth client (package + SHA-1) in the same Cloud project | Old built-in ID: Google answered `invalid_client: The OAuth client was not found` |
| Google Sign-In (iOS) | Not set up (no `GIDClientID` / URL scheme in `Info.plist`) | **BLOCKED** | `hospital-automate-mobile/README.md` lists the iOS steps |
| Push notifications | No push channel exists (`FIREBASE_CREDENTIALS_PATH` is unused) | **BLOCKED** (not implemented) | — |
| In-app notifications | Unchanged; independent of every external channel | Covered by the existing test suite | — |

### Twilio account findings (read-only API calls, no SMS sent)

- **Root `.env`** (the file `config/settings/base.py` loads): account `AC5…`, API key `SKb…`. Twilio rejects it: HTTP 401, error 8001. The key was revoked, or it belongs to another account.
- **`backend/.env`** (not loaded by Django settings): a different account, `AC6…`. Its auth token **is valid**, but:
  - it is a **Trial** account with a **$0.00** balance;
  - it has **no Verify services** and **no verified caller IDs** (a trial can text only verified numbers);
  - its `TWILIO_VERIFY_SERVICE_SID` holds an **API key SID (`SK…`)**, not a Verify service SID (`VA…`);
  - its `SENDGRID_API_KEY` is a placeholder (`YOU…`) and `DEFAULT_FROM_EMAIL` is `…@example.com`.

## 2. Changed files

| File | Change |
|---|---|
| `backend/users/twilio_verify.py` | Maps Twilio error **codes** (not message text) to outcomes: auth failure 20003/401 is logged CRITICAL as a configuration error; 20404 on check means "Invalid or expired OTP"; 20429/60202/60203/60212 are "Too many…"; 21211/21614/60200/60205 mean invalid number; 21608/60410/… mean undeliverable. Logs carry `***1234` only, never the full number or Twilio's message text (which echoes the number). `VerifyResult` gains an optional `reason`; `ok`/`message`/`sid` and every API response are unchanged. |
| `backend/users/patient_auth.py` | `verify_patient_otp` now enforces our own expiry (5 min) and attempt cap (5) on the latest SMS `OTPVerification` record before calling Twilio, so it no longer relies on Twilio's limit alone. A verify with no pending request never reaches Twilio. |
| `backend/notifications/services/providers.py` | `EmailProvider.is_configured()` is false for console/dummy/file backends, so a dev console "send" is no longer recorded as a delivered notification. |
| `backend/config/provider_checks.py` (new) | Read-only live checks: Twilio Verify service fetch, Twilio account fetch plus sender, SMTP login (no message), STT/LLM `GET /models` with model presence, Google client existence, push. Returns PASS / FAIL / BLOCKED / MOCK; no secrets, numbers or addresses in output. |
| `backend/users/management/commands/check_providers.py` (new) | `manage.py check_providers` runs the checks (exit 1 on FAIL). Real deliveries happen only behind explicit flags: `--send-sms`, `--verify-sms`, `--send-email`, `--llm-sample` (synthetic transcript, no patient data), `--transcribe`. |
| `hospital-automate-mobile/lib/features/auth/google_identity.dart`, `src/pages/PatientLogin.jsx`, `docker-compose.dev.yml` | Replaced the nonexistent Google client ID with the verified one (`GOOGLE_CLIENT_ID`). OAuth client IDs are public, not secrets. |
| `backend/users/test_twilio_verify_failures.py` (new) | 14 tests: error-code mapping, log masking, local attempt cap, expiry, approval. |
| `backend/config/test_provider_checks.py` (new) | 17 tests: check classification, SMTP failures, e-mail console handling, no mock registered when mocks are disallowed. |

Not changed (already correct): production settings refuse `console` OTP and mock AI providers, and require Twilio Verify when SMS OTP is on; STT/LLM adapters have timeouts and status-only error logging; Google verification checks `aud`/`iss`/`email_verified` and rejects unsigned tokens.

## 3. Real-provider evidence

`manage.py check_providers` run with this machine's real `.env` (read-only, nothing sent):

```
FAIL     twilio_verify     Twilio rejected the request: HTTP 401, code 8001
FAIL     twilio_messaging  Twilio rejected the credentials: HTTP 401, code 8001
MOCK     email             EMAIL_BACKEND is django.core.mail.backends.console.EmailBackend; nothing is delivered
MOCK     stt               only the development mock transcriber is available
MOCK     llm               only the development mock LLM is available
PASS     google_signin     Google recognises the OAuth client
BLOCKED  push              there is no push channel … in-app notifications are unaffected
```

No SMS, e-mail, transcription or LLM draft was delivered by a real provider in this session. **No successful real delivery is claimed.**

## 4. Failure-handling test results

- New tests: 31 run, 31 pass (`users.test_twilio_verify_failures`, `config.test_provider_checks`).
- Red check: against the previous `patient_auth.py`, 3 of the 4 attempt-cap tests fail. They cover the gaps fixed here.
- Full backend suite: 1177 tests, 0 failures (31 skipped), run in a clean copy of the repo with the changes applied.

These tests fake the provider's answer on purpose; they prove our handling, not delivery.

## 5. Missing credentials and configuration checklist

**Twilio Verify (SMS OTP)**
- [ ] Upgrade the account from Trial (or add funds), or verify each test number as a caller ID.
- [ ] Create a Verify service and put its `VA…` SID in `TWILIO_VERIFY_SERVICE_SID`.
- [ ] Create a new API key on **the same account** as `TWILIO_ACCOUNT_SID`; set `TWILIO_API_KEY` / `TWILIO_API_SECRET`. The current root `.env` pair is rejected.
- [ ] Delete or reconcile `backend/.env`; Django never reads it, and it points at a different account.
- [ ] For India: DLT-registered sender / template on the Verify service.
- [ ] Then run: `manage.py check_providers --send-sms <your number>` and `--verify-sms <your number> <code>`.

**Twilio Messaging (SMS/WhatsApp notifications)**
- [ ] `TWILIO_MESSAGING_SERVICE_SID` (preferred) or `TWILIO_PHONE_NUMBER`; `TWILIO_WHATSAPP_FROM` plus `TWILIO_WHATSAPP_CONTENT_SID` for WhatsApp.
- [ ] Optional: `TWILIO_STATUS_CALLBACK_URL` for delivery status.

**E-mail**
- [ ] `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and a real `DEFAULT_FROM_EMAIL` on a verified sender domain. SendGrid works over SMTP: host `smtp.sendgrid.net`, user `apikey`, password = the API key. The current `SENDGRID_API_KEY` is a placeholder and no code reads that variable.
- [ ] SPF/DKIM for the sending domain.
- [ ] Then run: `manage.py check_providers --send-email <your address>`.

**AI scribe**
- [ ] `AI_SCRIBE_STT_API_KEY` (and `AI_SCRIBE_STT_BASE_URL` / `AI_SCRIBE_STT_MODEL` for a non-OpenAI host).
- [ ] `AI_SCRIBE_API_KEY` (and `AI_SCRIBE_LLM_BASE_URL`, `AI_SCRIBE_MODEL`). Current dev `.env` sets `AI_SCRIBE_MODEL=gpt-4`, which `/models` must list.
- [ ] A signed BAA/DPA with the vendor before real patient audio is sent.
- [ ] Then run: `manage.py check_providers --llm-sample` and `--transcribe <audio you own>`.
- [ ] Doctor approve/reject/regenerate, consent and audio deletion are covered by `ai_scribe/test_scribe_workflow.py`. Re-run them against the real provider once keys exist.

**Google Sign-In**
- [ ] In the Google Cloud project that owns `GOOGLE_CLIENT_ID`: authorised JavaScript origins for every web host.
- [ ] Android OAuth client: package name plus the SHA-1 of both the debug and release signing keys.
- [ ] iOS: an iOS OAuth client, `GIDClientID` plus reversed-client-ID URL scheme in `ios/Runner/Info.plist`.
- [ ] A manual sign-in with a real Google account on web, Android and iOS; a valid ID token can't be minted without one.

**Push**
- [ ] Not implemented. Needs a push channel (FCM/APNs) before `FIREBASE_CREDENTIALS_PATH` means anything.
