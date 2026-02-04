# Requirements: BrasilIntel

**Defined:** 2026-02-04
**Core Value:** Senior management at Marsh Brasil receives actionable intelligence reports on their monitored insurers daily, with zero manual effort.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Management

- [ ] **DATA-01**: System stores 897 insurers with ANS Code, Name, CNPJ, Product Category, Market Master, Status, Enabled flag
- [ ] **DATA-02**: Admin can view insurers with search by name/ANS code and filter by category
- [ ] **DATA-03**: Admin can edit insurer details (name, search terms, enabled/disabled)
- [ ] **DATA-04**: Admin can upload Excel file to bulk import/update insurers
- [ ] **DATA-05**: Admin can preview import before committing changes
- [ ] **DATA-06**: Admin can export current insurer data as Excel
- [ ] **DATA-07**: System validates required fields (ANS Code, Name, Category) on import
- [ ] **DATA-08**: System rejects duplicate ANS codes with clear error messages

### News Collection

- [ ] **NEWS-01**: System scrapes Google News for each enabled insurer using name + ANS code
- [ ] **NEWS-02**: System scrapes Valor Econômico for insurance-related news
- [ ] **NEWS-03**: System scrapes InfoMoney for insurance-related news
- [ ] **NEWS-04**: System scrapes CQCS for insurance industry news
- [ ] **NEWS-05**: System scrapes ANS official releases
- [ ] **NEWS-06**: System scrapes Broadcast/Estadão for insurance news
- [ ] **NEWS-07**: System processes insurers in batches (30-50) with rate limiting
- [ ] **NEWS-08**: System stores news items with title, summary, source URL, source name, published date
- [ ] **NEWS-09**: System links news items to specific insurers and run records
- [ ] **NEWS-10**: System uses AI relevance scoring to filter low-value content

### Classification

- [ ] **CLASS-01**: Azure OpenAI classifies each insurer status as Critical, Watch, Monitor, or Stable
- [ ] **CLASS-02**: Classification based on news content analysis (financial crisis, regulatory action, M&A, leadership changes)
- [ ] **CLASS-03**: Azure OpenAI generates concise bullet-point summary for each news item
- [ ] **CLASS-04**: Azure OpenAI assigns sentiment (positive/negative/neutral) to each news item
- [ ] **CLASS-05**: Classification results stored with insurer records
- [ ] **CLASS-06**: LLM summarization can be toggled via configuration (USE_LLM_SUMMARY)

### Reporting

- [ ] **REPT-01**: System generates 3 separate daily reports (Health, Dental, Group Life)
- [ ] **REPT-02**: Reports match Marsh branding (colors, layout) from reference HTML designs
- [ ] **REPT-03**: Reports include confidential banner with classification level
- [ ] **REPT-04**: Reports include executive summary with key findings cards (Critical/Warning/Positive)
- [ ] **REPT-05**: Reports include coverage summary table with all insurers and status badges
- [ ] **REPT-06**: Reports group insurers by status priority (Critical first, then Watch, Monitor, Stable)
- [ ] **REPT-07**: Each insurer section shows news items with icons, titles, impact tags
- [ ] **REPT-08**: Reports include market context section with regulatory updates
- [ ] **REPT-09**: Reports include strategic recommendations section
- [ ] **REPT-10**: Azure OpenAI generates executive summary paragraph for each report
- [ ] **REPT-11**: Reports render correctly on mobile devices (responsive HTML)
- [ ] **REPT-12**: System stores generated reports in archive with date-based organization
- [ ] **REPT-13**: Admin can browse and view historical reports by date and category

### Delivery

- [ ] **DELV-01**: System sends reports via Microsoft Graph API (Exchange Online)
- [ ] **DELV-02**: Email supports TO, CC, BCC recipient lists per category
- [ ] **DELV-03**: Recipients configurable per product category (Health, Dental, Group Life)
- [ ] **DELV-04**: System sends immediate alert email when Critical status detected
- [ ] **DELV-05**: Critical alerts sent separately from daily digest
- [ ] **DELV-06**: System generates PDF version of each report
- [ ] **DELV-07**: PDF attached to email or available for download
- [ ] **DELV-08**: System tracks email delivery status per run

