"""Application settings loaded from environment variables (INFRA-06, INFRA-07)."""

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    database_url: str = Field(repr=False)
    admin_email: str
    admin_password: SecretStr
    cookie_secure: bool = True

    maritalk_api_key: SecretStr | None = None
    maritalk_api_base: str | None = None
    maritalk_model: str | None = None
    maritalk_fallback_model: str = "sabia-4-br-sp"

    storage_dir: str = "/app/storage"
    worker_enabled: bool = True
    max_upload_mb: int = 20
    max_request_mb: int = 120
    max_pages: int = 100
    max_megapixels: int = 100
    max_documents_per_process: int = 200
    max_uploads_per_minute: int = 60
    ai_timeout_seconds: int = 60
    ai_max_tokens: int = 8000

    @property
    def effective_maritalk_model(self) -> str:
        """The configured model, or the fallback when the variable is empty (EXT-02)."""
        return (self.maritalk_model or "").strip() or self.maritalk_fallback_model


def load_settings() -> Settings:
    """Load settings or exit naming the invalid variables, never their values."""
    try:
        return Settings()
    except ValidationError as exc:
        names = sorted({str(err["loc"][0]).upper() for err in exc.errors() if err["loc"]})
        raise SystemExit(
            "Configuração inválida: variáveis de ambiente ausentes ou inválidas: "
            + ", ".join(names)
        ) from None
