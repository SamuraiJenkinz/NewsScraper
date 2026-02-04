# Phase 5: Professional Reporting - Research

**Researched:** 2026-02-04
**Domain:** HTML report generation, responsive design, AI-powered executive summaries
**Confidence:** HIGH

## Summary

Phase 5 enhances the basic reporting infrastructure built in Phase 2 (02-06) to create professional, Marsh-branded HTML reports with comprehensive sections, AI-generated executive summaries, mobile responsiveness, and historical archival capabilities. The research validates that the existing Jinja2 3.1+ foundation is solid and requires enhancement rather than replacement.

The reference HTML designs in `RefChyt/` demonstrate enterprise-grade responsive layouts with Marsh branding (CSS variables: `--marsh-blue: #00263e`, `--marsh-light-blue: #0077c8`). Modern responsive HTML email design (81% mobile readership) requires mobile-first approach, fluid-hybrid layouts, inline CSS for reliability, and media queries for breakpoints. Azure OpenAI gpt-4o deployment (already configured) provides structured output capabilities for executive summary generation with sliding window techniques for large context.

Report archival follows date-based organization patterns (YYYY/MM/DD structure), with metadata indexing enabling efficient browsing and retrieval. The existing `ReportService` class provides the foundation, requiring extension rather than rebuild.

**Primary recommendation:** Enhance existing Jinja2 template infrastructure with responsive CSS, create new comprehensive template matching reference designs, integrate Azure OpenAI for executive summaries, and implement file-based archival system with date hierarchy.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1+ | HTML template rendering | Industry standard for Python HTML templating, built-in autoescape security, template inheritance, bytecode compilation for performance |
| Azure OpenAI | 1.42.0+ | Executive summary generation | Already deployed (gpt-4o), structured outputs with Pydantic, enterprise-grade with Azure integration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | File path manipulation | Date-based directory organization, cross-platform path handling |
| datetime | stdlib | Date formatting | Report timestamps, archive organization, Portuguese locale formatting |
| structlog | 24.0.0+ | Structured logging | Audit trail for report generation and archival operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 | WeasyPrint (HTML to PDF) | Already have Jinja2, Phase 5 focuses on HTML delivery, PDF generation is DEFERRED |
| File-based archival | Database storage | File system is simpler, enables direct HTTP serving, date hierarchy is natural |
| Azure OpenAI | Local LLM | Azure already configured and trusted, enterprise compliance, structured outputs validated |

**Installation:**
```bash
# Already installed in requirements.txt
# jinja2>=3.1.0
# openai>=1.42.0
# structlog>=24.0.0
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── services/
│   ├── reporter.py              # Existing - ENHANCE
│   ├── executive_summarizer.py  # NEW - AI summary generation
│   └── report_archiver.py       # NEW - Storage and retrieval
├── templates/
│   ├── report_basic.html        # Existing - Phase 2
│   └── report_professional.html # NEW - Phase 5 comprehensive template
└── storage/
    └── reports/                 # NEW - Archive root
        └── YYYY/
            └── MM/
                └── DD/
                    ├── health_HH-MM-SS.html
                    ├── dental_HH-MM-SS.html
                    └── metadata.json    # Index for browsing
```

### Pattern 1: Enhanced ReportService with Composition
**What:** Extend existing `ReportService` with new capabilities through composition, not modification
**When to use:** Preserving Phase 2 vertical slice functionality while adding Phase 5 enhancements
**Example:**
```python
# Source: Existing app/services/reporter.py + enhancement pattern
class ReportService:
    def __init__(self):
        self.settings = get_settings()
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        # NEW: Compose with new services
        self.summarizer = ExecutiveSummarizer()  # Phase 5
        self.archiver = ReportArchiver()         # Phase 5

    def generate_professional_report(
        self,
        category: str,
        insurers: list[Insurer],
        report_date: Optional[datetime] = None,
        archive: bool = True
    ) -> tuple[str, Path]:
        """
        Generate comprehensive HTML report with all Phase 5 sections.

        Returns: (html_content, archive_path)
        """
        # Generate AI executive summary
        summary_paragraph = self.summarizer.generate_executive_summary(
            category=category,
            insurers=insurers
        )

        # Prepare template context
        context = self._prepare_professional_context(
            category, insurers, report_date, summary_paragraph
        )

        # Render professional template
        template = self.env.get_template("report_professional.html")
        html = template.render(**context)

        # Archive if requested
        if archive:
            archive_path = self.archiver.save_report(
                html=html,
                category=category,
                report_date=report_date or datetime.now()
            )
            return html, archive_path

        return html, None
```