### Scheduling

- [ ] **SCHD-01**: System runs 3 scheduled jobs (one per product category)
- [ ] **SCHD-02**: Default schedule: Health 6 AM, Dental 7 AM, Group Life 8 AM (São Paulo time)
- [ ] **SCHD-03**: Admin can modify cron expression for each category
- [ ] **SCHD-04**: Admin can enable/disable each scheduled job
- [ ] **SCHD-05**: Admin can trigger manual run for any category via UI
- [ ] **SCHD-06**: System tracks run history (started, completed, status, items found, errors)
- [ ] **SCHD-07**: System shows next scheduled run time for each category

### Admin UI

- [ ] **ADMN-01**: Web dashboard accessible at configured port (default 3000)
- [ ] **ADMN-02**: Basic authentication with username/password from environment variables
- [ ] **ADMN-03**: Dashboard shows summary cards per category (insurer count, last run, next run)
- [ ] **ADMN-04**: Dashboard shows recent reports list with quick view links
- [ ] **ADMN-05**: Dashboard shows system status indicators (healthy/warning/error)
- [ ] **ADMN-06**: Insurers page with category tabs, search, status filters
- [ ] **ADMN-07**: Insurers page supports bulk enable/disable operations
- [ ] **ADMN-08**: Import page with drag-and-drop file upload
- [ ] **ADMN-09**: Import page shows preview before commit with validation errors
- [ ] **ADMN-10**: Recipients page with subscription checkboxes per category
- [ ] **ADMN-11**: Recipients page supports add/edit/remove recipient
- [ ] **ADMN-12**: Schedules page shows each category with cron expression, next runs, toggle
- [ ] **ADMN-13**: Schedules page has manual trigger button per category
- [ ] **ADMN-14**: Settings page for company branding (name, classification level)
- [ ] **ADMN-15**: Settings page for scraping config (batch size, timeout, lookback days)
- [ ] **ADMN-16**: API keys displayed masked with reveal toggle

### Deployment

- [ ] **DEPL-01**: Application runs as Python package with entry point `python -m src.main`
- [ ] **DEPL-02**: Docker container available for local Windows 11 development
- [ ] **DEPL-03**: Windows Scheduled Task setup via PowerShell script for production
- [ ] **DEPL-04**: PowerShell management script with start/stop/status/logs/run-now commands
- [ ] **DEPL-05**: Application uses Python venv for dependency isolation
- [ ] **DEPL-06**: All configuration via environment variables (.env file)
- [ ] **DEPL-07**: SQLite database stored in configurable data directory
- [ ] **DEPL-08**: Logs written to data/logs/ with date-stamped filenames
- [ ] **DEPL-09**: Health check endpoint at /api/health returns system status

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Intelligence

- **INTL-01**: Trend detection across historical data (requires 3-6 months archive)
- **INTL-02**: Competitive benchmarking (compare insurer activity levels)
- **INTL-03**: Visual dashboards with charts and graphs
- **INTL-04**: Regulatory change detection alerts
- **INTL-05**: Cross-insurer pattern recognition
- **INTL-06**: Automated battlecards per insurer

### Enhanced Delivery

- **DELV-09**: Customizable alert thresholds per recipient
- **DELV-10**: Multi-channel delivery (SMS/Slack for Critical)
- **DELV-11**: Two-way feedback (recipients flag false positives)

### Integrations

