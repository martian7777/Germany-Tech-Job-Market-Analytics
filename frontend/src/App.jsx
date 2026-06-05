import React, { useEffect, useState } from "react";
import Dashboard from "./components/Dashboard.jsx";
import JobExplorer from "./components/JobExplorer.jsx";
import SkillGapRecommender from "./components/SkillGapRecommender.jsx";
import BIReports from "./components/BIReports.jsx";
import { api } from "./api.js";

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: "📊", el: Dashboard },
  { id: "explorer", label: "Job Explorer", icon: "🔍", el: JobExplorer },
  { id: "recommender", label: "Skill Gap", icon: "🎯", el: SkillGapRecommender },
  { id: "reports", label: "BI Reports", icon: "📁", el: BIReports },
];

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [online, setOnline] = useState(null);

  useEffect(() => {
    api
      .health()
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
  }, []);

  const Active = TABS.find((t) => t.id === tab).el;

  return (
    <div className="min-h-screen">
      {/* Top navigation */}
      <header className="sticky top-0 z-40">
        <div className="glass border-x-0 border-t-0 rounded-none">
          <div className="mx-auto max-w-7xl px-5 py-3 flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl accent-bar flex items-center justify-center font-display font-bold text-white text-lg shadow-lg">
                D
              </div>
              <div className="leading-tight">
                <div className="font-display font-bold text-white text-lg">
                  DeTech<span className="gradient-text"> Jobs</span>
                </div>
                <div className="text-[0.65rem] uppercase tracking-[0.2em] text-slate-400">
                  German Market Analytics
                </div>
              </div>
            </div>

            <nav className="ml-auto hidden md:flex items-center gap-1">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    tab === t.id
                      ? "bg-white/10 text-white shadow-inner border border-white/10"
                      : "text-slate-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <span className="mr-1.5">{t.icon}</span>
                  {t.label}
                </button>
              ))}
            </nav>

            <div className="ml-auto md:ml-2 flex items-center gap-2 text-xs">
              <span
                className={`h-2 w-2 rounded-full ${
                  online === null
                    ? "bg-amber-400"
                    : online
                    ? "bg-emerald-400 shadow-[0_0_8px_2px_rgba(52,211,153,0.6)]"
                    : "bg-rose-500"
                }`}
              />
              <span className="text-slate-400 hidden sm:inline">
                {online === null ? "Connecting" : online ? "API Online" : "API Offline"}
              </span>
            </div>
          </div>

          {/* Mobile tab bar */}
          <nav className="md:hidden flex items-center gap-1 px-3 pb-3 overflow-x-auto">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`whitespace-nowrap px-3 py-1.5 rounded-lg text-xs font-medium ${
                  tab === t.id ? "bg-white/10 text-white" : "text-slate-400"
                }`}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8">
        {online === false && (
          <div className="glass rounded-2xl p-4 mb-6 border-rose-400/30 text-sm text-rose-200">
            ⚠️ Cannot reach the backend API. Start it with{" "}
            <code className="px-1.5 py-0.5 rounded bg-black/40 text-rose-100">
              uvicorn app.main:app --port 8000
            </code>{" "}
            inside <code className="px-1 rounded bg-black/40">backend/</code>.
          </div>
        )}
        <div key={tab} className="animate-fade-up">
          <Active />
        </div>
      </main>

      <footer className="mx-auto max-w-7xl px-5 py-8 text-center text-xs text-slate-500">
        DeTech Jobs Analytics · Berlin · Munich · Hamburg · Frankfurt · Stuttgart ·
        Built with FastAPI + React + Tailwind v4
      </footer>
    </div>
  );
}
