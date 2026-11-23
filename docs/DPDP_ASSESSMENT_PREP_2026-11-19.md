# DPDP privacy assessment — preparation report (2026-11-19)

**Purpose.** Brief the privacy assessor and counsel on what the software does today for each obligation in the Digital Personal Data Protection Act, 2023 (DPDP Act) and the DPDP Rules, 2025. Each entry also says what still needs a decision or evidence from the hospital (the Data Fiduciary).

**This is not legal advice and makes no claim of compliance.**
- Section references are an engineering reading. Counsel must confirm them against the current text, the commencement notifications (the Rules apply in phases) and any sector rules: the NMC record-keeping guidance, state clinical-establishment rules, CERT-In directions, and ABDM policy if ABDM is enabled.
- An internal review is not a substitute for the independent assessment.

Companion documents:
- [DPDP_COMPLIANCE.md](DPDP_COMPLIANCE.md): rights-request handling, breach runbook, retention table and processor register
- [PRIVACY_AND_PENTEST_PACK.md](PRIVACY_AND_PENTEST_PACK.md): Part B is the personal-data inventory, Part C the open questions
- [SECURITY_HARDENING_2026-11-19.md](SECURITY_HARDENING_2026-11-19.md): security controls and open findings

Legend: **Built** = in code with tests · **Partial** = some support, gaps listed · **Organisational** = a policy, contract or process the hospital must supply · **Open** = not built.

## 1. Assessment checklist by obligation

