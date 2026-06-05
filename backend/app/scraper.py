"""Modular BeautifulSoup scraper for German tech job listings.

The architecture is real and production-shaped:

    fetch(url)                  -> raw HTML (requests, polite headers, retries)
    parse_listing(html, source) -> list[ParsedJob]   (BeautifulSoup selectors)
    extract_skills(text)        -> list[str]          (keyword NLP over JD text)
    extract_language(text)      -> (german, english)  (CEFR regex extraction)
    persist(parsed, session)    -> int                (upsert into the DB)

Live scraping of commercial job boards is rate-limited and ToS-restricted, so the
default ``run_scrape`` uses an offline HTML fixture generator (``_demo_html``) that
mirrors a typical listing page. Point ``ScraperConfig.start_urls`` at a permitted
source and flip ``use_fixture=False`` to scrape for real — the parsing pipeline is
identical either way.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models import JobPosting, Skill
from app.seed import CITY_STATE, SKILL_CATALOG

USER_AGENT = (
    "Mozilla/5.0 (compatible; DeTechJobsBot/1.0; +https://example.de/bot) "
    "research/educational use"
)

CEFR_RE = re.compile(r"\b([ABC][12])\b")
# Longest skill names first so "Machine Learning" wins over "Learning" substrings.
_SKILL_PATTERNS = sorted(SKILL_CATALOG.keys(), key=len, reverse=True)


@dataclass
class ParsedJob:
    title: str
    company: str
    city: str
    description: str
    role_category: str
    work_type: str = "Hybrid"
    experience_level: str = "Mid"
    salary_min: int = 0
    salary_max: int = 0
    german_level: str = "None"
    english_level: str = "B2"
    source_url: str = ""
    source: str = "scraper"


@dataclass
class ScraperConfig:
    start_urls: list[str] = field(default_factory=list)
    request_delay: float = 1.0  # politeness delay between requests (seconds)
    timeout: int = 15
    max_retries: int = 3
    use_fixture: bool = True  # offline demo mode by default


# --- HTTP fetch -----------------------------------------------------------------
def fetch(url: str, config: ScraperConfig) -> str:
    """Fetch a URL with polite headers and simple retry/backoff."""
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"}
    last_exc: Exception | None = None
    for attempt in range(1, config.max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=config.timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:  # pragma: no cover - network
            last_exc = exc
            time.sleep(config.request_delay * attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_exc}")


# --- Parsing --------------------------------------------------------------------
def extract_skills(text: str) -> list[str]:
    """Keyword-match known skills against free-text job description."""
    found: list[str] = []
    for skill in _SKILL_PATTERNS:
        # word-ish boundary match, case-insensitive, escape regex specials
        pattern = r"(?<![A-Za-z0-9])" + re.escape(skill) + r"(?![A-Za-z0-9])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            found.append(skill)
    return found


def extract_language(text: str) -> tuple[str, str]:
    """Best-effort CEFR extraction for German/English requirements."""
    german, english = "None", "B2"
    lowered = text.lower()
    # find "German ... B2" or "Deutsch ... C1" style mentions
    for lang_key in ("german", "deutsch"):
        idx = lowered.find(lang_key)
        if idx != -1:
            window = text[idx: idx + 40]
            m = CEFR_RE.search(window)
            german = m.group(1) if m else "B2"
            break
    for lang_key in ("english", "englisch"):
        idx = lowered.find(lang_key)
        if idx != -1:
            window = text[idx: idx + 40]
            m = CEFR_RE.search(window)
            english = m.group(1) if m else "B2"
            break
    return german, english


def _classify_role(title: str) -> str:
    t = title.lower()
    if "rag" in t or "llm" in t or "genai" in t:
        return "RAG Engineer"
    if "robot" in t or "ros" in t:
        return "Robotics Engineer"
    if "ml" in t or "machine learning" in t or "ai engineer" in t:
        return "ML Engineer"
    if "data" in t and ("analyst" in t or "analytics" in t):
        return "Data Analyst"
    if "backend" in t or "back-end" in t or "software" in t:
        return "Backend Developer"
    return "Backend Developer"


def _parse_salary(text: str) -> tuple[int, int]:
    """Parse '€65,000 - €85,000' / '65.000–85.000 EUR' style ranges."""
    nums = re.findall(r"(\d{2,3})[.,]?(\d{3})", text)
    values = [int(a + b) for a, b in nums]
    if len(values) >= 2:
        return min(values[:2]), max(values[:2])
    if len(values) == 1:
        return values[0], values[0] + 10000
    return 0, 0


def parse_listing(html: str, source: str = "scraper") -> list[ParsedJob]:
    """Parse a listing page into structured ParsedJob records via BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[ParsedJob] = []

    for card in soup.select(".job-card"):
        title_el = card.select_one(".job-title")
        company_el = card.select_one(".job-company")
        city_el = card.select_one(".job-location")
        desc_el = card.select_one(".job-description")
        salary_el = card.select_one(".job-salary")
        type_el = card.select_one(".job-worktype")
        link_el = card.select_one("a")

        if not (title_el and company_el):
            continue

        title = title_el.get_text(strip=True)
        description = desc_el.get_text(" ", strip=True) if desc_el else title
        city = city_el.get_text(strip=True) if city_el else "Berlin"
        salary_min, salary_max = _parse_salary(salary_el.get_text() if salary_el else "")
        german, english = extract_language(description)

        jobs.append(
            ParsedJob(
                title=title,
                company=company_el.get_text(strip=True),
                city=city if city in CITY_STATE else "Berlin",
                description=description,
                role_category=_classify_role(title),
                work_type=(type_el.get_text(strip=True) if type_el else "Hybrid"),
                salary_min=salary_min,
                salary_max=salary_max,
                german_level=german,
                english_level=english,
                source_url=(link_el.get("href") if link_el else ""),
                source=source,
            )
        )
    return jobs


