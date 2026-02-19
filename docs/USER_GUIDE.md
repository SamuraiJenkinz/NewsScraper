# BrasilIntel User Guide

**Version:** 1.0.1
**Last Updated:** 2026-02-19

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Configuration](#configuration)
4. [Admin Dashboard](#admin-dashboard)
5. [Managing Insurers](#managing-insurers)
6. [Importing and Exporting Data](#importing-and-exporting-data)
7. [Reports](#reports)
8. [Scheduling](#scheduling)
9. [Email Delivery](#email-delivery)
10. [API Reference](#api-reference)
11. [Troubleshooting](#troubleshooting)

---

## Overview

BrasilIntel is an automated competitive intelligence system for Marsh Brasil that monitors 897 Brazilian insurers across three product categories:

- **Health** (Saúde) - 515 insurers
- **Dental** (Odontológico) - 237 insurers
- **Group Life** (Vida em Grupo) - 145 insurers

The system automatically:
- Scrapes news from 7 sources (Google News, Valor Econômico, InfoMoney, CQCS, ANS, Estadão, RSS feeds)
- Uses Azure OpenAI to classify insurer status and generate summaries
- Generates professional Marsh-branded HTML reports with PDF attachments
- Sends daily reports via email at scheduled times
- Sends immediate alerts when critical status is detected

---

## Getting Started

### System Requirements

- Python 3.11 or higher
- Windows 10/11 or Windows Server 2019+
- Internet connectivity for news scraping and email delivery

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SamuraiJenkinz/BrasilIntel.git
   cd BrasilIntel
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   copy .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize the database:**
   ```bash
   python -m app.main
   # The database is created automatically on first run
   ```

### Running the Application

**Development mode:**
```bash
python -m app.main
```

**Production mode (Windows Scheduled Task):**
```powershell
.\deploy\setup_scheduled_task.ps1
```

The application runs on `http://localhost:8000` by default.

---

## Configuration

All configuration is done via environment variables. Create a `.env` file in the project root:

### Required Settings

```env
# Azure OpenAI (for AI classification and summaries)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Microsoft Graph (for email delivery)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
SENDER_EMAIL=brasilintel@marsh.com

# Apify (for web scraping)
APIFY_TOKEN=your-apify-token
```

### Optional Settings

```env
# Application
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./data/brasilintel.db
DATA_DIR=./data

# Admin Interface
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# Report Recipients (comma-separated emails)
REPORT_RECIPIENTS_HEALTH=user1@marsh.com,user2@marsh.com
REPORT_RECIPIENTS_HEALTH_CC=manager@marsh.com
REPORT_RECIPIENTS_HEALTH_BCC=archive@marsh.com

REPORT_RECIPIENTS_DENTAL=dental-team@marsh.com
REPORT_RECIPIENTS_DENTAL_CC=
REPORT_RECIPIENTS_DENTAL_BCC=

REPORT_RECIPIENTS_GROUP_LIFE=life-team@marsh.com
REPORT_RECIPIENTS_GROUP_LIFE_CC=
REPORT_RECIPIENTS_GROUP_LIFE_BCC=

# Scheduling (cron expressions, São Paulo timezone)
SCHEDULE_HEALTH_CRON=0 6 * * *
SCHEDULE_DENTAL_CRON=0 7 * * *
SCHEDULE_GROUP_LIFE_CRON=0 8 * * *
SCHEDULE_HEALTH_ENABLED=true
SCHEDULE_DENTAL_ENABLED=true
SCHEDULE_GROUP_LIFE_ENABLED=true

# Scraping
BATCH_SIZE=30
BATCH_DELAY_SECONDS=2.0
MAX_CONCURRENT_SOURCES=3
SCRAPE_TIMEOUT_SECONDS=60
SCRAPE_MAX_RESULTS=10

# AI Features
USE_LLM_SUMMARY=true
USE_AI_RELEVANCE_SCORING=true
```

---

## Admin Dashboard

Access the admin dashboard at `http://localhost:8000/admin/`

### Login

Use the credentials configured in your environment:
- **Username:** Value of `ADMIN_USERNAME` (default: `admin`)
- **Password:** Value of `ADMIN_PASSWORD`

### Dashboard Overview

The dashboard displays:

1. **Category Cards** - One card per product category showing:
   - Total insurer count
   - Enabled insurer count
   - Last run status and time
   - Next scheduled run time

2. **System Status** - Health indicators for:
   - Database connectivity
   - Data directory access
   - Azure OpenAI configuration
   - Microsoft Graph configuration
   - Apify configuration
   - Scheduler status

3. **Recent Reports** - List of recently generated reports with:
   - Date and category
   - Quick view links

### Admin Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/admin/` | Category cards, system status, recent reports |
| Insurers | `/admin/insurers` | View, search, enable/disable insurers |
| Import | `/admin/import` | Upload Excel, preview, commit insurer data |
| Recipients | `/admin/recipients` | View configured TO/CC/BCC recipients per category |
| Schedules | `/admin/schedules` | Toggle schedules, trigger manual runs |
| Settings | `/admin/settings` | View system configuration and service status |

---

## Managing Insurers

### Viewing Insurers

Navigate to **Insurers** in the admin menu.

**Features:**
- **Category Tabs** - Filter by Health, Dental, or Group Life
- **Search** - Search by insurer name or ANS code
- **Status Filter** - Show all, enabled only, or disabled only
- **Pagination** - 50 insurers per page

### Editing an Insurer

Click on an insurer row to edit:
- **Name** - Display name
- **Search Terms** - Custom search terms for news scraping (comma-separated)
- **Enabled** - Toggle to include/exclude from scraping runs

### Bulk Operations

1. Select multiple insurers using checkboxes
2. Use the bulk action buttons:
   - **Enable Selected** - Enable all selected insurers
   - **Disable Selected** - Disable all selected insurers

---

## Importing and Exporting Data

### Importing Insurers

Navigate to **Import** in the admin menu.

1. **Upload File** - Drag and drop or click to select an Excel file (.xlsx)
2. **Preview** - Review the import preview showing:
   - New insurers to be added
   - Existing insurers to be updated
   - Validation errors (if any)
3. **Commit** - Click "Confirm Import" to apply changes

**Excel Format Requirements:**
| Column | Required | Description |
|--------|----------|-------------|
| ANS Code | Yes | Unique regulatory registration number |
| Name | Yes | Insurer name |
| Category | Yes | "Health", "Dental", or "Group Life" |
| CNPJ | No | Tax identification number |
| Market Master | No | Marsh global system code |
| Status | No | Current status |
| Enabled | No | "true" or "false" |

### Exporting Insurers

1. Navigate to **Import** page
2. Click **Export Current Data**
3. An Excel file will download with all current insurers

---

## Reports

### Report Types

BrasilIntel generates three daily reports:
1. **Health Insurer Intelligence Report**
2. **Dental Insurer Intelligence Report**
3. **Group Life Insurer Intelligence Report**

### Report Contents

Each report includes:

1. **Confidential Banner** - Classification level indicator
2. **Executive Summary** - AI-generated overview with:
   - Key findings (Critical, Warning, Positive)
   - Summary paragraph
3. **Coverage Summary Table** - All insurers with status badges
4. **Insurer Sections** - Grouped by status priority:
   - Critical (red)
   - Watch (orange)
   - Monitor (yellow)
   - Stable (green)
5. **News Items** - For each insurer:
   - Title and summary
   - Source attribution
   - Impact indicators
6. **Market Context** - Regulatory updates and industry trends
7. **Strategic Recommendations** - Action items based on findings

### Viewing Reports

**From Admin Dashboard:**
- Click any report in the "Recent Reports" list

**From Archive:**
- Navigate to `http://localhost:8000/api/reports/archive`
- Filter by date and category

### Report Formats

- **HTML** - Interactive web version (responsive, works on mobile)
- **PDF** - Attached to email for offline viewing

---

## Scheduling

### Default Schedule

| Category | Time (São Paulo) | Cron Expression |
|----------|------------------|-----------------|
| Health | 6:00 AM | `0 6 * * *` |
| Dental | 7:00 AM | `0 7 * * *` |
| Group Life | 8:00 AM | `0 8 * * *` |

### Managing Schedules

Navigate to **Schedules** in the admin menu.

**For each category, you can:**
- **View** next scheduled run time
- **Toggle** schedule on/off
- **Trigger** immediate manual run

### Manual Runs

To run a category immediately:
1. Go to **Schedules** page
2. Click **Run Now** for the desired category
3. Monitor progress in the run history

---

## Email Delivery

### Recipient Configuration

Recipients are configured per category via environment variables:

```env
# TO recipients (required for delivery)
REPORT_RECIPIENTS_HEALTH=user1@marsh.com,user2@marsh.com

# CC recipients (optional)
REPORT_RECIPIENTS_HEALTH_CC=manager@marsh.com

# BCC recipients (optional)
REPORT_RECIPIENTS_HEALTH_BCC=archive@marsh.com
```

### Email Types

1. **Daily Digest** - Scheduled report with PDF attachment
2. **Critical Alert** - Immediate notification when Critical status detected

### Critical Alerts

When an insurer is classified as **Critical**, the system:
1. Sends an immediate alert email (separate from the daily digest)
2. Uses a distinct red-themed template
3. Includes only the critical insurer details
4. Subject line: `[CRITICAL ALERT] BrasilIntel - {Category}`

---

## API Reference

### Health Check

```
GET /api/health
```

Returns system health status including database, services, and scheduler.

### Insurers

```
GET /api/insurers                    # List all insurers
GET /api/insurers/search?q={query}   # Search insurers
GET /api/insurers/{ans_code}         # Get single insurer by ANS code
POST /api/insurers                   # Create insurer
PATCH /api/insurers/{ans_code}       # Update insurer
DELETE /api/insurers/{ans_code}      # Delete insurer
```

### Import/Export

```
POST /api/import/preview             # Preview import (upload Excel)
POST /api/import/commit/{session_id} # Commit import
GET /api/import/sessions             # List active import sessions
DELETE /api/import/sessions/{id}     # Delete import session
GET /api/import/export               # Export insurers as Excel
GET /api/import/stats                # Import statistics
```

### Runs

```
GET /api/runs                        # List all runs
GET /api/runs/latest                 # Latest run per category
GET /api/runs/stats                  # Run statistics
GET /api/runs/{run_id}               # Get run details
GET /api/runs/{run_id}/news          # Get news items for a run
GET /api/runs/{run_id}/delivery      # Get delivery status
POST /api/runs/execute               # Execute single insurer run
POST /api/runs/execute/category      # Execute category run
GET /api/runs/health/scraper         # Scraper health check
```

### Schedules

```
GET /api/schedules                   # List all schedules
GET /api/schedules/health            # Schedule health status
GET /api/schedules/{category}        # Get schedule for category
PUT /api/schedules/{category}        # Update schedule
POST /api/schedules/{category}/trigger  # Trigger immediate run
POST /api/schedules/{category}/pause    # Pause schedule
POST /api/schedules/{category}/resume   # Resume schedule
```

### Reports

```
GET /api/reports/archive             # Browse archived reports
GET /api/reports/archive/dates       # List available dates
GET /api/reports/archive/{date}/{filename}  # Get specific report
GET /api/reports/preview             # Preview report template
```

---

## Troubleshooting

### Common Issues

#### "Admin password not configured"

**Cause:** The `ADMIN_PASSWORD` environment variable is empty or not set.

**Solution:** Set a password in your `.env` file:
```env
ADMIN_PASSWORD=your-secure-password
```

#### "Apify token not configured"

**Cause:** News scraping requires an Apify API token.

**Solution:**
1. Create an account at [apify.com](https://apify.com)
2. Get your API token from Settings > Integrations
3. Add to `.env`:
   ```env
   APIFY_TOKEN=your-token
   ```

#### "Azure OpenAI not configured"

**Cause:** AI classification and summaries require Azure OpenAI.

**Solution:** Configure all Azure OpenAI settings:
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

#### "Email delivery failed"

**Cause:** Microsoft Graph API not configured or authentication failed.

**Solution:**
1. Register an app in Azure AD
2. Grant `Mail.Send` application permission
3. Configure:
   ```env
   AZURE_TENANT_ID=your-tenant-id
   AZURE_CLIENT_ID=your-client-id
   AZURE_CLIENT_SECRET=your-client-secret
   SENDER_EMAIL=authorized-sender@marsh.com
   ```

#### "PDF generation failed"

**Cause:** WeasyPrint requires GTK3 runtime on Windows.

**Solution:**
1. Install GTK3: https://github.com/nickvergessen/gtk-for-windows-runtime-environment-installer
2. Add GTK3 bin directory to system PATH
3. Restart the application

**Fallback:** If PDF generation fails, reports are still sent as HTML-only emails.

#### "Port already in use"

**Cause:** Another process is using port 8000.

**Solution:**
1. Find the process: `netstat -ano | findstr :8000`
2. Kill it: `taskkill /PID <pid> /F`
3. Or use a different port: `PORT=8001` in `.env`

#### "Scheduler not starting"

**Cause:** Database file may be locked or scheduler disabled.

**Solution:**
1. Check `SCHEDULER_ENABLED=true` in `.env`
2. Ensure no other instance is running
3. Check logs for specific errors

### Logs

Logs are written to `data/logs/` with date-stamped filenames.

**Log levels:**
- `DEBUG` - Detailed debugging information
- `INFO` - General operational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages

Set the log level in `.env`:
```env
LOG_LEVEL=INFO
```

### Getting Help

For additional support:
1. Check the logs in `data/logs/`
2. Review the API documentation at `/docs`
3. Contact the development team

---

## Appendix

### Insurer Status Definitions

| Status | Color | Description |
|--------|-------|-------------|
| Critical | Red | Immediate attention required - financial crisis, regulatory action, or major incident |
| Watch | Orange | Elevated concern - developing situation that needs monitoring |
| Monitor | Yellow | Notable activity - news worth tracking but not urgent |
| Stable | Green | Normal operations - no significant news |

### Category Indicators

The AI classification identifies specific event types:

| Indicator | Portuguese | Description |
|-----------|------------|-------------|
| financial_crisis | Crise Financeira | Financial distress or insolvency risk |
| regulatory_action | Ação Regulatória | ANS intervention or sanctions |
| merger_acquisition | Fusão/Aquisição | M&A activity |
| leadership_change | Mudança de Liderança | Executive changes |
| market_expansion | Expansão de Mercado | Growth or new markets |
| product_launch | Lançamento de Produto | New products or services |
| legal_dispute | Disputa Legal | Lawsuits or legal issues |
| partnership | Parceria | Strategic partnerships |
| technology_investment | Investimento em Tecnologia | Tech or digital transformation |
| customer_complaint | Reclamação de Clientes | Service quality issues |

### News Sources

| Source | Type | Coverage |
|--------|------|----------|
| Google News | Apify Scraper | General news mentions |
| Valor Econômico | Apify Scraper | Business/financial news |
| InfoMoney | Apify Scraper | Financial news |
| CQCS | Apify Scraper | Insurance industry news |
| ANS | RSS Feed | Official regulatory releases |
| Estadão | Apify Scraper | General news |
| RSS (generic) | RSS Feed | Configurable RSS sources |

---

*BrasilIntel v1.0 — [SamuraiJenkinz/BrasilIntel](https://github.com/SamuraiJenkinz/BrasilIntel)*
