"""
Pydantic models that mirror the Northstar domain types in
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
    design = "design"
    business = "business"
    humanities = "humanities"
    health = "health"


class OpportunityType(str, Enum):
    program = "program"
    scholarship = "scholarship"
    competition = "competition"
    mentorship = "mentorship"
    internship = "internship"
    volunteer = "volunteer"
    journal = "journal"


class Audience(str, Enum):
    high_school = "high_school"
    college = "college"


class LocationPref(str, Enum):
    us = "us"
    international = "international"
    either = "either"


class StudentProfile(BaseModel):
    """Full student row as served by GET /me or POST /students response."""

    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[str] = None
    interests: list[str] = Field(default_factory=list)
    goals: Optional[str] = None
    audience: Audience = Audience.high_school
    location_pref: LocationPref = LocationPref.either
    # Quiz outputs synced from the frontend (shapes owned by
    # frontend/lib/scoring.ts): six 0-100 trait signals; six field shares
    # summing to 100. None until the student syncs an assessment.
    trait_scores: Optional[dict[str, float]] = None
    field_scores: Optional[dict[str, float]] = None
    # Sharing: the public-page name and the opt-in toggle (see /sharing).
    handle: Optional[str] = None
    public_profile: bool = False
    # Allowlisted self-published links (github/website/youtube/linkedin),
    # validated by app/social.py:clean_social_links on write.
    social_links: Optional[dict[str, str]] = None
    onboarded: bool = False
    # ISO 8601 timestamp when the student accepted the IRB-style data policy
    # during onboarding. NULL means consent has not been recorded.
    consented_at: Optional[str] = None


class AssessmentProfileSync(BaseModel):
    """Request body for POST /assessment-profile.

    Only these two columns are touched — deliberately not an upsert of the
    whole profile, so a quiz sync can never clobber onboarding fields.
    """

    trait_scores: dict[str, float]
    field_scores: dict[str, float]


class Mission(BaseModel):
    """A proof mission: a small real-world task tied to an archetype."""

    id: str
    archetype_id: str
    title: str
    description: str
    trait_focus: str
    effort: str
    sort_order: int = 0


class MissionCompletion(BaseModel):
    """Evidence that a student completed a mission."""

    id: str
    mission_id: str
    evidence: str = ""
    created_at: Optional[str] = None


class MissionCompleteBody(BaseModel):
    """Request body for POST /missions/{mission_id}/complete."""

    evidence: str = ""


class Dismissal(BaseModel):
    """A "not for me" mark on an opportunity."""

    id: str
    opportunity_id: str
    created_at: Optional[str] = None


class DismissalCreate(BaseModel):
    """Request body for POST /dismissals."""

    opportunity_id: str


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
    audience: Audience = Audience.high_school
    location_pref: LocationPref = LocationPref.either
    onboarded: bool = False
    consent: bool = False
    # Optional: when present it REPLACES the stored links (after
    # validation); when absent/None the column is left untouched.
    social_links: Optional[dict[str, str]] = None


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