| # | Obligation (engineering reading; confirm) | Status | What exists | Gaps and evidence to prepare |
|---|---|---|---|---|
| 1 | **Notice** before or at collection: what data, the purpose, how to exercise rights and complain (s.5; Rules on notice content) | Partial | Privacy-notice endpoint and card in the patient portal (`/api/consent/privacy-notice/`) showing the hospital's grievance officer and the answer time. | Final notice text from counsel, in English and Hindi (and the state language). A paper notice at the registration desk for walk-in patients. Evidence that the notice is shown before staff register a patient. |
| 2 | **Consent** free, specific, informed, unambiguous; withdrawable as easily as given (s.6) | Partial | Versioned consent forms (`consent.CONSENT_FORMS`): treatment, surgery, anaesthesia, **AI recording**, data sharing. `ConsentRecord` stores the form version, signer, proxy flag and `revoked_at`. AI scribe recording refuses to start without `patient_consent` and stores `recording_consent_at` per session. Record shares are scoped, expiring and revocable. | Which processing relies on consent and which on a **legitimate use** (s.7: medical treatment, emergencies). Counsel should map each purpose. A withdrawal screen for every consent type: check that the portal offers it for each form. What happens to data already processed after withdrawal. |
| 3 | **Legitimate uses** without consent, e.g. medical emergency, epidemics, employment (s.7) | Organisational / Partial | Break-glass emergency access: a reason is required, it expires (`BREAK_GLASS_DURATION_MINUTES`, default 60), reads are audited and an Admin reviews it afterwards. | A written list of the purposes processed under s.7, and a break-glass review procedure (who reviews, how fast). |
| 4 | **Children**: verifiable parental consent; no tracking or targeted ads (s.9) | Open / Partial | Consent can be signed by a proxy (`signed_by_proxy`, `proxy_relationship`). Family access exists, but only the patient can grant it. No behavioural tracking or advertising in the product. | Guardian-initiated access and consent for minors. Age checks at registration. How "verifiable" is achieved (an ID check at the desk). The Rules' exemption for clinical establishments needs counsel's reading. |
| 5 | **Accuracy and completeness** when data is used for decisions (s.8(3)) | Partial | Corrections are audited with before/after values. Clinical rows are marked "entered in error", never silently overwritten. | A correction-request workflow exists in data-rights requests (type "correction"). Confirm staff act on it within the period. |
| 6 | **Security safeguards** to prevent breach (s.8(5); Rules on safeguards) | Built / Partial | See the security report: encryption in transit (TLS, HSTS); encrypted backups (Fernet, `BACKUP_ENCRYPTION_KEY`); per-hospital isolation tested on every endpoint; role-based access; staff SMS OTP; per-account lockout (S-L1/S-L2); audit logging; mobile tokens in Keystore/Keychain; FLAG_SECURE; no backup or device transfer. | **Encryption at rest** of the database volume and media on the real host (hosting evidence). Key management and rotation records. An independent penetration test. Access reviews of staff accounts. |
| 7 | **Breach intimation** to the Board and each affected person (s.8(6); Rules: details and timeline, 72 h report at the time of writing) | Organisational | Breach runbook in `DPDP_COMPLIANCE.md` §2. The audit log lists the patients each request read, to scope a breach. | A named incident owner and contact sheet. CERT-In 6-hour reporting for specified incidents. A tabletop exercise record. |
| 8 | **Retention and erasure** when the purpose is served or consent is withdrawn, unless law requires keeping (s.8(7); Rules on retention periods) | Partial / Open | Nothing clinical is erased automatically, by design. OTPs are purged hourly. Audit-log cleanup is configurable (`AUDIT_LOG_RETENTION_DAYS`, default 0 = keep). Erasure requests are handled through the rights-request workflow with a written reason. | **A retention schedule approved by counsel** for clinical records, consultation audio, transcripts and AI drafts, documents, audit logs, backups, and staff and family-access data. There is **no automatic deletion of consultation audio** after the note is approved: decide a period and build it. Backup expiry. |
| 9 | **Grievance redressal** and a contact person (s.8(10), s.13) | Built / Organisational | Grievance-type rights requests; a per-hospital grievance officer shown in the notice; due dates with overdue flags. | Name the officers. A documented escalation path to the Data Protection Board. |
| 10 | **Right of access**: a summary of data and processing, and the processors it was shared with (s.11) | Partial | Patient portal shows their records. Rights-request type "summary". The audit log records shares and reads. FHIR `Patient/$everything` (Admin only, when FHIR is enabled) gives a machine-readable export. | There is no **self-service download** for the patient. Staff prepare the summary by hand. Decide the format and add the processor list (Twilio, email, AI, hosting) to the answer template. |
| 11 | **Correction, completion, updating and erasure** (s.12) | Partial | Rights-request types "correction" and "erasure", answered by Admin or Manager with a reason. | As 5 and 8. |
| 12 | **Nomination** of someone to act after death or incapacity (s.14) | Partial | Rights-request type "nominee". | How a nominee is verified and then acts (no nominee login). |
| 13 | **Processors** under a valid contract; the fiduciary stays responsible (s.8(2)) | Organisational | Processor register template in `DPDP_COMPLIANCE.md` §4. | Signed DPAs with hosting, Twilio, the email provider, the AI/STT provider, Google (sign-in) and backup storage. Storage location for each. |
| 14 | **Cross-border transfer** except to restricted countries (s.16) | Organisational | AI/STT defaults point to an OpenAI-compatible API (`AI_SCRIBE_STT_BASE_URL` default `https://api.openai.com/v1`); Twilio and Google are outside India. | Confirm where each provider processes and stores data. Check against any restricted-country notification. Consider an India-region or self-hosted STT/LLM for consultation audio. |
| 15 | **Significant Data Fiduciary** duties if notified: DPO in India, independent audit, DPIA (s.10) | Organisational | — | Counsel to assess the likelihood (health data at scale). If likely: appoint a DPO, schedule a DPIA, and run a periodic independent audit. |
| 16 | **Consent managers** (s.6(7)–(9)) | Not used | — | Confirm none is required. If ABDM consent artefacts are used later, map them here. |
| 17 | **Logs** kept for the period the Rules require for traffic and processing records (Rules: one year at the time of writing; CERT-In: 180 days of ICT logs) | Partial | Audit log in the database (kept by default). Server logs rotate locally. | Ship server and nginx logs to retained, access-controlled storage for at least the longest required period. Set `AUDIT_LOG_RETENTION_DAYS` to match. |

## 2. Review areas requested

### 2.1 Patient consent lifecycle
- **Capture:** a versioned form, the signer, a proxy flag and the recording staff member; the per-session AI recording consent timestamp.
- **Withdraw:** `revoked_at` is set; record shares can be revoked and expire.
- **Audit:** every consent and share action, and every read by a share recipient, is logged.
- **Gaps:**
  - It is not documented, for each purpose, which processing stops when consent is withdrawn.
  - AI consent is captured per session, but there is no per-patient standing refusal that would stop staff asking again.
  - Minors (item 4).

