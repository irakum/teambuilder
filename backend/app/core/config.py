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
    export_dir: str = "/tmp/teambuilder_exports"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/callback"

    # JWT
    jwt_secret: str = "dev-jwt-secret"
    jwt_expire_minutes: int = 10080  # 7 днів

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
