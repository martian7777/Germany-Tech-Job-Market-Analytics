"""Seed the database with 120+ highly realistic German tech job postings.

The generator is deterministic (``random.seed``) so the dataset is reproducible
and statistically balanced across the five target roles, five hub cities and a
roster of real German employers. Run directly::

    python -m app.seed            # create + seed (idempotent: wipes & reseeds)
    python -m app.seed --keep     # only seed if the table is empty
"""

from __future__ import annotations

import argparse
import random
from datetime import date, timedelta

from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models import (
    EXPERIENCE_LEVELS,
    JobPosting,
    Skill,
)

RNG = random.Random(42)  # deterministic dataset

# --- Reference data -------------------------------------------------------------
CITY_STATE = {
    "Berlin": "Berlin",
    "Munich": "Bavaria",
    "Hamburg": "Hamburg",
    "Frankfurt": "Hesse",
    "Stuttgart": "Baden-Württemberg",
}

# company -> plausible hub cities
COMPANIES = {
    "SAP": ["Frankfurt", "Stuttgart", "Munich"],
    "Siemens": ["Munich", "Frankfurt"],
    "Allianz": ["Munich", "Frankfurt"],
    "Delivery Hero": ["Berlin"],
    "Zalando": ["Berlin", "Hamburg"],
    "BMW Group": ["Munich"],
    "Mercedes-Benz": ["Stuttgart"],
    "Bosch": ["Stuttgart", "Munich"],
    "N26": ["Berlin"],
    "Trade Republic": ["Berlin"],
    "Celonis": ["Munich"],
    "Personio": ["Munich"],
    "Deutsche Bank": ["Frankfurt"],
    "Commerzbank": ["Frankfurt"],
    "KUKA Robotics": ["Munich", "Stuttgart"],
    "Otto Group": ["Hamburg"],
    "ABOUT YOU": ["Hamburg"],
    "Infineon": ["Munich"],
    "HelloFresh": ["Berlin"],
    "DeepL": ["Berlin", "Hamburg"],
    "Aleph Alpha": ["Stuttgart", "Berlin"],
    "Flink": ["Berlin"],
    "Wayfair": ["Berlin"],
    "Forto": ["Berlin", "Hamburg"],
}

# Skill catalogue: name -> category
SKILL_CATALOG: dict[str, str] = {
    # Programming
    "Python": "Programming", "Java": "Programming", "Go": "Programming",
    "C++": "Programming", "TypeScript": "Programming", "Scala": "Programming",
    "SQL": "Programming", "Rust": "Programming",
    # Data
    "Pandas": "Data", "Spark": "Data", "dbt": "Data", "Airflow": "Data",
    "Snowflake": "Data", "BigQuery": "Data", "Kafka": "Data", "Statistics": "Data",
    "Data Modeling": "Data", "ETL": "Data",
    # BI
    "Power BI": "BI", "Tableau": "BI", "Looker": "BI", "Excel": "BI",
    "Data Visualization": "BI",
    # Cloud
    "AWS": "Cloud", "Azure": "Cloud", "GCP": "Cloud",
    # DevOps
    "Docker": "DevOps", "Kubernetes": "DevOps", "CI/CD": "DevOps",
    "Terraform": "DevOps", "Linux": "DevOps",
    # ML/AI
    "Machine Learning": "ML/AI", "PyTorch": "ML/AI", "TensorFlow": "ML/AI",
    "scikit-learn": "ML/AI", "MLOps": "ML/AI", "Deep Learning": "ML/AI",
    "NLP": "ML/AI", "Computer Vision": "ML/AI",
    # GenAI / RAG
    "LLMs": "GenAI", "LangChain": "GenAI", "RAG": "GenAI",
    "Vector Databases": "GenAI", "Prompt Engineering": "GenAI",
    "Embeddings": "GenAI", "Hugging Face": "GenAI", "LlamaIndex": "GenAI",
    # Backend
    "REST APIs": "Backend", "Microservices": "Backend", "PostgreSQL": "Backend",
    "Redis": "Backend", "gRPC": "Backend", "GraphQL": "Backend", "FastAPI": "Backend",
    "Spring Boot": "Backend",
    # Robotics
    "ROS2": "Robotics", "SLAM": "Robotics", "Sensor Fusion": "Robotics",
    "Embedded Systems": "Robotics", "Control Systems": "Robotics",
    "Motion Planning": "Robotics",
    # Soft / Language
    "German Language": "Language", "English Language": "Language",
    "Agile/Scrum": "Soft", "Stakeholder Management": "Soft",
}