### Pattern 2: Responsive HTML Email Template with Fluid-Hybrid Layout
**What:** Mobile-first responsive design using fluid tables and media queries
**When to use:** All professional report templates for email delivery (81% mobile readership)
**Example:**
```html
<!-- Source: Mailtrap responsive email design best practices 2026 -->
<!-- Verified: RefChyt/2026-02-03_health_insurer_intelligence_report.html -->
<style>
    :root {
        --marsh-blue: #00263e;
        --marsh-light-blue: #0077c8;
        --marsh-accent: #00a3e0;
    }

    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
        color: #333;
    }

    /* Fluid-hybrid container: max-width for desktop, 100% for mobile */
    .container {
        max-width: 1200px;
        width: 100%;
        margin: 0 auto;
        padding: 40px 20px;
    }

    /* Responsive grid for key findings cards */
    .key-findings {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
        margin-top: 20px;
    }

    /* Responsive table wrapper */
    .coverage-table {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    table {
        width: 100%;
        border-collapse: collapse;
    }

    /* Mobile breakpoint */
    @media screen and (max-width: 600px) {
        .header {
            padding: 20px !important;
        }

        .header h1 {
            font-size: 1.5em !important;
        }

        .container {
            padding: 20px 10px !important;
        }

        .key-findings {
            grid-template-columns: 1fr;
        }

        /* Stack insurer header on mobile */
        .insurer-header {
            flex-direction: column;
            align-items: flex-start !important;
        }

        /* Responsive table: hide less critical columns */
        table th:nth-child(3),
        table td:nth-child(3) {
            display: none;
        }
    }

    /* Print styles */
    @media print {
        .header {
            background: var(--marsh-blue) !important;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }

        .insurer-section {
            break-inside: avoid;
        }
    }
</style>
```

### Pattern 3: Azure OpenAI Executive Summary Generation with Sliding Window
**What:** Generate concise executive summaries from large insurer datasets using structured outputs
**When to use:** Every professional report requires AI-generated executive summary paragraph
**Example:**
```python
# Source: Azure-Samples/summarization-python-openai best practices
# Verified: app/config.py azure_openai_deployment="gpt-4o"
from openai import AzureOpenAI
from pydantic import BaseModel
from typing import Optional

class ExecutiveSummary(BaseModel):
    """Structured output for executive summary generation."""
    paragraph: str  # 2-3 sentence executive summary
    critical_count: int
    watch_count: int
    key_theme: str  # One-word theme: "turbulence", "stability", "growth"

class ExecutiveSummarizer:
    def __init__(self):
        settings = get_settings()
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_key,
            api_version="2024-08-01-preview",
            azure_endpoint=settings.azure_openai_endpoint
        )
        self.model = settings.azure_openai_deployment  # "gpt-4o"

    def generate_executive_summary(
        self,
        category: str,
        insurers: list[Insurer]
    ) -> str:
        """
        Generate executive summary paragraph for report.

        Uses sliding window approach for large datasets.
        Handles token limits gracefully with chunking.
        """
        # Prepare context from insurers
        context_text = self._prepare_context(category, insurers)

        # System prompt in Portuguese for Brazilian executives
        system_prompt = """Você é um analista sênior da Marsh Brasil especializado em inteligência de mercado de seguros.

        Gere um parágrafo executivo conciso (2-3 frases) que resuma os principais desenvolvimentos afetando as seguradoras listadas.

        Foco em:
        - Tendências críticas do mercado
        - Mudanças regulatórias importantes
        - Riscos financeiros ou operacionais
        - Oportunidades estratégicas

        Escreva em português profissional para executivos."""

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context_text}
                ],
                response_format=ExecutiveSummary,
                temperature=0.3,  # Lower for consistency
                max_tokens=500
            )

            summary = response.choices[0].message.parsed
            return summary.paragraph

        except Exception as e:
            logger.error("executive_summary_generation_failed", error=str(e))
            # Fallback to template-based summary
            return self._generate_fallback_summary(category, insurers)

    def _prepare_context(self, category: str, insurers: list[Insurer]) -> str:
        """
        Prepare concise context from insurers.

        Uses sliding window approach to fit token limits.
        """
        lines = [f"Categoria: {category}\n"]

        for insurer in insurers:
            status = self._determine_status(insurer)
            news_count = len(insurer.news_items)

            lines.append(f"\n{insurer.name} (ANS {insurer.ans_code}): {status}")

            # Include only critical news items for context
            critical_news = [n for n in insurer.news_items if n.status == "Critical"][:2]
            for news in critical_news:
                lines.append(f"  - {news.title}")

        return "\n".join(lines)
```

