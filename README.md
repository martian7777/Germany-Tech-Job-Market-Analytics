# DeTech Jobs Analytics 🇩🇪

**German Tech Job Market Analytics Platform** — a full-stack application that collects,
parses and analyses tech job openings across Germany's five biggest tech hubs
(Berlin, Munich, Hamburg, Frankfurt, Stuttgart), then helps job seekers close their
skill gaps against real market demand.

Built with **FastAPI + SQLite + SQLAlchemy** on the backend and
**React + Vite + Tailwind CSS v4 + Recharts** on the frontend.

---

## ✨ Features

| Module | What it does |
| --- | --- |
| **📊 Dashboard** | Top-15 demanded skills (per role), avg salary by role, openings by city, German-level distribution, and a role↔language radar — all from live SQL aggregations. |
| **🔍 Job Explorer** | Paginated, multi-filter job board (role, city, work type, experience, skill tags, German-level ceiling) with a detail drawer showing extracted skills. |
| **🎯 Skill Gap Recommender** | Enter your skills + German level + target role → demand-weighted match score, ranked missing skills, a "language fit" assessment, and matching job recommendations. |
| **📁 BI Reports** | Export the dataset to CSV (flat + long skills-fact table) and JSON, plus a step-by-step Power BI star-schema import guide. |
| **🕷️ Scraper** | Modular BeautifulSoup pipeline (`fetch → parse → extract skills/language → persist`) with an offline demo fixture and a live mode. |

The database auto-seeds **125 highly realistic job postings** across 5 roles
(Data Analyst, ML Engineer, Backend Developer, Robotics Engineer, RAG Engineer)
and 24 real German employers on first run.

---

## 🚀 Quick start

### Prerequisites
- Python 3.11+
- Node.js 20+

### 1. Backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Seed the database (creates detech_jobs.db with 125 jobs)
python -m app.seed

# Run the API (auto-seeds if empty)
uvicorn app.main:app --port 8000 --reload
```

API docs (Swagger UI): http://localhost:8000/docs

### 2. Frontend (React + Vite)

```powershell
cd frontend
npm install
npm run dev
```

Open the app at the URL Vite prints (e.g. **http://localhost:5173**).
The dev server proxies `/api/*` to the backend on port 8000.

---

## 🧩 API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness check |
| GET | `/api/jobs` | Paginated, filtered job search |
| GET | `/api/jobs/filters` | Distinct filter values + salary bounds |
| GET | `/api/jobs/{id}` | Single job detail |
| GET | `/api/analytics/overview` | KPI summary |
| GET | `/api/analytics/skill-demand?role=&limit=` | Top demanded skills |
| GET | `/api/analytics/salary-by-role` | Salary distribution per role |
| GET | `/api/analytics/geo` | Openings + avg salary by city |
| GET | `/api/analytics/language-demand` | German-level distribution |
| GET | `/api/analytics/role-language` | German requirement per role |
| GET | `/api/recommender/roles` | Supported target roles |
| POST | `/api/recommender` | Skill-gap analysis + job recommendations |
| POST | `/api/scrape?use_fixture=true` | Run the scraper pipeline |

### Recommender request example
```json
POST /api/recommender
{
  "target_role": "ML Engineer",
  "skills": ["Python", "SQL", "Docker"],
  "german_level": "A2",
  "preferred_cities": ["Berlin"]
}
```

---

## 🕷️ Running the scraper

```powershell
cd backend
python -m app.scraper          # offline demo fixture (safe, no network)
```

To scrape a permitted live source, set `ScraperConfig.start_urls` and
`use_fixture=False`. The parsing/extraction pipeline is identical in both modes.
The provided `.job-card` CSS selectors are a template — adapt them to the target
page's markup.

---

## 🏗️ Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, lifespan auto-seed
│   │   ├── database.py        # SQLAlchemy engine/session
│   │   ├── models.py          # JobPosting, Skill, job_skills junction
│   │   ├── schemas.py         # Pydantic v2 schemas
│   │   ├── seed.py            # Deterministic 125-job generator
│   │   ├── scraper.py         # BeautifulSoup pipeline
│   │   └── routes/
│   │       ├── jobs.py
│   │       ├── analytics.py
│   │       └── recommender.py
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx            # Shell + tab navigation
    │   ├── api.js            # Fetch client
    │   ├── index.css        # Tailwind v4 + glassmorphism design system
    │   └── components/
    │       ├── Dashboard.jsx
    │       ├── JobExplorer.jsx
    │       ├── SkillGapRecommender.jsx
    │       ├── BIReports.jsx
    │       └── ui.jsx
    └── vite.config.js
```

---

## 🔧 Tech & design notes

- **Database**: portable single-file SQLite. German/English requirements are stored
  as ordered CEFR columns on the posting; skills are normalised via a many-to-many
  junction for fast demand aggregations.
- **Match scoring**: the recommender weights each skill by how often the market
  demands it, so covering high-demand skills counts more than raw skill count.
- **Design system**: Tailwind v4 (CSS-first `@theme`) with a custom dark
  glassmorphism aesthetic, indigo→cyan accent, and Recharts visualisations.
