# DPDP Act operations: rights requests, breaches, retention, processors

Applies the Digital Personal Data Protection Act 2023 and DPDP Rules 2025 to this HMS. **This is engineering's working note, not legal advice.** Confirm the duties, dates and wording with counsel before go-live. The Rules come into force in phases, so check which apply to you today.

## 1. Rights requests (built, P1-03)

| Who | Where | What |
|---|---|---|
| Patient | Patient portal → Consent → **Your data rights** | Files a request: summary of data, correction, erasure, complaint (grievance), nominee. Sees status and answer. |
| Admin / Hospital Manager | Admin dashboard → **Patients' data requests** | Answers by the due date: in progress, completed or refused, with a written reason. Overdue requests are flagged. |
| Everyone | Privacy notice (same card) | Shows the hospital's grievance officer (set in Admin → Hospitals) and the answer time. |

- **Answer time:** `DPDP_RESPONSE_DAYS` (default 30). Confirm the period with counsel.
- **Audit:** every filing and answer is audited (`consent.rights_request.create` / `.respond`).
- **Nothing is erased automatically.** For erasure, weigh the request against record-keeping duties (section 3). Remove what you may; explain in the answer what must be kept and why.
- **Access requests:** use the patient timeline and the Audit log (who read the record, and the shares made) to prepare the summary.

**Before go-live:**
- name a grievance officer for every hospital
- publish the privacy notice text at registration (paper and portal)
- train the Admin/Manager who will answer requests

## 2. Personal data breach runbook

1. **Contain** (within the hour):
   - revoke leaked credentials and JWT keys (rotate `JWT_PRIVATE_KEY`)
   - disable affected accounts
   - preserve logs and the audit table
2. **Assess:**
   - which hospitals and patients were affected
   - what data (identity, clinical, financial) was involved
   - how it happened

   Use the Audit log (`audit_auditlog`, `*.read` rows list patient ids per request) and the server logs.
3. **Notify:**
   - the Data Protection Board of India and every affected patient, without delay
   - a detailed report to the Board within the period the Rules set (72 hours at the time of writing; confirm)

   The patient notice says what happened, what data was involved, what you did, what they can do, and the grievance officer's contact.
4. **Record:** keep the timeline, decisions and notices with the incident ticket.
5. **Review:** post-mortem within two weeks, with fixes tracked to closure.

## 3. Retention schedule (confirm with counsel and state rules)

| Data | Keep for | Where it is set |
|---|---|---|
| In-patient medical records | at least 3 years from the record (NMC/MCI guidance); longer for medico-legal cases and minors per state law | not deleted by the system |
| Schedule H1 register | 3 years | Pharmacy → Schedule H1 register (printable) |
| GST tax invoices | 6 years (the 72-month accounts rule; confirm) | not deleted by the system |
| Audit log | `AUDIT_LOG_RETENTION_DAYS`; must cover the longest record you must account for | `audit.tasks.cleanup_old_audit_logs` (daily) |
| OTP codes | minutes; expired rows purged hourly | `notifications.tasks.cleanup_expired_otp` |
| Backups | as long as the data they contain may be kept | backup job (P0-06) |

## 4. Processor (vendor) register

| Processor | Purpose | Data shared | Contract / DPA | Location |
|---|---|---|---|---|
| Hosting provider | runs the servers and database | all | to sign | to record |
| Twilio | SMS, WhatsApp, voice, OTP | mobile number, message text | Twilio DPA | to record |
| Email provider (SMTP) | invites, OTP, notices | email address, message text | to sign | to record |
| AI scribe / LLM provider (if enabled) | drafts from consultations | audio/transcript of the consultation | to sign before enabling | to record |
| Backup storage | off-site copies | all (encrypted) | to sign | to record |

Keep this table current; add a row before any new provider sees personal data.