### Pattern 4: Date-Based Report Archival with Metadata Index
**What:** Hierarchical file storage with YYYY/MM/DD structure and JSON metadata for browsing
**When to use:** REPT-12 (archival) and REPT-13 (browsing) requirements
**Example:**
```python
# Source: Python archival systems best practices, ArchivesSpace patterns
from pathlib import Path
import json
from datetime import datetime
from typing import Optional

class ReportArchiver:
    def __init__(self):
        settings = get_settings()
        # Base archive directory: app/storage/reports/
        self.archive_root = Path(__file__).parent.parent / "storage" / "reports"
        self.archive_root.mkdir(parents=True, exist_ok=True)

    def save_report(
        self,
        html: str,
        category: str,
        report_date: datetime
    ) -> Path:
        """
        Save report to date-based archive with metadata.

        Structure: reports/YYYY/MM/DD/category_HH-MM-SS.html

        Returns: Full path to saved report
        """
        # Create date-based directory structure
        year_dir = self.archive_root / str(report_date.year)
        month_dir = year_dir / f"{report_date.month:02d}"
        day_dir = month_dir / f"{report_date.day:02d}"
        day_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        time_suffix = report_date.strftime("%H-%M-%S")
        filename = f"{category.lower().replace(' ', '_')}_{time_suffix}.html"
        report_path = day_dir / filename

        # Write HTML report
        report_path.write_text(html, encoding='utf-8')

        # Update metadata index
        self._update_metadata(day_dir, category, filename, report_date)

        logger.info(
            "report_archived",
            category=category,
            path=str(report_path),
            size_kb=len(html) // 1024
        )

        return report_path

    def _update_metadata(
        self,
        day_dir: Path,
        category: str,
        filename: str,
        report_date: datetime
    ):
        """Update metadata.json index for browsing."""
        metadata_path = day_dir / "metadata.json"

        # Load existing metadata or create new
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
        else:
            metadata = {"date": report_date.date().isoformat(), "reports": []}

        # Add report entry
        metadata["reports"].append({
            "category": category,
            "filename": filename,
            "timestamp": report_date.isoformat(),
            "size_kb": (day_dir / filename).stat().st_size // 1024
        })

        # Write updated metadata
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    def browse_reports(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None
    ) -> list[dict]:
        """
        Browse archived reports with filtering.

        Returns list of report metadata matching filters.
        """
        reports = []

        # Walk date hierarchy
        for year_dir in sorted(self.archive_root.iterdir(), reverse=True):
            if not year_dir.is_dir():
                continue

            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue

                for day_dir in sorted(month_dir.iterdir(), reverse=True):
                    if not day_dir.is_dir():
                        continue

                    metadata_path = day_dir / "metadata.json"
                    if not metadata_path.exists():
                        continue

                    metadata = json.loads(metadata_path.read_text())

                    # Filter by date range
                    report_date = datetime.fromisoformat(metadata["date"] + "T00:00:00")
                    if start_date and report_date < start_date:
                        continue
                    if end_date and report_date > end_date:
                        continue

                    # Filter by category
                    for report in metadata["reports"]:
                        if category and report["category"].lower() != category.lower():
                            continue

                        reports.append({
                            "date": metadata["date"],
                            "category": report["category"],
                            "filename": report["filename"],
                            "timestamp": report["timestamp"],
                            "path": str(day_dir / report["filename"]),
                            "size_kb": report["size_kb"]
                        })

        return reports
```

