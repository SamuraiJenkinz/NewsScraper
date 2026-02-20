# BrasilIntel Deployment Guide

**Version:** 1.1.0
**Last Updated:** 2026-02-19

This guide covers two deployment options:
1. **Docker** - For local development and containerized deployments
2. **Windows Server** - Production deployment using Python venv and Windows Scheduled Tasks

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Option 1: Docker Deployment](#option-1-docker-deployment)
3. [Option 2: Windows Server Deployment](#option-2-windows-server-deployment)
4. [Post-Deployment Verification](#post-deployment-verification)
5. [Enterprise API Setup](#enterprise-api-setup)
6. [Maintenance](#maintenance)
7. [Backup and Recovery](#backup-and-recovery)

---

## Prerequisites

### Common Requirements

- Git for cloning the repository
- Access to configure environment variables
- Network access for:
  - Azure OpenAI API
  - Microsoft Graph API
  - MMC Core API (Factiva news, equity prices) - optional, enterprise features degrade gracefully

### Docker Deployment Requirements

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+

### Windows Server Deployment Requirements

- Windows Server 2019 or later (or Windows 10/11 for development)
- Python 3.11 or higher
- Administrator access for scheduled task setup
- PowerShell 5.1 or higher

### Optional: PDF Generation

PDF generation requires GTK3 runtime on Windows:
- Download from: https://github.com/nickvergessen/gtk-for-windows-runtime-environment-installer
- Add GTK3 `bin` directory to system PATH
- Restart after installation

> **Note:** If GTK3 is not installed, reports will still be generated and emailed as HTML. PDF attachment will be skipped with a warning.

---

## Option 1: Docker Deployment

### 1.1 Clone Repository

```bash
git clone https://github.com/SamuraiJenkinz/BrasilIntel.git
cd BrasilIntel
```

### 1.2 Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings (see [Configuration Reference](#configuration-reference) below).

### 1.3 Build and Start

```bash
# Build the image
docker-compose build

# Start in detached mode
docker-compose up -d
```

### 1.4 Verify Deployment

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f

# Test health endpoint
curl http://localhost:8000/api/health
```

### 1.5 Docker Commands Reference

```bash
# Stop the application
docker-compose down

# Restart the application
docker-compose restart

# View logs
docker-compose logs -f brasilintel

# Execute command in container
docker-compose exec brasilintel python -m app.main --help

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d
```

### 1.6 Docker Data Persistence

Data is persisted via Docker volumes:
- `./data:/app/data` - Database, logs, and report archives

To backup:
```bash
# Stop container first
docker-compose down

# Backup data directory
tar -czf brasilintel-backup.tar.gz data/

# Restart
docker-compose up -d
```

---

## Option 2: Windows Server Deployment

This is the recommended production deployment for Windows Server environments.

### 2.1 Install Python

1. Download Python 3.11+ from https://www.python.org/downloads/
2. Run installer with these options:
   - Add Python to PATH
   - Install for all users
   - Customize installation > Add Python to environment variables

3. Verify installation:
   ```powershell
   python --version
   # Should show: Python 3.11.x or higher
   ```

### 2.2 Clone Repository

```powershell
cd C:\
git clone https://github.com/SamuraiJenkinz/BrasilIntel.git
cd C:\BrasilIntel
```

### 2.3 Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 2.4 Configure Environment

```powershell
# Copy example configuration
copy .env.example .env

# Edit with your settings
notepad .env
```

**Required settings** (see [Configuration Reference](#configuration-reference) for all options):

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Microsoft Graph (Email)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
SENDER_EMAIL=brasilintel@marsh.com

# Admin Interface
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# Email Recipients
REPORT_RECIPIENTS_HEALTH=user1@marsh.com,user2@marsh.com
REPORT_RECIPIENTS_DENTAL=dental-team@marsh.com
REPORT_RECIPIENTS_GROUP_LIFE=life-team@marsh.com
```

**Enterprise API settings** (optional - for Factiva news and equity prices):

```env
# MMC Core API
MMC_API_BASE_URL=https://mmc-dallas-int-non-prod-ingress.mgti.mmc.com
MMC_API_CLIENT_ID=your-client-id
MMC_API_CLIENT_SECRET=your-client-secret
MMC_API_KEY=your-api-key
```

> **Note:** When MMC credentials are not configured, the app boots normally. Enterprise features (Factiva collection, equity prices) are skipped gracefully.

### 2.5 Initialize Database

```powershell
# Start the application once to initialize the database
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Press Ctrl+C after you see "Application startup complete"

# Run enterprise API migrations (creates api_events, factiva_config, equity_tickers tables)
python scripts/migrate_007_enterprise_api_tables.py
python scripts/migrate_008_factiva_date_range.py
```

### 2.6 Import Insurer Data

```powershell
# Activate virtual environment if not already active
.\venv\Scripts\Activate.ps1

# Start the server
Start-Process powershell -ArgumentList "-Command", "cd C:\BrasilIntel; .\venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

# Wait for server to start, then import data via API or admin UI
# Option 1: Use admin UI at http://localhost:8000/admin/import
# Option 2: Use API (see below)
```

### 2.7 Setup Scheduled Tasks

Run PowerShell as Administrator:

```powershell
cd C:\BrasilIntel

# Setup all scheduled tasks (Health 6 AM, Dental 7 AM, Group Life 8 AM)
.\deploy\setup_scheduled_task.ps1

# Or setup specific category
.\deploy\setup_scheduled_task.ps1 -Category health

# Setup and run immediately
.\deploy\setup_scheduled_task.ps1 -RunNow
```

This creates Windows Scheduled Tasks that:
- Run daily at configured times (Sao Paulo timezone)
- Execute as SYSTEM account
- Auto-restart on failure (up to 3 times)
- Log output to `data\logs\`

### 2.8 Verify Scheduled Tasks

```powershell
# Check status of all tasks
.\deploy\manage_service.ps1 -Action status
```

Expected output:
```
=== Scheduled Tasks Status ===

Task: BrasilIntel_health
  State: Ready
  Last Run: (none or date)
  Last Result: 0
  Next Run: 2/6/2026 6:00:00 AM

Task: BrasilIntel_dental
  State: Ready
  Last Run: (none or date)
  Last Result: 0
  Next Run: 2/6/2026 7:00:00 AM

Task: BrasilIntel_group_life
  State: Ready
  Last Run: (none or date)
  Last Result: 0
  Next Run: 2/6/2026 8:00:00 AM
```

### 2.9 Start the Web Server (Optional)

If you want the admin dashboard and API available continuously:

**Option A: Run manually**
```powershell
cd C:\BrasilIntel
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Option B: Run at startup via Windows Task Scheduler (Recommended)**

```powershell
# Create batch script for web server
$BatchContent = @"
@echo off
cd /d C:\BrasilIntel
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
"@
Set-Content -Path "C:\BrasilIntel\deploy\run_webserver.bat" -Value $BatchContent

# Create scheduled task to run at startup
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c C:\BrasilIntel\deploy\run_webserver.bat" -WorkingDirectory "C:\BrasilIntel"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName "BrasilIntel_WebServer" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "BrasilIntel Web Server"
```

**Manage the web server task:**
```powershell
# Start immediately
Start-ScheduledTask -TaskName "BrasilIntel_WebServer"

# Check status
Get-ScheduledTask -TaskName "BrasilIntel_WebServer" | Select-Object TaskName, State

# Stop/Disable
Stop-ScheduledTask -TaskName "BrasilIntel_WebServer"
Disable-ScheduledTask -TaskName "BrasilIntel_WebServer"

# Remove
Unregister-ScheduledTask -TaskName "BrasilIntel_WebServer" -Confirm:$false
```

---

## Configuration Reference

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEBUG` | No | `false` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `DATABASE_URL` | No | `sqlite:///./data/brasilintel.db` | Database connection string |
| `DATA_DIR` | No | `./data` | Data directory path |

### Azure OpenAI

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Yes | API key |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Deployment name (e.g., `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | No | API version (default: `2024-08-01-preview`) |
| `USE_LLM_SUMMARY` | No | Enable AI summaries (default: `true`) |

### Microsoft Graph (Email)

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_TENANT_ID` | Yes | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | Yes | App registration client ID |
| `AZURE_CLIENT_SECRET` | Yes | App registration client secret |
| `SENDER_EMAIL` | Yes | Email address to send from |

### MMC Core API (Enterprise)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MMC_API_BASE_URL` | No* | - | MMC Core API base URL (Apigee gateway) |
| `MMC_API_CLIENT_ID` | No* | - | OAuth2 client ID |
| `MMC_API_CLIENT_SECRET` | No* | - | OAuth2 client secret |
| `MMC_API_KEY` | No* | - | X-Api-Key for data endpoints |
| `MMC_API_TOKEN_PATH` | No | `/coreapi/access-management/v1/token` | Token endpoint path |

> *Required for Factiva news collection and equity price enrichment. When not configured, enterprise features are skipped gracefully.

### Admin Interface

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_USERNAME` | No | `admin` | Admin login username |
| `ADMIN_PASSWORD` | Yes | - | Admin login password |

### Report Recipients

| Variable | Description |
|----------|-------------|
| `REPORT_RECIPIENTS_HEALTH` | TO recipients for Health reports (comma-separated) |
| `REPORT_RECIPIENTS_HEALTH_CC` | CC recipients for Health reports |
| `REPORT_RECIPIENTS_HEALTH_BCC` | BCC recipients for Health reports |
| `REPORT_RECIPIENTS_DENTAL` | TO recipients for Dental reports |
| `REPORT_RECIPIENTS_DENTAL_CC` | CC recipients for Dental reports |
| `REPORT_RECIPIENTS_DENTAL_BCC` | BCC recipients for Dental reports |
| `REPORT_RECIPIENTS_GROUP_LIFE` | TO recipients for Group Life reports |
| `REPORT_RECIPIENTS_GROUP_LIFE_CC` | CC recipients for Group Life reports |
| `REPORT_RECIPIENTS_GROUP_LIFE_BCC` | BCC recipients for Group Life reports |

### Scheduling

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULER_ENABLED` | `true` | Enable/disable scheduler |
| `SCHEDULE_HEALTH_CRON` | `0 6 * * *` | Health schedule (6 AM) |
| `SCHEDULE_DENTAL_CRON` | `0 7 * * *` | Dental schedule (7 AM) |
| `SCHEDULE_GROUP_LIFE_CRON` | `0 8 * * *` | Group Life schedule (8 AM) |
| `SCHEDULE_HEALTH_ENABLED` | `true` | Enable Health schedule |
| `SCHEDULE_DENTAL_ENABLED` | `true` | Enable Dental schedule |
| `SCHEDULE_GROUP_LIFE_ENABLED` | `true` | Enable Group Life schedule |

---

## Post-Deployment Verification

### 1. Health Check

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "brasilintel",
  "checks": {
    "database": {"status": "healthy"},
    "data_directory": {"status": "healthy"},
    "scheduler": {"status": "healthy"}
  }
}
```

### 2. Admin Dashboard

1. Open browser to `http://localhost:8000/admin/`
2. Login with configured credentials
3. Verify:
   - Dashboard loads with category cards
   - System status shows green indicators
   - Insurers page shows data

### 3. Manual Test Run

```powershell
# Windows
.\deploy\manage_service.ps1 -Action run-now -Category health

# Or via API
curl -X POST "http://localhost:8000/api/runs/execute/category" -H "Content-Type: application/json" -d '{"category": "Health", "send_email": false}'
```

### 4. Check Logs

```powershell
# Windows
.\deploy\manage_service.ps1 -Action logs -Category health

# Or directly
Get-Content .\data\logs\health_*.log -Tail 50
```

---

## Enterprise API Setup

This section covers setting up Factiva news collection and equity price enrichment via MMC Core API.

### 1. Configure Credentials

Add the following to your `.env` file:

```env
MMC_API_BASE_URL=https://mmc-dallas-int-non-prod-ingress.mgti.mmc.com
MMC_API_CLIENT_ID=your-client-id
MMC_API_CLIENT_SECRET=your-client-secret
MMC_API_KEY=your-api-key
```

### 2. Run Database Migration

```powershell
python scripts/migrate_007_enterprise_api_tables.py
python scripts/migrate_008_factiva_date_range.py
```

This creates three tables:
- `api_events` - Logs all enterprise API calls (token requests, Factiva fetches, equity lookups)
- `factiva_config` - Stores Factiva query parameters (industry codes, keywords, date range)
- `equity_tickers` - Maps insurers to B3 ticker symbols

### 3. Validate Authentication

```powershell
python scripts/test_auth.py
```

This script:
- Attempts to acquire a JWT token from MMC Access Management API
- Verifies token structure and expiry
- Logs the result to `api_events` table
- Exits 0 on success, 1 on failure

### 4. Validate Factiva Collection

```powershell
python scripts/test_factiva.py
```

This script:
- Collects a test batch of articles from Factiva
- Performs URL deduplication
- Runs semantic deduplication
- Validates article fields
- Exits 0 on success (also exits 0 if credentials not configured)

### 5. Seed Factiva Configuration

```powershell
python scripts/seed_factiva_config.py
```

This populates default Factiva query parameters:
- Brazilian insurance industry codes (i82, i8200, i82001, i82002, i82003)
- Portuguese insurance keywords (seguro, seguradora, resseguro, etc.)
- 48-hour date window for article collection

### 6. Configure Equity Tickers

1. Open the admin dashboard: `http://localhost:8000/admin/equity`
2. Add ticker mappings (e.g., "SulAmerica" -> "SULA11", exchange "BVMF")
3. Tickers are fetched during each pipeline run and displayed as equity chips in reports

### 7. Verify End-to-End

After setup, trigger a manual run and verify:
- Factiva articles appear in the run results
- Articles are matched to insurers
- Equity chips display in the generated report
- API events are logged in the database

---

## Maintenance

### Management Commands (Windows)

```powershell
# Check status of all scheduled tasks
.\deploy\manage_service.ps1 -Action status

# Run a category immediately
.\deploy\manage_service.ps1 -Action run-now -Category health

# Enable/disable tasks
.\deploy\manage_service.ps1 -Action start -Category all
.\deploy\manage_service.ps1 -Action stop -Category dental

# View logs
.\deploy\manage_service.ps1 -Action logs -Category health -LogLines 100

# Remove all scheduled tasks
.\deploy\manage_service.ps1 -Action remove

# Test server connectivity
.\deploy\manage_service.ps1 -Action test
```

### Updating the Application

```powershell
cd C:\BrasilIntel

# Stop scheduled tasks
.\deploy\manage_service.ps1 -Action stop

# Pull latest code
git pull origin master

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Update dependencies
pip install -r requirements.txt

# Run any database migrations
python scripts\migrate_007_enterprise_api_tables.py
python scripts\migrate_008_factiva_date_range.py

# Re-enable scheduled tasks
.\deploy\manage_service.ps1 -Action start
```

### Log Rotation

Logs are stored in `data\logs\` with date-stamped filenames. Implement log rotation:

```powershell
# Delete logs older than 30 days
Get-ChildItem "C:\BrasilIntel\data\logs\*.log" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item
```

Add this as a weekly scheduled task for automatic cleanup.

---

## Backup and Recovery

### What to Backup

1. **Database:** `data\brasilintel.db` (includes api_events, factiva_config, equity_tickers)
2. **Configuration:** `.env`
3. **Report Archive:** `app\storage\reports\`

### Backup Script

```powershell
# backup.ps1
$BackupDir = "C:\Backups\BrasilIntel"
$Date = Get-Date -Format "yyyy-MM-dd"
$BackupPath = "$BackupDir\$Date"

New-Item -ItemType Directory -Path $BackupPath -Force

# Backup database
Copy-Item "C:\BrasilIntel\data\brasilintel.db" "$BackupPath\brasilintel.db"

# Backup configuration
Copy-Item "C:\BrasilIntel\.env" "$BackupPath\.env"

# Backup report archive (optional - can be large)
Compress-Archive -Path "C:\BrasilIntel\app\storage\reports" -DestinationPath "$BackupPath\reports.zip"

Write-Host "Backup complete: $BackupPath"
```

### Recovery

```powershell
# Stop services
.\deploy\manage_service.ps1 -Action stop

# Restore database
Copy-Item "C:\Backups\BrasilIntel\2026-02-05\brasilintel.db" "C:\BrasilIntel\data\brasilintel.db"

# Restore configuration
Copy-Item "C:\Backups\BrasilIntel\2026-02-05\.env" "C:\BrasilIntel\.env"

# Restart services
.\deploy\manage_service.ps1 -Action start
```

---

## Firewall Configuration

If the server needs to be accessible from other machines:

```powershell
# Allow inbound on port 8000
New-NetFirewallRule -DisplayName "BrasilIntel Web" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

## Security Recommendations

1. **Change default admin password** - Never use `admin` in production
2. **Use HTTPS** - Put behind a reverse proxy (IIS, nginx) with SSL
3. **Restrict network access** - Only allow necessary IP ranges
4. **Secure .env file** - Set restrictive file permissions
5. **Regular updates** - Keep Python and dependencies updated
6. **Monitor logs** - Set up alerting for errors
7. **Monitor API events** - Check `api_events` table for auth failures or excessive usage

---

## Support

For issues:
1. Check logs in `data\logs\`
2. Verify configuration in `.env`
3. Test health endpoint: `/api/health`
4. Validate enterprise auth: `python scripts/test_auth.py`
5. Review troubleshooting section in [USER_GUIDE.md](USER_GUIDE.md)

---

*BrasilIntel v1.1 -- [SamuraiJenkinz/BrasilIntel](https://github.com/SamuraiJenkinz/BrasilIntel)*
