# Phase 6: Delivery & Critical Alerts - Research

**Researched:** 2026-02-04
**Domain:** Email delivery with PDF attachments, recipient management, critical alerting
**Confidence:** HIGH

## Summary

Phase 6 implements reliable email delivery with PDF attachments, recipient management per category, and immediate critical alerts separate from daily digests. The research identifies proven patterns for HTML-to-PDF conversion, Microsoft Graph API attachment handling, delivery status tracking, and alert notification strategies.

The standard approach uses WeasyPrint for static HTML-to-PDF conversion (avoiding browser dependencies), Microsoft Graph's sendMail endpoint with base64-encoded attachments (under 3MB limit), category-based recipient configuration already present in settings, and separate email workflows for critical alerts vs. daily digests.

Key findings show that:
- WeasyPrint offers optimal performance for static HTML reports without JavaScript dependencies
- Microsoft Graph base64 encoding inflates file size by ~33%, requiring 3MB limit for 4MB API constraint
- Message Trace API (new in 2026) provides modern delivery status tracking
- Tiered notification routing prevents alert fatigue through separation of critical vs. informational emails

**Primary recommendation:** Implement WeasyPrint for PDF generation, extend existing GraphEmailService with attachment support, add delivery tracking to Run model, and create separate critical alert workflow with distinct subject lines and recipient targeting.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| weasyprint | 63.1+ | HTML to PDF conversion | Industry standard for static HTML, no browser dependencies, excellent CSS support, 2026-recommended |
| httpx | 0.27+ | Async HTTP client (already in project) | Used by existing GraphEmailService, async-native for FastAPI |
| azure-identity | 1.19+ | Azure AD authentication (already in project) | Required for Microsoft Graph daemon authentication |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| playwright | 1.49+ | Browser-based PDF generation | Only if JavaScript-heavy content needed (not applicable here) |
| Pillow | 10.4+ | Image processing for WeasyPrint | Required dependency for WeasyPrint image handling |
| pydantic | 2.10+ | Data validation (already in project) | Recipient configuration validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | Playwright | Playwright requires browser engine (70MB+ dependency), slower, overkill for static HTML |
| WeasyPrint | ReportLab | ReportLab requires manual layout programming vs. HTML template reuse |
| Base64 inline | Upload session | Upload session adds complexity, only needed for >3MB attachments |

**Installation:**
```bash
pip install weasyprint>=63.1
# WeasyPrint dependencies (Windows):
# Automatically installs required libraries including Pillow
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── services/
│   ├── emailer.py           # GraphEmailService (exists - extend)
│   ├── reporter.py          # ReportService (exists - use)
│   ├── pdf_generator.py     # NEW: PDFGeneratorService
│   └── alert_service.py     # NEW: CriticalAlertService
├── models/
│   └── run.py               # Add delivery tracking fields
├── schemas/
│   └── delivery.py          # NEW: DeliveryStatus, EmailRecipients
└── routers/
    └── runs.py              # Orchestrate delivery after classification
```

### Pattern 1: PDF Generation from HTML Reports
**What:** Convert existing HTML reports to PDF using WeasyPrint with CSS print media support
**When to use:** After HTML report generation, before email attachment

**Example:**
```python
# Source: WeasyPrint official docs + Best practices 2026
from pathlib import Path
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

class PDFGeneratorService:
    """Generate PDF from HTML reports using WeasyPrint."""

    def __init__(self):
        # Font configuration for proper rendering
        self.font_config = FontConfiguration()

    async def html_to_pdf(
        self,
        html_content: str,
        output_path: Path | None = None
    ) -> bytes:
        """
        Convert HTML to PDF.

        Args:
            html_content: HTML string to convert
            output_path: Optional file path to save PDF

        Returns:
            PDF bytes for attachment or storage
        """
        # Use CSS for print media optimization
        css = CSS(string='''
            @page {
                size: A4;
                margin: 2cm;
            }
            @media print {
                .no-print { display: none; }
            }
        ''', font_config=self.font_config)

        # Generate PDF in memory
        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[css],
            font_config=self.font_config
        )

        # Optionally save to file
        if output_path:
            output_path.write_bytes(pdf_bytes)

        return pdf_bytes
```

### Pattern 2: Email with PDF Attachment via Microsoft Graph
**What:** Extend GraphEmailService to support base64-encoded file attachments
**When to use:** Sending reports with PDF attachments (under 3MB)