- **INTG-01**: Integration with Marsh internal systems (CRM, sales tools)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Social media monitoring | Brazilian insurance news primarily from traditional media; scope creep risk |
| Real-time live dashboards | Executive audience checks once daily; scheduled reports + Critical alerts sufficient |
| Full-text article storage | Copyright issues, storage costs; store headlines, summaries, links only |
| Collaborative annotation tools | 5-10 recipients don't need Slack-like features; over-engineering |
| Multi-user permission levels | Small admin team; single admin role sufficient for v1 |
| Custom report builder UI | Fixed daily report format; predefined templates only |
| Browser extensions/mobile apps | Email-first delivery; responsive web dashboard sufficient |
| Automated response actions | Intelligence delivery only; humans decide actions |
| Historical trend analysis (deep) | No historical data yet; add after 6+ months of archive |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| DATA-06 | Phase 1 | Pending |
| DATA-07 | Phase 1 | Pending |
| DATA-08 | Phase 1 | Pending |
| NEWS-01 | Phase 2 | Pending |
| NEWS-02 | Phase 3 | Pending |
| NEWS-03 | Phase 3 | Pending |
| NEWS-04 | Phase 3 | Pending |
| NEWS-05 | Phase 3 | Pending |
| NEWS-06 | Phase 3 | Pending |
| NEWS-07 | Phase 3 | Pending |
| NEWS-08 | Phase 3 | Pending |
| NEWS-09 | Phase 3 | Pending |
| NEWS-10 | Phase 3 | Pending |
| CLASS-01 | Phase 2 | Pending |
| CLASS-02 | Phase 4 | Pending |
| CLASS-03 | Phase 2 | Pending |
| CLASS-04 | Phase 4 | Pending |
| CLASS-05 | Phase 4 | Pending |
| CLASS-06 | Phase 4 | Pending |
| REPT-01 | Phase 2 | Pending |
| REPT-02 | Phase 5 | Pending |
| REPT-03 | Phase 5 | Pending |
| REPT-04 | Phase 5 | Pending |
| REPT-05 | Phase 5 | Pending |
| REPT-06 | Phase 5 | Pending |
| REPT-07 | Phase 5 | Pending |
| REPT-08 | Phase 5 | Pending |
| REPT-09 | Phase 5 | Pending |
| REPT-10 | Phase 5 | Pending |
| REPT-11 | Phase 5 | Pending |
| REPT-12 | Phase 5 | Pending |
| REPT-13 | Phase 5 | Pending |
| DELV-01 | Phase 2 | Pending |
| DELV-02 | Phase 6 | Pending |
| DELV-03 | Phase 6 | Pending |
| DELV-04 | Phase 6 | Pending |
| DELV-05 | Phase 6 | Pending |
| DELV-06 | Phase 6 | Pending |
| DELV-07 | Phase 6 | Pending |
| DELV-08 | Phase 6 | Pending |
| SCHD-01 | Phase 7 | Pending |
| SCHD-02 | Phase 7 | Pending |
| SCHD-03 | Phase 7 | Pending |
| SCHD-04 | Phase 7 | Pending |
| SCHD-05 | Phase 7 | Pending |
| SCHD-06 | Phase 7 | Pending |
| SCHD-07 | Phase 7 | Pending |
| ADMN-01 | Phase 8 | Pending |
| ADMN-02 | Phase 8 | Pending |
| ADMN-03 | Phase 8 | Pending |
| ADMN-04 | Phase 8 | Pending |
| ADMN-05 | Phase 8 | Pending |
| ADMN-06 | Phase 8 | Pending |
| ADMN-07 | Phase 8 | Pending |
| ADMN-08 | Phase 8 | Pending |
| ADMN-09 | Phase 8 | Pending |
| ADMN-10 | Phase 8 | Pending |
| ADMN-11 | Phase 8 | Pending |
| ADMN-12 | Phase 8 | Pending |
| ADMN-13 | Phase 8 | Pending |
| ADMN-14 | Phase 8 | Pending |
| ADMN-15 | Phase 8 | Pending |
| ADMN-16 | Phase 8 | Pending |
| DEPL-01 | Phase 2 | Pending |
| DEPL-02 | Phase 2 | Pending |
| DEPL-03 | Phase 2 | Pending |
| DEPL-04 | Phase 2 | Pending |
| DEPL-05 | Phase 2 | Pending |
| DEPL-06 | Phase 2 | Pending |
| DEPL-07 | Phase 2 | Pending |
| DEPL-08 | Phase 2 | Pending |
| DEPL-09 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 63 total
- Mapped to phases: 63
- Unmapped: 0 (100% coverage)

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-04 after roadmap creation*
