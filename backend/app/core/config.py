"""Application settings loaded from environment variables (INFRA-06, INFRA-07)."""

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    database_url: str
    admin_email: str
    admin_password: SecretStr
    cookie_secure: bool = True

    maritalk_api_key: SecretStr | None = None
    maritalk_api_base: str | None = None
    maritalk_model: str | None = None
    maritalk_fallback_model: str = "sabia-4-br-sp"


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
