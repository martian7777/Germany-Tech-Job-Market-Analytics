"""ORM models for the DeTech Jobs Analytics platform.

Design notes
------------
* ``JobPosting`` holds the denormalised, per-job attributes that analytics query
  most often (role, city, salary band, work type, experience and language levels).
* ``Skill`` is a normalised catalogue. ``job_skills`` is the many-to-many junction
  enabling fast "which skills does role X demand" aggregations.
* German/English requirements are modelled as ordered enum-like string columns on
  the posting itself. Each job has exactly one German level and one English level,
  so a dedicated junction table would add joins without adding information.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Ordered language proficiency scale (index == rank). "None" means not required.
LANGUAGE_LEVELS: list[str] = ["None", "A1", "A2", "B1", "B2", "C1", "C2"]
EXPERIENCE_LEVELS: list[str] = ["Junior", "Mid", "Senior", "Lead"]
WORK_TYPES: list[str] = ["Remote", "Hybrid", "Onsite"]
ROLE_CATEGORIES: list[str] = [
    "Data Analyst",
    "ML Engineer",
    "Backend Developer",
    "Robotics Engineer",
    "RAG Engineer",
]


def language_rank(level: str) -> int:
    """Return the ordinal rank of a CEFR level; unknown values rank as 0 (None)."""
    try:
        return LANGUAGE_LEVELS.index(level)
    except ValueError:
        return 0


# --- Association table: JobPosting <-> Skill -------------------------------------
job_skills = Table(
    "job_skills",
    Base.metadata,
    Column("job_id", ForeignKey("job_postings.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)


class Skill(Base):
    """A single demandable skill (e.g. Python, Power BI, ROS2, German Language)."""

    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("name", name="uq_skill_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    # e.g. "Programming", "Data", "Cloud", "DevOps", "ML/AI", "BI", "Robotics", "Soft"
    category: Mapped[str] = mapped_column(String(40), index=True, nullable=False)

    jobs: Mapped[list["JobPosting"]] = relationship(
        secondary=job_skills, back_populates="skills"
    )


class JobPosting(Base):
    """A single job opening parsed from a German tech job source."""

    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    role_category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    experience_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    work_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    salary_min: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")

    german_level: Mapped[str] = mapped_column(String(8), nullable=False, default="None", index=True)
    english_level: Mapped[str] = mapped_column(String(8), nullable=False, default="B2", index=True)

    date_posted: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str] = mapped_column(String(60), nullable=False, default="seed")

    skills: Mapped[list[Skill]] = relationship(
        secondary=job_skills, back_populates="jobs", lazy="selectin"
    )

    @property
    def salary_avg(self) -> int:
        return (self.salary_min + self.salary_max) // 2

    @property
    def skill_names(self) -> list[str]:
        return sorted(s.name for s in self.skills)
