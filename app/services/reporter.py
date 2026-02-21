"""
HTML report generation service using Jinja2 templates.

Transforms classified insurer news into professional HTML reports suitable
for email delivery. Groups insurers by status priority with executive summary.

Phase 5: Enhanced with professional template, AI summaries, and archival.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.insurer import Insurer
from app.models.news_item import NewsItem
from app.models.run import Run
from app.services.executive_summarizer import ExecutiveSummarizer
from app.services.report_archiver import ReportArchiver
from app.schemas.report import KeyFinding, ReportContext


@dataclass
class ReportData:
    """
    Container for report generation data.

    Organizes insurers and metadata for template rendering.
    """
    category: str
    insurers: list[Insurer]
    report_date: datetime
    company_name: str = "Marsh Brasil"


class ReportService:
    """
    Service for generating HTML reports using Jinja2 templates.

    Generates professional HTML reports with:
    - Executive summary with status counts
    - Insurers grouped by status (Critical first)
    - News items with summaries and sentiment
    """

    # Indicator label mapping for Portuguese display
    INDICATOR_LABELS = {
        "market_share_change": "Variacao de Market Share",
        "financial_health": "Saude Financeira",
        "regulatory_compliance": "Conformidade Regulatoria",
        "customer_satisfaction": "Satisfacao do Cliente",
        "product_innovation": "Inovacao de Produtos",
        "leadership_change": "Mudanca de Lideranca",
        "merger_acquisition": "Fusao e Aquisicao",
        "legal_issues": "Questoes Legais",
        "technology_investment": "Investimento em Tecnologia",
        "partnership": "Parceria",
    }

    def __init__(self):
        """Initialize Jinja2 environment with template loader."""
        self.settings = get_settings()

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Register custom filter for indicator labels
        self.env.filters['indicator_label'] = self.get_indicator_label

        # Phase 5: Compose with new services
        self.summarizer = ExecutiveSummarizer()
        self.archiver = ReportArchiver()

    def get_insurers_by_status(self, insurers: list[Insurer]) -> dict[str, list[Insurer]]:
        """
        Group insurers by status priority.

        Returns dict with keys: Critical, Watch, Monitor, Stable
        Each containing list of insurers with that status.
        Order ensures Critical appears first in reports.
        """
        status_priority = ["Critical", "Watch", "Monitor", "Stable"]
        grouped = {status: [] for status in status_priority}

        for insurer in insurers:
            # Determine insurer status from their news items
            if not insurer.news_items:
                continue

            # Use the most severe status from any news item
            statuses = [news.status for news in insurer.news_items if news.status]
            if not statuses:
                continue

            # Find most critical status
            for status in status_priority:
                if status in statuses:
                    grouped[status].append(insurer)
                    break

        return grouped

    def get_status_counts(self, insurers_by_status: dict[str, list[Insurer]]) -> dict[str, int]:
        """
        Calculate count of insurers in each status.

        Returns dict with status names as keys and counts as values.
        """
        return {
            status: len(insurers)
            for status, insurers in insurers_by_status.items()
        }

    def generate_report(
        self,
        category: str,
        insurers: list[Insurer],
        report_date: Optional[datetime] = None
    ) -> str:
        """
        Generate HTML report for a category of insurers.

        Args:
            category: Insurer category (Health, Dental, Group Life)
            insurers: List of Insurer objects with loaded news_items
            report_date: Date for report (defaults to now)

        Returns:
            Rendered HTML report as string
        """
        if report_date is None:
            report_date = datetime.now()

        # Group insurers by status
        insurers_by_status = self.get_insurers_by_status(insurers)
        status_counts = self.get_status_counts(insurers_by_status)

        # Load and render template
        template = self.env.get_template("report_basic.html")

        return template.render(
            company_name=self.settings.company_name,
            category=category,
            report_date=report_date.strftime("%d/%m/%Y"),
            generation_timestamp=datetime.now().strftime("%d/%m/%Y às %H:%M"),
            total_insurers=len(insurers),
            insurers_by_status=insurers_by_status,
            status_counts=status_counts
        )

    def generate_report_from_db(
        self,
        category: str,
        run_id: int,
        db_session: Session
    ) -> str:
        """
        Generate report for a specific run from database.

        Loads insurers and their news items for the specified run,
        then generates the HTML report.

        Args:
            category: Insurer category to filter by
            run_id: Run ID to generate report for
            db_session: Database session

        Returns:
            Rendered HTML report as string

        Raises:
            ValueError: If run not found
        """
        # Verify run exists
        run = db_session.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise ValueError(f"Run {run_id} not found")

        # Load insurers with their news items for this run
        insurers = (
            db_session.query(Insurer)
            .filter(
                Insurer.category == category,
                Insurer.enabled == True
            )
            .join(NewsItem, NewsItem.insurer_id == Insurer.id)
            .filter(NewsItem.run_id == run_id)
            .distinct()
            .all()
        )

        # Load news items for each insurer, then detach from session.
        # Order matters: query BEFORE expunge to avoid lazy load errors
        # when downstream code accesses insurer.news_items on the detached object.
        for insurer in insurers:
            # Query news items while insurer is still bound to session
            run_news_items = (
                db_session.query(NewsItem)
                .filter(
                    NewsItem.insurer_id == insurer.id,
                    NewsItem.run_id == run_id
                )
                .all()
            )
            # Expunge to detach from session, then assign pre-loaded items
            db_session.expunge(insurer)
            insurer.news_items = run_news_items

        return self.generate_report(
            category=category,
            insurers=insurers,
            report_date=run.started_at
        )

    def preview_template(self) -> str:
        """
        Generate a preview report with sample data for testing.

        Creates mock insurers and news items to demonstrate
        the report template layout and styling.

        Returns:
            Rendered HTML report with sample data
        """
        # Create mock insurers with news
        critical_insurer = Insurer(
            id=1,
            ans_code="123456",
            name="Seguradora XYZ",
            cnpj="12.345.678/0001-90",
            category="Health",
            status="Critical"
        )
        critical_insurer.news_items = [
            NewsItem(
                id=1,
                title="Seguradora enfrenta problemas financeiros graves",
                source_name="Folha de S.Paulo",
                source_url="https://example.com/news1",
                published_at=datetime(2024, 1, 15),
                status="Critical",
                sentiment="negative",
                summary="• Prejuízo de R$ 50 milhões no último trimestre\n• Inadimplência cresceu 15%\n• ANS abriu processo de fiscalização"
            )
        ]

        watch_insurer = Insurer(
            id=2,
            ans_code="234567",
            name="Plano Saúde ABC",
            cnpj="23.456.789/0001-01",
            category="Health",
            status="Watch"
        )
        watch_insurer.news_items = [
            NewsItem(
                id=2,
                title="Reclamações aumentam no Reclame Aqui",
                source_name="Portal da Saúde",
                source_url="https://example.com/news2",
                published_at=datetime(2024, 1, 14),
                status="Watch",
                sentiment="neutral",
                summary="• Aumento de 25% nas reclamações\n• Demora na autorização de procedimentos\n• Empresa divulgou nota oficial"
            )
        ]

        stable_insurer = Insurer(
            id=3,
            ans_code="345678",
            name="Saúde Vida Seguros",
            cnpj="34.567.890/0001-12",
            category="Health",
            status="Stable"
        )
        stable_insurer.news_items = [
            NewsItem(
                id=3,
                title="Empresa lança novo produto para PMEs",
                source_name="Valor Econômico",
                source_url="https://example.com/news3",
                published_at=datetime(2024, 1, 13),
                status="Stable",
                sentiment="positive",
                summary="• Novo plano com cobertura ampliada\n• Foco em pequenas e médias empresas\n• Expectativa de crescer 10% no segmento"
            )
        ]

        mock_insurers = [critical_insurer, watch_insurer, stable_insurer]

        return self.generate_report(
            category="Health",
            insurers=mock_insurers,
            report_date=datetime.now()
        )

    # =========================================================================
    # Phase 5: Professional Report Generation
    # =========================================================================

    @staticmethod
    def get_indicator_label(indicator: str) -> str:
        """
        Get Portuguese label for category indicator.

        Used as Jinja2 filter for template rendering.

        Args:
            indicator: Indicator key (e.g., 'financial_health')

        Returns:
            Portuguese label or formatted key if not found
        """
        return ReportService.INDICATOR_LABELS.get(
            indicator.strip(),
            indicator.strip().replace("_", " ").title()
        )

    def generate_professional_report(
        self,
        category: str,
        insurers: list[Insurer],
        report_date: Optional[datetime] = None,
        use_ai_summary: bool = True,
        archive_report: bool = True,
        equity_data: dict = None
    ) -> Tuple[str, Optional[Path]]:
        """
        Generate comprehensive professional HTML report.

        Uses the professional template with:
        - AI-generated executive summary (optional)
        - Market context sections
        - Strategic recommendations
        - Category indicators with Portuguese labels
        - Equity price chips (optional)
        - Report archival (optional)

        Args:
            category: Insurer category (Health, Dental, Group Life)
            insurers: List of Insurer objects with loaded news_items
            report_date: Date for report (defaults to now)
            use_ai_summary: Whether to use AI for executive summary
            archive_report: Whether to save report to archive
            equity_data: Optional dict mapping insurer_id to list of price dicts

        Returns:
            Tuple of (rendered HTML string, archive path or None)
        """
        if report_date is None:
            report_date = datetime.now()

        # Default equity_data to empty dict for backward compatibility
        if equity_data is None:
            equity_data = {}

        # Group insurers by status
        insurers_by_status = self.get_insurers_by_status(insurers)
        status_counts = self.get_status_counts(insurers_by_status)

        # Generate executive summary (AI or fallback)
        if use_ai_summary:
            executive_summary = self.summarizer.generate_executive_summary(
                category=category,
                insurers=insurers
            )
        else:
            executive_summary = self._get_basic_summary(category, insurers, status_counts)

        # Generate key findings
        key_findings = self.summarizer.generate_key_findings(insurers_by_status)

        # Generate market context
        market_context = self._generate_market_context(category, insurers, status_counts)

        # Generate recommendations
        recommendations = self._generate_recommendations(insurers_by_status, status_counts)

        # Load and render professional template
        template = self.env.get_template("report_professional.html")

        html = template.render(
            company_name=self.settings.company_name,
            category=category,
            report_date=report_date.strftime("%d/%m/%Y"),
            generation_timestamp=datetime.now().strftime("%d/%m/%Y as %H:%M"),
            total_insurers=len(insurers),
            insurers_by_status=insurers_by_status,
            status_counts=status_counts,
            executive_summary=executive_summary,
            key_findings=key_findings,
            market_context=market_context,
            recommendations=recommendations,
            equity_by_insurer=equity_data
        )

        # Archive report if requested
        archive_path = None
        if archive_report:
            archive_path = self.archiver.save_report(
                html=html,
                category=category,
                report_date=report_date
            )

        return html, archive_path

    def generate_professional_report_from_db(
        self,
        category: str,
        run_id: int,
        db_session: Session,
        use_ai_summary: bool = True,
        archive_report: bool = True,
        equity_data: dict = None
    ) -> Tuple[str, Optional[Path]]:
        """
        Generate professional report for a specific run from database.

        Loads insurers and their news items for the specified run,
        then generates the professional HTML report.

        Args:
            category: Insurer category to filter by
            run_id: Run ID to generate report for
            db_session: Database session
            use_ai_summary: Whether to use AI for executive summary
            archive_report: Whether to save report to archive
            equity_data: Optional dict mapping insurer_id to list of price dicts

        Returns:
            Tuple of (rendered HTML string, archive path or None)

        Raises:
            ValueError: If run not found
        """
        # Verify run exists
        run = db_session.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise ValueError(f"Run {run_id} not found")

        # Load insurers with their news items for this run
        insurers = (
            db_session.query(Insurer)
            .filter(
                Insurer.category == category,
                Insurer.enabled == True
            )
            .join(NewsItem, NewsItem.insurer_id == Insurer.id)
            .filter(NewsItem.run_id == run_id)
            .distinct()
            .all()
        )

        # Load news items for each insurer, then detach from session.
        # Order matters: query BEFORE expunge to avoid lazy load errors
        # when downstream code accesses insurer.news_items on the detached object.
        for insurer in insurers:
            # Query news items while insurer is still bound to session
            run_news_items = (
                db_session.query(NewsItem)
                .filter(
                    NewsItem.insurer_id == insurer.id,
                    NewsItem.run_id == run_id
                )
                .all()
            )
            # Expunge to detach from session, then assign pre-loaded items
            db_session.expunge(insurer)
            insurer.news_items = run_news_items

        return self.generate_professional_report(
            category=category,
            insurers=insurers,
            report_date=run.started_at,
            use_ai_summary=use_ai_summary,
            archive_report=archive_report,
            equity_data=equity_data
        )

    def _get_basic_summary(
        self,
        category: str,
        insurers: list[Insurer],
        status_counts: dict[str, int]
    ) -> str:
        """
        Generate basic template-based summary without AI.

        Args:
            category: Report category
            insurers: List of insurers
            status_counts: Status count dictionary

        Returns:
            Basic Portuguese summary paragraph
        """
        total = len(insurers)
        critical = status_counts.get("Critical", 0)
        watch = status_counts.get("Watch", 0)

        if critical > 0:
            return (
                f"Este relatorio analisa {total} seguradoras na categoria {category}. "
                f"Identificamos {critical} seguradora(s) em situacao critica e {watch} sob monitoramento ativo. "
                f"Recomenda-se atencao prioritaria aos casos criticos destacados neste documento."
            )
        elif watch > 0:
            return (
                f"Este relatorio analisa {total} seguradoras na categoria {category}. "
                f"Identificamos {watch} seguradora(s) sob monitoramento ativo. "
                f"O mercado apresenta estabilidade geral com pontos de atencao especificos."
            )
        else:
            return (
                f"Este relatorio analisa {total} seguradoras na categoria {category}. "
                f"O mercado apresenta estabilidade geral sem alertas criticos no periodo analisado."
            )

    def _generate_market_context(
        self,
        category: str,
        insurers: list[Insurer],
        status_counts: dict[str, int]
    ) -> list[ReportContext]:
        """
        Generate market context items for report.

        Creates 3-4 context items based on category and data.

        Args:
            category: Report category
            insurers: List of insurers
            status_counts: Status count dictionary

        Returns:
            List of ReportContext objects
        """
        total = len(insurers)
        critical = status_counts.get("Critical", 0)
        watch = status_counts.get("Watch", 0)
        stable = status_counts.get("Stable", 0)

        # Category-specific context descriptions
        category_descriptions = {
            "Health": "planos de saude e operadoras medico-hospitalares",
            "Dental": "operadoras odontologicas e planos dentais",
            "Group Life": "seguros de vida em grupo e beneficios corporativos"
        }

        category_desc = category_descriptions.get(category, f"seguradoras de {category}")

        context_items = [
            ReportContext(
                title=f"Categoria {category}",
                description=f"Monitoramento de {total} {category_desc} registradas no banco de dados da Marsh Brasil."
            ),
            ReportContext(
                title="Distribuicao de Status",
                description=f"Distribuicao atual: {critical} critico, {watch} observacao, {status_counts.get('Monitor', 0)} monitorar, {stable} estavel."
            ),
            ReportContext(
                title="Metodologia de Analise",
                description="Classificacao automatica via Azure OpenAI com analise de sentimento e categorizacao de indicadores de mercado."
            )
        ]

        # Add risk context if critical/watch insurers exist
        if critical > 0 or watch > 0:
            context_items.append(ReportContext(
                title="Aviso de Risco",
                description=f"Ha {critical + watch} seguradora(s) requerendo atencao especial. Recomenda-se avaliacao de exposicao de clientes."
            ))

        return context_items

    def _generate_recommendations(
        self,
        insurers_by_status: dict[str, list[Insurer]],
        status_counts: dict[str, int]
    ) -> list[dict]:
        """
        Generate strategic recommendations based on data.

        Creates prioritized recommendations list.

        Args:
            insurers_by_status: Insurers grouped by status
            status_counts: Status count dictionary

        Returns:
            List of recommendation dicts with 'title' and 'description'
        """
        recommendations = []
        rec_number = 1

        critical = status_counts.get("Critical", 0)
        watch = status_counts.get("Watch", 0)
        stable = status_counts.get("Stable", 0)

        # Critical insurer recommendations
        if critical > 0:
            critical_names = [i.name for i in insurers_by_status.get("Critical", [])[:2]]
            recommendations.append({
                "number": rec_number,
                "title": "Monitorar Seguradoras Criticas de Perto",
                "description": f"Ha {critical} seguradora(s) em status critico ({', '.join(critical_names)}). Avalie exposicao de clientes e considere planos de contingencia."
            })
            rec_number += 1

        # Watch insurer recommendations
        if watch > 0:
            watch_names = [i.name for i in insurers_by_status.get("Watch", [])[:2]]
            recommendations.append({
                "number": rec_number,
                "title": "Revisar Seguradoras em Observacao",
                "description": f"{watch} seguradora(s) em observacao ({', '.join(watch_names)}). Comunicar proativamente com clientes e avaliar alternativas."
            })
            rec_number += 1

        # Stable insurer positioning
        if stable > 0:
            recommendations.append({
                "number": rec_number,
                "title": "Posicionar Seguradoras Estaveis para Crescimento",
                "description": f"Com {stable} seguradora(s) em status estavel, considere-as para novas colocacoes de clientes buscando estabilidade."
            })
            rec_number += 1

        # Always recommend continued monitoring
        recommendations.append({
            "number": rec_number,
            "title": "Continuar Monitoramento de Inteligencia",
            "description": "Mantenha monitoramento diario via BrasilIntel para desenvolvimentos que possam impactar seus clientes e operacoes."
        })

        return recommendations

    def preview_professional_template(self) -> Tuple[str, None]:
        """
        Generate a preview of professional report with sample data.

        Creates mock insurers and news items to demonstrate
        the professional template layout and styling.

        Returns:
            Tuple of (rendered HTML, None) - no archival for preview
        """
        # Create mock insurers with news and indicators
        critical_insurer = Insurer(
            id=1,
            ans_code="123456",
            name="Seguradora XYZ",
            cnpj="12.345.678/0001-90",
            category="Health",
            status="Critical"
        )
        critical_insurer.news_items = [
            NewsItem(
                id=1,
                title="Seguradora enfrenta problemas financeiros graves",
                source_name="Valor Economico",
                source_url="https://example.com/news1",
                published_at=datetime(2024, 1, 15),
                status="Critical",
                sentiment="negative",
                summary="Prejuizo de R$ 50 milhoes no ultimo trimestre\nInadimplencia cresceu 15%\nANS abriu processo de fiscalizacao",
                category_indicators="financial_health,regulatory_compliance"
            )
        ]

        watch_insurer = Insurer(
            id=2,
            ans_code="234567",
            name="Plano Saude ABC",
            cnpj="23.456.789/0001-01",
            category="Health",
            status="Watch"
        )
        watch_insurer.news_items = [
            NewsItem(
                id=2,
                title="Reclamacoes aumentam no Reclame Aqui",
                source_name="Portal da Saude",
                source_url="https://example.com/news2",
                published_at=datetime(2024, 1, 14),
                status="Watch",
                sentiment="neutral",
                summary="Aumento de 25% nas reclamacoes\nDemora na autorizacao de procedimentos\nEmpresa divulgou nota oficial",
                category_indicators="customer_satisfaction"
            )
        ]

        stable_insurer = Insurer(
            id=3,
            ans_code="345678",
            name="Saude Vida Seguros",
            cnpj="34.567.890/0001-12",
            category="Health",
            status="Stable"
        )
        stable_insurer.news_items = [
            NewsItem(
                id=3,
                title="Empresa lanca novo produto para PMEs",
                source_name="InfoMoney",
                source_url="https://example.com/news3",
                published_at=datetime(2024, 1, 13),
                status="Stable",
                sentiment="positive",
                summary="Novo plano com cobertura ampliada\nFoco em pequenas e medias empresas\nExpectativa de crescer 10% no segmento",
                category_indicators="product_innovation,market_share_change"
            )
        ]

        mock_insurers = [critical_insurer, watch_insurer, stable_insurer]

        return self.generate_professional_report(
            category="Health",
            insurers=mock_insurers,
            report_date=datetime.now(),
            use_ai_summary=False,  # Use fallback for preview
            archive_report=False   # Don't archive preview
        )
