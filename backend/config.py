"""
config.py — centralised settings loaded from environment variables.
All secrets come from docker-compose environment, never hardcoded.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL — asyncpg driver
    postgres_user: str = "faceuser"
    postgres_password: str = "facepass"
    postgres_db: str = "facedb"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # CORS origins (comma-separated)
    cors_origins: str = "http://localhost:3000,http://frontend:3000"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
