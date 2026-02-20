# BrasilIntel

Automated competitive intelligence system for monitoring Brazilian insurers.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-proprietary-red.svg)]()

---

## Overview

BrasilIntel monitors **897 Brazilian insurers** across three product categories, automatically collecting news, classifying risk status using AI, and delivering professional daily intelligence reports.

### Categories

| Category | Insurers | Schedule (Sao Paulo) |
|----------|----------|---------------------|
| Health (Saude) | 515 | 6:00 AM |
| Dental (Odontologico) | 237 | 7:00 AM |
| Group Life (Vida em Grupo) | 145 | 8:00 AM |

### Features

- **Factiva News Collection** - Enterprise-grade news via Dow Jones Factiva / MMC Core API with Brazilian insurance industry codes and Portuguese keyword filtering
- **AI Insurer Matching** - Deterministic name matching with AI fallback for ambiguous articles (Azure OpenAI)
- **Semantic Deduplication** - sentence-transformers embedding similarity removes duplicate articles before processing
- **AI Classification** - Azure OpenAI classifies insurer status (Critical, Watch, Monitor, Stable)
- **Executive Summaries** - AI-generated executive summaries per report
- **Equity Price Enrichment** - Inline B3 stock prices (ticker, price, change%) for tracked insurers via MMC Core API
- **Professional Reports** - Marsh-branded HTML reports with PDF attachments and equity data chips
- **Email Delivery** - Automated daily delivery via Microsoft Graph API
- **Critical Alerts** - Immediate notifications for critical status detection
- **Admin Dashboard** - Web interface for managing insurers, equity tickers, Factiva config, schedules, and reports
- **Enterprise API Auth** - OAuth2 client credentials with automatic token refresh for MMC Core API
- **API Event Logging** - All enterprise API calls logged to persistent event table for observability

---

## Quick Start

```bash
# Clone repository
git clone https://github.com/SamuraiJenkinz/BrasilIntel.git
cd BrasilIntel

# Setup Python environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# Configure
copy .env.example .env
# Edit .env with your API keys

# Run database migrations
python scripts/migrate_007_enterprise_api_tables.py
python scripts/migrate_008_factiva_date_range.py

# Run
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/admin/** to access the dashboard.

See [Quickstart Guide](docs/QUICKSTART.md) for detailed setup instructions.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Quickstart Guide](docs/QUICKSTART.md) | Get running in 5 minutes |
| [User Guide](docs/USER_GUIDE.md) | Complete feature documentation |
| [Deployment Guide](docs/DEPLOYMENT.md) | Production deployment options |

---

## Architecture

```
+-------------------------------------------------------------+
|                       BrasilIntel                            |
+-------------------------------------------------------------+
|  +-----------+  +-----------+  +-----------+  +-----------+  |
|  |  Factiva  |  | Insurer   |  |  AI       |  |  Report   |  |
|  | Collector |  | Matcher   |  | Classifier|  | Generator |  |
|  +-----+-----+  +-----+-----+  +-----+-----+  +-----+-----+  |
|        |              |              |              |         |
|        v              v              v              v         |
|  +---------------------------------------------------+      |
|  |           Orchestration Layer                      |      |
|  |      (APScheduler + FastAPI Pipeline)              |      |
|  +---------------------------------------------------+      |
|        |         |         |         |         |             |
|        v         v         v         v         v             |
|  +--------+ +--------+ +--------+ +--------+ +--------+     |
|  | SQLite | | Azure  | | MS     | | MMC    | | Equity |     |
|  |   DB   | | OpenAI | | Graph  | | Core   | | Price  |     |
|  |        | |        | | (mail) | | API    | | Client |     |
|  +--------+ +--------+ +--------+ +--------+ +--------+     |
+-------------------------------------------------------------+
```

### Pipeline Flow

```
Factiva API --> Collect articles --> URL dedup --> Semantic dedup
    --> Deterministic insurer matching --> AI matching (ambiguous)
    --> AI classification --> Equity price enrichment
    --> Report generation --> Email delivery (Graph API)
```

### Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, pydantic-settings
- **Database**: SQLite
- **AI**: Azure OpenAI (GPT-4o) for classification, matching, and summaries
- **News**: Factiva/Dow Jones via MMC Core API (replaced Apify in v1.1)
- **Deduplication**: sentence-transformers (semantic similarity)
- **Equity Data**: MMC Core API Equity Price endpoint (B3/BVMF tickers)
- **Auth**: OAuth2 client credentials (MMC Core API), Azure AD (Graph API)
- **Email**: Microsoft Graph API
- **PDF**: WeasyPrint
- **Scheduler**: APScheduler (in-app) + Windows Task Scheduler (production)
- **Frontend**: Jinja2 Templates, Bootstrap 5, HTMX

---

## Configuration

Create a `.env` file from the example:

```bash
copy .env.example .env
```

### Required Settings

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Microsoft Graph (Email)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
SENDER_EMAIL=sender@company.com

# Admin Interface
ADMIN_PASSWORD=your-secure-password

# Report Recipients
REPORT_RECIPIENTS_HEALTH=user1@company.com,user2@company.com
REPORT_RECIPIENTS_DENTAL=dental@company.com
REPORT_RECIPIENTS_GROUP_LIFE=life@company.com
```

