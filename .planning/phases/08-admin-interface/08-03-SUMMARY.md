---
phase: 08-admin-interface
plan: 03
subsystem: admin-ui
tags: [htmx, templates, insurers, bulk-operations, pagination]

dependency-graph:
  requires: [08-01]
  provides:
    - Insurers management page with filtering
    - Bulk enable/disable operations
    - HTMX partial updates for table
  affects: []

tech-stack:
  added: []
  patterns:
    - HTMX partial updates for filtered table
    - Bootstrap nav-tabs for category filtering
    - Form-based bulk operations with checkbox selection

file-tracking:
  created:
    - app/templates/admin/insurers.html
    - app/templates/admin/partials/insurer_table.html
  modified:
    - app/routers/admin.py

decisions:
  - name: "HTMX partial response pattern"
    choice: "Return partial for HX-Request header, full page otherwise"
    rationale: "Enables progressive enhancement with proper browser history"
  - name: "50 insurers per page"
    choice: "Fixed page size of 50 with pagination controls"
    rationale: "Balance between performance and usability for 902 insurers"
  - name: "Checkbox-based bulk selection"
    choice: "Form with checkbox inputs and Form(...) parsing"
    rationale: "Standard HTML form pattern works with HTMX"

metrics:
  duration: ~4 minutes
  completed: 2026-02-04
---

# Phase 8 Plan 03: Insurers Management Page Summary

Insurers page with category tabs, search box, status filter, and bulk enable/disable operations.

## What Was Built

### Admin Router Enhancements (app/routers/admin.py)

1. **Enhanced Insurers Endpoint**
   - Query parameters: category, search, enabled, page
   - Filter by category (Health, Dental, Group Life)
   - Search by name (ilike) or ANS code (contains)
   - Status filter (enabled/disabled/all)
   - Pagination: 50 per page
   - Returns partial HTML for HTMX requests

2. **Bulk Enable Endpoint** (`POST /admin/insurers/bulk-enable`)
   - Accepts list of ANS codes via Form
   - Updates enabled=True for selected insurers
   - Returns dismissible success alert

3. **Bulk Disable Endpoint** (`POST /admin/insurers/bulk-disable`)
   - Accepts list of ANS codes via Form
   - Updates enabled=False for selected insurers
   - Returns dismissible warning alert

### Insurers Page Template (app/templates/admin/insurers.html)

1. **Page Header**
   - Title with building icon
   - Total insurer count badge

2. **Category Tabs**
   - All, Health, Dental, Group Life tabs
   - HTMX-powered filtering without page reload
   - Active tab styling with Marsh blue accent

3. **Filter Row**
   - Search input with debounce (300ms)
   - Status dropdown (All/Enabled/Disabled)
   - Bulk action buttons (Enable/Disable Selected)
   - Buttons disabled when no checkboxes selected

4. **JavaScript Functionality**
   - toggleAll() for select-all checkbox
   - updateBulkButtons() for button state management
   - Event listeners for checkbox changes
   - Table refresh after bulk operations

### Insurer Table Partial (app/templates/admin/partials/insurer_table.html)

1. **Table Structure**
   - Columns: Checkbox, ANS Code, Name, Category, Status, Actions
   - Category badges with distinct colors
   - Status badges (green Enabled, yellow Disabled)
   - View button for detail modal

2. **Pagination**
   - Previous/Next navigation
   - Page number links with ellipsis for large sets
   - "Showing X-Y of Z insurers" summary
   - Maintains filter state in pagination links

3. **Empty State**
   - Inbox icon with "No insurers found" message
   - Displayed when filters return no results

4. **Detail Modal**
   - Bootstrap modal for insurer details
   - Loads via HTMX from /api/insurers/{ans_code}
   - Loading spinner during fetch

## Requirements Fulfilled

| Requirement | Description | Status |
|-------------|-------------|--------|
| ADMN-06 | Category tabs, search, status filters | DONE |
| ADMN-07 | Bulk enable/disable operations | DONE |

## Technical Decisions

1. **HTMX Partial Response Pattern**
   - Check HX-Request header to determine response type
   - Full page for direct navigation, partial for AJAX
   - Enables browser history with hx-push-url

2. **Filter Composition**
   - All filters work together (category + search + status)
   - hx-include preserves other filter values
   - URL updates reflect current filter state

3. **Pagination Design**
   - 50 items per page for optimal UX
   - Smart page number display with ellipsis
   - All filters included in pagination links

## Commits

| Hash | Message |
|------|---------|
| 83b72b6 | feat(08-03): add insurers management page with filters and bulk actions |

## Files Changed

- `app/routers/admin.py` - Enhanced insurers endpoint + bulk action endpoints
- `app/templates/admin/insurers.html` - Full insurers page with tabs and filters
- `app/templates/admin/partials/insurer_table.html` - HTMX partial for table with pagination

## Next Phase Readiness

Plan 08-04 (Recipients Page) can proceed:
- Admin router pattern established
- HTMX partial pattern documented
- Base template tested with form interactions
