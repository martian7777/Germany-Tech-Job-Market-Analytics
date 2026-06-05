"""Skill-Gap Recommender engine.

Given a target role, the user's current skills and German level, it computes:
  * an overall match score against the role's market demand,
  * the most important missing skills (ranked by how often the market asks for them),
  * a "language fit" assessment vs. the typical German requirement for the role,
  * concrete recommended job openings ranked by per-job skill overlap.
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LANGUAGE_LEVELS, ROLE_CATEGORIES, JobPosting, language_rank
from app.schemas import (
    LanguageFit,
    MissingSkillItem,
    RecommendedJob,
    RecommendRequest,
    RecommendResponse,
)

router = APIRouter(prefix="/api/recommender", tags=["recommender"])

# Skills counted toward the gap analysis exclude the auto-added language tags,
# which are assessed separately via the language-fit logic.
LANGUAGE_SKILLS = {"German Language", "English Language"}


def _normalise(skills: list[str]) -> set[str]:
    return {s.strip().lower() for s in skills if s.strip()}


def _importance(pct: float) -> str:
    if pct >= 60:
        return "Critical"
    if pct >= 30:
        return "Important"
    return "Nice to have"


@router.get("/roles", response_model=list[str])
def supported_roles():
    return ROLE_CATEGORIES


@router.post("", response_model=RecommendResponse)
def recommend(payload: RecommendRequest, db: Session = Depends(get_db)):
    role = payload.target_role
    if role not in ROLE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Unknown role '{role}'.")

    jobs = db.scalars(
        select(JobPosting).where(JobPosting.role_category == role)
    ).all()
    if not jobs:
        raise HTTPException(status_code=404, detail="No market data for this role.")

    user_skills = _normalise(payload.skills)

    # --- Market skill demand for the role -------------------------------------
    demand: Counter[str] = Counter()
    canonical: dict[str, tuple[str, str]] = {}  # lower -> (display, category)
    for job in jobs:
        for skill in job.skills:
            if skill.name in LANGUAGE_SKILLS:
                continue
            key = skill.name.lower()
            demand[key] += 1
            canonical[key] = (skill.name, skill.category)

    n_jobs = len(jobs)
    demand_pct = {k: 100 * v / n_jobs for k, v in demand.items()}

    # --- Match score ----------------------------------------------------------
    # Weighted by demand: having a high-demand skill counts more. This rewards the
    # user for covering what the market actually asks for, not just raw skill count.
    total_weight = sum(demand_pct.values()) or 1.0
    have_weight = sum(pct for k, pct in demand_pct.items() if k in user_skills)
    match_score = round(100 * have_weight / total_weight, 1)

    have_skills = sorted(
        canonical[k][0] for k in demand_pct if k in user_skills
    )

    # --- Missing skills (ranked by market demand) -----------------------------
    missing: list[MissingSkillItem] = []
    for key, pct in sorted(demand_pct.items(), key=lambda x: x[1], reverse=True):
        if key in user_skills:
            continue
        display, category = canonical[key]
        missing.append(
            MissingSkillItem(
                skill=display,
                category=category,
                market_demand_pct=round(pct, 1),
                importance=_importance(pct),
            )
        )
    missing = missing[:12]

    # --- Language fit ---------------------------------------------------------
    language_fit = _assess_language(role, jobs, payload.german_level)

    # --- Recommended jobs -----------------------------------------------------
    recommended = _rank_jobs(jobs, user_skills, payload.preferred_cities)

    summary = _build_summary(role, match_score, missing, language_fit)

    return RecommendResponse(
        target_role=role,
        match_score=match_score,
        have_skills=have_skills,
        missing_skills=missing,
        language_fit=language_fit,
        recommended_jobs=recommended,
        summary=summary,
    )


def _assess_language(role: str, jobs, user_level: str) -> LanguageFit:
    if user_level not in LANGUAGE_LEVELS:
        user_level = "None"
    # "Typical" requirement = the modal German level among postings that require it.
    required_levels = [j.german_level for j in jobs if j.german_level != "None"]
    if required_levels:
        typical = Counter(required_levels).most_common(1)[0][0]
    else:
        typical = "None"

    sufficient = language_rank(user_level) >= language_rank(typical)
    if typical == "None":
        message = f"{role} roles are typically English-first — German is rarely required."
        action = None
    elif sufficient:
        message = (
            f"Your German ({user_level}) meets the typical requirement "
            f"({typical}) for {role} roles. You're well positioned."
        )
        action = None
    else:
        message = (
            f"This role usually requires {typical} German; your current level is "
            f"{user_level}. This may exclude you from a share of openings."
        )
        action = (
            f"Recommended action: progress from {user_level} towards {typical} "
            f"(e.g. an intensive Business German course)."
        )

    return LanguageFit(
        user_level=user_level,
        typical_required_level=typical,
        is_sufficient=sufficient,
        message=message,
        recommended_action=action,
    )


def _rank_jobs(jobs, user_skills: set[str], preferred_cities: list[str]) -> list[RecommendedJob]:
    preferred = {c.strip().lower() for c in preferred_cities if c.strip()}
    scored: list[tuple[float, RecommendedJob]] = []
    for job in jobs:
        job_skill_names = [s.name for s in job.skills if s.name not in LANGUAGE_SKILLS]
        job_keys = {s.lower() for s in job_skill_names}
        if not job_keys:
            continue
        matched = sorted(s for s in job_skill_names if s.lower() in user_skills)
        missing = sorted(s for s in job_skill_names if s.lower() not in user_skills)
        match_pct = round(100 * len(matched) / len(job_keys), 1)

        rank_score = match_pct
        if preferred and job.city.lower() in preferred:
            rank_score += 15  # gentle boost for location preference

        scored.append((
            rank_score,
            RecommendedJob(
                id=job.id,
                title=job.title,
                company=job.company,
                city=job.city,
                work_type=job.work_type,
                salary_avg=job.salary_avg,
                match_pct=match_pct,
                matched_skills=matched,
                missing_skills=missing,
            ),
        ))

    scored.sort(key=lambda x: (x[0], x[1].salary_avg), reverse=True)
    return [job for _, job in scored[:8]]


def _build_summary(role, score, missing, fit: LanguageFit) -> str:
    if score >= 75:
        band = "a strong match"
    elif score >= 50:
        band = "a solid foundation"
    elif score >= 25:
        band = "a developing profile"
    else:
        band = "an early-stage profile"

    top_missing = ", ".join(m.skill for m in missing[:3]) or "no major gaps"
    lang = "" if fit.is_sufficient or fit.typical_required_level == "None" else (
        f" Mind the language gap: {fit.typical_required_level} German is typically expected."
    )
    return (
        f"You have {band} for {role} roles ({score}% demand-weighted match). "
        f"Highest-impact skills to add next: {top_missing}.{lang}"
    )
