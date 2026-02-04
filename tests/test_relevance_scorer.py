"""
Tests for the relevance scorer service.

Tests focus on keyword filtering (free pass) and configuration behavior.
AI filtering is mocked as it requires Azure OpenAI credentials.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.relevance_scorer import RelevanceScorer
from app.services.sources import ScrapedNewsItem


@pytest.fixture
def sample_items() -> list[ScrapedNewsItem]:
    """Create sample news items for testing."""
    return [
        ScrapedNewsItem(
            title="Amil anuncia novo plano de saude",
            description="A Amil lanca produto inovador para PMEs",
            url="https://example.com/1",
            source="google_news",
            published_at=datetime.now(),
        ),
        ScrapedNewsItem(
            title="Unimed expande rede de atendimento",
            description="Nova clinica em Sao Paulo",
            url="https://example.com/2",
            source="google_news",
            published_at=datetime.now(),
        ),
        ScrapedNewsItem(
            title="Setor de seguros cresce em 2024",
            description="Mercado brasileiro mostra resiliencia",
            url="https://example.com/3",
            source="google_news",
            published_at=datetime.now(),
        ),
        ScrapedNewsItem(
            title="AMIL e investigada pela ANS",
            description="Regulador abre processo administrativo",
            url="https://example.com/4",
            source="google_news",
            published_at=datetime.now(),
        ),
    ]


@pytest.fixture
def scorer() -> RelevanceScorer:
    """Create RelevanceScorer with mocked settings."""
    with patch("app.services.relevance_scorer.get_settings") as mock_settings:
        settings = MagicMock()
        settings.is_azure_openai_configured.return_value = False
        settings.use_ai_relevance_scoring = False  # Disable AI for unit tests
        settings.relevance_keyword_threshold = 20
        settings.relevance_ai_batch_size = 10
        mock_settings.return_value = settings

        return RelevanceScorer()


class TestKeywordFilter:
    """Test keyword-based filtering."""

    def test_filters_by_name_parts(
        self, scorer: RelevanceScorer, sample_items: list[ScrapedNewsItem]
    ):
        """Keyword filter should match items containing name parts."""
        results = scorer._keyword_filter(sample_items, "Amil Saude")

        # Should match items 0 and 3 (both mention Amil)
        assert len(results) == 2
        assert "Amil" in results[0].title
        assert "AMIL" in results[1].title

    def test_case_insensitive_matching(
        self, scorer: RelevanceScorer, sample_items: list[ScrapedNewsItem]
    ):
        """Keyword filter should be case insensitive."""
        results = scorer._keyword_filter(sample_items, "amil")

        # Should match both uppercase and lowercase mentions
        assert len(results) == 2

    def test_matches_in_description(self, scorer: RelevanceScorer):
        """Keyword filter should also search descriptions."""
        items = [
            ScrapedNewsItem(
                title="Noticias do setor",
                description="Porto Seguro reporta lucro recorde",
                url="https://example.com/1",
                source="test",
            ),
            ScrapedNewsItem(
                title="Outra noticia",
                description="Sem mencao relevante",
                url="https://example.com/2",
                source="test",
            ),
        ]

        results = scorer._keyword_filter(items, "Porto Seguro")
        assert len(results) == 1
        assert results[0].description == "Porto Seguro reporta lucro recorde"

    def test_skips_short_name_parts(self, scorer: RelevanceScorer):
        """Keyword filter should skip short words like 'de', 'da'."""
        items = [
            ScrapedNewsItem(
                title="Amil de Saude apresenta resultados",
                description=None,
                url="https://example.com/1",
                source="test",
            ),
            ScrapedNewsItem(
                title="Noticia de interesse geral",
                description=None,
                url="https://example.com/2",
                source="test",
            ),
        ]

        # "de" should be skipped, only "Amil" and "Saude" should match
        results = scorer._keyword_filter(items, "Amil de Saude")
        assert len(results) == 1
        assert "Amil" in results[0].title

    def test_empty_list_returns_empty(self, scorer: RelevanceScorer):
        """Empty input should return empty output."""
        results = scorer._keyword_filter([], "Test Insurer")
        assert results == []

    def test_no_matches_returns_empty(self, scorer: RelevanceScorer, sample_items):
        """No matches should return empty list."""
        results = scorer._keyword_filter(sample_items, "NonexistentInsurer")
        assert len(results) == 0


class TestScoreBatch:
    """Test main score_batch method."""

    def test_empty_list_handling(self, scorer: RelevanceScorer):
        """Empty list should return empty result."""
        results = scorer.score_batch([], "Amil")
        assert results == []

    def test_max_results_limiting(
        self, scorer: RelevanceScorer, sample_items: list[ScrapedNewsItem]
    ):
        """Should respect max_results limit."""
        # All items match when insurer name is generic
        items = [
            ScrapedNewsItem(
                title=f"Test insurer noticia {i}",
                description=None,
                url=f"https://example.com/{i}",
                source="test",
            )
            for i in range(10)
        ]

        results = scorer.score_batch(items, "Test insurer", max_results=3)
        assert len(results) == 3

    def test_ai_skipped_below_threshold(
        self, scorer: RelevanceScorer, sample_items: list[ScrapedNewsItem]
    ):
        """AI scoring should be skipped when below threshold."""
        # Create items that match keyword filter
        items = [
            ScrapedNewsItem(
                title=f"Amil noticia {i}",
                description=None,
                url=f"https://example.com/{i}",
                source="test",
            )
            for i in range(5)  # Below default threshold of 20
        ]

        # Even with AI enabled, should not call AI (below threshold)
        scorer.use_ai = True
        scorer.keyword_threshold = 20

        results = scorer.score_batch(items, "Amil")
        assert len(results) == 5  # All items kept (keyword match, no AI filtering)


class TestParseRelevanceResponse:
    """Test parsing of AI response format."""

    def test_parses_standard_format(self, scorer: RelevanceScorer):
        """Should parse standard numbered response."""
        response = """1: relevant
