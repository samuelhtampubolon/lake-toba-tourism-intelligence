# Requirements & Traceability Matrix

## 1. Project Purpose & Scope
The **Lake Toba Tourism Intelligence** platform is a secure, local-first decision-support software application designed for tourism demand analysis, customer segmentation, revenue forecasting, and marketing-budget scenarios for the Lake Toba region (North Sumatra, Indonesia).

### Primary Stakeholders & Roles
1. **Tourism Business Owner (`business_owner`)**: Operates regional hotel chains, ferries, or resorts; oversees ROI scenarios, administrative credentials, system audit logs, and backups.
2. **Tourism Analyst (`tourism_analyst`)**: Ingests UTF-8 CSV datasets, evaluates data quality, conducts time-series aggregations, trains demand forecasts, and exports reports.
3. **Marketing Manager (`marketing_manager`)**: Formulates promotional campaigns, simulates price adjustments, models seasonality shifts, and measures simulated ROI.
4. **Read-Only Executive (`read_only_executive`)**: Views regional performance dashboards, forecast intervals, customer segments, and compiled management briefs.

---

## 2. Requirements Traceability Matrix (RTM)

| Req ID | Requirement Description | Implementation Module | Automated Test Gate |
|---|---|---|---|
| **REQ-ING-01** | Support UTF-8 and UTF-8 with BOM CSV ingestion with column mapping | `app/services/ingestion_service.py` | `tests/test_ingestion_quality.py::test_csv_preview_and_bom_support` |
| **REQ-ING-02** | Atomic rejection of malformed dates or unknown destination codes | `app/services/ingestion_service.py` | `tests/test_ingestion_quality.py::test_csv_rejection_on_invalid_date` |
| **REQ-QUAL-01** | Data quality profiler computing null counts, duplicate keys, and date gaps | `app/services/quality_service.py` | `tests/test_ingestion_quality.py::test_data_quality_profiler_metrics` |
| **REQ-AGG-01** | Time-series aggregation across daily, weekly, and monthly temporal grains | `app/services/analytics_service.py` | `tests/test_domain_calculations.py` & API integration tests |
| **REQ-FCST-01** | Mandated Seasonal-Naive baseline benchmark (Lag-7 cycle) | `app/services/forecast_service.py` | `tests/test_domain_calculations.py::test_seasonal_naive_baseline_hand_checked` |
| **REQ-FCST-02** | Chronological train-val split preventing future lookahead data leakage | `app/services/forecast_service.py` | `tests/test_domain_calculations.py` |
| **REQ-FCST-03** | MAE and MASE calculation against in-sample naive error | `app/services/forecast_service.py` | `tests/test_domain_calculations.py::test_mae_calculation_hand_checked` |
| **REQ-SCEN-01** | What-if scenario budget & pricing simulator with diminishing returns | `app/services/scenario_service.py` | `tests/test_domain_calculations.py::test_scenario_roi_positive_spend` |
| **REQ-SCEN-02** | Graceful zero-denominator ROI calculation handling $0 spend safely | `app/services/scenario_service.py` | `tests/test_domain_calculations.py::test_scenario_roi_zero_spend_no_zero_division` |
| **REQ-SEC-01** | Argon2id password hashing with salt and PBKDF2 fallback | `app/security/auth.py` | `tests/test_auth_security.py::test_password_hashing` |
| **REQ-SEC-02** | Opaque server-side session tokens with SHA-256 hash storage | `app/security/auth.py` | `tests/test_auth_security.py::test_session_lifecycle` |
| **REQ-SEC-03** | Synchronizer CSRF token validation on state-changing requests | `app/security/csrf.py` | `tests/test_auth_security.py::test_csrf_token_verification` |
| **REQ-SEC-04** | CSV Formula Injection defense neutralizing dangerous leading chars | `app/services/export_service.py` | `tests/test_auth_security.py::test_csv_formula_injection_defense` |
| **REQ-OPS-01** | Hot consistent SQLite snapshots via native SQLite backup API | `app/database.py`, `scripts/cli.py` | CLI backup/restore verification |
| **REQ-OPS-02** | Pre-restore PRAGMA integrity verification | `app/database.py`, `scripts/cli.py` | CLI backup/restore verification |

---

## 3. Explicit Non-Goals
1. **No Cloud-Only Dependency**: Product does not require AWS, GCP, Azure, or remote SaaS APIs to execute full baseline analytics.
2. **No Unbounded Code Execution**: Uploaded CSV files are strictly parsed as data tables; no macros or arbitrary scripts are executed.
3. **No Automatic Network Exposure**: The development application binds exclusively to loopback `127.0.0.1` and never opens public firewall ports autonomously.
4. **No Fabrication of Production Claims**: Synthetic benchmark data is unmistakably flagged with visual warning badges.