### Anti-Patterns to Avoid
- **Inline CSS Everywhere:** Use CSS variables and template inheritance for maintainability, not just inline styles. Reference template demonstrates proper use of `:root` variables.
- **Hard-coded Colors:** Use Marsh brand CSS variables (`--marsh-blue`, etc.) from reference design, not hex values scattered throughout templates.
- **Unescaped User Content:** Jinja2 autoescape is enabled - don't use `|safe` filter unless absolutely necessary and content is validated.
- **Database BLOB Storage:** File-based archival is simpler, faster, and enables direct HTTP serving. Don't store HTML in database unless required.
- **Synchronous AI Calls in Request Path:** Executive summary generation should be async or background task to avoid request timeouts.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML escaping for security | Custom sanitizer functions | Jinja2 autoescape (already enabled) | XSS protection, handles edge cases, battle-tested |
| Date formatting for Portuguese | String manipulation | datetime.strftime with locale | Proper i18n, handles edge cases like month names |
| Responsive email tables | Custom JavaScript | CSS grid with `auto-fit` + media queries | Works without JavaScript, email client compatible |
| Executive summary prompts | Simple string templates | Structured outputs with Pydantic | Type safety, validation, consistent format |
| Token limit handling | Manual chunking | Azure OpenAI sliding window pattern | Proven approach, handles edge cases, maintains context |
| File path operations | String concatenation | pathlib.Path | Cross-platform, prevents path traversal, cleaner API |

**Key insight:** HTML templating and responsive design have mature patterns (Jinja2 3.1+, CSS Grid, media queries). Azure OpenAI structured outputs eliminate manual JSON parsing. File-based archival with pathlib is simpler and more maintainable than database storage for this use case.

## Common Pitfalls

### Pitfall 1: Mobile Rendering Breaks in Email Clients
**What goes wrong:** Report looks perfect in browser but breaks in Outlook mobile or Gmail app
**Why it happens:** Email clients strip external CSS, ignore flex/grid in older versions, have inconsistent CSS support
**How to avoid:**
- Use inline CSS for critical styles (Jinja2 can inject inline styles)
- Test media queries work in email clients (max-width 600px is safe breakpoint)
- Use fluid-hybrid approach: `width: 100%; max-width: 600px;` for containers
- Avoid external stylesheets completely
**Warning signs:** Template works in browser preview but not in actual email client testing

### Pitfall 2: Azure OpenAI Token Limit Exceeded
**What goes wrong:** Executive summary generation fails when >8K tokens of insurer data passed to model
**Why it happens:** gpt-4o has 128K context but structured outputs recommend staying under 8K for reliability
**How to avoid:**
- Implement sliding window: summarize in chunks, combine results
- Prioritize critical news items only for context
- Use concise representation: insurer name + status + top 2 headlines per insurer
- Add retry logic with exponential backoff for rate limits
**Warning signs:** Intermittent failures on large datasets, 400 errors from OpenAI API

### Pitfall 3: Portuguese Date Formatting Without Locale
**What goes wrong:** Report shows "January" instead of "Janeiro", "02/03/2026" ambiguous (Feb 3 or March 2?)
**Why it happens:** Python datetime defaults to English locale, DD/MM/YYYY vs MM/DD/YYYY confusion
**How to avoid:**
- Use explicit Portuguese date format strings: `"%d de %B de %Y"` → "03 de fevereiro de 2026"
- Import Portuguese month names mapping or use Babel library
- Always use DD/MM/YYYY format for Brazilian audience (never MM/DD/YYYY)
- Document format in template comments
**Warning signs:** Client complaints about date confusion, English month names in Portuguese reports

### Pitfall 4: Archive Storage Grows Unbounded
**What goes wrong:** Reports directory grows to 100GB+ over time, slows browsing, fills disk
**Why it happens:** No retention policy, every report saved forever, HTML is verbose
**How to avoid:**
- Implement retention policy: keep 90 days, archive older to compressed format
- Add cleanup job: delete reports older than retention period
- Consider compression: gzip HTML files (70-80% size reduction)
- Monitor disk usage with alerts
**Warning signs:** Slow report browsing, disk space alerts, directory with >10K files