# Per-role definition: core skills (always), pool (sampled), salary bands by level,
# typical German requirement weighting, and title specialisations.
ROLE_DEFS = {
    "Data Analyst": {
        "core": ["SQL", "Excel"],
        "pool": ["Python", "Power BI", "Tableau", "Looker", "Statistics",
                 "Data Visualization", "dbt", "Snowflake", "BigQuery",
                 "Data Modeling", "ETL", "Stakeholder Management"],
        "pool_n": (3, 5),
        "salary": {"Junior": (45000, 56000), "Mid": (55000, 70000),
                   "Senior": (68000, 85000), "Lead": (82000, 100000)},
        "german_weights": [("None", 1), ("B1", 3), ("B2", 4), ("C1", 2)],
        "specials": ["Marketing Analytics", "Product Analytics", "BI",
                     "Finance", "Supply Chain", ""],
    },
    "ML Engineer": {
        "core": ["Python", "Machine Learning"],
        "pool": ["PyTorch", "TensorFlow", "scikit-learn", "MLOps", "Docker",
                 "Kubernetes", "AWS", "GCP", "Azure", "Spark", "SQL",
                 "Deep Learning", "Airflow"],
        "pool_n": (4, 6),
        "salary": {"Junior": (55000, 66000), "Mid": (65000, 85000),
                   "Senior": (84000, 105000), "Lead": (104000, 130000)},
        "german_weights": [("None", 5), ("B1", 2), ("B2", 2), ("A2", 1)],
        "specials": ["Computer Vision", "NLP", "Recommender Systems",
                     "MLOps", "Forecasting", ""],
    },
    "Backend Developer": {
        "core": ["REST APIs"],
        "pool": ["Python", "Java", "Go", "TypeScript", "Docker", "Kubernetes",
                 "PostgreSQL", "Microservices", "Kafka", "AWS", "CI/CD",
                 "Redis", "gRPC", "GraphQL", "Spring Boot", "FastAPI"],
        "pool_n": (4, 6),
        "salary": {"Junior": (50000, 60000), "Mid": (60000, 80000),
                   "Senior": (80000, 100000), "Lead": (100000, 125000)},
        "german_weights": [("None", 4), ("B1", 3), ("B2", 2), ("A2", 1)],
        "specials": ["Payments", "Platform", "E-Commerce", "Cloud",
                     "Distributed Systems", ""],
    },
    "Robotics Engineer": {
        "core": ["ROS2", "C++"],
        "pool": ["Python", "Computer Vision", "SLAM", "Sensor Fusion",
                 "Embedded Systems", "Control Systems", "Motion Planning",
                 "Linux", "Machine Learning"],
        "pool_n": (3, 5),
        "salary": {"Junior": (50000, 62000), "Mid": (62000, 82000),
                   "Senior": (82000, 105000), "Lead": (104000, 128000)},
        "german_weights": [("None", 1), ("B1", 2), ("B2", 4), ("C1", 3)],
        "specials": ["Autonomous Systems", "Industrial Automation",
                     "Perception", "Manipulation", "Mobile Robots", ""],
    },
    "RAG Engineer": {
        "core": ["Python", "LLMs", "RAG"],
        "pool": ["LangChain", "LlamaIndex", "Vector Databases",
                 "Prompt Engineering", "Embeddings", "Hugging Face",
                 "FastAPI", "AWS", "NLP", "Docker", "MLOps"],
        "pool_n": (3, 6),
        "salary": {"Junior": (60000, 72000), "Mid": (72000, 95000),
                   "Senior": (95000, 120000), "Lead": (120000, 145000)},
        "german_weights": [("None", 6), ("B1", 1), ("A2", 1)],
        "specials": ["Enterprise Search", "Conversational AI",
                     "Knowledge Assistants", "Agentic Systems", ""],
    },
}

WORK_TYPE_WEIGHTS = [("Remote", 2), ("Hybrid", 5), ("Onsite", 3)]
EXP_WEIGHTS = [("Junior", 2), ("Mid", 4), ("Senior", 3), ("Lead", 1)]

JOBS_PER_ROLE = 25  # 5 roles -> 125 postings


def _weighted_choice(weighted: list[tuple[str, int]]) -> str:
    population = [v for v, _ in weighted]
    weights = [w for _, w in weighted]
    return RNG.choices(population, weights=weights, k=1)[0]


def _round_salary(value: int) -> int:
    return int(round(value / 1000.0)) * 1000


