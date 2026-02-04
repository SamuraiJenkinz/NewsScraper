"""Tests for batch processor service."""
import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.batch_processor import BatchProcessor, BatchProgress, InsurerResult


class TestBatchProgress:
    """Tests for BatchProgress dataclass."""

    def test_percent_complete_zero_insurers(self):
        """Percent complete should be 0 when no insurers."""
        progress = BatchProgress(total_insurers=0)
        assert progress.percent_complete == 0.0

    def test_percent_complete_partial(self):
        """Percent complete should calculate correctly."""
        progress = BatchProgress(total_insurers=100, processed_insurers=25)
        assert progress.percent_complete == 25.0

    def test_percent_complete_full(self):
        """Percent complete should be 100 when all processed."""
        progress = BatchProgress(total_insurers=50, processed_insurers=50)
        assert progress.percent_complete == 100.0

    def test_percent_complete_with_items(self):
        """Progress should track total items found."""
        progress = BatchProgress(
            total_insurers=100,
            processed_insurers=75,
            total_items_found=500
        )
        assert progress.percent_complete == 75.0
        assert progress.total_items_found == 500

    def test_elapsed_seconds(self):
        """Elapsed seconds should increase over time."""
        progress = BatchProgress()
        time.sleep(0.1)
        assert progress.elapsed_seconds >= 0.1

    def test_errors_list(self):
        """Errors should be trackable."""
        progress = BatchProgress()
        progress.errors.append("Error 1")
        progress.errors.append("Error 2")
        assert len(progress.errors) == 2
        assert "Error 1" in progress.errors


class TestInsurerResult:
    """Tests for InsurerResult dataclass."""

    def test_success_with_items(self):
        """Success should be True when no error."""
        result = InsurerResult(insurer_id=1, insurer_name="Test")
        assert result.success is True

    def test_success_with_error(self):
        """Success should be False when error present."""
        result = InsurerResult(insurer_id=1, insurer_name="Test", error="Failed")
        assert result.success is False

    def test_items_default_empty(self):
        """Items should default to empty list."""
        result = InsurerResult(insurer_id=1, insurer_name="Test")
        assert result.items == []


class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_init_defaults(self):
        """Should initialize with default settings."""
        with patch('app.services.batch_processor.SourceRegistry') as mock_registry:
            mock_registry.get_all.return_value = []
            bp = BatchProcessor(sources=[])
            assert bp.batch_size == 30
            assert bp.max_concurrent == 3
            assert bp.delay_seconds == 2.0

    def test_init_custom_values(self):
        """Should accept custom configuration."""
        bp = BatchProcessor(
            batch_size=50,
            max_concurrent=5,
            delay_seconds=1.0,
            sources=[],
        )
        assert bp.batch_size == 50
        assert bp.max_concurrent == 5
        assert bp.delay_seconds == 1.0

    @pytest.mark.asyncio
    async def test_process_empty_list(self):
        """Should handle empty insurer list gracefully."""
        bp = BatchProcessor(sources=[])
        progress = await bp.process_insurers([])
        assert progress.total_insurers == 0
        assert progress.processed_insurers == 0

    @pytest.mark.asyncio
    async def test_process_no_sources(self):
        """Should report error when no sources configured."""
        bp = BatchProcessor(sources=[])

        mock_insurer = Mock()
        mock_insurer.id = 1
        mock_insurer.name = "Test Insurer"
        mock_insurer.ans_code = "123456"
        mock_insurer.search_terms = None

        progress = await bp.process_insurers([mock_insurer])
        assert len(progress.errors) > 0
        assert "No news sources" in progress.errors[0]

    @pytest.mark.asyncio
    async def test_process_single_insurer(self):
        """Should process a single insurer successfully."""
        # Create mock source
        mock_source = Mock()
        mock_source.SOURCE_NAME = "test_source"
        mock_source.search = AsyncMock(return_value=[])

        bp = BatchProcessor(sources=[mock_source])

        mock_insurer = Mock()
        mock_insurer.id = 1
        mock_insurer.name = "Test Insurer"
        mock_insurer.ans_code = "123456"
        mock_insurer.search_terms = None

        progress = await bp.process_insurers([mock_insurer])
        assert progress.total_insurers == 1
        assert progress.processed_insurers == 1
        assert len(progress.errors) == 0

    @pytest.mark.asyncio
    async def test_process_uses_custom_search_terms(self):
        """Should use custom search terms when available."""
        mock_source = Mock()
        mock_source.SOURCE_NAME = "test_source"
        mock_source.search = AsyncMock(return_value=[])

        bp = BatchProcessor(sources=[mock_source])

        mock_insurer = Mock()
        mock_insurer.id = 1
        mock_insurer.name = "Test Insurer"
        mock_insurer.ans_code = "123456"
        mock_insurer.search_terms = "custom search query"

        await bp.process_insurers([mock_insurer])

        # Verify custom search terms were used
        mock_source.search.assert_called_once()
        call_args = mock_source.search.call_args
        assert call_args.kwargs.get('query') == "custom search query" or call_args[1].get('query') == "custom search query"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