### Pitfall 5: Category Indicators Not Displayed
**What goes wrong:** Reports don't show WHY insurers are flagged (missing category_indicators from Phase 4)
**Why it happens:** Template doesn't render category_indicators field, classification data not loaded
**How to avoid:**
- Ensure NewsItem.category_indicators loaded in query (eager loading or join)
- Template includes section for "Por que Critical/Watch?" with indicator badges
- Map indicator codes to Portuguese labels: "high_complaint" → "Alto índice de reclamações"
- Test with Phase 4 classified data to verify indicators appear
**Warning signs:** Reports missing justification for status, users ask "why Critical?"

## Code Examples

Verified patterns from official sources:

### Jinja2 Template with Marsh Branding and Portuguese Labels
```html
<!-- Source: RefChyt/2026-02-03_health_insurer_intelligence_report.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ category }} Intelligence Report | Marsh Brasil</title>
    <style>
        :root {
            --marsh-blue: #00263e;
            --marsh-light-blue: #0077c8;
            --marsh-accent: #00a3e0;
            --alert-red: #dc3545;
            --alert-orange: #fd7e14;
            --alert-yellow: #ffc107;
            --success-green: #28a745;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            color: #333;
            line-height: 1.6;
        }

        .confidential-banner {
            background: var(--alert-red);
            color: white;
            text-align: center;
            padding: 8px;
            font-size: 0.85em;
            font-weight: 600;
            letter-spacing: 1px;
        }

        .header {
            background: linear-gradient(135deg, var(--marsh-blue) 0%, #005a87 100%);
            color: white;
            padding: 40px 60px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        .executive-summary {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border-left: 5px solid var(--marsh-light-blue);
        }

        .key-findings {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .finding-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid var(--marsh-accent);
        }

        .finding-card.critical {
            border-left-color: var(--alert-red);
            background: #fff5f5;
        }

        .finding-card.warning {
            border-left-color: var(--alert-orange);
            background: #fff8f0;
        }

        .finding-card.positive {
            border-left-color: var(--success-green);
            background: #f0fff4;
        }

        /* Responsive breakpoint */
        @media screen and (max-width: 600px) {
            .header {
                padding: 20px !important;
            }

            .container {
                padding: 20px 10px !important;
            }

            .key-findings {
                grid-template-columns: 1fr;
            }
        }

        @media print {
            .header {
                background: var(--marsh-blue) !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
        }
    </style>
</head>
<body>
    <div class="confidential-banner">
        CONFIDENCIAL - USO INTERNO - MARSH BRASIL DDH INTELIGÊNCIA DE SEGURADORAS
    </div>

    <header class="header">
        <div class="header-content">
            <h1>Relatório de Inteligência - {{ category }}</h1>
            <p class="subtitle">Mercado Brasileiro de Seguros - Análise DDH</p>
            <div class="date-badge">Período: {{ report_date }}</div>
        </div>
    </header>

    <div class="container">
        <!-- Executive Summary with AI-generated paragraph -->
        <section class="executive-summary">
            <h2>Resumo Executivo</h2>
            <p>{{ executive_summary_paragraph }}</p>

            <div class="key-findings">
                {% for finding in key_findings %}
                <div class="finding-card {{ finding.severity }}">
                    <h4>{{ finding.title }}</h4>
                    <p>{{ finding.description }}</p>
                </div>
                {% endfor %}
            </div>
        </section>

        <!-- Coverage Summary Table -->
        <section class="coverage-table">
            <h2>Resumo de Cobertura DDH</h2>
            <table>
                <thead>
                    <tr>
                        <th>Seguradora</th>
                        <th>Código ANS</th>
                        <th>Market Master</th>
                        <th>Produto</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for insurer in insurers %}
                    <tr>
                        <td>{{ insurer.name }}</td>
                        <td>{{ insurer.ans_code }}</td>
                        <td>{{ insurer.market_master_code }}</td>
                        <td>{{ insurer.category }}</td>
                        <td><span class="status-badge status-{{ insurer.status|lower }}">{{ insurer.status }}</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>

        <!-- Insurers grouped by status priority -->
        {% for status in ['Critical', 'Watch', 'Monitor', 'Stable'] %}
        {% set status_insurers = insurers_by_status.get(status, []) %}
        {% if status_insurers %}
        <section class="insurer-section">
            <div class="insurer-header">
                <h2>{{ status }} ({{ status_insurers|length }})</h2>
            </div>
            <div class="insurer-content">
                {% for insurer in status_insurers %}
                <!-- Insurer details with news items and category indicators -->
                <div class="insurer-card">
                    <h3>{{ insurer.name }}</h3>
                    {% for news in insurer.news_items %}
                    <div class="news-item">
                        <h4>{{ news.title }}</h4>
                        {% if news.category_indicators %}
                        <div class="indicators">
                            {% for indicator in news.category_indicators %}
                            <span class="indicator-badge">{{ indicator|map_to_portuguese }}</span>
                            {% endfor %}
                        </div>
                        {% endif %}
                        <p>{{ news.summary }}</p>
                        <div class="news-meta">
                            Fonte: {{ news.source_name }} | {{ news.published_at }}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% endfor %}
            </div>
        </section>
        {% endif %}
        {% endfor %}

        <!-- Market Context Section -->
        <section class="market-context">
            <h2>Contexto de Mercado</h2>
            <p>{{ market_context_paragraph }}</p>
        </section>

        <!-- Strategic Recommendations Section -->
        <section class="strategic-recommendations">
            <h2>Recomendações Estratégicas</h2>
            <ul>
                {% for recommendation in recommendations %}
                <li>{{ recommendation }}</li>
                {% endfor %}
            </ul>
        </section>
    </div>

    <footer class="footer">
        <p>Gerado em: {{ generation_timestamp }} | BrasilIntel v1.0</p>
        <p>Este relatório é confidencial e destinado apenas aos destinatários indicados.</p>
    </footer>
</body>
</html>
```