### Enterprise API (Optional - for Factiva and Equity)

```env
# MMC Core API
MMC_API_BASE_URL=https://mmc-dallas-int-non-prod-ingress.mgti.mmc.com
MMC_API_CLIENT_ID=your-client-id
MMC_API_CLIENT_SECRET=your-client-secret
MMC_API_KEY=your-api-key
```

When MMC credentials are not configured, the pipeline runs without enterprise features (no Factiva collection, no equity enrichment). See [Deployment Guide](docs/DEPLOYMENT.md) for complete configuration reference.

---

## Deployment Options

### Docker

```bash
docker-compose build
docker-compose up -d
```

### Windows Server (Production)

```powershell
# Setup scheduled tasks (Health 6 AM, Dental 7 AM, Group Life 8 AM)
.\deploy\setup_scheduled_task.ps1

# Check status
.\deploy\manage_service.ps1 -Action status

# Run a category immediately
.\deploy\manage_service.ps1 -Action run-now -Category health
```

See [Deployment Guide](docs/DEPLOYMENT.md) for detailed instructions.

---

## API

Interactive API documentation available at `/docs` when the server is running.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System health check |
| GET | `/api/insurers` | List all insurers |
| GET | `/api/insurers/search?q=` | Search insurers |
| POST | `/api/runs/execute/category` | Execute category run |
| GET | `/api/runs/latest` | Latest run per category |
| GET | `/api/reports/archive` | Browse archived reports |
| GET | `/api/schedules` | List schedules |
| POST | `/api/schedules/{category}/trigger` | Trigger immediate run |
| GET | `/api/import/export` | Export insurers as Excel |

---

## Project Structure

```
BrasilIntel/
├── app/
│   ├── main.py              # FastAPI app entry point + health check
│   ├── config.py            # Pydantic Settings (all env vars + MMC config)
│   ├── database.py          # SQLAlchemy engine + session
│   ├── dependencies.py      # Auth + session helpers
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── insurer.py       # Insurer model (897 tracked)
│   │   ├── news_item.py     # NewsItem model
│   │   ├── run.py           # Run model
│   │   ├── api_event.py     # Enterprise API event log
│   │   ├── factiva_config.py # Factiva query configuration
│   │   └── equity_ticker.py # Insurer-to-ticker mappings
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── classification.py
│   │   ├── delivery.py
│   │   ├── insurer.py
│   │   ├── matching.py      # Insurer match results
│   │   ├── news.py
│   │   ├── report.py
│   │   ├── run.py
│   │   └── schedule.py
│   ├── routers/             # FastAPI route handlers
│   │   ├── admin.py         # Admin dashboard UI routes (incl. equity tickers)
│   │   ├── import_export.py # Excel import/export API
│   │   ├── insurers.py      # Insurer CRUD API
│   │   ├── reports.py       # Report archive API
│   │   ├── runs.py          # Run execution + pipeline API
│   │   └── schedules.py     # Schedule management API
│   ├── services/            # Business logic
│   │   ├── ai_matcher.py    # AI-assisted insurer matching (Azure OpenAI)
│   │   ├── alert_service.py # Critical alert notifications
│   │   ├── classifier.py    # AI classification
│   │   ├── deduplicator.py  # Semantic dedup (sentence-transformers)
│   │   ├── emailer.py       # Microsoft Graph email
│   │   ├── equity_client.py # MMC Core API equity prices
│   │   ├── excel_service.py # Excel import/export
│   │   ├── executive_summarizer.py
│   │   ├── insurer_matcher.py # Deterministic insurer matching
│   │   ├── pdf_generator.py
│   │   ├── report_archiver.py
│   │   ├── reporter.py      # Report generation (with equity data)
│   │   └── scheduler_service.py
│   ├── storage/reports/     # Generated report archive
│   └── templates/           # Jinja2 HTML templates
│       ├── admin/           # Admin dashboard pages (incl. equity.html)
│       ├── report_professional.html  # Main report (with equity chips)
│       └── alert_critical.html
├── deploy/                  # Deployment scripts (PowerShell + batch)
├── docs/                    # Documentation
├── scripts/                 # Database migrations + validation scripts
│   ├── migrate_007_enterprise_api_tables.py
│   ├── migrate_008_factiva_date_range.py
│   ├── seed_factiva_config.py
│   ├── test_auth.py         # MMC API auth validation
│   └── test_factiva.py      # Factiva collection end-to-end test
└── tests/                   # Test suite
```

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| v1.1 | 2026-02 | Factiva news, equity prices, enterprise API auth, insurer matching, semantic dedup |
| v1.0 | 2026-02-05 | MVP - 7 Apify sources, AI classification, reports, email, scheduling, admin dashboard |

---

## License

Proprietary - Marsh Brasil

---

## Support

For issues and support, contact the development team.

---

*BrasilIntel v1.1 -- [SamuraiJenkinz/BrasilIntel](https://github.com/SamuraiJenkinz/BrasilIntel)*
