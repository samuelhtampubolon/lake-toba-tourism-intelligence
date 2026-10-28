# Security Policy, Threat Model & Privacy Architecture

## GitHub Pages showcase boundary

The `docs/` site is a public, static presentation that uses only synthetic figures. It is not the application and must never receive database files, exports, uploaded CSV files, credentials, API keys, session tokens, or real visitor data. It uses a restrictive meta Content Security Policy, has no third-party font/CDN dependencies, and performs no fetch/XHR requests. GitHub Pages does not support this repository setting arbitrary HTTP response headers; the meta policy is defense in depth, not a replacement for a production web-server policy.

## 1. Threat Modeling (STRIDE Matrix)

| Threat Category | Asset at Risk | Potential Vector | Implemented Defense | Residual Risk & Guidance |
|---|---|---|---|---|
| **Spoofing** | User identity & admin privileges | Credential brute force, weak sessions | Argon2id password hashing, opaque 32-byte session tokens with DB SHA-256 digests, inactivity & absolute timeouts | Enforce strong passwords during CLI bootstrap |
| **Tampering** | Tourism observations & database integrity | Unauthorized record modification or SQL injection | Parameterized SQLAlchemy statements, foreign key constraints, atomic transactions | Never expose direct SQLite file access to clients |
| **Repudiation** | Dataset deletion, high-budget scenario creation | Operator denying destructive changes | Append-only `audit_events` logging user ID, action, timestamp, and entity ID | Ensure server filesystem logs are periodically archived |
| **Information Disclosure** | Server diagnostics, secrets in logs | Stack trace leakage, config dump | Global exception handler returning generic errors; log redaction masking `token`, `secret`, `password` | In production, disable `/docs` endpoint |
| **Denial of Service** | Process memory & thread starvation | Huge CSV file uploads, complex simulations | Max upload limit (10MB), bounded 50k rows, bounded in-memory aggregation cache (100 entries) | Deploy behind a reverse proxy (Nginx/Caddy) with rate limits |
| **Elevation of Privilege** | Administrative commands, dataset deletion | Cross-Site Request Forgery (CSRF) | Per-session synchronizer CSRF tokens verified on every POST/PUT/DELETE; server-side RBAC dependencies | Keep `SESSION_COOKIE_NAME` with `HttpOnly` and `SameSite=Lax` |

---

## 2. OWASP ASVS Alignment Checklist

- **V2: Authentication**: Handled via Argon2id (or OWASP-recommended PBKDF2-HMAC-SHA256 310,000 iterations). Opaque session tokens rotated on login and revoked on logout.
- **V3: Session Management**: Cookies configured with `HttpOnly=True`, `SameSite="lax"`, and path scoped. Configurable inactivity timeout (60 min) and absolute lifetime (8 hours).
- **V4: Access Control**: Role-based access control (`business_owner`, `tourism_analyst`, `marketing_manager`, `read_only_executive`) checked server-side in router dependencies.
- **V5: Validation & Sanitization**: Strict input schemas, CSV size bounds, encoding validation (`utf-8`, `utf-8-sig`), numeric ranges.
- **V12: File Uploads & CSV Exports**:
  - Uploaded files are processed strictly in memory and saved as normalized SQLite records. No executable scripts or macros are saved.
  - CSV exports neutralize formula injection: all cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are prefixed with a single quote (`'`).
- **V14: Configuration & Headers**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy: default-src 'self' ...`

---

## 3. Data Privacy & Minimization
- The customer segmentation model is derived purely from macro behavioral metrics (group size, stay duration, daily spend).
- No personally identifiable information (PII), national identity numbers (NIK), passports, or payment card details are stored or processed.
- Synthetic demo data is marked with visible `is_synthetic=True` badges to prevent confusing synthetic benchmarks with certified census data.