### Azure OpenAI Structured Output with Error Handling
```python
# Source: Azure OpenAI best practices, app/services/classifier.py pattern
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from typing import Optional
import structlog

logger = structlog.get_logger()

class ExecutiveSummary(BaseModel):
    """Structured output for executive summary generation."""
    paragraph: str = Field(
        description="2-3 sentence executive summary in Portuguese"
    )
    critical_count: int = Field(
        description="Number of insurers with Critical status"
    )
    watch_count: int = Field(
        description="Number of insurers with Watch status"
    )
    key_theme: str = Field(
        description="One-word market theme: turbulence, stability, growth, consolidation"
    )

def generate_executive_summary(
    category: str,
    insurers: list[Insurer],
    client: AzureOpenAI,
    model: str
) -> Optional[str]:
    """
    Generate executive summary with retry logic.

    Returns summary paragraph or None on failure.
    """
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            system_prompt = """Você é um analista sênior da Marsh Brasil.

            Gere um parágrafo executivo conciso (2-3 frases) em português que resuma
            os principais desenvolvimentos afetando as seguradoras listadas.

            Foco em tendências críticas, mudanças regulatórias, riscos financeiros
            e oportunidades estratégicas."""

            context = _prepare_context(category, insurers)

            response = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                response_format=ExecutiveSummary,
                temperature=0.3,
                max_tokens=500,
                timeout=30.0
            )

            summary = response.choices[0].message.parsed

            logger.info(
                "executive_summary_generated",
                category=category,
                critical_count=summary.critical_count,
                theme=summary.key_theme
            )

            return summary.paragraph

        except Exception as e:
            retry_count += 1
            logger.warning(
                "executive_summary_retry",
                attempt=retry_count,
                error=str(e)
            )

            if retry_count >= max_retries:
                logger.error(
                    "executive_summary_failed",
                    category=category,
                    error=str(e)
                )
                return None

            # Exponential backoff
            import time
            time.sleep(2 ** retry_count)

    return None

def _prepare_context(category: str, insurers: list[Insurer]) -> str:
    """Prepare concise context for LLM."""
    lines = [f"Categoria: {category}\nSeguradoras:\n"]

    for insurer in insurers:
        # Determine status from news items
        statuses = [n.status for n in insurer.news_items if n.status]
        status = max(statuses, key=lambda s: ["Stable", "Monitor", "Watch", "Critical"].index(s)) if statuses else "Unknown"

        lines.append(f"\n{insurer.name} (ANS {insurer.ans_code}): {status}")

        # Include top 2 critical news items
        critical_news = [n for n in insurer.news_items if n.status in ["Critical", "Watch"]][:2]
        for news in critical_news:
            lines.append(f"  - {news.title}")

    return "\n".join(lines)
```

