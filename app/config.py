"""
Application configuration loaded from environment variables.

Uses pydantic-settings for validation and .env file loading.
All external service credentials centralized here.
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas.delivery import EmailRecipients


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
    report_recipients_health: str = ""  # Comma-separated emails (TO)
    report_recipients_health_cc: str = ""  # CC recipients
    report_recipients_health_bcc: str = ""  # BCC recipients
    report_recipients_dental: str = ""
    report_recipients_dental_cc: str = ""
    report_recipients_dental_bcc: str = ""
    report_recipients_group_life: str = ""
    report_recipients_group_life_cc: str = ""
    report_recipients_group_life_bcc: str = ""

    # Batch processing settings (NEWS-07)
    batch_size: int = 30  # Insurers per batch (30-50 recommended)
    batch_delay_seconds: float = 2.0  # Delay between batches
    max_concurrent_sources: int = 3  # Max sources to query in parallel
    scrape_timeout_seconds: int = 60  # Default per-source timeout
    scrape_max_results: int = 10  # Max results per insurer per source

    # Source-specific timeouts (website crawlers need longer)
    source_timeout_valor: int = 120  # Valor Economico
    source_timeout_cqcs: int = 120  # CQCS

    # Relevance scoring settings (NEWS-10)
    use_ai_relevance_scoring: bool = True  # Enable AI relevance pre-filter
    relevance_keyword_threshold: int = 20  # Items below this skip AI scoring
    relevance_ai_batch_size: int = 10  # Items per AI scoring request

    # Admin interface settings (Phase 8)
    admin_username: str = "admin"
    admin_password: str = ""  # Must be set via env var for security

    # Scheduler settings (Phase 7)
    scheduler_enabled: bool = True
    schedule_health_cron: str = "0 6 * * *"  # 6:00 AM Sao Paulo
    schedule_dental_cron: str = "0 7 * * *"  # 7:00 AM Sao Paulo
    schedule_group_life_cron: str = "0 8 * * *"  # 8:00 AM Sao Paulo
    schedule_health_enabled: bool = True
    schedule_dental_enabled: bool = True
    schedule_group_life_enabled: bool = True
    scheduler_misfire_grace_time: int = 3600  # 1 hour grace
    scheduler_coalesce: bool = True  # Combine missed runs
    scheduler_max_instances: int = 1  # Prevent overlap

    def _parse_recipient_list(self, recipients_str: str) -> list[str]:
        """Parse comma-separated email list, stripping whitespace."""
        if not recipients_str:
            return []
        return [r.strip() for r in recipients_str.split(",") if r.strip()]

    def get_report_recipients(self, category: str) -> list[str]:
        """Get list of TO recipients for a category (backward compatibility)."""
        recipients_map = {
            "Health": self.report_recipients_health,
            "Dental": self.report_recipients_dental,
            "Group Life": self.report_recipients_group_life,
        }
        recipients_str = recipients_map.get(category, "")
        return self._parse_recipient_list(recipients_str)

    def get_email_recipients(self, category: str) -> EmailRecipients:
        """
        Get structured TO/CC/BCC recipients for category.

        Args:
            category: One of "Health", "Dental", or "Group Life"

        Returns:
            EmailRecipients with to, cc, and bcc lists populated
        """
        # Map category to field prefixes
        field_map = {
            "Health": ("report_recipients_health", "report_recipients_health_cc", "report_recipients_health_bcc"),
            "Dental": ("report_recipients_dental", "report_recipients_dental_cc", "report_recipients_dental_bcc"),
            "Group Life": ("report_recipients_group_life", "report_recipients_group_life_cc", "report_recipients_group_life_bcc"),
        }

        fields = field_map.get(category)
        if not fields:
            return EmailRecipients(to=[], cc=[], bcc=[])

        to_field, cc_field, bcc_field = fields
        return EmailRecipients(
            to=self._parse_recipient_list(getattr(self, to_field, "")),
            cc=self._parse_recipient_list(getattr(self, cc_field, "")),
            bcc=self._parse_recipient_list(getattr(self, bcc_field, "")),
        )

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

    def get_schedule_config(self, category: str) -> dict:
        """
        Get schedule configuration for a category.

        Args:
            category: One of "Health", "Dental", or "Group Life"

        Returns:
            Dictionary with cron expression and enabled flag
        """
        config_map = {
            "Health": {
                "cron": self.schedule_health_cron,
                "enabled": self.schedule_health_enabled,
            },
            "Dental": {
                "cron": self.schedule_dental_cron,
                "enabled": self.schedule_dental_enabled,
            },
            "Group Life": {
                "cron": self.schedule_group_life_cron,
                "enabled": self.schedule_group_life_enabled,
            },
        }
        return config_map.get(category, {"cron": "0 6 * * *", "enabled": False})


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure only one Settings object is created.
    """
    return Settings()
