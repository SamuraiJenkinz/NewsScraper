"""
PDF generation service using WeasyPrint.

Converts HTML reports to PDF format for email attachments.
Uses asyncio.to_thread() to avoid blocking the event loop.
"""
import asyncio
from pathlib import Path
from typing import Optional, Tuple

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import structlog

logger = structlog.get_logger()


class PDFGeneratorService:
    """
    Service for generating PDFs from HTML reports.

    Uses WeasyPrint for static HTML rendering with CSS print
    media support. All PDF generation runs in a thread pool
    to avoid blocking the async event loop.
    """

    # Maximum PDF size for email attachment (3MB - base64 inflates by ~33%)
    MAX_PDF_SIZE = 3 * 1024 * 1024

    def __init__(self):
        """Initialize with font configuration and print CSS."""
        self.font_config = FontConfiguration()

        # Print-optimized CSS
        self.print_css = CSS(string='''
            @page {
                size: A4;
                margin: 1.5cm;
            }
            @media print {
                .no-print { display: none; }
                a { color: #0066cc; text-decoration: underline; }
                body { font-size: 10pt; }
                h1 { page-break-after: avoid; }
                h2, h3 { page-break-after: avoid; }
                table { page-break-inside: avoid; }
                .insurer-card { page-break-inside: avoid; }
            }
        ''', font_config=self.font_config)

    async def generate_pdf(
        self,
        html_content: str,
        output_path: Optional[Path] = None
    ) -> Tuple[bytes, int]:
        """
        Generate PDF from HTML content asynchronously.

        Runs the CPU-intensive PDF generation in a thread pool
        to avoid blocking the event loop.

        Args:
            html_content: HTML string to convert
            output_path: Optional path to save PDF file

        Returns:
            Tuple of (pdf_bytes, file_size_bytes)

        Raises:
            ValueError: If PDF exceeds size limit or generation fails
        """
        logger.info("pdf_generation_started", html_size=len(html_content))

        try:
            # Run CPU-intensive operation in thread pool
            pdf_bytes = await asyncio.to_thread(
                self._generate_pdf_sync,
                html_content
            )

            file_size = len(pdf_bytes)

            # Check size limit for email attachment
            if file_size > self.MAX_PDF_SIZE:
                raise ValueError(
                    f"PDF size {file_size:,} bytes exceeds "
                    f"{self.MAX_PDF_SIZE:,} byte limit for email attachment"
                )

            # Optionally save to file
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(output_path.write_bytes, pdf_bytes)
                logger.info("pdf_saved", path=str(output_path), size_kb=file_size // 1024)

            logger.info("pdf_generation_complete", size_kb=file_size // 1024)
            return pdf_bytes, file_size

        except Exception as e:
            logger.error("pdf_generation_failed", error=str(e))
            raise

    def _generate_pdf_sync(self, html_content: str) -> bytes:
        """
        Synchronous PDF generation (runs in thread pool).

        Args:
            html_content: HTML string to convert

        Returns:
            PDF bytes
        """
        return HTML(string=html_content).write_pdf(
            stylesheets=[self.print_css],
            font_config=self.font_config
        )

    async def generate_pdf_from_file(
        self,
        html_path: Path,
        output_path: Optional[Path] = None
    ) -> Tuple[bytes, int]:
        """
        Generate PDF from HTML file.

        Args:
            html_path: Path to HTML file
            output_path: Optional path to save PDF file

        Returns:
            Tuple of (pdf_bytes, file_size_bytes)
        """
        html_content = await asyncio.to_thread(
            html_path.read_text,
            encoding='utf-8'
        )
        return await self.generate_pdf(html_content, output_path)
