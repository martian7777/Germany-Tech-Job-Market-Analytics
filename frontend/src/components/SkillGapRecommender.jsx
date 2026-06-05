import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Card, Chip, ErrorState, Spinner, colorFor, eur } from "./ui.jsx";

const GERMAN_LEVELS = ["None", "A1", "A2", "B1", "B2", "C1", "C2"];
const IMPORTANCE_STYLE = {
  Critical: { color: "#fb7185", bg: "rgba(251,113,133,0.14)" },
  Important: { color: "#fbbf24", bg: "rgba(251,191,36,0.14)" },
  "Nice to have": { color: "#94a3b8", bg: "rgba(148,163,184,0.14)" },
};

function ScoreRing({ score }) {
  const r = 54;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  const hue = score >= 70 ? "#34d399" : score >= 40 ? "#fbbf24" : "#fb7185";
  return (
    <div className="relative h-36 w-36 shrink-0">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" />
        <circle
          cx="60" cy="60" r={r} fill="none" stroke={hue} strokeWidth="10"
          strokelinecap="round" strokeDasharray={c} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.9s cubic-bezier(0.2,0.8,0.2,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-3xl font-display font-bold text-white">{score}%</div>
        <div className="text-[0.65rem] uppercase tracking-wide text-slate-400">Match</div>
      </div>
    </div>
  );
}

function GapBar({ item }) {
  const style = IMPORTANCE_STYLE[item.importance];
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-200 font-medium">{item.skill}</span>
        <span
          className="text-[0.68rem] font-semibold px-2 py-0.5 rounded-full"
          style={{ color: style.color, background: style.bg }}
        >
          {item.importance} · {item.market_demand_pct}%
        </span>
      </div>
      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${item.market_demand_pct}%`,
            background: `linear-gradient(90deg, ${colorFor(item.category)}, ${style.color})`,
          }}
        />
      </div>
    </div>
  );
}

export default function SkillGapRecommender() {
  const [roles, setRoles] = useState([]);
  const [allSkills, setAllSkills] = useState([]);
  const [cities, setCities] = useState([]);
  const [role, setRole] = useState("");
  const [skills, setSkills] = useState([]);
  const [skillInput, setSkillInput] = useState("");
  const [german, setGerman] = useState("None");
  const [prefCities, setPrefCities] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.recommendRoles(), api.filters()])
      .then(([r, f]) => {
        setRoles(r);
        setRole(r[0]);
        setAllSkills(f.skills.filter((s) => !s.endsWith("Language")));
        setCities(f.cities);
      })
      .catch((e) => setError(e.message));
  }, []);

  const addSkill = (s) => {
    const v = s.trim();
    if (v && !skills.includes(v)) setSkills([...skills, v]);
    setSkillInput("");
  };
  const removeSkill = (s) => setSkills(skills.filter((x) => x !== s));
  const toggleCity = (c) =>
    setPrefCities((p) => (p.includes(c) ? p.filter((x) => x !== c) : [...p, c]));

  const analyze = () => {
    setLoading(true);
    setError(null);
    api
      .recommend({
        target_role: role,
        skills,
        german_level: german,
        preferred_cities: prefCities,
      })
      .then(setResult)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const suggestions = allSkills
    .filter(
      (s) =>
        skillInput &&
        s.toLowerCase().includes(skillInput.toLowerCase()) &&
        !skills.includes(s)
    )
    .slice(0, 6);

  if (error) return <ErrorState message={error} onRetry={() => setError(null)} />;
  if (roles.length === 0) return <Spinner label="Loading recommender…" />;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
      {/* Profile form */}
      <Card className="p-6 space-y-5 lg:sticky lg:top-28 self-start">
        <div>
          <h2 className="text-xl font-bold text-white">Build your profile</h2>
          <p className="text-sm text-slate-400 mt-1">
            We'll benchmark you against live market demand.
          </p>
        </div>

        <div>
          <label className="text-xs text-slate-400 mb-1 block">Target role</label>
          <select className="field" value={role} onChange={(e) => setRole(e.target.value)}>
            {roles.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-slate-400 mb-1 block">Your skills</label>
          <div className="relative">
            <input
              className="field"
              placeholder="Type a skill, e.g. Python…"
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addSkill(suggestions[0] || skillInput);
                }
              }}
            />
            {suggestions.length > 0 && (
              <div className="absolute z-10 mt-1 w-full glass rounded-xl p-1.5 space-y-0.5">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    className="block w-full text-left px-3 py-1.5 rounded-lg text-sm text-slate-200 hover:bg-white/10"
                    onClick={() => addSkill(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {skills.map((s) => (
              <span key={s} className="chip chip-active">
                {s}
                <button className="ml-1 opacity-80 hover:opacity-100" onClick={() => removeSkill(s)}>
                  ✕
                </button>
              </span>
            ))}
            {skills.length === 0 && (
              <span className="text-xs text-slate-500">No skills added yet.</span>
            )}
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-400 mb-1 block">
            Current German level
          </label>
          <div className="flex flex-wrap gap-2">
            {GERMAN_LEVELS.map((g) => (
              <Chip key={g} active={german === g} onClick={() => setGerman(g)}>
                {g === "None" ? "None" : g}
              </Chip>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-400 mb-1 block">
            Preferred cities (optional)
          </label>
          <div className="flex flex-wrap gap-2">
            {cities.map((c) => (
              <Chip key={c} active={prefCities.includes(c)} onClick={() => toggleCity(c)}>
                {c}
              </Chip>
            ))}
          </div>
        </div>

        <button className="btn-primary w-full" onClick={analyze} disabled={loading}>
          {loading ? "Analyzing…" : "Analyze my fit →"}
        </button>
      </Card>

      {/* Results */}
      <section>
        {loading ? (
          <Spinner label="Computing your skill gap…" />
        ) : !result ? (
          <Card className="p-10 text-center">
            <div className="text-5xl mb-3">🎯</div>
            <h3 className="text-lg font-semibold text-white">
              Your personalized gap analysis appears here
            </h3>
            <p className="text-sm text-slate-400 mt-2 max-w-md mx-auto">
              Pick a target role, add the skills you already have and your German
              level. We'll score your market fit, surface the highest-impact skills
              to learn next, and recommend matching openings.
            </p>
          </Card>
        ) : (
          <div className="space-y-6">
            {/* Score + summary */}
            <Card className="p-6 flex flex-col sm:flex-row items-center gap-6">
              <ScoreRing score={result.match_score} />
              <div>
                <div className="text-xs uppercase tracking-[0.15em] text-cyan-300/80">
                  {result.target_role}
                </div>
                <p className="text-slate-200 mt-1 leading-relaxed">{result.summary}</p>
                {result.have_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {result.have_skills.map((s) => (
                      <span key={s} className="chip">✓ {s}</span>
                    ))}
                  </div>
                )}
              </div>
            </Card>

            {/* Language fit */}
            <Card
              className="p-5 border-l-4"
              style={{
                borderLeftColor: result.language_fit.is_sufficient
                  ? "#34d399"
                  : "#fbbf24",
              }}
            >
              <div className="flex items-start gap-3">
                <div className="text-2xl">
                  {result.language_fit.is_sufficient ? "✅" : "🗣️"}
                </div>
                <div>
                  <div className="font-semibold text-white">
                    Language Fit ·{" "}
                    <span
                      className={
                        result.language_fit.is_sufficient
                          ? "text-emerald-300"
                          : "text-amber-300"
                      }
                    >
                      {result.language_fit.is_sufficient ? "On track" : "Gap detected"}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300 mt-1">
                    {result.language_fit.message}
                  </p>
                  {result.language_fit.recommended_action && (
                    <p className="text-sm text-amber-200/90 mt-1">
                      💡 {result.language_fit.recommended_action}
                    </p>
                  )}
                </div>
              </div>
            </Card>

            {/* Missing skills */}
            <Card className="p-6">
              <h3 className="font-bold text-white mb-1">
                Skill gaps ranked by market demand
              </h3>
              <p className="text-sm text-slate-400 mb-4">
                Bars show how often each skill appears in {result.target_role} postings.
              </p>
              {result.missing_skills.length === 0 ? (
                <div className="text-sm text-emerald-300">
                  🎉 No major gaps — you cover the in-demand skills for this role.
                </div>
              ) : (
                <div className="space-y-4">
                  {result.missing_skills.map((m) => (
                    <GapBar key={m.skill} item={m} />
                  ))}
                </div>
              )}
            </Card>

            {/* Recommended jobs */}
            <Card className="p-6">
              <h3 className="font-bold text-white mb-4">
                Recommended openings for you
              </h3>
              <div className="space-y-3">
                {result.recommended_jobs.map((j) => (
                  <div
                    key={j.id}
                    className="rounded-xl border border-white/8 bg-white/[0.03] p-4 flex flex-col sm:flex-row sm:items-center gap-3"
                  >
                    <div className="flex-1">
                      <div className="font-semibold text-white">{j.title}</div>
                      <div className="text-sm text-slate-400">
                        {j.company} · {j.city} · {j.work_type} · {eur(j.salary_avg)}
                      </div>
                      {j.matched_skills.length > 0 && (
                        <div className="text-xs text-emerald-300/90 mt-1">
                          Matches: {j.matched_skills.join(", ")}
                        </div>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-2xl font-display font-bold gradient-text">
                        {j.match_pct}%
                      </div>
                      <div className="text-[0.65rem] text-slate-500 uppercase">
                        skill match
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
      </section>
    </div>
  );
}
