// Thin API client for the DeTech Jobs Analytics backend.
// In dev, Vite proxies /api to the FastAPI server (see vite.config.js).

const BASE = import.meta.env.VITE_API_BASE || "";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

function qs(params) {
  const sp = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    if (Array.isArray(v)) v.forEach((item) => sp.append(k, item));
    else sp.append(k, v);
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => request("/api/health"),

  // Jobs
  listJobs: (params) => request(`/api/jobs${qs(params)}`),
  getJob: (id) => request(`/api/jobs/${id}`),
  filters: () => request("/api/jobs/filters"),

  // Analytics
  overview: () => request("/api/analytics/overview"),
  skillDemand: (role, limit = 15) =>
    request(`/api/analytics/skill-demand${qs({ role, limit })}`),
  salaryByRole: () => request("/api/analytics/salary-by-role"),
  geo: () => request("/api/analytics/geo"),
  languageDemand: () => request("/api/analytics/language-demand"),
  roleLanguage: () => request("/api/analytics/role-language"),

  // Recommender
  recommendRoles: () => request("/api/recommender/roles"),
  recommend: (payload) =>
    request("/api/recommender", { method: "POST", body: JSON.stringify(payload) }),
};

export { qs };
