import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import {
  Card,
  Chip,
  ErrorState,
  Spinner,
  colorFor,
  eur,
} from "./ui.jsx";

const WORK_TYPE_ICON = { Remote: "🏠", Hybrid: "🔀", Onsite: "🏢" };

function SkillTag({ name, category }) {
  return (
    <span
      className="text-[0.7rem] font-medium px-2 py-0.5 rounded-md border"
      style={{
        color: colorFor(category),
        borderColor: `${colorFor(category)}55`,
        background: `${colorFor(category)}14`,
      }}
    >
      {name}
    </span>
  );
}

function JobCard({ job, skillCategory, onOpen }) {
  return (
    <Card className="p-5 cursor-pointer" >
      <div onClick={() => onOpen(job)}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold text-white leading-snug">{job.title}</h3>
            <div className="text-sm text-slate-400 mt-0.5">
              {job.company} · {job.city}, {job.state}
            </div>
          </div>
          <span className="chip shrink-0">
            {WORK_TYPE_ICON[job.work_type]} {job.work_type}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
          <span className="chip">{job.role_category}</span>
          <span className="chip">{job.experience_level}</span>
          <span className="chip">
            {job.german_level === "None" ? "🇬🇧 English-only" : `🇩🇪 German ${job.german_level}`}
          </span>
        </div>

        <div className="mt-3 text-cyan-300 font-semibold">
          {eur(job.salary_min)} – {eur(job.salary_max)}
        </div>

        <div className="flex flex-wrap gap-1.5 mt-3">
          {job.skill_names.slice(0, 6).map((s) => (
            <SkillTag key={s} name={s} category={skillCategory[s]} />
          ))}
          {job.skill_names.length > 6 && (
            <span className="text-[0.7rem] text-slate-500 self-center">
              +{job.skill_names.length - 6} more
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}

function JobDrawer({ job, skillCategory, onClose }) {
  if (!job) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-fade-up"
      onClick={onClose}
    >
      <div
        className="glass h-full w-full max-w-xl rounded-l-3xl rounded-r-none p-7 overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">{job.title}</h2>
            <div className="text-slate-400 mt-1">
              {job.company} · {job.city}, {job.state}
            </div>
          </div>
          <button className="btn-ghost !py-1.5 !px-3" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 mt-6">
          <Card className="p-4">
            <div className="text-xs text-slate-400">Salary range</div>
            <div className="text-lg font-semibold text-cyan-300">
              {eur(job.salary_min)} – {eur(job.salary_max)}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-xs text-slate-400">Work type</div>
            <div className="text-lg font-semibold text-white">
              {WORK_TYPE_ICON[job.work_type]} {job.work_type}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-xs text-slate-400">German level</div>
            <div className="text-lg font-semibold text-white">
              {job.german_level === "None" ? "Not required" : job.german_level}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-xs text-slate-400">English level</div>
            <div className="text-lg font-semibold text-white">{job.english_level}</div>
          </Card>
        </div>

        <h3 className="text-sm font-semibold text-white mt-6 mb-2">
          Extracted Skills
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {job.skill_names.map((s) => (
            <SkillTag key={s} name={s} category={skillCategory[s]} />
          ))}
        </div>

        <h3 className="text-sm font-semibold text-white mt-6 mb-2">Description</h3>
        <p className="text-sm text-slate-300 leading-relaxed">{job.description}</p>

        <a
          href={job.source_url}
          target="_blank"
          rel="noreferrer"
          className="btn-primary inline-block mt-6 no-underline"
        >
          Apply / View source ↗
        </a>
        <div className="text-xs text-slate-500 mt-3">
          Posted {job.date_posted} · source: {job.source}
        </div>
      </div>
    </div>
  );
}

export default function JobExplorer() {
  const [filters, setFilters] = useState(null);
  const [skillCategory, setSkillCategory] = useState({});
  const [results, setResults] = useState(null);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [query, setQuery] = useState({
    q: "",
    role: "",
    city: "",
    work_type: "",
    experience_level: "",
    min_german: "",
    skills: [],
    sort: "date",
    order: "desc",
    page: 1,
    page_size: 12,
  });

  // Load filter metadata once (also build skill -> category map).
  useEffect(() => {
    api
      .filters()
      .then((f) => {
        setFilters(f);
        return api.skillDemand(undefined, 50);
      })
      .then((sd) => {
        const map = {};
        sd.forEach((s) => (map[s.skill] = s.category));
        setSkillCategory(map);
      })
      .catch((e) => setError(e.message));
  }, []);

  // Re-fetch jobs whenever the query changes.
  useEffect(() => {
    setLoading(true);
    api
      .listJobs(query)
      .then(setResults)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [query]);

  const update = (patch) => setQuery((q) => ({ ...q, ...patch, page: 1 }));
  const toggleSkill = (skill) =>
    setQuery((q) => ({
      ...q,
      page: 1,
      skills: q.skills.includes(skill)
        ? q.skills.filter((s) => s !== skill)
        : [...q.skills, skill],
    }));

  if (error) return <ErrorState message={error} onRetry={() => location.reload()} />;
  if (!filters) return <Spinner label="Loading filters…" />;

  const popularSkills = [
    "Python", "SQL", "AWS", "Docker", "Kubernetes", "PyTorch",
    "LangChain", "ROS2", "Power BI", "Machine Learning", "LLMs", "Java",
  ].filter((s) => filters.skills.includes(s));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6">
      {/* Filter panel */}
      <aside className="lg:sticky lg:top-28 self-start space-y-4">
        <Card className="p-5 space-y-4">
          <input
            className="field"
            placeholder="🔍 Search title, company…"
            value={query.q}
            onChange={(e) => update({ q: e.target.value })}
          />

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Role</label>
            <select
              className="field"
              value={query.role}
              onChange={(e) => update({ role: e.target.value })}
            >
              <option value="">All roles</option>
              {filters.roles.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">City</label>
            <select
              className="field"
              value={query.city}
              onChange={(e) => update({ city: e.target.value })}
            >
              <option value="">All cities</option>
              {filters.cities.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Work type</label>
            <div className="flex flex-wrap gap-2">
              {filters.work_types.map((w) => (
                <Chip
                  key={w}
                  active={query.work_type === w}
                  onClick={() =>
                    update({ work_type: query.work_type === w ? "" : w })
                  }
                >
                  {WORK_TYPE_ICON[w]} {w}
                </Chip>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">
              Experience level
            </label>
            <div className="flex flex-wrap gap-2">
              {filters.experience_levels.map((x) => (
                <Chip
                  key={x}
                  active={query.experience_level === x}
                  onClick={() =>
                    update({
                      experience_level: query.experience_level === x ? "" : x,
                    })
                  }
                >
                  {x}
                </Chip>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">
              Max German level you accept
            </label>
            <select
              className="field"
              value={query.min_german}
              onChange={(e) => update({ min_german: e.target.value })}
            >
              <option value="">Any</option>
              {["None", "A1", "A2", "B1", "B2", "C1", "C2"].map((g) => (
                <option key={g} value={g}>
                  {g === "None" ? "No German required" : `Up to ${g}`}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">
              Skills {query.skills.length > 0 && `(${query.skills.length})`}
            </label>
            <div className="flex flex-wrap gap-2">
              {popularSkills.map((s) => (
                <Chip
                  key={s}
                  active={query.skills.includes(s)}
                  onClick={() => toggleSkill(s)}
                >
                  {s}
                </Chip>
              ))}
            </div>
          </div>

          <button
            className="btn-ghost w-full"
            onClick={() =>
              setQuery({
                q: "", role: "", city: "", work_type: "", experience_level: "",
                min_german: "", skills: [], sort: "date", order: "desc",
                page: 1, page_size: 12,
              })
            }
          >
            Reset filters
          </button>
        </Card>
      </aside>

      {/* Results */}
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="text-sm text-slate-400">
            {results ? (
              <>
                <span className="text-white font-semibold">{results.total}</span>{" "}
                matching openings
              </>
            ) : (
              "…"
            )}
          </div>
          <div className="flex items-center gap-2">
            <select
              className="field max-w-[160px]"
              value={`${query.sort}:${query.order}`}
              onChange={(e) => {
                const [sort, order] = e.target.value.split(":");
                update({ sort, order });
              }}
            >
              <option value="date:desc">Newest first</option>
              <option value="salary:desc">Salary: high → low</option>
              <option value="salary:asc">Salary: low → high</option>
              <option value="title:asc">Title A–Z</option>
              <option value="company:asc">Company A–Z</option>
            </select>
          </div>
        </div>

        {loading && !results ? (
          <Spinner label="Searching…" />
        ) : results && results.items.length === 0 ? (
          <Card className="p-10 text-center text-slate-400">
            No openings match these filters. Try widening your search.
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {results?.items.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                skillCategory={skillCategory}
                onOpen={setSelected}
              />
            ))}
          </div>
        )}

        {/* Pagination */}
        {results && results.pages > 1 && (
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              className="btn-ghost"
              disabled={query.page <= 1}
              onClick={() => setQuery((q) => ({ ...q, page: q.page - 1 }))}
            >
              ← Prev
            </button>
            <span className="text-sm text-slate-400">
              Page {results.page} of {results.pages}
            </span>
            <button
              className="btn-ghost"
              disabled={query.page >= results.pages}
              onClick={() => setQuery((q) => ({ ...q, page: q.page + 1 }))}
            >
              Next →
            </button>
          </div>
        )}
      </section>

      <JobDrawer
        job={selected}
        skillCategory={skillCategory}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
