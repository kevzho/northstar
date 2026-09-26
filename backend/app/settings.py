"""
Environment settings loaded from process env via pydantic only (no extra deps).

Reads directly from os.environ so the same module works in local dev, CI, and
the Vercel serverless deploy (backend/vercel.json -> backend/api/index.py).
Defaults are dev-safe; production should set every field explicitly. Sensitive values are loaded lazily and never logged.
"""

import os
from pathlib import Path

from pydantic import BaseModel

# Load ``backend/.env`` before the settings snapshot is taken. The docs tell
# students to put SUPABASE_* there; without this the file was read by nothing
# and the backend fell back to defaults (→ 500 "missing SUPABASE_JWT_SECRET").
# ``override=False`` keeps real process env (Render, Railway, CI) authoritative.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:  # python-dotenv absent → process env only, still valid
    pass


class Settings(BaseModel):
    # Comma-separated list of allowed browser origins. More than one exists
    # during a domain migration (custom domain + the old .vercel.app URL).
    frontend_url: str = "http://localhost:3000"

    @property
    def frontend_urls(self) -> list[str]:
        return [u.strip().rstrip("/") for u in self.frontend_url.split(",") if u.strip()]

    supabase_url: str = "http://localhost:54321"
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwt_secret: str = ""

    # Optional: raises the GitHub Search rate limit for /projects from
    # 10 requests/minute to 30. A classic PAT with no scopes is enough.
    github_token: str = ""

    # Advisor spend controls. The free NIM tier is a fixed pool of calls
    # rather than a monthly allowance, so these are hard ceilings, not
    # smoothing. Raise them once the key's own quota is raised.
    advisor_per_student_daily: int = 10
    advisor_global_daily: int = 150
    advisor_cache_ttl_h: int = 24

    # Optional: the route advisor (POST /advisor) and the nightly candidate
    # verifier — any OpenAI-compatible chat API. Absent key = 503, feature off.
    #
    # Production uses NVIDIA NIM's free tier. The defaults name it rather than
    # a provider this project has never called: the old defaults said DeepSeek
    # while every real call went to NIM, which meant the fallback in
    # .github/workflows/scrape.yml would have silently pointed a CI run at the
    # wrong vendor entirely.
    #
    # LLM_MODEL is pinned and checked by scripts/check_llm.py before each
    # scrape, because hosted models are retired on a schedule:
    # meta/llama-3.1-70b-instruct reached end of life on 2026-08-26 and every
    # verifier call returned 410 for the next four weeks, unnoticed.
    llm_api_key: str = ""
    llm_api_base: str = "https://integrate.api.nvidia.com/v1"
    llm_model: str = "openai/gpt-oss-20b"

    # Per-job provider override for the VERIFIER only, falling back to the
    # LLM_* values above when unset.
    #
    # The two jobs have different constraints and it stopped being honest to
    # pretend otherwise. The verifier reads scraped public listings and sends no
    # student data anywhere, so it can move to a paid-but-stable provider today.
    # The advisor sends a student's trait scores, interests and goal statement in
    # their own words, and frontend/app/privacy/page.tsx names NVIDIA as the
    # recipient — so moving it requires changing a promise made to minors about
    # where their words go, in four languages, and that is a deliberate act and
    # not a config change.
    #
    # Set VERIFIER_* and the nightly scrape switches provider while /advisor
    # does not.
    verifier_api_key: str = ""
    verifier_api_base: str = ""
    verifier_model: str = ""

    @property
    def verifier_provider(self) -> tuple[str, str, str]:
        """(base, key, model) for the verifier — its own, else the shared one."""
        return (
            self.verifier_api_base or self.llm_api_base,
            self.verifier_api_key or self.llm_api_key,
            self.verifier_model or self.llm_model,
        )

    @classmethod
    def from_env(cls) -> "Settings":
        def _int(name: str, default: int) -> int:
            """Unset, empty, or malformed all fall back to the default.

            os.getenv returns "" for a set-but-empty variable, which int()
            rejects — and a CI runner exporting an undefined secret produces
            exactly that.
            """
            try:
                return int(os.getenv(name, ""))
            except ValueError:
                return default

        return cls(
            frontend_url=os.getenv("FRONTEND_URL", "http://localhost:3000"),
            supabase_url=os.getenv("SUPABASE_URL", "http://localhost:54321"),
            supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
            supabase_secret_key=os.getenv("SUPABASE_SECRET_KEY", ""),
            supabase_jwt_secret=os.getenv("SUPABASE_JWT_SECRET", ""),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            verifier_api_key=os.getenv("VERIFIER_API_KEY", ""),
            verifier_api_base=os.getenv("VERIFIER_API_BASE", ""),
            verifier_model=os.getenv("VERIFIER_MODEL", ""),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_api_base=os.getenv("LLM_API_BASE", "https://integrate.api.nvidia.com/v1"),
            llm_model=os.getenv("LLM_MODEL", "openai/gpt-oss-20b"),
            advisor_per_student_daily=_int("ADVISOR_PER_STUDENT_DAILY", 10),
            advisor_global_daily=_int("ADVISOR_GLOBAL_DAILY", 150),
            advisor_cache_ttl_h=_int("ADVISOR_CACHE_TTL_H", 24),
        )


settings = Settings.from_env()
