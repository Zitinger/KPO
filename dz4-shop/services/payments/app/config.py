from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    service_name: str = "payments"
    database_dsn: str
    rabbit_url: str

    outbox_publish_interval_sec: float = 0.5
    outbox_batch_size: int = 50


def load_settings() -> Settings:
    return Settings()
