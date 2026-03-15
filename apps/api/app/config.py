from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    log_level: str = Field(default="info", validation_alias="API_LOG_LEVEL")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")

    postgres_user: str = Field(default="mockadmin", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="mockpassword", validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="mockapi", validation_alias="POSTGRES_DB")
    postgres_host: str = Field(default="postgres", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")

    admin_username: str = Field(default="admin", validation_alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin123", validation_alias="ADMIN_PASSWORD")

    enable_openapi: bool = Field(default=True, validation_alias="ENABLE_OPENAPI")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
