# Deployment & Installation Runbook

## 1. Quick Start Guide (Windows PowerShell First)

### Step 1: Provision Environment & Initialize Schema
Run the setup script from the repository root:
```powershell
.\scripts\setup.ps1
```
This script validates Python 3.12+, provisions `.venv`, installs locked dependencies, and initializes SQLite tables with baseline Lake Toba destinations.

### Step 2: Bootstrap the Initial Administrator
Run the secure CLI command:
```powershell
.\.venv\Scripts\python.exe scripts\cli.py bootstrap-admin --username admin --email admin@laketoba.local --password AdminPassword123!
```

### Step 3: Seed Synthetic Benchmark Data (Optional)
```powershell
.\.venv\Scripts\python.exe scripts\cli.py seed-demo
```
This populates 2 full years of daily observation facts (4,386 records) across Parapat, Tuktuk, Balige, Tongging, Pangururan, and Silangit.

### Step 4: Start the Local Development Server
```powershell
.\scripts\run_local.ps1
```
The server will bind strictly to loopback `http://127.0.0.1:8000` and write its PID to `data\server.pid`.

### Step 5: Stop the Server
```powershell
.\scripts\stop_local.ps1
```
Safely terminates only the server PID without killing unrelated Python tasks.

---

## 2. Deployment Mode Matrix

| Capability | Local Development | Trusted LAN Pilot | Public Production Deployment |
|---|---|---|---|
| **Network Binding** | `127.0.0.1` (Loopback only) | Approved LAN IP Subnet | Reverse Proxy (`0.0.0.0` blocked directly) |
| **TLS / HTTPS** | Optional (Plain HTTP) | Required via Private CA / Reverse Proxy | **Mandatory** via Valid TLS (Certbot/Let's Encrypt) |
| **Session Cookie** | `Secure=False` | `Secure=True` | `Secure=True`, `HttpOnly=True`, `SameSite=Lax` |
| **API Docs (`/docs`)**| Enabled | Disabled | **Disabled** |
| **Secret Key** | Default Dev Key Allowed | **Must be 32+ Random Chars** | **Must be 32+ Random Chars** |
| **Workers** | 1 Process (SQLite Safe) | 1 Process | 1 Process (or migrate to PostgreSQL for multi-worker) |

---

## 3. Database Backup & Restore Operations

### Hot Consistent Backup
```powershell
.\.venv\Scripts\python.exe scripts\cli.py backup
```
Creates a snapshot file in `data\backups\lake_toba_backup_<TIMESTAMP>.sqlite`.

### Restore Backup with Integrity Verification
```powershell
.\.venv\Scripts\python.exe scripts\cli.py restore data\backups\lake_toba_backup_YYYYMMDD_HHMMSS.sqlite -y
```
Runs `PRAGMA integrity_check;` before restoring live data.