2: not_relevant
3: relevant"""

        results = scorer._parse_relevance_response(response, 3)
        assert results == [True, False, True]

    def test_handles_extra_text(self, scorer: RelevanceScorer):
        """Should handle responses with extra formatting."""
        response = """Avaliacao:
1: relevant (menciona diretamente)
2: not_relevant (mencao generica)
3: relevant"""

        results = scorer._parse_relevance_response(response, 3)
        assert results == [True, False, True]

    def test_defaults_to_relevant_on_parse_error(self, scorer: RelevanceScorer):
        """Should default to relevant (fail-open) on parse error."""
        response = "Invalid response format"

        results = scorer._parse_relevance_response(response, 3)
        # All should default to True (fail-open)
        assert results == [True, True, True]

    def test_handles_partial_response(self, scorer: RelevanceScorer):
        """Should handle responses with missing items."""
        response = """1: relevant
3: not_relevant"""

        results = scorer._parse_relevance_response(response, 3)
        # Item 2 should default to True (fail-open)
        assert results == [True, True, False]


class TestHealthCheck:
    """Test health check functionality."""

    def test_health_check_no_client(self, scorer: RelevanceScorer):
        """Health check should report degraded when no client."""
        result = scorer.health_check()

        assert result["status"] == "degraded"
        assert result["ai_enabled"] is False
        assert "keyword filtering only" in result["message"]

    def test_health_check_ai_disabled(self):
        """Health check should report OK when AI disabled by config."""
        with patch("app.services.relevance_scorer.get_settings") as mock_settings:
            settings = MagicMock()
            settings.is_azure_openai_configured.return_value = True
            settings.azure_openai_endpoint = "https://test.openai.azure.com"
            settings.azure_openai_api_key = "test-key"
            settings.azure_openai_api_version = "2024-08-01-preview"
            settings.azure_openai_deployment = "gpt-4o"
            settings.use_ai_relevance_scoring = False
            settings.relevance_keyword_threshold = 20
            settings.relevance_ai_batch_size = 10
            mock_settings.return_value = settings

            scorer = RelevanceScorer()
            result = scorer.health_check()

            assert result["status"] == "ok"
            assert result["ai_enabled"] is False
