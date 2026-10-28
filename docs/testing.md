# Testing Strategy & Execution Verification

## 1. Test Suite Architecture
The test suite is organized into modular categories covering domain mathematics, security controls, CSV ingestion edge cases, and HTTP endpoint flows:

```
tests/
├── conftest.py                   # In-memory SQLite StaticPool, seed users, auth client
├── test_auth_security.py         # Password hashing, session revocation, CSRF, formula injection
├── test_domain_calculations.py   # Seasonal-Naive baseline, MAE/MASE, zero-denominator ROI
├── test_ingestion_quality.py     # CSV parsing, BOM, bad dates, unknown dest, quality profiler
└── test_api_routes.py            # /health/live, /health/ready, /login, /dashboard, auth gates
```

---

## 2. Test Execution Commands

### Run Full Test Suite (PowerShell)
```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

### Run Live Server Smoke Test
```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py http://127.0.0.1:8000
```

---

## 3. Verified Test Outcome Summary

| Test File | Tests Run | Passed | Failed | Key Invariant Asserted |
|---|---|---|---|---|
| `test_auth_security.py` | 4 | 4 | 0 | Argon2id verification, session revocation on logout, CSRF token validation, formula injection prefixing |
| `test_domain_calculations.py` | 6 | 6 | 0 | Hand-verified Lag-7 seasonal-naive repeat, MAE hand calculation, zero-spend ROI zero-division safety |
| `test_ingestion_quality.py` | 4 | 4 | 0 | UTF-8 with BOM support, date format validation, unknown destination rejection, data quality null/gap profiler |
| `test_api_routes.py` | 5 | 5 | 0 | `/health/live`, `/health/ready`, login password rejection & success, protected route denial, CSRF state change rejection |
| **Total Suite** | **19** | **19** | **0** | **100% Pass Rate** |
