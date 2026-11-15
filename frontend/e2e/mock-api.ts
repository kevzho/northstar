/**
 * A signed-in student with no real backend behind them.
 *
 * The suite runs against `next build` with the same placeholder env CI uses,
 * so every Supabase and API request is answered here instead. The session is
 * planted in localStorage under the key supabase-js derives from the project
 * URL (sb-<ref>-auth-token); getUser() then asks /auth/v1/user, which this
 * answers too. Nothing leaves the machine and no real account is touched.
 *
 * The fixture text is deliberately long in places. Phone layouts break on the
 * long title and the unbroken host name, not on "Test Program".
 */
import type { Page, Route } from "@playwright/test";

export const SUPABASE = "https://placeholder.supabase.co";
export const API = "http://localhost:8000";

const USER = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "student@example.com",
  aud: "authenticated",
  role: "authenticated",
  app_metadata: { provider: "email" },
  user_metadata: {},
  created_at: "2026-09-01T00:00:00Z",
};

const SESSION = {
  access_token: "e2e-access-token",
  refresh_token: "e2e-refresh-token",
  token_type: "bearer",
  expires_in: 3600,
  // 2100-01-01: never refreshed during a run.
  expires_at: 4102444800,
  user: USER,
};

export const PROFILE = {
  id: USER.id,
  email: USER.email,
  name: "Avery Student",
  grade: "10",
  interests: ["biology", "cs"],
  goals: "Find a summer research program and build something with data.",
  audience: "high_school",
  location_pref: "either",
  onboarded: true,
  consented_at: "2026-09-01T00:00:00Z",
  handle: null,
  public_profile: false,
  social_links: null,
  trait_scores: { builder: 0.7, analyst: 0.8, connector: 0.4, risk: 0.5 },
  field_scores: { biology: 0.9, cs: 0.7, math: 0.4 },
};

function opportunity(i: number, overrides: Record<string, unknown> = {}) {
  return {
    id: `00000000-0000-4000-8000-00000000000${i}`,
    title: `Opportunity ${i}`,
    host: "Example Host",
    field: "biology",
    type: "program",
    blurb: "A short description of what a student does here.",
    description: "A longer description of the opportunity for the detail page.",
    deadline: "2027-03-01",
    cost: 0,
    grade_min: 9,
    grade_max: 12,
    url: `https://example.org/opportunity-${i}`,
    tags: ["research", "summer"],
    location: null,
    location_scope: "us",
    entry_gate: "apply",
    entry_note: null,
    state: null,
    ...overrides,
  };
}

export const OPPORTUNITIES = [
  opportunity(1, {
    title: "Summer Science Research Fellowship for Rising Juniors and Seniors in Computational Biology",
    host: "InternationalComputationalBiologyConsortiumFoundation",
    blurb:
      "Six weeks in a university lab pairing wet-lab genomics with Python analysis, ending in a poster session judged by faculty.",
  }),
  opportunity(2, {
    title: "Regional Science and Engineering Fair",
    field: "interdisciplinary",
    type: "competition",
    entry_gate: "advance",
    entry_note: "Qualify through your school fair first.",
    deadline: "2027-02-01",
  }),
  opportunity(3, { title: "Open-Source Data Science Mentorship", field: "cs", type: "mentorship", deadline: null }),
  opportunity(4, { title: "Community Health Volunteer Corps", field: "health", type: "volunteer", cost: 150 }),
  opportunity(5, { title: "Youth Bioinformatics Hackathon", field: "cs", type: "competition", deadline: "2026-12-05" }),
  opportunity(6, { title: "Student Journal of Life Sciences", field: "biology", type: "journal", deadline: null }),
];

export const MATCHES = OPPORTUNITIES.map((opp, i) => ({
  opportunity: opp,
  score: {
    opportunity_id: opp.id,
    score: 0.9 - i * 0.1,
    explanation: `Matches your interest in ${opp.field} and your grade.`,
  },
}));

function step(i: number, phase: number, overrides: Record<string, unknown> = {}) {
  return {
    category: "skill",
    title: `Step ${i}`,
    step_key: `step-${i}`,
    edge_reason: "ladder",
    edge_note: "Builds the skill the next step assumes.",
    opportunity_id: null,
    resource_id: null,
    mission_id: null,
    timeframe: "week",
    due_in_months: phase + 1,
    phase_index: phase,
    phase_label: phase === 0 ? "This month" : "Next three months",
    ordinal: i,
    ...overrides,
  };
}