**Example:**
```python
# Source: Microsoft Graph API official docs 2026
import base64

async def send_email_with_attachment(
    self,
    to_addresses: list[str],
    subject: str,
    html_body: str,
    attachment_bytes: bytes,
    attachment_name: str,
    cc_addresses: list[str] | None = None,
    bcc_addresses: list[str] | None = None,
) -> dict[str, Any]:
    """Send email with PDF attachment via Microsoft Graph."""

    # Check size limit (3MB for base64 safety)
    if len(attachment_bytes) > 3 * 1024 * 1024:
        return {
            "status": "error",
            "message": "Attachment exceeds 3MB limit"
        }

    # Base64 encode attachment
    attachment_base64 = base64.b64encode(attachment_bytes).decode('utf-8')

    # Build message with attachment
    message_payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [
                {"emailAddress": {"address": addr}} for addr in to_addresses
            ],
            "attachments": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": attachment_name,
                    "contentType": "application/pdf",
                    "contentBytes": attachment_base64
                }
            ]
        },
        "saveToSentItems": True
    }

    # Add CC/BCC if provided
    if cc_addresses:
        message_payload["message"]["ccRecipients"] = [
            {"emailAddress": {"address": addr}} for addr in cc_addresses
        ]
    if bcc_addresses:
        message_payload["message"]["bccRecipients"] = [
            {"emailAddress": {"address": addr}} for addr in bcc_addresses
        ]

    # Send via Graph API (same endpoint as existing send_email)
    # ... token acquisition and HTTP POST logic ...
```

### Pattern 3: Category-Based Recipient Management
**What:** Use existing Settings.get_report_recipients() with TO/CC/BCC expansion
**When to use:** Determining recipients for each report category

**Example:**
```python
# Source: Existing app/config.py + Email management best practices 2026
from pydantic import BaseModel

class EmailRecipients(BaseModel):
    """Email recipient lists per category."""
    to: list[str]
    cc: list[str] = []
    bcc: list[str] = []

class Settings(BaseSettings):
    # Existing fields...
    report_recipients_health: str = ""  # TO addresses
    report_recipients_health_cc: str = ""  # NEW: CC addresses
    report_recipients_health_bcc: str = ""  # NEW: BCC addresses

    def get_email_recipients(self, category: str) -> EmailRecipients:
        """Get TO/CC/BCC recipients for category."""
        category_key = category.lower().replace(" ", "_")

        to_field = f"report_recipients_{category_key}"
        cc_field = f"report_recipients_{category_key}_cc"
        bcc_field = f"report_recipients_{category_key}_bcc"

        return EmailRecipients(
            to=self._parse_recipient_list(getattr(self, to_field, "")),
            cc=self._parse_recipient_list(getattr(self, cc_field, "")),
            bcc=self._parse_recipient_list(getattr(self, bcc_field, ""))
        )

    def _parse_recipient_list(self, recipients_str: str) -> list[str]:
        """Parse comma-separated email list."""
        if not recipients_str:
            return []
        return [r.strip() for r in recipients_str.split(",") if r.strip()]
```

### Pattern 4: Critical Alert Separation
**What:** Separate immediate critical alerts from daily digest reports
**When to use:** When Critical status detected during classification

**Example:**
```python
# Source: Alert notification best practices 2026
class CriticalAlertService:
    """Send immediate critical alerts separate from daily digest."""

    def __init__(self, email_service: GraphEmailService):
        self.email_service = email_service
        self.settings = get_settings()

    async def send_critical_alert(
        self,
        category: str,
        critical_insurers: list[Insurer],
        run_id: int
    ) -> dict[str, Any]:
        """
        Send immediate alert for critical status detection.

        Separate from daily digest with:
        - Distinct subject line with [CRITICAL ALERT] prefix
        - Focused content on critical items only
        - Same recipients as daily digest (configurable later)
        """
        recipients = self.settings.get_email_recipients(category)

        if not recipients.to:
            return {"status": "skipped", "message": "No recipients"}

        # Build focused alert content
        alert_html = self._build_critical_alert_html(
            category=category,
            critical_insurers=critical_insurers,
            run_id=run_id
        )

        # Distinct subject with CRITICAL prefix
        subject = (
            f"[CRITICAL ALERT] {category} Insurer Status - "
            f"{len(critical_insurers)} Critical Item(s)"
        )

        # Send immediately (no PDF attachment for speed)
        return await self.email_service.send_email(
            to_addresses=recipients.to,
            cc_addresses=recipients.cc,
            subject=subject,
            html_body=alert_html,
            save_to_sent=True
        )

    def _build_critical_alert_html(
        self,
        category: str,
        critical_insurers: list[Insurer],
        run_id: int
    ) -> str:
        """Build concise HTML for critical alert."""
        # Use simplified template focusing on critical items
        # Include: insurer name, critical news headline, link to full report
        # ...template rendering logic...
```

