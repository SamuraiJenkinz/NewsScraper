"""
AI-powered executive summary generation using Azure OpenAI.

Generates concise Portuguese executive summaries for insurance intelligence reports
using structured outputs with Pydantic schemas.

Supports both standard Azure OpenAI endpoints and corporate proxy endpoints.
"""
import re
import time
from typing import Optional
import logging

from openai import AzureOpenAI, OpenAI

from app.config import get_settings
from app.models.insurer import Insurer
from app.schemas.report import ExecutiveSummary, KeyFinding

logger = logging.getLogger(__name__)


class ExecutiveSummarizer:
    """
    Service for generating AI-powered executive summaries.

    Uses Azure OpenAI gpt-4o with structured outputs to generate
    consistent, schema-conformant summaries in Portuguese.
    """

    def __init__(self):
        """Initialize Azure OpenAI client with settings."""
        self.settings = get_settings()

        if not self.settings.is_azure_openai_configured():
            logger.warning("Azure OpenAI not configured - summaries will use fallback")
            self.client = None
            self.model = None
        else:
            endpoint = self.settings.azure_openai_endpoint
            api_key = self.settings.get_azure_openai_key()

            # Detect corporate proxy URL format (contains full path to chat/completions)
            if "/deployments/" in endpoint and "/chat/completions" in endpoint:
                # Extract base URL up to deployment (includes /deployments/{model})
                # Format: .../v1/deployments/{deployment}/chat/completions
                # OpenAI client will append /chat/completions to base_url
                match = re.search(r"(.+/deployments/[^/]+)/chat/completions", endpoint)
                if match:
                    base_url = match.group(1)
                    # Extract model name for logging
                    model_match = re.search(r"/deployments/([^/]+)", endpoint)
                    self.model = model_match.group(1) if model_match else "unknown"
                    logger.info(f"ExecutiveSummarizer using proxy: {base_url}, model: {self.model}")
                    self.client = OpenAI(
                        base_url=base_url,
                        api_key=api_key,
                    )
                else:
                    logger.error(f"Could not parse proxy endpoint: {endpoint}")
                    self.client = None
                    self.model = None
            else:
                # Standard Azure OpenAI endpoint
                self.client = AzureOpenAI(
                    api_key=api_key,
                    api_version=self.settings.azure_openai_api_version,
                    azure_endpoint=endpoint
                )
                self.model = self.settings.azure_openai_deployment

        self.use_llm = self.settings.use_llm_summary

    def generate_executive_summary(
        self,
        category: str,
        insurers: list[Insurer],
        max_retries: int = 3
    ) -> str:
        """
        Generate executive summary paragraph for report.

        Args:
            category: Report category (Health, Dental, Group Life)
            insurers: List of insurers with loaded news_items
            max_retries: Maximum retry attempts on failure

        Returns:
            Portuguese executive summary paragraph (2-3 sentences)
        """
        if not self.client or not self.use_llm:
            logger.info("LLM summary disabled or not configured, using fallback")
            return self._generate_fallback_summary(category, insurers)

        # Prepare context from insurers
        context_text = self._prepare_context(category, insurers)

        # System prompt in Portuguese for Brazilian executives
        system_prompt = """Voce e um analista senior da Marsh Brasil especializado em inteligencia de mercado de seguros.

Gere um paragrafo executivo conciso (2-3 frases) em portugues que resuma os principais desenvolvimentos afetando as seguradoras listadas.

Foco em:
- Tendencias criticas do mercado
- Mudancas regulatorias importantes
- Riscos financeiros ou operacionais
- Oportunidades estrategicas

Escreva em portugues profissional para executivos. Seja direto e objetivo."""

        retry_count = 0
        while retry_count < max_retries:
            try:
                response = self.client.beta.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": context_text}
                    ],
                    response_format=ExecutiveSummary,
                    temperature=0.3,  # Lower for consistency
                    max_tokens=500,
                    timeout=30.0
                )

                summary = response.choices[0].message.parsed

                logger.info(
                    "Executive summary generated",
                    extra={
                        "category": category,
                        "critical_count": summary.critical_count,
                        "watch_count": summary.watch_count,
                        "theme": summary.key_theme
                    }
                )

                return summary.paragraph

            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Executive summary retry {retry_count}: {e}",
                    extra={"category": category, "attempt": retry_count}
                )

                if retry_count >= max_retries:
                    logger.error(
                        f"Executive summary failed after {max_retries} retries: {e}",
                        extra={"category": category}
                    )
                    return self._generate_fallback_summary(category, insurers)

                # Exponential backoff
                time.sleep(2 ** retry_count)

        return self._generate_fallback_summary(category, insurers)

    def generate_key_findings(
        self,
        insurers_by_status: dict[str, list[Insurer]]
    ) -> list[KeyFinding]:
        """
        Generate key findings cards from insurer data.

        Creates 3-4 findings based on critical/watch insurers and their news.
        Does not use LLM - derives from data directly.

        Args:
            insurers_by_status: Insurers grouped by status

        Returns:
            List of KeyFinding objects for template rendering
        """
        findings = []

        # Critical findings
        critical_insurers = insurers_by_status.get("Critical", [])
        if critical_insurers:
            # Get most severe critical news
            critical_names = [i.name for i in critical_insurers[:2]]
            findings.append(KeyFinding(
                severity="critical",
                title=f"Alerta Critico - {len(critical_insurers)} Seguradora(s)",
                description=f"Seguradoras em situacao critica: {', '.join(critical_names)}. Requer atencao imediata."
            ))

        # Watch findings
        watch_insurers = insurers_by_status.get("Watch", [])
        if watch_insurers:
            watch_names = [i.name for i in watch_insurers[:2]]
            findings.append(KeyFinding(
                severity="warning",
                title=f"Monitoramento Ativo - {len(watch_insurers)} Seguradora(s)",
                description=f"Seguradoras sob observacao: {', '.join(watch_names)}. Acompanhar desenvolvimentos."
            ))

        # Positive findings (from stable with good news)
        stable_insurers = insurers_by_status.get("Stable", [])
        if stable_insurers:
            # Find insurers with positive sentiment news
            positive_insurers = []
            for insurer in stable_insurers:
                if any(n.sentiment == "positive" for n in insurer.news_items if n.sentiment):
                    positive_insurers.append(insurer)

            if positive_insurers:
                positive_names = [i.name for i in positive_insurers[:2]]
                findings.append(KeyFinding(
                    severity="positive",
                    title="Desenvolvimentos Positivos",
                    description=f"Noticias favoraveis para: {', '.join(positive_names)}."
                ))

        # Monitor summary
        monitor_insurers = insurers_by_status.get("Monitor", [])
        if monitor_insurers and len(findings) < 4:
            findings.append(KeyFinding(
                severity="warning",
                title=f"Em Acompanhamento - {len(monitor_insurers)} Seguradora(s)",
                description=f"{len(monitor_insurers)} seguradoras requerem monitoramento continuo."
            ))

        return findings

    def _prepare_context(self, category: str, insurers: list[Insurer]) -> str:
        """
        Prepare concise context for LLM from insurers.

        Limits token usage by including only key information:
        - Insurer name and status
        - Top 2 critical/watch news items per insurer

        Args:
            category: Report category
            insurers: List of insurers

        Returns:
            Formatted context string
        """
        status_priority = ["Critical", "Watch", "Monitor", "Stable"]

        lines = [f"Categoria: {category}\nSeguradoras analisadas:\n"]

        for insurer in insurers:
            # Determine status from news items
            statuses = [n.status for n in insurer.news_items if n.status]
            if not statuses:
                continue

            # Use most severe status
            status = "Stable"
            for s in status_priority:
                if s in statuses:
                    status = s
                    break

            lines.append(f"\n{insurer.name} (ANS {insurer.ans_code}): {status}")

            # Include top 2 critical/watch news items for context
            important_news = [
                n for n in insurer.news_items
                if n.status in ["Critical", "Watch"]
            ][:2]

            for news in important_news:
                lines.append(f"  - {news.title}")
                if news.category_indicators:
                    indicators = news.category_indicators.split(",") if isinstance(news.category_indicators, str) else news.category_indicators
                    lines.append(f"    Indicadores: {', '.join(indicators[:3])}")

        return "\n".join(lines)

    def _generate_fallback_summary(
        self,
        category: str,
        insurers: list[Insurer]
    ) -> str:
        """
        Generate template-based fallback summary when LLM unavailable.

        Args:
            category: Report category
            insurers: List of insurers

        Returns:
            Basic Portuguese summary paragraph
        """
        # Count statuses
        status_counts = {"Critical": 0, "Watch": 0, "Monitor": 0, "Stable": 0}
        for insurer in insurers:
            statuses = [n.status for n in insurer.news_items if n.status]
            if "Critical" in statuses:
                status_counts["Critical"] += 1
            elif "Watch" in statuses:
                status_counts["Watch"] += 1
            elif "Monitor" in statuses:
                status_counts["Monitor"] += 1
            else:
                status_counts["Stable"] += 1

        total = len(insurers)
        critical = status_counts["Critical"]
        watch = status_counts["Watch"]

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

    def health_check(self) -> dict:
        """
        Check Azure OpenAI service connectivity.

        Returns dict with status and any error message.
        """
        if not self.client:
            return {"status": "error", "message": "Azure OpenAI not configured"}

        if not self.use_llm:
            return {"status": "disabled", "message": "LLM summarization disabled"}

        try:
            # Simple test completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return {
                "status": "ok",
                "model": self.model,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
