"""Pydantic v2 schemas for request validation and response serialisation."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# --- Skills ---------------------------------------------------------------------
class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str


# --- Jobs -----------------------------------------------------------------------
class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    city: str
    state: str
    description: str
    role_category: str
    experience_level: str
    work_type: str
    salary_min: int
    salary_max: int
    salary_currency: str
    salary_avg: int
    german_level: str
    english_level: str
    date_posted: date
    source_url: str
    source: str
    skill_names: list[str] = Field(default_factory=list)


class JobListOut(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[JobOut]


class FilterOptions(BaseModel):
    """Distinct values used to populate frontend filter controls."""

    roles: list[str]
    cities: list[str]
    states: list[str]
    work_types: list[str]
    experience_levels: list[str]
    german_levels: list[str]
    skills: list[str]
    companies: list[str]
    salary_range: dict[str, int]


# --- Analytics ------------------------------------------------------------------
class CountItem(BaseModel):
    label: str
    value: int


class SkillDemandItem(BaseModel):
    skill: str
    category: str
    count: int
    percentage: float


class SalaryByRoleItem(BaseModel):
    role: str
    avg_salary: int
    min_salary: int
    max_salary: int
    job_count: int


class GeoItem(BaseModel):
    city: str
    state: str
    count: int
    avg_salary: int


class LanguageDemandItem(BaseModel):
    german_level: str
    count: int
    percentage: float


class RoleLanguageItem(BaseModel):
    role: str
    requires_german_pct: float  # % of postings needing German >= B1
    avg_german_rank: float


class AnalyticsOverview(BaseModel):
    total_jobs: int
    total_companies: int
    total_skills: int
    avg_salary: int
    remote_share_pct: float
    german_required_pct: float
    roles: list[CountItem]
    work_types: list[CountItem]
    experience_levels: list[CountItem]


# --- Recommender ----------------------------------------------------------------
class RecommendRequest(BaseModel):
    target_role: str = Field(..., description="One of the supported role categories")
    skills: list[str] = Field(default_factory=list, description="Skills the user already has")
    german_level: str = Field("None", description="Current CEFR German level")
    experience_level: str | None = Field(None, description="Optional self-assessed level")
    preferred_cities: list[str] = Field(default_factory=list)


class MissingSkillItem(BaseModel):
    skill: str
    category: str
    market_demand_pct: float  # how often this skill appears in the role's postings
    importance: str  # "Critical" | "Important" | "Nice to have"


class LanguageFit(BaseModel):
    user_level: str
    typical_required_level: str
    is_sufficient: bool
    message: str
    recommended_action: str | None = None


class RecommendedJob(BaseModel):
    id: int
    title: str
    company: str
    city: str
    work_type: str
    salary_avg: int
    match_pct: float
    matched_skills: list[str]
    missing_skills: list[str]


class RecommendResponse(BaseModel):
    target_role: str
    match_score: float
    have_skills: list[str]
    missing_skills: list[MissingSkillItem]
    language_fit: LanguageFit
    recommended_jobs: list[RecommendedJob]
    summary: str
