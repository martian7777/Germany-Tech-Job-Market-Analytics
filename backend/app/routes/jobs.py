"""Job listing endpoints: paginated search, filtering and filter metadata."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JobPosting, Skill, job_skills, language_rank
from app.schemas import FilterOptions, JobListOut, JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

SORT_FIELDS = {
    "date": JobPosting.date_posted,
    "salary": JobPosting.salary_max,
    "title": JobPosting.title,
    "company": JobPosting.company,
}


@router.get("", response_model=JobListOut)
def list_jobs(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Free text over title/company/description"),
    role: str | None = None,
    city: str | None = None,
    state: str | None = None,
    work_type: str | None = None,
    experience_level: str | None = None,
    company: str | None = None,
    skills: list[str] | None = Query(None, description="Repeatable; AND semantics"),
    min_german: str | None = Query(None, description="Max German level the user accepts"),
    min_salary: int | None = None,
    sort: str = Query("date", pattern="^(date|salary|title|company)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Return a paginated, filtered list of postings."""
    stmt = select(JobPosting)

    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            JobPosting.title.ilike(like)
            | JobPosting.company.ilike(like)
            | JobPosting.description.ilike(like)
        )
    if role:
        stmt = stmt.where(JobPosting.role_category == role)
    if city:
        stmt = stmt.where(JobPosting.city == city)
    if state:
        stmt = stmt.where(JobPosting.state == state)
    if work_type:
        stmt = stmt.where(JobPosting.work_type == work_type)
    if experience_level:
        stmt = stmt.where(JobPosting.experience_level == experience_level)
    if company:
        stmt = stmt.where(JobPosting.company == company)
    if min_salary:
        stmt = stmt.where(JobPosting.salary_max >= min_salary)

    # Skill AND filter: a job must contain every requested skill.
    if skills:
        for skill_name in skills:
            sub = (
                select(job_skills.c.job_id)
                .join(Skill, Skill.id == job_skills.c.skill_id)
                .where(Skill.name == skill_name)
            )
            stmt = stmt.where(JobPosting.id.in_(sub))

    # German level ceiling: include jobs requiring <= the user's stated level.
    if min_german:
        ceiling = language_rank(min_german)
        allowed = [lvl for lvl, rank in _level_ranks() if rank <= ceiling]
        stmt = stmt.where(JobPosting.german_level.in_(allowed))

    # Total before pagination
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    sort_col = SORT_FIELDS[sort]
    sort_col = sort_col.asc() if order == "asc" else sort_col.desc()
    stmt = stmt.order_by(sort_col, JobPosting.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    items = db.scalars(stmt).all()
    pages = max(1, math.ceil(total / page_size))
    return JobListOut(
        total=total, page=page, page_size=page_size, pages=pages,
        items=[JobOut.model_validate(j) for j in items],
    )


@router.get("/filters", response_model=FilterOptions)
def filter_options(db: Session = Depends(get_db)):
    """Distinct filter values + salary bounds for populating UI controls."""

    def distinct(col):
        return [r[0] for r in db.execute(select(col).distinct().order_by(col)).all()]

    salary_min = db.scalar(select(func.min(JobPosting.salary_min))) or 0
    salary_max = db.scalar(select(func.max(JobPosting.salary_max))) or 0
    skill_names = [
        r[0] for r in db.execute(select(Skill.name).order_by(Skill.name)).all()
    ]
    return FilterOptions(
        roles=distinct(JobPosting.role_category),
        cities=distinct(JobPosting.city),
        states=distinct(JobPosting.state),
        work_types=distinct(JobPosting.work_type),
        experience_levels=distinct(JobPosting.experience_level),
        german_levels=distinct(JobPosting.german_level),
        skills=skill_names,
        companies=distinct(JobPosting.company),
        salary_range={"min": salary_min, "max": salary_max},
    )


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(JobPosting, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


def _level_ranks():
    from app.models import LANGUAGE_LEVELS

    return [(lvl, i) for i, lvl in enumerate(LANGUAGE_LEVELS)]