### Pattern 5: Delivery Status Tracking
**What:** Track email delivery per run using new Message Trace API (2026)
**When to use:** After email send for delivery confirmation and debugging

**Example:**
```python
# Source: Microsoft Graph Message Trace API 2026 (Public Preview)
from datetime import datetime, timedelta

class DeliveryStatusTracker:
    """Track email delivery status using Message Trace API."""

    async def check_delivery_status(
        self,
        sender_email: str,
        recipient_email: str,
        sent_time: datetime
    ) -> dict[str, Any]:
        """
        Check delivery status for sent email.

        Note: Message Trace API has delay (5-15 minutes typical)
        Use for post-send verification, not immediate confirmation.
        """
        # Message Trace endpoint (beta as of 2026-01-27)
        endpoint = "https://graph.microsoft.com/beta/admin/exchange/tracing/messageTraces"

        # Query parameters
        params = {
            "$filter": (
                f"senderAddress eq '{sender_email}' and "
                f"recipientAddress eq '{recipient_email}' and "
                f"receivedDateTime ge {sent_time.isoformat()}Z"
            )
        }

        # ... token acquisition and API call ...
        # Returns: status (Delivered, Failed, Pending, GettingStatus)
```

### Anti-Patterns to Avoid
- **Synchronous PDF Generation:** Use async wrapper for WeasyPrint to avoid blocking event loop
- **Large Attachments in Base64:** Never exceed 3MB before encoding (4MB API limit)
- **Single Recipient List:** Always separate TO/CC/BCC for proper email etiquette
- **Critical Alerts in Digest:** Never delay critical alerts - send immediately
- **Missing Delivery Tracking:** Always log email send attempts to Run model for debugging

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML to PDF conversion | Custom rendering engine | WeasyPrint | Handles CSS pagination, fonts, images, print media queries - complex edge cases |
| Email attachment encoding | Manual base64 with size checks | Built-in base64.b64encode() + size validation | Proper chunking, memory efficiency, encoding correctness |
| Recipient parsing | String splitting logic | Pydantic validators | Email format validation, duplicate removal, whitespace handling |
| Delivery retry logic | Custom exponential backoff | httpx retry middleware | Handles transient failures, idempotency, timeout management |
| PDF file size optimization | Manual compression | WeasyPrint optimization options | Built-in image compression, font subsetting, efficient rendering |

**Key insight:** Email delivery and PDF generation have numerous edge cases (malformed emails, font rendering, attachment size limits, encoding errors). Use battle-tested libraries rather than reimplementing these complex systems.

## Common Pitfalls

### Pitfall 1: Base64 Encoding Size Bloat
**What goes wrong:** Attachment appears under 4MB but fails with "Request entity too large"
**Why it happens:** Base64 encoding inflates binary size by ~33%, so 3MB file becomes ~4MB encoded
**How to avoid:** Check file size limit at 3MB before encoding, not after
**Warning signs:** HTTP 413 errors from Graph API, "Payload too large" messages

### Pitfall 2: WeasyPrint Windows Font Issues
**What goes wrong:** PDF renders with missing fonts or incorrect characters
**Why it happens:** Windows font paths differ from Linux, FontConfiguration needed
**How to avoid:** Always initialize FontConfiguration(), test on target Windows Server environment
**Warning signs:** Boxes instead of characters in PDF, font substitution warnings

### Pitfall 3: Blocking Event Loop with PDF Generation
**What goes wrong:** API becomes unresponsive during PDF generation
**Why it happens:** WeasyPrint is CPU-intensive synchronous operation in async context
**How to avoid:** Use asyncio.to_thread() or ThreadPoolExecutor for PDF generation
**Warning signs:** Request timeouts, poor concurrent request handling

