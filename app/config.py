"""
Application configuration loaded from environment variables.

Uses pydantic-settings for validation and .env file loading.
All external service credentials centralized here.
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Allow extra env vars without error
    )

    # Database
    database_url: str = "sqlite:///./data/brasilintel.db"
    data_dir: str = "./data"

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-08-01-preview"
    use_llm_summary: bool = True

    # Microsoft Graph (for email)
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    sender_email: str = ""

    # Apify (for web scraping)
    apify_token: str = ""

    # Application
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Report settings
    company_name: str = "Marsh Brasil"
    report_recipients_health: str = ""  # Comma-separated emails
    report_recipients_dental: str = ""
    report_recipients_group_life: str = ""

    # Batch processing settings (NEWS-07)
    batch_size: int = 30  # Insurers per batch (30-50 recommended)
    batch_delay_seconds: float = 2.0  # Delay between batches
    max_concurrent_sources: int = 3  # Max sources to query in parallel
    scrape_timeout_seconds: int = 60  # Default per-source timeout
    scrape_max_results: int = 10  # Max results per insurer per source

    # Source-specific timeouts (website crawlers need longer)
    source_timeout_valor: int = 120  # Valor Economico
    source_timeout_cqcs: int = 120  # CQCS

    def get_report_recipients(self, category: str) -> list[str]:
        """Get list of recipients for a category."""
        recipients_map = {
            "Health": self.report_recipients_health,
            "Dental": self.report_recipients_dental,
            "Group Life": self.report_recipients_group_life,
        }
        recipients_str = recipients_map.get(category, "")
        if not recipients_str:
            return []
        return [r.strip() for r in recipients_str.split(",") if r.strip()]

    def is_azure_openai_configured(self) -> bool:
        """Check if Azure OpenAI is fully configured."""
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_deployment
        )

    def is_graph_configured(self) -> bool:
        """Check if Microsoft Graph email is fully configured."""
        return bool(
            self.azure_tenant_id
            and self.azure_client_id
            and self.azure_client_secret
            and self.sender_email
        )

    def is_apify_configured(self) -> bool:
        """Check if Apify is configured."""
        return bool(self.apify_token)

    def get_source_timeout(self, source_name: str) -> int:
        """
        Get timeout for a specific source.

        Args:
            source_name: Name of the source (e.g., "valor", "cqcs")

        Returns:
            Timeout in seconds, falling back to default if not configured
        """
        timeout_map = {
            "valor": self.source_timeout_valor,
            "cqcs": self.source_timeout_cqcs,
        }
        return timeout_map.get(source_name, self.scrape_timeout_seconds)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure only one Settings object is created.
    """
    return Settings()
