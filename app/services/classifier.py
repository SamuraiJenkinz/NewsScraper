"""
Azure OpenAI classification service for insurer news analysis.

Uses structured outputs with Pydantic models to ensure consistent
classification responses. All summaries generated in Portuguese.

Supports both standard Azure OpenAI endpoints and corporate proxy endpoints.
"""
import logging
from typing import Any

from openai import AzureOpenAI, OpenAI

from app.config import get_settings
from app.schemas.classification import NewsClassification, InsurerClassification

logger = logging.getLogger(__name__)

# ~50K chars is ~12.5K tokens, leaving ample room for system prompt + title + response
# within GPT-4o-mini's 128K token limit. Articles front-load the most relevant info.
MAX_DESCRIPTION_CHARS = 50_000


# System prompts in Portuguese for better output consistency
SYSTEM_PROMPT_SINGLE = """Você é um analista financeiro especializado em seguradoras brasileiras.
Analise a notícia fornecida e classifique o status da seguradora.

Critérios de classificação:
- CRITICAL: Crise financeira, intervenção da ANS, risco de falência, fraude, acusações criminais
- WATCH: Atividade de M&A, mudanças significativas na liderança, ações regulatórias, perdas significativas
- MONITOR: Mudanças de tarifa, alterações na rede, expansão de mercado, anúncios de parcerias
- STABLE: Sem notícias significativas ou apenas atualizações operacionais rotineiras

Indicadores de categoria (inclua todos que se aplicam):
- financial_crisis: Crise financeira, problemas de solvência, risco de falência
- regulatory_action: Intervenção da ANS, multas, sanções, ações regulatórias
- m_and_a: Fusões, aquisições, vendas de operações
- leadership_change: Mudança de CEO, diretoria, conselho
- fraud_criminal: Fraude, investigações criminais, acusações
- rate_change: Reajustes de preços, mudanças tarifárias
- network_change: Alterações na rede credenciada, hospitais, médicos
- market_expansion: Novos mercados, expansão geográfica, novos produtos
- partnership: Parcerias, acordos comerciais, alianças
- routine_operations: Operações normais, sem eventos significativos

Responda em português brasileiro para todos os campos de texto."""

SYSTEM_PROMPT_AGGREGATE = """Você é um analista financeiro especializado em seguradoras brasileiras.
Analise todas as notícias fornecidas sobre esta seguradora e determine o status geral.

Critérios de classificação:
- CRITICAL: Qualquer indicação de crise financeira, intervenção regulatória, ou risco sistêmico
- WATCH: M&A ativa, mudanças de liderança, ou ações regulatórias em andamento
- MONITOR: Mudanças comerciais normais, expansão, ou parcerias
- STABLE: Operações normais sem eventos significativos

Priorize o status mais grave se houver múltiplas indicações.
Responda em português brasileiro para todos os campos de texto."""


class ClassificationService:
    """
    Service for classifying insurer news using Azure OpenAI.

    Uses structured outputs with Pydantic models to ensure
    consistent and validated JSON responses from the LLM.
    """

    def __init__(self):
        settings = get_settings()

        if not settings.is_azure_openai_configured():
            logger.warning("Azure OpenAI not configured - classification will fail")
            self.client = None
            self.model = None
        else:
            endpoint = settings.azure_openai_endpoint
            api_key = settings.get_azure_openai_key()

            # Detect corporate proxy URL format (contains full path to chat/completions)
            if "/deployments/" in endpoint and "/chat/completions" in endpoint:
                # Extract base URL up to deployment (includes /deployments/{model})
                # Format: .../v1/deployments/{deployment}/chat/completions
                # OpenAI client will append /chat/completions to base_url
                import re
                match = re.search(r"(.+/deployments/[^/]+)/chat/completions", endpoint)
                if match:
                    base_url = match.group(1)
                    # Extract model name for logging
                    model_match = re.search(r"/deployments/([^/]+)", endpoint)
                    self.model = model_match.group(1) if model_match else "unknown"
                    logger.info(f"Using proxy endpoint: {base_url}, model: {self.model}")
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
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=settings.azure_openai_api_version,
                )
                self.model = settings.azure_openai_deployment

        self.use_llm = settings.use_llm_summary

    def classify_single_news(
        self,
        insurer_name: str,
        news_title: str,
        news_description: str | None = None,
    ) -> NewsClassification | None:
        """
        Classify a single news item for an insurer.

        Args:
            insurer_name: Name of the insurer
            news_title: News headline
            news_description: Optional news description/snippet

        Returns:
            NewsClassification object or None if classification fails
        """
        if not self.client or not self.use_llm:
            logger.info("LLM classification disabled or not configured")
            return self._fallback_classification()

        if news_description and len(news_description) > MAX_DESCRIPTION_CHARS:
            original_len = len(news_description)
            news_description = news_description[:MAX_DESCRIPTION_CHARS]
            logger.warning(
                f"Truncated description for '{news_title[:80]}' "
                f"from {original_len} to {MAX_DESCRIPTION_CHARS} chars"
            )

        content = f"Título: {news_title}"
        if news_description:
            content += f"\n\nDescrição: {news_description}"

        user_prompt = f"""Analise esta notícia sobre {insurer_name}:

{content}

Forneça a classificação com resumo em bullet points."""

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_SINGLE},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=NewsClassification,
                temperature=0,  # Deterministic outputs
            )

            return completion.choices[0].message.parsed

        except Exception as e:
            logger.error(f"Classification failed for {insurer_name}: {e}")
            return self._fallback_classification()

    def classify_insurer_news(
        self,
        insurer_name: str,
        news_items: list[dict[str, Any]],
    ) -> InsurerClassification | None:
        """
        Classify an insurer based on multiple news items.

        Aggregates all news to determine overall status and key findings.

        Args:
            insurer_name: Name of the insurer
            news_items: List of news items with title and description keys

        Returns:
            InsurerClassification object or None if classification fails
        """
        if not self.client or not self.use_llm:
            logger.info("LLM classification disabled or not configured")
            return self._fallback_insurer_classification()

        if not news_items:
            return self._fallback_insurer_classification()

        # Format news for prompt
        news_text = "\n\n".join([
            f"- {item.get('title', 'Sem título')}: {item.get('description', '')}"
            for item in news_items[:10]  # Limit to 10 items to avoid token limits
        ])

        user_prompt = f"""Analise estas {len(news_items)} notícias sobre {insurer_name}:

{news_text}

Determine o status geral da seguradora e forneça os principais achados."""

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_AGGREGATE},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=InsurerClassification,
                temperature=0,
            )

            return completion.choices[0].message.parsed

        except Exception as e:
            logger.error(f"Aggregate classification failed for {insurer_name}: {e}")
            return self._fallback_insurer_classification()

    def _fallback_classification(self) -> NewsClassification:
        """Return fallback classification when LLM is unavailable."""
        return NewsClassification(
            status="Monitor",
            summary_bullets=["Classificação automática indisponível"],
            sentiment="neutral",
            reasoning="Classificação de fallback - LLM não configurado ou desabilitado",
            category_indicators=["routine_operations"],
        )

    def _fallback_insurer_classification(self) -> InsurerClassification:
        """Return fallback insurer classification when LLM is unavailable."""
        return InsurerClassification(
            overall_status="Monitor",
            key_findings=["Classificação automática indisponível"],
            risk_factors=[],
            sentiment_breakdown={"positive": 0, "negative": 0, "neutral": 0},
            reasoning="Classificação de fallback - LLM não configurado ou desabilitado",
        )

    def health_check(self) -> dict[str, Any]:
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
