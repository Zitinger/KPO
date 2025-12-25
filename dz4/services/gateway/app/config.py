from __future__ import annotations

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_base_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "http://" + u
    return u.rstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    orders_urls: str = "http://orders-1:8000,http://orders-2:8000"
    payments_url: str = "http://payments:8000"

    @field_validator("orders_urls")
    @classmethod
    def _validate_orders_urls(cls, v: str) -> str:
        parts = [p.strip() for p in (v or "").split(",") if p.strip()]
        if not parts:
            return v
        parts = [_normalize_base_url(p) for p in parts]
        return ",".join(parts)

    @field_validator("payments_url")
    @classmethod
    def _validate_payments_url(cls, v: str) -> str:
        return _normalize_base_url(v)

    def orders_base_urls(self) -> List[str]:
        return [p.strip() for p in self.orders_urls.split(",") if p.strip()]


settings = Settings()


def load_settings() -> Settings:
    return settings
