# BrasilIntel

Automated competitive intelligence system for monitoring Brazilian insurers.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-proprietary-red.svg)]()

---

## Overview

BrasilIntel monitors **897 Brazilian insurers** across three product categories, automatically collecting news, classifying risk status using AI, and delivering professional daily intelligence reports.

### Categories

| Category | Insurers | Schedule (São Paulo) |
|----------|----------|---------------------|
| Health (Saúde) | 515 | 6:00 AM |
| Dental (Odontológico) | 237 | 7:00 AM |
| Group Life (Vida em Grupo) | 145 | 8:00 AM |

### Features

- **Automated News Collection** - Scrapes 7 sources (Google News, Valor Econômico, InfoMoney, CQCS, ANS, Estadão, RSS)
- **AI Classification** - Azure OpenAI classifies insurer status (Critical, Watch, Monitor, Stable)
- **AI Relevance Scoring** - Pre-filters news items for relevance before classification
- **Executive Summaries** - AI-generated executive summaries per report
- **Professional Reports** - Marsh-branded HTML reports with PDF attachments
- **Email Delivery** - Automated daily delivery via Microsoft Graph API
- **Critical Alerts** - Immediate notifications for critical status detection
- **Admin Dashboard** - Web interface for managing insurers, schedules, recipients, and reports
- **Batch Processing** - Configurable batch sizes and concurrent source scraping

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
┌─────────────────────────────────────────────────────────────┐
│                      BrasilIntel                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Scraper   │  │  Classifier │  │   Report    │         │
│  │   Service   │  │   Service   │  │  Generator  │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────┐       │
│  │              Orchestration Layer                 │       │
│  │         (APScheduler + FastAPI)                  │       │
│  └─────────────────────────────────────────────────┘       │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐           │
│  │  SQLite   │    │   Azure   │    │ Microsoft │           │
│  │    DB     │    │  OpenAI   │    │   Graph   │           │
│  └───────────┘    └───────────┘    └───────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, pydantic-settings
- **Database**: SQLite
- **AI**: Azure OpenAI (GPT-4o)
- **Email**: Microsoft Graph API
- **Scraping**: Apify SDK (7 source adapters)
- **PDF**: WeasyPrint
- **Scheduler**: APScheduler (in-app) + Windows Task Scheduler (production)
- **Frontend**: Jinja2 Templates, Bootstrap 5

---

## Configuration

Create a `.env` file with the following required settings:

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

# Apify (Web Scraping)
APIFY_TOKEN=your-apify-token

# Admin Interface
ADMIN_PASSWORD=your-secure-password

# Report Recipients
REPORT_RECIPIENTS_HEALTH=user1@company.com,user2@company.com
REPORT_RECIPIENTS_DENTAL=dental@company.com
REPORT_RECIPIENTS_GROUP_LIFE=life@company.com
```

See [Deployment Guide](docs/DEPLOYMENT.md) for complete configuration reference.

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
│   ├── config.py            # Pydantic Settings (all env vars)
│   ├── database.py          # SQLAlchemy engine + session
│   ├── dependencies.py      # Auth + session helpers
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── insurer.py       # Insurer model
│   │   ├── news_item.py     # NewsItem model
│   │   └── run.py           # Run model
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── classification.py
│   │   ├── delivery.py
│   │   ├── insurer.py
│   │   ├── news.py
│   │   ├── report.py
│   │   ├── run.py
│   │   └── schedule.py
│   ├── routers/             # FastAPI route handlers
│   │   ├── admin.py         # Admin dashboard UI routes
│   │   ├── import_export.py # Excel import/export API
│   │   ├── insurers.py      # Insurer CRUD API
│   │   ├── reports.py       # Report archive API
│   │   ├── runs.py          # Run execution API
│   │   └── schedules.py     # Schedule management API
│   ├── services/            # Business logic
│   │   ├── scraper.py       # News collection orchestrator
│   │   ├── classifier.py    # AI classification
│   │   ├── reporter.py      # Report generation
│   │   ├── emailer.py       # Microsoft Graph email
│   │   ├── alert_service.py # Critical alert notifications
│   │   ├── batch_processor.py
│   │   ├── executive_summarizer.py
│   │   ├── pdf_generator.py
│   │   ├── relevance_scorer.py
│   │   ├── report_archiver.py
│   │   ├── scheduler_service.py
│   │   ├── excel_service.py
│   │   └── sources/         # 7 news source adapters
│   ├── storage/reports/     # Generated report archive
│   └── templates/           # Jinja2 HTML templates
│       ├── admin/           # Admin dashboard pages
│       ├── report_professional.html
│       └── alert_critical.html
├── deploy/                  # Deployment scripts (PowerShell + batch)
├── docs/                    # Documentation
├── scripts/                 # Database migrations
└── tests/                   # Test suite
```

---

## License

Proprietary - Marsh Brasil

---

## Support

For issues and support, contact the development team.

---

*BrasilIntel v1.0 — [SamuraiJenkinz/BrasilIntel](https://github.com/SamuraiJenkinz/BrasilIntel)*