def _build_description(company, city, role, level, special, skills, german, english) -> str:
    spec = f" focused on {special}" if special else ""
    skills_str = ", ".join(skills[:6])
    de = (
        f"Conversational German ({german}) is required for daily collaboration."
        if german != "None"
        else "This is an English-first team; German is not required."
    )
    return (
        f"{company} is hiring a {level} {role}{spec} to join our team in {city}, Germany. "
        f"You will work on impactful, production-grade systems alongside a multidisciplinary team. "
        f"Core stack and expertise: {skills_str}. "
        f"We offer a competitive salary, 30 days vacation, a relocation package and a "
        f"strong learning budget. "
        f"Working language: English ({english}). {de} "
        f"Apply now to help shape data-driven products in the German market."
    )


def _get_or_create_skills(session) -> dict[str, Skill]:
    """Ensure the full skill catalogue exists; return name -> Skill map."""
    existing = {s.name: s for s in session.scalars(select(Skill)).all()}
    for name, category in SKILL_CATALOG.items():
        if name not in existing:
            skill = Skill(name=name, category=category)
            session.add(skill)
            existing[name] = skill
    session.flush()
    return existing


def generate_postings(session) -> list[JobPosting]:
    skills_map = _get_or_create_skills(session)
    postings: list[JobPosting] = []
    company_names = list(COMPANIES.keys())
    today = date(2026, 6, 5)

    for role, cfg in ROLE_DEFS.items():
        for _ in range(JOBS_PER_ROLE):
            company = RNG.choice(company_names)
            city = RNG.choice(COMPANIES[company])
            state = CITY_STATE[city]
            level = _weighted_choice(EXP_WEIGHTS)
            work_type = _weighted_choice(WORK_TYPE_WEIGHTS)
            special = RNG.choice(cfg["specials"])

            # Skills: core + sampled pool
            n = RNG.randint(*cfg["pool_n"])
            sampled = RNG.sample(cfg["pool"], min(n, len(cfg["pool"])))
            skill_names = list(dict.fromkeys(cfg["core"] + sampled))

            # Salary band, widened slightly + rounded
            lo, hi = cfg["salary"][level]
            jitter = RNG.randint(-2000, 3000)
            salary_min = _round_salary(lo + jitter)
            salary_max = _round_salary(hi + jitter + RNG.randint(0, 4000))
            if salary_max <= salary_min:
                salary_max = salary_min + 8000

            # Language
            german = _weighted_choice(cfg["german_weights"])
            english = RNG.choices(["B2", "C1", "C2"], weights=[3, 4, 2], k=1)[0]

            # Reflect language requirements as skills too (plan requirement)
            lang_skills = []
            if german in ("B1", "B2", "C1", "C2"):
                lang_skills.append("German Language")
            lang_skills.append("English Language")
            full_skill_names = list(dict.fromkeys(skill_names + lang_skills))

            title = f"{level} {role}"
            if special:
                title += f" ({special})"

            posted = today - timedelta(days=RNG.randint(0, 90))
            slug = f"{company.lower().replace(' ', '-')}-{role.lower().replace(' ', '-')}"
            url = f"https://careers.example.de/{slug}/{RNG.randint(10000, 99999)}"

            description = _build_description(
                company, city, role, level, special, skill_names, german, english
            )

            posting = JobPosting(
                title=title,
                company=company,
                city=city,
                state=state,
                description=description,
                role_category=role,
                experience_level=level,
                work_type=work_type,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency="EUR",
                german_level=german,
                english_level=english,
                date_posted=posted,
                source_url=url,
                source="seed",
                skills=[skills_map[name] for name in full_skill_names],
            )
            session.add(posting)
            postings.append(posting)

    session.flush()
    return postings


def seed(keep_existing: bool = False) -> int:
    """Create tables and populate the database. Returns number of postings."""
    init_db()
    session = SessionLocal()
    try:
        existing = session.scalar(select(JobPosting).limit(1))
        if existing is not None:
            if keep_existing:
                count = session.query(JobPosting).count()
                print(f"Database already seeded ({count} postings); --keep set, skipping.")
                return count
            # wipe for a clean reseed
            session.query(JobPosting).delete()
            session.commit()

        postings = generate_postings(session)
        session.commit()
        print(f"Seeded {len(postings)} job postings across {len(ROLE_DEFS)} roles.")
        print(f"Skill catalogue size: {len(SKILL_CATALOG)}")
        return len(postings)
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the DeTech Jobs database.")
    parser.add_argument("--keep", action="store_true", help="Skip if already seeded.")
    args = parser.parse_args()
    seed(keep_existing=args.keep)
