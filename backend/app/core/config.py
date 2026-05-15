from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str
    sync_database_url: str

    # App
    app_env: str = "development"
    secret_key: str = "dev-secret"
    cors_origins: str = "http://localhost:5173"

    # Export
    export_dir: str = "/tmp/teambuilder_exports"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
