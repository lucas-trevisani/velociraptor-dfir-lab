from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "velociraptor-license-api"
    app_env: str = "development"
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    rate_limit_default: str = "60/minute"
    cors_origins: str = "http://localhost:18080"
    public_api_base: str = "https://YOUR_VPS_IP:18443"
    rsa_private_key_path: Path = Field(default=Path("secrets/license_private.pem"))
    rsa_public_key_path: Path = Field(default=Path("secrets/license_public.pem"))
    aes_key_base64: str
    hunt_storage_path: Path = Field(default=Path("storage/hunts"))
    result_storage_path: Path = Field(default=Path("storage/results"))
    launcher_min_version: str = "1.0.0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
