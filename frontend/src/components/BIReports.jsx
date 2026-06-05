import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Card, ErrorState, SectionTitle, Spinner, eur } from "./ui.jsx";

// Flatten a job posting into a single BI-friendly row (skills pipe-joined).
function toFlatRow(job) {
  return {
    id: job.id,
    title: job.title,
    company: job.company,
    city: job.city,
    state: job.state,
    role_category: job.role_category,
    experience_level: job.experience_level,
    work_type: job.work_type,
    salary_min: job.salary_min,
    salary_max: job.salary_max,
    salary_avg: job.salary_avg,
    salary_currency: job.salary_currency,
    german_level: job.german_level,
    english_level: job.english_level,
    date_posted: job.date_posted,
    skills: job.skill_names.join("|"),
    skill_count: job.skill_names.length,
    source: job.source,
    source_url: job.source_url,
  };
}

function toCSV(rows) {
  if (rows.length === 0) return "";
  const headers = Object.keys(rows[0]);
  const escape = (v) => {
    const s = String(v ?? "");
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [headers.join(",")];
  rows.forEach((r) => lines.push(headers.map((h) => escape(r[h])).join(",")));
  return lines.join("\r\n");
}

// A long-format skills fact table for star-schema modeling in Power BI / Tableau.
function toSkillFactRows(jobs) {
  const rows = [];
  jobs.forEach((j) =>
    j.skill_names.forEach((s) =>
      rows.push({
        job_id: j.id,
        skill: s,
        role_category: j.role_category,
        city: j.city,
        salary_avg: j.salary_avg,
      })
    )
  );
  return rows;
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function ExportTile({ icon, title, desc, actions }) {
  return (
    <Card className="p-6">
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="font-semibold text-white">{title}</h3>
      <p className="text-sm text-slate-400 mt-1 mb-4">{desc}</p>
      <div className="flex flex-wrap gap-2">{actions}</div>
    </Card>
  );
}

const PBI_STEPS = [
  ["Get Data → Text/CSV", "In Power BI Desktop, choose Home → Get Data → Text/CSV and select the exported jobs file. Confirm comma delimiter and UTF-8 encoding."],
  ["Load both tables", "Import jobs_export.csv (your dimension/fact) and skills_fact.csv (long-format). The skills file has one row per job-skill pair."],
  ["Model relationships", "In Model view, create a 1-to-many relationship from jobs_export[id] → skills_fact[job_id]. This enables drill-down from any job into its skills."],
  ["Build measures", "Add DAX measures, e.g. Avg Salary = AVERAGE(jobs_export[salary_avg]) and Skill Demand % = DIVIDE(DISTINCTCOUNT(skills_fact[job_id]), [Total Jobs])."],
  ["Visualize", "Use a Matrix (role × skill), a Map on city, and a Bar chart of avg salary by role. Slice by german_level and work_type for instant insights."],
];

export default function BIReports() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    // Pull the full dataset (single large page) for export.
    api
      .listJobs({ page: 1, page_size: 100, sort: "date", order: "desc" })
      .then(async (first) => {
        let items = [...first.items];
        for (let p = 2; p <= first.pages; p++) {
          const next = await api.listJobs({ page: p, page_size: 100 });
          items = items.concat(next.items);
        }
        setJobs(items);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Preparing your dataset…" />;
  if (error) return <ErrorState message={error} onRetry={() => location.reload()} />;

  const flatRows = jobs.map(toFlatRow);
  const skillRows = toSkillFactRows(jobs);
  const stamp = new Date().toISOString().slice(0, 10);

  return (
    <div className="space-y-8">
      <div className="glass rounded-3xl p-7">
        <SectionTitle
          eyebrow="Business Intelligence"
          title="Export & Reporting Center"
          subtitle={`${jobs.length} job records ready for Power BI, Tableau or your warehouse.`}
        />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-2">
          <div>
            <div className="text-2xl font-bold gradient-text">{jobs.length}</div>
            <div className="text-xs text-slate-400">Job rows</div>
          </div>
          <div>
            <div className="text-2xl font-bold gradient-text">{skillRows.length}</div>
            <div className="text-xs text-slate-400">Skill-fact rows</div>
          </div>
          <div>
            <div className="text-2xl font-bold gradient-text">
              {new Set(jobs.map((j) => j.company)).size}
            </div>
            <div className="text-xs text-slate-400">Companies</div>
          </div>
          <div>
            <div className="text-2xl font-bold gradient-text">
              {eur(Math.round(flatRows.reduce((a, r) => a + r.salary_avg, 0) / (flatRows.length || 1)))}
            </div>
            <div className="text-xs text-slate-400">Avg salary</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <ExportTile
          icon="📄"
          title="Jobs — CSV"
          desc="Flat, one row per job. Skills pipe-joined. Ideal as the main Power BI table."
          actions={
            <button
              className="btn-primary"
              onClick={() =>
                download(`jobs_export_${stamp}.csv`, toCSV(flatRows), "text/csv;charset=utf-8")
              }
            >
              ⬇ Download CSV
            </button>
          }
        />
        <ExportTile
          icon="🧩"
          title="Skills Fact — CSV"
          desc="Long format, one row per job-skill pair. Use as a fact table in a star schema."
          actions={
            <button
              className="btn-primary"
              onClick={() =>
                download(`skills_fact_${stamp}.csv`, toCSV(skillRows), "text/csv;charset=utf-8")
              }
            >
              ⬇ Download CSV
            </button>
          }
        />
        <ExportTile
          icon="{ }"
          title="Full dataset — JSON"
          desc="Nested JSON with the complete skill arrays. Great for APIs and notebooks."
          actions={
            <button
              className="btn-primary"
              onClick={() =>
                download(
                  `jobs_dataset_${stamp}.json`,
                  JSON.stringify(jobs, null, 2),
                  "application/json"
                )
              }
            >
              ⬇ Download JSON
            </button>
          }
        />
      </div>

      {/* Power BI guide */}
      <Card className="p-6">
        <SectionTitle
          eyebrow="Guide"
          title="Importing into Power BI"
          subtitle="Five steps from CSV to an interactive star-schema report."
        />
        <ol className="space-y-4">
          {PBI_STEPS.map(([head, body], i) => (
            <li key={i} className="flex gap-4">
              <div className="h-8 w-8 shrink-0 rounded-lg accent-bar flex items-center justify-center font-bold text-white">
                {i + 1}
              </div>
              <div>
                <div className="font-semibold text-white">{head}</div>
                <p className="text-sm text-slate-400 mt-0.5">{body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Card>

      {/* Preview table */}
      <Card className="p-6 overflow-x-auto">
        <SectionTitle
          eyebrow="Preview"
          title="Dataset preview"
          subtitle="First 8 rows of the flat export"
        />
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-white/10">
              {["Title", "Company", "City", "Role", "Salary avg", "German", "Skills"].map((h) => (
                <th key={h} className="py-2 pr-4 font-medium whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {flatRows.slice(0, 8).map((r) => (
              <tr key={r.id} className="border-b border-white/5">
                <td className="py-2 pr-4 text-slate-200 whitespace-nowrap">{r.title}</td>
                <td className="py-2 pr-4 text-slate-300">{r.company}</td>
                <td className="py-2 pr-4 text-slate-300">{r.city}</td>
                <td className="py-2 pr-4 text-slate-300">{r.role_category}</td>
                <td className="py-2 pr-4 text-cyan-300">{eur(r.salary_avg)}</td>
                <td className="py-2 pr-4 text-slate-300">{r.german_level}</td>
                <td className="py-2 pr-4 text-slate-500 max-w-[260px] truncate">{r.skills}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
