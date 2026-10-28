# Operations Runbook: Daily Maintenance & Incident Response

## 1. Daily Operations & System Health

### 1.1 Automated Health Verification
Verify that the service is running and ready:
```powershell
curl http://127.0.0.1:8000/health/live
# Expected: {"status": "alive", "service": "lake-toba-tourism-intelligence"}

curl http://127.0.0.1:8000/health/ready
# Expected: {"status": "ready", "database": "connected", "service": "lake-toba-tourism-intelligence"}
```

### 1.2 System Environment Diagnostic Report
Run the diagnostic tool to inspect active database path, integrity, and configuration:
```powershell
.\.venv\Scripts\python.exe scripts\cli.py report-env
```

---

## 2. User Administration & Access Recovery

### Create Additional Authorized Users
Log into the web application as a `business_owner` or invoke the CLI:
```powershell
.\.venv\Scripts\python.exe scripts\cli.py bootstrap-admin --username analyst_jane --email jane@laketoba.local --password JanePassword123! --force
```

### Emergency Session Invalidation
If a user account or cookie is compromised:
1. Access the SQLite database:
   ```powershell
   .\.venv\Scripts\python.exe -c "from app.database import SessionLocal; from app.models.entities import UserSession; db = SessionLocal(); db.query(UserSession).update({'is_revoked': True}); db.commit(); print('[+] All active sessions revoked.')"
   ```
2. Restart the application. All users will be forced to re-authenticate with their credentials.

---

## 3. Troubleshooting Matrix

| Symptom | Probable Cause | Corrective Procedure |
|---|---|---|
| `Address already in use: 8000` | Stale or duplicate process | Run `.\scripts\stop_local.ps1` or pass an alternate port: `.\scripts\run_local.ps1 -Port 8080`. |
| `sqlite3.OperationalError: database is locked` | Concurrent write lock | Ensure only 1 worker process is running (`workers=1`). The application enforces a 15-second busy timeout. |
| `403 Forbidden: Invalid or missing CSRF security token` | Expired session or state-changing form tampering | Ensure request includes valid session cookie and form has `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`. |
| `File exceeds maximum allowed size (10 MB)` | Oversized CSV import | Split input CSV or adjust `MAX_UPLOAD_SIZE_BYTES` in `.env` if authorized. |
| `Data quality warning: Missing calendar dates` | Date continuity gaps in uploaded series | Inspect the Data Quality profile (`/datasets/{id}/quality`) to examine flagged gap windows. |

---

## 4. Disaster Recovery & Database Restoration Drill
1. Shut down the live process: `.\scripts\stop_local.ps1`
2. Validate snapshot integrity: `.\.venv\Scripts\python.exe scripts\cli.py restore data\backups\<FILE>.sqlite -y`
3. Restart process: `.\scripts\run_local.ps1`
4. Confirm health: `.\.venv\Scripts\python.exe scripts\smoke_test.py`
