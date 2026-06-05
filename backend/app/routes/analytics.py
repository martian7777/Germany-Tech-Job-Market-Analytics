"""Analytics endpoints: SQL aggregations powering the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JobPosting, Skill, job_skills, language_rank
from app.schemas import (
    AnalyticsOverview,
    CountItem,
    GeoItem,
    LanguageDemandItem,
    RoleLanguageItem,
    SalaryByRoleItem,
    SkillDemandItem,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(db: Session = Depends(get_db)):
    total_jobs = db.scalar(select(func.count(JobPosting.id))) or 0
    total_companies = db.scalar(select(func.count(distinct(JobPosting.company)))) or 0
    total_skills = db.scalar(select(func.count(Skill.id))) or 0
    avg_salary = db.scalar(
        select(func.avg((JobPosting.salary_min + JobPosting.salary_max) / 2))
    ) or 0

    remote = db.scalar(
        select(func.count(JobPosting.id)).where(JobPosting.work_type == "Remote")
    ) or 0
    german_required = db.scalar(
        select(func.count(JobPosting.id)).where(JobPosting.german_level != "None")
    ) or 0

    def counts(col):
        rows = db.execute(
            select(col, func.count(JobPosting.id)).group_by(col).order_by(func.count(JobPosting.id).desc())
        ).all()
        return [CountItem(label=r[0], value=r[1]) for r in rows]

    return AnalyticsOverview(
        total_jobs=total_jobs,
        total_companies=total_companies,
        total_skills=total_skills,
        avg_salary=int(avg_salary),
        remote_share_pct=round(100 * remote / total_jobs, 1) if total_jobs else 0.0,
        german_required_pct=round(100 * german_required / total_jobs, 1) if total_jobs else 0.0,
        roles=counts(JobPosting.role_category),
        work_types=counts(JobPosting.work_type),
        experience_levels=counts(JobPosting.experience_level),
    )


@router.get("/skill-demand", response_model=list[SkillDemandItem])
def skill_demand(
    db: Session = Depends(get_db),
    role: str | None = Query(None, description="Restrict to one role category"),
    limit: int = Query(15, ge=1, le=50),
):
    """Top demanded skills, optionally scoped to a role, with demand %."""
    base = select(func.count(distinct(JobPosting.id)))
    if role:
        base = base.where(JobPosting.role_category == role)
    denominator = db.scalar(base) or 0

    stmt = (
        select(Skill.name, Skill.category, func.count(distinct(JobPosting.id)).label("c"))
        .select_from(Skill)
        .join(job_skills, job_skills.c.skill_id == Skill.id)
        .join(JobPosting, JobPosting.id == job_skills.c.job_id)
    )
    if role:
        stmt = stmt.where(JobPosting.role_category == role)
    stmt = stmt.group_by(Skill.name, Skill.category).order_by(func.count(distinct(JobPosting.id)).desc()).limit(limit)

    rows = db.execute(stmt).all()
    return [
        SkillDemandItem(
            skill=r[0],
            category=r[1],
            count=r[2],
            percentage=round(100 * r[2] / denominator, 1) if denominator else 0.0,
        )
        for r in rows
    ]


@router.get("/salary-by-role", response_model=list[SalaryByRoleItem])
def salary_by_role(db: Session = Depends(get_db)):
    avg_expr = (JobPosting.salary_min + JobPosting.salary_max) / 2
    rows = db.execute(
        select(
            JobPosting.role_category,
            func.avg(avg_expr),
            func.min(JobPosting.salary_min),
            func.max(JobPosting.salary_max),
            func.count(JobPosting.id),
        )
        .group_by(JobPosting.role_category)
        .order_by(func.avg(avg_expr).desc())
    ).all()
    return [
        SalaryByRoleItem(
            role=r[0], avg_salary=int(r[1]), min_salary=int(r[2]),
            max_salary=int(r[3]), job_count=r[4],
        )
        for r in rows
    ]


@router.get("/geo", response_model=list[GeoItem])
def geo_distribution(db: Session = Depends(get_db)):
    avg_expr = (JobPosting.salary_min + JobPosting.salary_max) / 2
    rows = db.execute(
        select(
            JobPosting.city, JobPosting.state,
            func.count(JobPosting.id), func.avg(avg_expr),
        )
        .group_by(JobPosting.city, JobPosting.state)
        .order_by(func.count(JobPosting.id).desc())
    ).all()
    return [
        GeoItem(city=r[0], state=r[1], count=r[2], avg_salary=int(r[3]))
        for r in rows
    ]


@router.get("/language-demand", response_model=list[LanguageDemandItem])
def language_demand(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(JobPosting.id))) or 0
    rows = db.execute(
        select(JobPosting.german_level, func.count(JobPosting.id))
        .group_by(JobPosting.german_level)
    ).all()
    # order by CEFR rank
    rows = sorted(rows, key=lambda r: language_rank(r[0]))
    return [
        LanguageDemandItem(
            german_level=r[0],
            count=r[1],
            percentage=round(100 * r[1] / total, 1) if total else 0.0,
        )
        for r in rows
    ]


@router.get("/role-language", response_model=list[RoleLanguageItem])
def role_language(db: Session = Depends(get_db)):
    """Correlation between role and German requirement (>= B1 considered required)."""
    results: list[RoleLanguageItem] = []
    roles = [r[0] for r in db.execute(select(distinct(JobPosting.role_category))).all()]
    for role in roles:
        jobs = db.execute(
            select(JobPosting.german_level).where(JobPosting.role_category == role)
        ).all()
        if not jobs:
            continue
        ranks = [language_rank(j[0]) for j in jobs]
        requires = sum(1 for r in ranks if r >= language_rank("B1"))
        results.append(
            RoleLanguageItem(
                role=role,
                requires_german_pct=round(100 * requires / len(jobs), 1),
                avg_german_rank=round(sum(ranks) / len(ranks), 2),
            )
        )
    results.sort(key=lambda x: x.requires_german_pct, reverse=True)
    return results