### Pitfall 4: Critical Alerts Lost in Digest
**What goes wrong:** Critical status discovered but recipient doesn't see alert until next day
**Why it happens:** Critical detection happens during classification but only sent with daily digest
**How to avoid:** Send critical alerts immediately upon detection, separate from digest workflow
**Warning signs:** User complaints about delayed notifications, missed urgent issues

### Pitfall 5: Email Send Success != Delivery Confirmation
**What goes wrong:** Email marked as "sent successfully" but bounces or is filtered
**Why it happens:** Microsoft Graph sendMail returns 202 Accepted (queued), not delivered
**How to avoid:** Use Message Trace API for post-send verification, log send attempts in Run model
**Warning signs:** Users report not receiving emails despite "success" status

### Pitfall 6: Hardcoded Recipient Lists
**What goes wrong:** Adding new recipients requires code changes and deployment
**Why it happens:** Recipient lists in code instead of configuration
**How to avoid:** Use environment variables per category (already implemented), add TO/CC/BCC support
**Warning signs:** Frequent deployment requests just to update recipient lists

## Code Examples

Verified patterns from official sources:

### Complete PDF Generation with Error Handling
```python
# Source: WeasyPrint official docs + Python async best practices 2026
import asyncio
from pathlib import Path
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

class PDFGeneratorService:
    """Generate PDFs from HTML reports."""

    def __init__(self):
        self.font_config = FontConfiguration()
        self.css = CSS(string='''
            @page {
                size: A4;
                margin: 2cm;
            }
            @media print {
                .no-print { display: none; }
                a { color: #0066cc; text-decoration: underline; }
            }
        ''', font_config=self.font_config)

    async def generate_pdf(
        self,
        html_content: str,
        output_path: Path | None = None
    ) -> tuple[bytes, int]:
        """
        Generate PDF from HTML asynchronously.

        Returns:
            Tuple of (pdf_bytes, file_size_bytes)

        Raises:
            ValueError: If PDF generation fails or exceeds size limit
        """
        # Run CPU-intensive PDF generation in thread pool
        pdf_bytes = await asyncio.to_thread(
            self._generate_pdf_sync,
            html_content
        )

        file_size = len(pdf_bytes)

        # Check 3MB limit for email attachment
        max_size = 3 * 1024 * 1024
        if file_size > max_size:
            raise ValueError(
                f"PDF size {file_size} bytes exceeds "
                f"{max_size} byte limit for email attachment"
            )

        # Save to archive if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(output_path.write_bytes, pdf_bytes)

        return pdf_bytes, file_size

    def _generate_pdf_sync(self, html_content: str) -> bytes:
        """Synchronous PDF generation (runs in thread)."""
        return HTML(string=html_content).write_pdf(
            stylesheets=[self.css],
            font_config=self.font_config
        )
```

### Email Delivery with Full Tracking
```python
# Source: Microsoft Graph API official docs + Run model extension
from datetime import datetime
from sqlalchemy.orm import Session

class EmailDeliveryService:
    """Orchestrate email delivery with tracking."""

    def __init__(
        self,
        email_service: GraphEmailService,
        pdf_service: PDFGeneratorService,
        db_session: Session
    ):
        self.email_service = email_service
        self.pdf_service = pdf_service
        self.db = db_session

    async def send_report_with_pdf(
        self,
        category: str,
        html_content: str,
        run_id: int,
        report_date: datetime
    ) -> dict[str, Any]:
        """
        Send HTML report with PDF attachment and tracking.

        Updates Run model with delivery status.
        """
        try:
            # Generate PDF
            pdf_bytes, pdf_size = await self.pdf_service.generate_pdf(
                html_content=html_content
            )

            # Get recipients
            settings = get_settings()
            recipients = settings.get_email_recipients(category)

            if not recipients.to:
                return await self._log_delivery(
                    run_id, "skipped", "No recipients configured"
                )

            # Prepare email
            subject = (
                f"[{settings.company_name}] {category} Intelligence Report - "
                f"{report_date.strftime('%d/%m/%Y')}"
            )

            attachment_name = (
                f"{category}_Report_{report_date.strftime('%Y%m%d')}.pdf"
            )

            # Send email with attachment
            result = await self.email_service.send_email_with_attachment(
                to_addresses=recipients.to,
                cc_addresses=recipients.cc,
                bcc_addresses=recipients.bcc,
                subject=subject,
                html_body=html_content,
                attachment_bytes=pdf_bytes,
                attachment_name=attachment_name
            )

            # Log delivery status
            return await self._log_delivery(
                run_id=run_id,
                status=result["status"],
                message=result.get("message"),
                recipient_count=len(recipients.to),
                pdf_size=pdf_size
            )

        except Exception as e:
            return await self._log_delivery(
                run_id, "error", str(e)
            )

    async def _log_delivery(
        self,
        run_id: int,
        status: str,
        message: str | None = None,
        recipient_count: int = 0,
        pdf_size: int = 0
    ) -> dict[str, Any]:
        """Update Run model with delivery tracking."""
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.email_status = status
            run.email_sent_at = datetime.utcnow()
            run.email_recipients = recipient_count
            run.pdf_size_bytes = pdf_size
            if message:
                run.email_error_message = message
            self.db.commit()

        return {
            "status": status,
            "run_id": run_id,
            "recipients": recipient_count,
            "pdf_size": pdf_size,
            "message": message
        }
```

