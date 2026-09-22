"""
Supabase service-role client for backend reads/writes.

The backend uses the service-role key (``SUPABASE_SECRET_KEY``) which bypasses
RLS — it owns upserting student profiles, reading the catalog, persisting
matches. The frontend never queries a table directly — it uses the publishable key
for auth only and reaches data through this API.

Lazy-imports ``create_client`` so test code and lightweight imports don't
require network/disk unless the client is actually used.
"""

from functools import lru_cache

from .settings import settings


@lru_cache(maxsize=1)
def get_supabase():
    """Return a cached service-role Supabase client.

    Raises a clear RuntimeError if ``SUPABASE_URL`` or the secret key are
    missing, rather than letting the SDK fail with a cryptic message later.
    """

    if not settings.supabase_url or not settings.supabase_secret_key:
        raise RuntimeError(
            "Supabase backend client requires SUPABASE_URL and "
            "SUPABASE_SECRET_KEY to be set."
        )

    from supabase import create_client  # lazy import keeps tests light

    return create_client(settings.supabase_url, settings.supabase_secret_key)
