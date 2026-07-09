"""
Environment settings loaded from process env via pydantic only (no extra deps).

Reads directly from os.environ so the same module works in local dev, CI, and
the eventual Railway/Fly.io deploy. Defaults are dev-safe; production should
set every field explicitly. Sensitive values are loaded lazily and never logged.
"""

import os

from pydantic import BaseModel


class Settings(BaseModel):
    frontend_url: str = "http://localhost:3000"

    supabase_url: str = "http://localhost:54321"
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwt_secret: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            frontend_url=os.getenv("FRONTEND_URL", "http://localhost:3000"),
            supabase_url=os.getenv("SUPABASE_URL", "http://localhost:54321"),
            supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
            supabase_secret_key=os.getenv("SUPABASE_SECRET_KEY", ""),
            supabase_jwt_secret=os.getenv("SUPABASE_JWT_SECRET", ""),
        )


settings = Settings.from_env()
