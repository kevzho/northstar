"""
Pydantic models that mirror the Meridian domain types in
``frontend/lib/types.ts``. They serve as the single source of truth for the
``FastAPI`` request/response shapes that the frontend consumes. Backend routers
import from here; the frontend keeps its duplicate TS definition in sync via
manual review (Day 3 and beyond will tighten this with shared types).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OpportunityField(str, Enum):
    cs = "cs"
    biology = "biology"
    math = "math"
    physics = "physics"
    engineering = "engineering"
    interdisciplinary = "interdisciplinary"


class OpportunityType(str, Enum):
    program = "program"
    scholarship = "scholarship"
    competition = "competition"
    mentorship = "mentorship"


class StudentProfile(BaseModel):
    """Full student row as served by GET /me or POST /students response."""

    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[str] = None
    interests: list[str] = Field(default_factory=list)
    goals: Optional[str] = None
    onboarded: bool = False
    # ISO 8601 timestamp when the student accepted the IRB-style data policy
    # during onboarding. NULL means consent has not been recorded.
    consented_at: Optional[str] = None


class StudentProfileCreate(BaseModel):
    """Request body for POST /students (upsert).

    ``id`` is omitted — the backend derives it from the JWT ``sub`` claim.
    ``email`` is omitted — the backend copies it from ``auth.users.email``
    via the Supabase client, or the client may supply it. If absent the
    upsert leaves the column alone.

    ``consent`` (bool, default False) — when True the backend stamps
    ``consented_at = now()`` on the row; when False the column is left
    untouched (so we never revoke an earlier consent via a stub call).
    """

    name: Optional[str] = None
    grade: Optional[str] = None
    interests: list[str] = Field(default_factory=list)
    goals: Optional[str] = None
    onboarded: bool = False
    consent: bool = False


class Bookmark(BaseModel):
    """A saved opportunity reference for a student."""

    id: str
    opportunity_id: str
    created_at: Optional[str] = None


class BookmarkCreate(BaseModel):
    """Request body for POST /bookmarks."""

    opportunity_id: str


class OutcomeCreate(BaseModel):
    """Request body for POST /outcomes."""

    opportunity_id: str
    status: str   # accepted | rejected | waitlisted | withdrew | completed
    impact_notes: Optional[str] = None


class Outcome(BaseModel):
    """Logged outcome row."""

    id: str
    opportunity_id: str
    status: str
    impact_notes: Optional[str] = None
    created_at: Optional[str] = None
