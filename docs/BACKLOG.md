# BrasilIntel Feature Backlog

**Version:** v1.1 Candidates
**Last Updated:** 2026-02-05

---

## High Priority

### Run Management

- [ ] **Cancel Run Button** - Ability to abort a run in progress from the admin UI
  - Add cancel endpoint to API
  - Add cancel button to Schedules page
  - Gracefully stop scraping tasks
  - Mark run as "cancelled" status

- [ ] **Progress Indicator** - Real-time visibility into run progress
  - Show "Processing X of Y insurers"
  - Display current source being scraped
  - Update dashboard in real-time (WebSocket or polling)
  - Show estimated time remaining

### Run Status Display

- [ ] **Live Run Status** - See active runs on dashboard
  - Indicate when a run is in progress
  - Show which category is running
  - Display elapsed time

---

## Medium Priority

### Admin UI Enhancements

- [ ] **Editable Recipients via UI** - Manage email recipients without editing .env
  - Add recipients management page
  - Store in database instead of env vars
  - Support TO/CC/BCC per category

- [ ] **Run History Page** - View past runs with details
  - List all runs with status, duration, items found
  - Filter by category, date, status
  - Link to generated reports

- [ ] **Insurer Search Improvements**
  - Advanced filtering (by status, last activity)
  - Bulk edit search terms
  - Import/export search term overrides

### Reporting

- [ ] **Report Preview Before Send** - Preview report before email delivery
  - Generate report without sending
  - Allow edits/annotations
  - Manual send trigger

- [ ] **Historical Trend Analysis** - Track insurer status over time
  - Status history per insurer
  - Trend charts on dashboard
  - Alert on status changes

---

## Low Priority / Future

### Integration

- [ ] **Webhook Notifications** - POST to external URL on events
  - Run completed
  - Critical status detected
  - Errors occurred

- [ ] **API Authentication** - Secure API endpoints
  - API key authentication
  - Rate limiting
  - Audit logging

### Performance

- [ ] **Parallel Source Scraping** - Faster runs
  - Scrape multiple sources simultaneously
  - Configurable concurrency

- [ ] **Caching Layer** - Reduce redundant API calls
  - Cache news results for configurable duration
  - Skip unchanged insurers

---

## Completed (v1.0)

- [x] HTML Login Form (replaced browser Basic Auth popup)
- [x] Session-based authentication with cookies
- [x] Logout functionality
- [x] Docker deployment
- [x] Windows Server deployment (venv + Scheduled Tasks)
- [x] Comprehensive documentation

---

## How to Contribute

1. Pick an item from the backlog
2. Create a branch: `feature/description`
3. Implement with tests
4. Submit PR for review

---

*BrasilIntel Backlog - Updated after v1.0 release*
