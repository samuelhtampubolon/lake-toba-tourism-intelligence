# Security Policy

## Supported Versions
Only the latest released version of Lake Toba Tourism Intelligence receives active security maintenance.

| Version | Supported |
|---|---|
| 1.0.x | :white_check_mark: |
| < 1.0 | :x: |

## Reporting a Vulnerability
If you discover a security vulnerability or potential disclosure risk:
1. Please **do not** open a public GitHub issue.
2. Email details to: `samuel@example.com` or create a private GitHub Advisory on the repository.
3. Include reproduction steps, environment details, and affected components.
4. We aim to acknowledge receipt within 48 hours and provide remediation updates.

## Deployment Hardening Notes
- **Local Dev**: Safe for single-user localhost loopback (`127.0.0.1`).
- **LAN / Pilot**: Requires reverse proxy with valid TLS certificate and firewall restricted to authorized internal subnets.
- **Production**: Disable `/docs`, set a strong 32+ character random `APP_SECRET_KEY`, enable `COOKIE_SECURE=true`, and perform automated daily database backups.