export const ROADMAP = {
  horizon_months: 18,
  grade: 10,
  phases: [
    {
      label: "This month",
      steps: [
        step(1, 0, { title: "Learn Python basics with a genomics dataset" }),
        step(2, 0, { category: "project", title: "Analyse a public gene-expression dataset and write it up" }),
      ],
    },
    {
      label: "Next three months",
      steps: [
        step(3, 1, { category: "outreach", title: "Email two lab coordinators about summer openings" }),
        step(4, 1, {
          category: "application",
          title: OPPORTUNITIES[0].title,
          opportunity_id: OPPORTUNITIES[0].id,
          edge_reason: "window",
          edge_note: "Applications open in January.",
        }),
      ],
    },
  ],
  horizon: [
    {
      title: "Research Science Institute",
      opens_at_grade: 11,
      opportunity_id: "00000000-0000-4000-8000-000000000099",
      edge_reason: "eligibility",
      edge_note: "Open to rising seniors.",
    },
  ],
  notes: { dated_steps: 1, authored_edges: 2, outcomes_logged: 0 },
  archetype_id: "researcher",
  has_spine: true,
  resource_count: 3,
  spine_source: "authored",
  spine_hollow: false,
};

export const PATHWAYS = {
  nodes: OPPORTUNITIES.map((o, i) => ({
    id: o.id,
    title: o.title,
    field: o.field,
    type: o.type,
    score: 0.9 - i * 0.1,
    deadline: o.deadline,
    tags: o.tags,
  })),
  edges: [{ source: OPPORTUNITIES[0].id, target: OPPORTUNITIES[5].id, weight: 0.5 }],
};

type Handler = (route: Route) => unknown;

/** Answer every request to the placeholder Supabase project and the API. */
export async function mockBackend(
  page: Page,
  { signedIn = true, overrides = {} }: { signedIn?: boolean; overrides?: Record<string, Handler> } = {},
): Promise<string[]> {
  const unmocked: string[] = [];

  if (signedIn) {
    await page.addInitScript(
      (session) => localStorage.setItem("sb-placeholder-auth-token", JSON.stringify(session)),
      SESSION,
    );
  }

  await page.route(`${SUPABASE}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/auth/v1/user") {
      return signedIn
        ? route.fulfill({ json: USER })
        : route.fulfill({ status: 401, json: { message: "no session" } });
    }
    if (path.startsWith("/rest/v1/")) return route.fulfill({ json: [] });
    return route.fulfill({ json: {} });
  });

  const handlers: Record<string, Handler> = {
    "GET /me": (r) => r.fulfill({ json: PROFILE }),
    "GET /match": (r) => r.fulfill({ json: MATCHES }),
    "GET /roadmap": (r) => r.fulfill({ json: ROADMAP }),
    "GET /pathways": (r) => r.fulfill({ json: PATHWAYS }),
    "GET /timeline": (r) => r.fulfill({ json: [] }),
    "GET /bookmarks": (r) => r.fulfill({ json: [] }),
    "GET /dismissals": (r) => r.fulfill({ json: [] }),
    "GET /outcomes": (r) => r.fulfill({ json: [] }),
    "GET /missions": (r) => r.fulfill({ json: [] }),
    "GET /missions/completions": (r) => r.fulfill({ json: [] }),
    "GET /catalog": (r) => r.fulfill({ json: OPPORTUNITIES }),
    "GET /catalog/public": (r) => r.fulfill({ json: OPPORTUNITIES }),
    "GET /resources": (r) => r.fulfill({ json: [] }),
    "POST /assessment-profile": (r) => r.fulfill({ json: { ok: true } }),
    "POST /chosen-path": (r) => r.fulfill({ json: { ok: true } }),
    ...overrides,
  };

  await page.route(`${API}/**`, (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const key = `${request.method()} ${path}`;
    const handler = handlers[key];
    if (handler) return handler(route);
    const detail = /^\/opportunities\/([0-9a-f-]+)$/.exec(path);
    if (request.method() === "GET" && detail) {
      const opp = OPPORTUNITIES.find((o) => o.id === detail[1]);
      return opp
        ? route.fulfill({ json: opp })
        : route.fulfill({ status: 404, json: { detail: "Opportunity not found" } });
    }
    unmocked.push(key);
    return route.fulfill({ status: 404, json: { detail: `unmocked in e2e: ${key}` } });
  });

  return unmocked;
}