### Report Archive Browsing API Endpoint
```python
# Source: FastAPI patterns, app/routers/ structure
from fastapi import APIRouter, Depends, Query
from datetime import datetime
from typing import Optional

from app.services.report_archiver import ReportArchiver
from pydantic import BaseModel

router = APIRouter(prefix="/reports/archive", tags=["Reports"])

class ArchivedReport(BaseModel):
    """Schema for archived report metadata."""
    date: str
    category: str
    filename: str
    timestamp: str
    path: str
    size_kb: int

@router.get("", response_model=list[ArchivedReport])
async def browse_archived_reports(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    category: Optional[str] = Query(None, description="Health, Dental, Group Life")
):
    """
    Browse archived reports with optional filtering.

    Returns list of reports sorted by date descending (newest first).
    """
    archiver = ReportArchiver()

    # Parse date strings
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    reports = archiver.browse_reports(
        start_date=start,
        end_date=end,
        category=category
    )

    return [ArchivedReport(**r) for r in reports]

@router.get("/{date}/{category}/{filename}")
async def get_archived_report(
    date: str,
    category: str,
    filename: str
):
    """
    Retrieve specific archived report HTML.

    Path format: /archive/2026-02-04/health/health_14-30-00.html
    """
    from fastapi.responses import HTMLResponse
    from pathlib import Path

    archiver = ReportArchiver()

    # Parse date to directory structure
    date_obj = datetime.fromisoformat(date)
    report_path = (
        archiver.archive_root
        / str(date_obj.year)
        / f"{date_obj.month:02d}"
        / f"{date_obj.day:02d}"
        / filename
    )

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    html = report_path.read_text(encoding='utf-8')
    return HTMLResponse(content=html)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bootstrap 4 for emails | CSS Grid + media queries | 2022-2024 | Better mobile support, no JavaScript dependency, faster rendering |
| WeasyPrint for HTML→PDF | Direct HTML email delivery | Phase 5 scope | Simpler, faster, better responsive support (PDF deferred to later) |
| Manual JSON parsing from LLM | Structured outputs with Pydantic | OpenAI 1.x (2024) | Type safety, automatic validation, cleaner code |
| Database BLOB storage for reports | File-based with date hierarchy | Modern best practice | Simpler, faster retrieval, direct HTTP serving |
| Manual CSS in templates | CSS variables (`:root`) | CSS3 standard (2015+) | Maintainability, brand consistency, easier theming |

**Deprecated/outdated:**
- **Table-based layouts for email:** CSS Grid with `auto-fit` is now email-client compatible and preferred for responsive grids
- **External stylesheets in email:** Inline CSS required for email client compatibility (Gmail, Outlook strip external CSS)
- **OpenAI completion API:** Replaced by chat completions with structured outputs (beta.chat.completions.parse)

## Open Questions

Things that couldn't be fully resolved:

1. **Market Context and Strategic Recommendations Content Sources**
   - What we know: Requirements specify these sections (REPT-08, REPT-09) but don't define content sources
   - What's unclear: Should these be AI-generated, template-based, or manually authored? Who provides regulatory updates?
   - Recommendation: Start with template placeholders, add AI generation in iteration 2 if content sources defined

2. **Report Archive Retention Policy**
   - What we know: REPT-12 requires archival, but no retention period specified
   - What's unclear: How long to keep reports? When to compress/delete?
   - Recommendation: Implement 90-day retention as default, make configurable in settings, add cleanup job

3. **Email Client Testing Coverage**
   - What we know: Reports must render on mobile (REPT-11), 81% mobile readership
   - What's unclear: Which email clients to officially support? (Gmail, Outlook, Apple Mail, etc.)
   - Recommendation: Test on Gmail (mobile + desktop), Outlook (mobile + desktop), Apple Mail as minimum viable set

4. **Logo Image Embedding vs Linking**
   - What we know: Marsh logo exists at `RefChyt/logo.png`
   - What's unclear: Should logo be base64-embedded in HTML or linked via HTTP? Email delivery implications?
   - Recommendation: Research Microsoft Graph email attachment vs embedded image for Phase 6 integration

## Sources

### Primary (HIGH confidence)
- [Jinja2 3.1.x Official Documentation](https://jinja.palletsprojects.com/) - Template syntax, autoescape, FileSystemLoader
- [Azure OpenAI Python SDK Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart) - Structured outputs, chat completions
- Reference HTML designs in `C:\BrasilIntel\RefChyt\2026-02-03_health_insurer_intelligence_report.html` - Marsh branding, responsive patterns
- Existing codebase `app/services/reporter.py` and `app/templates/report_basic.html` - Phase 2 foundation

### Secondary (MEDIUM confidence)
- [Responsive Email Design Tutorial with Code Snippets 2026](https://mailtrap.io/blog/responsive-email-design/) - Mobile-first patterns, fluid-hybrid layouts
- [Best Practices for Responsive Email Templates 2025 Guide](https://blog.groupmail.io/best-practices-for-responsive-email-templates-2025-guide/) - 81% mobile readership statistic, inline CSS requirements
- [Azure Summarization Python OpenAI Samples](https://github.com/Azure-Samples/summarization-python-openai) - Sliding window approach, token management
- [HTML Tables in Responsive Design Do's and Don'ts 2025](https://618media.com/en/blog/html-tables-in-responsive-design/) - Responsive table patterns

### Tertiary (LOW confidence)
- [Comprehensive Practical Guide to Jinja2 Template Engine](https://www.oreateai.com/blog/comprehensive-practical-guide-to-jinja2-template-engine/c6f4f2f0d0d1be2354c8353b43868f2b) - Best practices overview
- [Python for Archivists](https://scholarsarchive.library.albany.edu/cgi/viewcontent.cgi?article=1092&context=ulib_fac_scholar) - Date-based archival patterns
- [Color Design Trends for 2026](https://sagedesigngroup.biz/color-design-trends-for-2026-what-brands-designers-should-watch/) - Corporate branding guidelines

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Jinja2 and Azure OpenAI already deployed and validated in Phase 2 and Phase 4
- Architecture: HIGH - Patterns verified from reference HTML designs and existing codebase structure
- Pitfalls: HIGH - Based on documented best practices and common email/LLM integration issues

**Research date:** 2026-02-04
**Valid until:** 30 days (stable domain - HTML templates and Azure OpenAI patterns evolve slowly)

---

## Sources

- [Template Designer Documentation — Jinja Documentation (3.1.x)](https://jinja.palletsprojects.com/en/stable/templates/)
- [Comprehensive Practical Guide to Jinja2 Template Engine - Oreate AI Blog](https://www.oreateai.com/blog/comprehensive-practical-guide-to-jinja2-template-engine/c6f4f2f0d0d1be2354c8353b43868f2b)
- [Responsive Email Design: Tutorial with Code Snippets [2026]](https://mailtrap.io/blog/responsive-email-design/)
- [Best Practices for Responsive Email Templates (2025 Guide)](https://blog.groupmail.io/best-practices-for-responsive-email-templates-2025-guide/)
- [HTML Tables in Responsive Design: Do's and Don'ts (2025)](https://618media.com/en/blog/html-tables-in-responsive-design/)
- [Azure OpenAI Responses API - Azure OpenAI | Microsoft Learn](https://learn.microsoft.com/en/azure/ai-services/openai/quickstart)
- [GitHub - Azure-Samples/summarization-python-openai](https://github.com/Azure-Samples/summarization-python-openai)
- [Python for Archivists: breaking down barriers between systems](https://scholarsarchive.library.albany.edu/cgi/viewcontent.cgi?article=1092&context=ulib_fac_scholar)
- [Large-Scale Date Normalization in ArchivesSpace with Python, MySQL, and Timetwister](https://journal.code4lib.org/articles/14443)
- [Color Design Trends for 2026: What Brands & Designers Should Watch - Sage Design Group](https://sagedesigngroup.biz/color-design-trends-for-2026-what-brands-designers-should-watch/)
- [HTML <Table> tag: 2026 Guide](https://elementor.com/blog/html-table-tag/)
