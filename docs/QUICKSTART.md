# BrasilIntel Quickstart Guide

Get up and running in 5 minutes.

---

## 1. Prerequisites

- Python 3.11+
- Azure OpenAI API access
- Microsoft 365 (for email delivery)
- Apify account (for web scraping)

---

## 2. Install

```powershell
# Clone and setup
git clone https://github.com/SamuraiJenkinz/BrasilIntel.git
cd BrasilIntel

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## 3. Configure

```powershell
copy .env.example .env
notepad .env
```

**Required settings:**

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Email (Microsoft Graph)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
SENDER_EMAIL=brasilintel@yourcompany.com

# Web Scraping
APIFY_TOKEN=your-apify-token

# Admin Login
ADMIN_PASSWORD=your-secure-password

# Report Recipients
REPORT_RECIPIENTS_HEALTH=user1@company.com,user2@company.com
REPORT_RECIPIENTS_DENTAL=dental-team@company.com
REPORT_RECIPIENTS_GROUP_LIFE=life-team@company.com
```

---

## 4. Start

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open: **http://localhost:8000/admin/**

Login with `admin` / your configured password.

---

## 5. Import Insurers

1. Go to **Import** in the admin menu
2. Upload your Excel file with columns:
   - `ANS Code` (required) - Regulatory registration number
   - `Name` (required) - Insurer name
   - `Category` (required) - "Health", "Dental", or "Group Life"
3. Review preview and click **Confirm Import**

---

## 6. Run Your First Report

**Option A: Admin Dashboard**
1. Go to **Schedules**
2. Click **Run Now** for any category

**Option B: API**
```bash
curl -X POST "http://localhost:8000/api/runs/execute/category" ^
  -H "Content-Type: application/json" ^
  -d "{\"category\": \"Health\", \"send_email\": false}"
```

---

## 7. Schedule Daily Reports

Run PowerShell as Administrator:

```powershell
.\deploy\setup_scheduled_task.ps1
```

This creates scheduled tasks:
| Category | Time (São Paulo) |
|----------|------------------|
| Health | 6:00 AM |
| Dental | 7:00 AM |
| Group Life | 8:00 AM |

Check status:
```powershell
.\deploy\manage_service.ps1 -Action status
```

---

## Quick Reference

### Admin Dashboard
- **Dashboard**: http://localhost:8000/admin/
- **Insurers**: View/edit monitored insurers
- **Import**: Upload insurer data
- **Recipients**: View configured email recipients per category
- **Schedules**: Manage automated runs and trigger manual runs
- **Settings**: View system configuration status

### Key Commands
```powershell
# Check scheduled task status
.\deploy\manage_service.ps1 -Action status

# Run category immediately
.\deploy\manage_service.ps1 -Action run-now -Category health

# View logs
.\deploy\manage_service.ps1 -Action logs -Category health
```

### API Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | System health check |
| `GET /api/insurers` | List all insurers |
| `GET /api/insurers/search?q=` | Search insurers |
| `POST /api/runs/execute/category` | Run a category |
| `GET /api/runs/latest` | Latest run per category |
| `GET /api/reports/archive` | Browse archived reports |
| `GET /api/schedules` | List all schedules |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Admin password not configured" | Set `ADMIN_PASSWORD` in `.env` |
| "Azure OpenAI not configured" | Set all `AZURE_OPENAI_*` variables |
| "Apify token not configured" | Set `APIFY_TOKEN` in `.env` |
| Port 8000 in use | Change `PORT` in `.env` or kill existing process |

---

## Next Steps

- [Full User Guide](USER_GUIDE.md) - Complete feature documentation
- [Deployment Guide](DEPLOYMENT.md) - Production deployment options
- API docs at `/docs` when server is running

---

*BrasilIntel v1.0 — [SamuraiJenkinz/BrasilIntel](https://github.com/SamuraiJenkinz/BrasilIntel)*
