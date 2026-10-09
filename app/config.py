from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    # libpq sslmode; use "require" (or stricter) for hosted databases such as Supabase
    postgres_sslmode: Literal[
        "disable", "allow", "prefer", "require", "verify-ca", "verify-full"
    ] = "prefer"

    db_echo: bool = False

    @property
    def database_url(self) -> URL:
        # URL.create escapes special characters in the password
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            query={"sslmode": self.postgres_sslmode},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
