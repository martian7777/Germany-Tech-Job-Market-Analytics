// Small shared UI primitives reused across the app.
import React from "react";

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-400">
      <div className="h-9 w-9 rounded-full border-2 border-indigo-400/30 border-t-indigo-400 animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="glass rounded-2xl p-8 text-center">
      <div className="text-rose-300 font-semibold mb-2">Something went wrong</div>
      <p className="text-sm text-slate-400 mb-4">{message}</p>
      {onRetry && (
        <button className="btn-ghost" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function Card({ children, className = "", style }) {
  return (
    <div className={`glass glass-hover rounded-2xl ${className}`} style={style}>
      {children}
    </div>
  );
}

export function SectionTitle({ eyebrow, title, subtitle, right }) {
  return (
    <div className="flex items-end justify-between gap-4 mb-5">
      <div>
        {eyebrow && (
          <div className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-cyan-300/80 mb-1">
            {eyebrow}
          </div>
        )}
        <h2 className="text-xl font-bold text-white">{title}</h2>
        {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Chip({ active, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`chip ${active ? "chip-active" : ""}`}
    >
      {children}
    </button>
  );
}

// Currency formatting for EUR salaries.
export function eur(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function eurShort(value) {
  return `€${Math.round(value / 1000)}k`;
}

// Category -> accent color for skill chips and charts.
export const CATEGORY_COLORS = {
  Programming: "#818cf8",
  Data: "#22d3ee",
  BI: "#34d399",
  Cloud: "#fbbf24",
  DevOps: "#f472b6",
  "ML/AI": "#a78bfa",
  GenAI: "#67e8f9",
  Backend: "#60a5fa",
  Robotics: "#fb7185",
  Language: "#fcd34d",
  Soft: "#94a3b8",
};

export function colorFor(category, i = 0) {
  const fallback = ["#818cf8", "#22d3ee", "#34d399", "#fbbf24", "#fb7185", "#a78bfa"];
  return CATEGORY_COLORS[category] || fallback[i % fallback.length];
}