### 2.2 Access control and least privilege
- Hospital-scoped viewsets fail closed. Per-hospital roles are checked per request. Patients and family members get read-only tokens tied to a grant.
- The Admin's security overview now shows only the Admin's own hospital's records (S-L5).
- Platform-wide AI configuration can no longer be written by hospital staff (S-L8).
- **For the assessor to review:** that the role-permission matrix (`users/role_permissions.py`) matches each hospital's real job roles.
- **Gap:** no periodic access review or recertification of staff accounts. This is an organisational control.

### 2.3 Audit logs and break-glass
- Covered: writes (with before/after values), sensitive reads (with patient ids), authentication events (including the new `*.locked` events), consent and shares, rights requests, and break-glass grants with a review queue.
- **Gaps:**
  - The audit table is not tamper-evident (no hash chain or write-once storage). Admins can read it, and database superusers can change it.
  - The retention default is "keep forever" (item 17).

### 2.4 PHI in logs
- Application logs carry ids, not names. Phone numbers are masked (`mask_phone`), and provider errors log the exception type only.
- Consultation audio now gets a server-chosen file name, so client file names never reach the STT log line (S-L6).
- The mobile app has no HTTP body or header logging, and only debug builds log at all.
- **Gap:** no automated PHI-redaction filter on the Django logger. Add one, or add a CI check that rejects new log calls with personal fields.

### 2.5 Data retention and deletion
- See item 8. Mobile: tokens are cleared at sign-out and after a reinstall; audio is deleted after upload, after a crash and at sign-out; app data is excluded from backup and device transfer.
- **Server-side gap:** consultation audio, documents and backups have no retention period.

### 2.6 Patient data export
- See item 10. There is a FHIR export for an Admin, but no patient self-service download.

### 2.7 Backup security
- Backups are Fernet-encrypted (`scripts/deploy/backup.sh`) and there is a restore drill.
- **Evidence needed:**
  - where the key is stored, separate from the backups
  - off-site location and its DPA
  - backup retention and expiry
  - the latest restore-test record

### 2.8 Third-party AI data handling
- The AI scribe sends consultation audio (to STT) and the transcript (to the LLM) only when the scribe is enabled with a real key. Production refuses mock providers.
- The doctor must review and approve every draft. Transcripts and drafts cannot be edited directly (S-M1).
- **Before enabling with real patients:**
  - a DPA with the provider that forbids training and retention by them
  - the processing location (item 14)
  - a per-patient AI-recording consent text approved by counsel
  - a retention period for audio and transcripts
  - a decision on whether the provider's zero-data-retention option is required

### 2.9 Cross-hospital data isolation
- Tested on every endpoint (`test_tenant_isolation`, `test_handwritten_views_isolation`, `test_tenancy_guard`).
- Fixed in this round: legacy hospital-less stock (S-L3) and the cross-hospital security overview (S-L5).
- **Note for the assessor:** one patient identity is shared across hospitals (each hospital holds its own registration). Confirm that the notice tells patients this, and that each hospital is a separate Data Fiduciary for its own registration.

## 3. Evidence pack to hand the assessor

1. This report, `DPDP_COMPLIANCE.md` and `PRIVACY_AND_PENTEST_PACK.md` Parts B and C.
2. The test run outputs in `SECURITY_HARDENING_2026-11-19.md` §4, which the assessor can re-run on staging.
3. Screenshots of:
   - the patient privacy notice
   - the consent capture screens, including AI recording
   - the rights-request screens on both sides
   - the break-glass review queue
4. Hospital-supplied:
   - signed DPAs
   - the processor locations
   - the retention schedule
   - the named grievance officer(s)
   - the incident contact sheet
   - backup and encryption-at-rest evidence from the host
   - the staff access-review record
5. The penetration test report and retest, when done.

## 4. Engineering follow-ups that would close gaps

Not built in this round, so each needs a decision first:

- Automatic deletion of consultation audio N days after the note is approved (N to be set with counsel).
- Patient self-service data download from the portal.
- Guardian-initiated access and consent for minors.
- Off-host log shipping with a fixed retention, and a tamper-evident audit log.
- A PHI-redaction logging filter, or a CI lint for log calls.