# --- Persistence ----------------------------------------------------------------
def persist(parsed: list[ParsedJob], session) -> int:
    """Insert parsed jobs, linking extracted skills. Returns count inserted."""
    skill_cache = {s.name: s for s in session.scalars(select(Skill)).all()}
    inserted = 0
    for pj in parsed:
        # de-dupe on (title, company, city)
        exists = session.scalar(
            select(JobPosting).where(
                JobPosting.title == pj.title,
                JobPosting.company == pj.company,
                JobPosting.city == pj.city,
            )
        )
        if exists:
            continue

        skill_names = extract_skills(pj.description) or extract_skills(pj.title)
        if pj.german_level != "None":
            skill_names.append("German Language")
        skill_names.append("English Language")

        skills = []
        for name in dict.fromkeys(skill_names):
            skill = skill_cache.get(name)
            if skill is None:
                skill = Skill(name=name, category=SKILL_CATALOG.get(name, "Soft"))
                session.add(skill)
                skill_cache[name] = skill
            skills.append(skill)

        job = JobPosting(
            title=pj.title,
            company=pj.company,
            city=pj.city,
            state=CITY_STATE.get(pj.city, "Berlin"),
            description=pj.description,
            role_category=pj.role_category,
            experience_level=pj.experience_level,
            work_type=pj.work_type,
            salary_min=pj.salary_min or 55000,
            salary_max=pj.salary_max or 75000,
            salary_currency="EUR",
            german_level=pj.german_level,
            english_level=pj.english_level,
            date_posted=date.today(),
            source_url=pj.source_url or "https://careers.example.de/scraped",
            source=pj.source,
            skills=skills,
        )
        session.add(job)
        inserted += 1
    session.commit()
    return inserted


# --- Demo fixture ---------------------------------------------------------------
def _demo_html() -> str:
    """A small fixture mirroring a real listing page, for offline demonstration."""
    cards = [
        ("Senior RAG Engineer (Enterprise Search)", "Aleph Alpha", "Berlin",
         "Build retrieval-augmented generation systems with Python, LangChain, "
         "Vector Databases and LLMs. English C1 required, German A2 a plus.",
         "€95.000 - €120.000", "Hybrid"),
        ("ML Engineer (Computer Vision)", "BMW Group", "Munich",
         "Develop ML models with Python, PyTorch and MLOps on AWS. "
         "German B2 and English B2 required.",
         "€80.000 - €105.000", "Onsite"),
        ("Data Analyst - Product Analytics", "Zalando", "Berlin",
         "Drive insights with SQL, Python, Power BI and Tableau. "
         "English B2 required; German B1 welcome.",
         "€58.000 - €72.000", "Remote"),
        ("Robotics Engineer (Perception)", "KUKA Robotics", "Munich",
         "Work on ROS2, C++, SLAM and Sensor Fusion for industrial robots. "
         "German B2 required, English B2.",
         "€78.000 - €98.000", "Onsite"),
    ]
    html = ["<html><body><ul class='jobs'>"]
    for title, company, city, desc, salary, wt in cards:
        html.append(
            f"<li class='job-card'>"
            f"<a href='https://careers.example.de/{company.lower().replace(' ', '-')}'>"
            f"<h2 class='job-title'>{title}</h2></a>"
            f"<span class='job-company'>{company}</span>"
            f"<span class='job-location'>{city}</span>"
            f"<span class='job-salary'>{salary}</span>"
            f"<span class='job-worktype'>{wt}</span>"
            f"<p class='job-description'>{desc}</p>"
            f"</li>"
        )
    html.append("</ul></body></html>")
    return "".join(html)


def run_scrape(config: ScraperConfig | None = None) -> dict:
    """Entry point used by the CLI and the API controller route."""
    config = config or ScraperConfig()
    init_db()
    session = SessionLocal()
    try:
        all_parsed: list[ParsedJob] = []
        if config.use_fixture or not config.start_urls:
            all_parsed = parse_listing(_demo_html(), source="scraper-demo")
        else:
            for url in config.start_urls:
                html = fetch(url, config)
                all_parsed.extend(parse_listing(html, source="scraper"))
                time.sleep(config.request_delay)

        inserted = persist(all_parsed, session)
        return {
            "parsed": len(all_parsed),
            "inserted": inserted,
            "skipped_duplicates": len(all_parsed) - inserted,
            "mode": "fixture" if (config.use_fixture or not config.start_urls) else "live",
        }
    finally:
        session.close()


if __name__ == "__main__":
    result = run_scrape()
    print(result)
