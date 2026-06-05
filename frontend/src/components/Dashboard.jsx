import React, { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api.js";
import {
  Card,
  ErrorState,
  SectionTitle,
  Spinner,
  colorFor,
  eur,
  eurShort,
} from "./ui.jsx";

const ROLES = [
  "All Roles",
  "Data Analyst",
  "ML Engineer",
  "Backend Developer",
  "Robotics Engineer",
  "RAG Engineer",
];

const tooltipStyle = {
  background: "rgba(10,14,31,0.95)",
  border: "1px solid rgba(129,140,248,0.4)",
  borderRadius: "0.75rem",
  color: "#e7e9f5",
  fontSize: "0.8rem",
};

function StatCard({ label, value, sub, accent }) {
  return (
    <Card className="p-5 relative overflow-hidden">
      <div
        className="absolute -right-6 -top-6 h-20 w-20 rounded-full blur-2xl opacity-40"
        style={{ background: accent }}
      />
      <div className="text-[0.7rem] uppercase tracking-[0.15em] text-slate-400">
        {label}
      </div>
      <div className="text-3xl font-display font-bold text-white mt-1">{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
    </Card>
  );
}

export default function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [salary, setSalary] = useState([]);
  const [geo, setGeo] = useState([]);
  const [langDemand, setLangDemand] = useState([]);
  const [roleLang, setRoleLang] = useState([]);
  const [skillRole, setSkillRole] = useState("All Roles");
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadCore = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.overview(),
      api.salaryByRole(),
      api.geo(),
      api.languageDemand(),
      api.roleLanguage(),
    ])
      .then(([o, s, g, l, rl]) => {
        setOverview(o);
        setSalary(s);
        setGeo(g);
        setLangDemand(l);
        setRoleLang(rl);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadCore, []);

  useEffect(() => {
    const role = skillRole === "All Roles" ? undefined : skillRole;
    api.skillDemand(role, 15).then(setSkills).catch(() => setSkills([]));
  }, [skillRole]);

  const langPieData = useMemo(
    () =>
      langDemand.map((d) => ({
        name: d.german_level === "None" ? "No German" : `German ${d.german_level}`,
        value: d.count,
        level: d.german_level,
      })),
    [langDemand]
  );

  if (loading) return <Spinner label="Crunching the German job market…" />;
  if (error) return <ErrorState message={error} onRetry={loadCore} />;

  const LANG_COLORS = [
    "#475569", "#34d399", "#22d3ee", "#818cf8", "#a78bfa", "#fbbf24", "#fb7185",
  ];

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="glass rounded-3xl p-7 relative overflow-hidden">
        <div className="absolute inset-0 opacity-60 accent-bar h-1 top-0 bottom-auto" />
        <h1 className="text-3xl md:text-4xl font-bold text-white max-w-2xl">
          The German tech job market, <span className="gradient-text">decoded</span>.
        </h1>
        <p className="text-slate-400 mt-3 max-w-2xl">
          Live analytics across {overview.total_jobs} curated openings from{" "}
          {overview.total_companies} employers in Germany's five biggest tech hubs.
          Track skill demand, salary benchmarks and language requirements in real time.
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Open Positions"
          value={overview.total_jobs}
          sub={`${overview.total_companies} companies`}
          accent="#6366f1"
        />
        <StatCard
          label="Avg. Salary"
          value={eur(overview.avg_salary)}
          sub="across all roles"
          accent="#06b6d4"
        />
        <StatCard
          label="Remote Share"
          value={`${overview.remote_share_pct}%`}
          sub="fully remote roles"
          accent="#34d399"
        />
        <StatCard
          label="Require German"
          value={`${overview.german_required_pct}%`}
          sub="A1–C2 expected"
          accent="#fbbf24"
        />
      </div>

      {/* Skill demand */}
      <Card className="p-6">
        <SectionTitle
          eyebrow="Demand Signal"
          title="Top 15 Demanded Skills"
          subtitle="Share of postings mentioning each skill"
          right={
            <select
              className="field max-w-[200px]"
              value={skillRole}
              onChange={(e) => setSkillRole(e.target.value)}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          }
        />
        <ResponsiveContainer width="100%" height={420}>
          <BarChart
            data={skills}
            layout="vertical"
            margin={{ left: 20, right: 40 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              type="number"
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              unit="%"
            />
            <YAxis
              type="category"
              dataKey="skill"
              width={130}
              tick={{ fill: "#cbd5e1", fontSize: 12 }}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v, n, p) => [`${v}% (${p.payload.count} jobs)`, "Demand"]}
              cursor={{ fill: "rgba(129,140,248,0.08)" }}
            />
            <Bar dataKey="percentage" radius={[0, 6, 6, 0]} barSize={18}>
              {skills.map((s, i) => (
                <Cell key={i} fill={colorFor(s.category, i)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Salary by role */}
        <Card className="p-6">
          <SectionTitle
            eyebrow="Compensation"
            title="Average Salary by Role"
            subtitle="EUR per year, gross"
          />
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={salary} margin={{ left: 10, right: 10 }}>
              <defs>
                <linearGradient id="salGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#818cf8" />
                  <stop offset="100%" stopColor="#06b6d4" />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="role"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                interval={0}
                angle={-12}
                textAnchor="end"
                height={60}
              />
              <YAxis
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                tickFormatter={eurShort}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v) => [eur(v), "Avg salary"]}
                cursor={{ fill: "rgba(129,140,248,0.08)" }}
              />
              <Bar dataKey="avg_salary" fill="url(#salGrad)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Language demand pie */}
        <Card className="p-6">
          <SectionTitle
            eyebrow="Language"
            title="German Level Requirements"
            subtitle="Distribution across all openings"
          />
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie
                data={langPieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={110}
                paddingAngle={3}
                label={(e) => e.name}
                labelLine={false}
                fontSize={11}
              >
                {langPieData.map((e, i) => (
                  <Cell key={i} fill={LANG_COLORS[i % LANG_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v) => [`${v} jobs`, "Count"]}
              />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Geo distribution */}
        <Card className="p-6">
          <SectionTitle
            eyebrow="Geography"
            title="Openings by City"
            subtitle="Hub comparison with avg. salary"
          />
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={geo} margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="city" tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ fill: "rgba(129,140,248,0.08)" }}
                formatter={(v, n, p) =>
                  n === "count"
                    ? [`${v} jobs`, "Openings"]
                    : [eur(p.payload.avg_salary), "Avg salary"]
                }
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]} barSize={46}>
                {geo.map((g, i) => (
                  <Cell key={i} fill={colorFor(null, i)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Role vs language radar */}
        <Card className="p-6">
          <SectionTitle
            eyebrow="Correlation"
            title="German Requirement by Role"
            subtitle="% of postings needing B1+ German"
          />
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={roleLang} outerRadius={110}>
              <PolarGrid stroke="rgba(255,255,255,0.12)" />
              <PolarAngleAxis
                dataKey="role"
                tick={{ fill: "#cbd5e1", fontSize: 11 }}
              />
              <Radar
                name="Requires German B1+"
                dataKey="requires_german_pct"
                stroke="#22d3ee"
                fill="#22d3ee"
                fillOpacity={0.35}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v) => [`${v}%`, "Requires German"]}
              />
              <Legend wrapperStyle={{ fontSize: "0.75rem", color: "#94a3b8" }} />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