### Critical Alert Detection and Immediate Send
```python
# Source: Alert notification patterns 2026
class CriticalAlertOrchestrator:
    """Detect and send critical alerts immediately."""

    def __init__(
        self,
        email_service: GraphEmailService,
        db_session: Session
    ):
        self.email_service = email_service
        self.db = db_session
        self.settings = get_settings()

    async def check_and_send_critical_alerts(
        self,
        category: str,
        run_id: int
    ) -> dict[str, Any]:
        """
        Check for critical status and send immediate alert.

        Called during classification phase, separate from daily digest.
        """
        # Find insurers with Critical status in this run
        critical_insurers = (
            self.db.query(Insurer)
            .join(NewsItem)
            .filter(
                Insurer.category == category,
                NewsItem.run_id == run_id,
                NewsItem.status == "Critical"
            )
            .distinct()
            .all()
        )

        if not critical_insurers:
            return {"status": "none", "message": "No critical alerts"}

        # Load news items for each critical insurer
        for insurer in critical_insurers:
            insurer.critical_news = (
                self.db.query(NewsItem)
                .filter(
                    NewsItem.insurer_id == insurer.id,
                    NewsItem.run_id == run_id,
                    NewsItem.status == "Critical"
                )
                .all()
            )

        # Build focused alert HTML
        alert_html = self._build_alert_html(
            category=category,
            critical_insurers=critical_insurers
        )

        # Get recipients (same as daily digest)
        recipients = self.settings.get_email_recipients(category)

        if not recipients.to:
            return {"status": "skipped", "message": "No recipients"}

        # Send immediate alert (no PDF for speed)
        subject = (
            f"[CRITICAL ALERT] {category} Insurer Status - "
            f"{len(critical_insurers)} Critical Item(s) Detected"
        )

        result = await self.email_service.send_email(
            to_addresses=recipients.to,
            cc_addresses=recipients.cc,
            subject=subject,
            html_body=alert_html,
            save_to_sent=True
        )

        # Log critical alert send
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.critical_alert_sent = True
            run.critical_alert_sent_at = datetime.utcnow()
            run.critical_insurers_count = len(critical_insurers)
            self.db.commit()

        return {
            "status": result["status"],
            "critical_count": len(critical_insurers),
            "recipients": len(recipients.to)
        }

    def _build_alert_html(
        self,
        category: str,
        critical_insurers: list[Insurer]
    ) -> str:
        """Build concise critical alert HTML."""
        # Use Jinja2 template for alert email
        # Simpler than full report - focus on critical items only
        template = """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d32f2f;">Critical Alert: {category} Insurers</h2>
            <p>The following insurers have been flagged with <strong>Critical</strong> status:</p>

            {% for insurer in insurers %}
            <div style="border-left: 4px solid #d32f2f; padding-left: 12px; margin: 16px 0;">
                <h3>{{ insurer.name }}</h3>
                <ul>
                {% for news in insurer.critical_news %}
                    <li><strong>{{ news.title }}</strong> - {{ news.source_name }}</li>
                {% endfor %}
                </ul>
            </div>
            {% endfor %}

            <p><em>Full detailed report will be sent in the daily digest.</em></p>
        </body>
        </html>
        """
        # ... template rendering with Jinja2 ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| wkhtmltopdf | WeasyPrint or Playwright | 2024-2025 | wkhtmltopdf based on ancient WebKit, lacks modern CSS support |
| Reporting Web Service | Message Trace API | Jan 2026 | New REST-based delivery tracking, legacy service retiring Apr 2026 |
| Single recipient list | TO/CC/BCC separation | 2025-2026 | Proper email etiquette, reduces reply-all noise |
| Combined notifications | Tiered alert routing | 2026 | Critical vs. informational separation prevents alert fatigue |
| Sync PDF generation | Async with thread pool | 2025-2026 | Prevents event loop blocking in async frameworks like FastAPI |

**Deprecated/outdated:**
- **python-pdfkit/wkhtmltopdf:** Based on Qt WebKit from 2011, lacks flexbox/grid/modern CSS
- **Reporting Web Service for Message Trace:** Retiring April 6, 2026, use Microsoft Graph Message Trace API
- **Inline base64 without size checks:** Graph API changed to stricter 4MB limits, require pre-validation
- **Graph SDK for Windows Server:** Long path issues on Windows, use REST API directly (project already does this)

## Open Questions

1. **PDF Archive Storage Strategy**
   - What we know: ReportArchiver already stores HTML in YYYY/MM/DD hierarchy
   - What's unclear: Should PDFs be stored alongside HTML or separate? Storage limits?
   - Recommendation: Store PDFs in same archive structure, monitor disk usage, add cleanup policy

2. **Message Trace API Availability**
   - What we know: Public Preview started Jan 2026, GA rollout by Feb 2026
   - What's unclear: Exact GA date, beta endpoint stability for production use
   - Recommendation: Implement delivery tracking with graceful fallback, plan upgrade when GA

3. **Critical Alert Recipient Customization**
   - What we know: Currently using same recipients as daily digest
   - What's unclear: Should critical alerts go to different/additional recipients?
   - Recommendation: Start with same recipients, add separate config later if needed (YAGNI)

4. **Email Send Rate Limits**
   - What we know: Graph API has rate limits, sendMail is throttled
   - What's unclear: Specific limits for daemon apps, burst capacity
   - Recommendation: Implement sequential sending per category, monitor for 429 responses

5. **PDF Template Optimization**
   - What we know: Professional HTML template exists with Marsh branding
   - What's unclear: May need PDF-specific CSS adjustments (page breaks, print colors)
   - Recommendation: Test PDF output, add @media print rules as needed

## Sources

### Primary (HIGH confidence)
- [Microsoft Graph sendMail API Documentation](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0) - Official API reference
- [Microsoft Graph Large Attachments](https://learn.microsoft.com/en-us/graph/outlook-large-attachments) - Attachment handling guidance
- [Message Trace API Public Preview](https://techcommunity.microsoft.com/blog/exchange/message-trace-support-using-graph-api-is-now-in-public-preview/4488587) - New delivery tracking feature
- [WeasyPrint Official Documentation](https://weasyprint.org/) - PDF generation library docs

### Secondary (MEDIUM confidence)
- [Python HTML to PDF Libraries 2026 Comparison](https://www.wps.com/blog/python-html-to-pdf-top-5-html-to-pdf-using-python-libraries/) - Library comparison
- [Top Python PDF Generators 2025](https://www.nutrient.io/blog/top-10-ways-to-generate-pdfs-in-python/) - Industry recommendations
- [Critical Alert Best Practices](https://www.confluent.io/blog/build-real-time-alerts/) - Real-time alerting patterns
- [Email Notification Patterns 2026](https://www.courier.com/blog/notification-platform-for-developers/) - Digest vs. immediate alerts

### Tertiary (LOW confidence)
- [Base64 Encoding Memory Efficiency](https://thelinuxcode.com/base64b64encode-in-python-a-practical-production-focused-guide-with-pitfalls-patterns-and-real-examples/) - Performance considerations
- [Email Deliverability 2026](https://expertsender.com/blog/email-deliverability-in-2026-key-observations-trends-challenges-for-marketers/) - Industry trends

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - WeasyPrint is 2026-recommended, existing Graph API proven in Phase 2
- Architecture: HIGH - Builds on existing services, proven patterns from official Microsoft docs
- Pitfalls: HIGH - Based on official documentation warnings and 2026 best practices

**Research date:** 2026-02-04
**Valid until:** 2026-04-04 (60 days - stable email/PDF domain, but Message Trace API in preview)
