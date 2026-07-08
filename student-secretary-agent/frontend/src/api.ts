// Typed client for the Campus FastAPI (campus.api.server). In dev, Vite proxies
// these paths to http://localhost:8000; in prod, serve dist/ behind the API origin.

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function jget<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return (await r.json()) as T;
}

async function jpost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return (await r.json()) as T;
}

async function jdel<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return (await r.json()) as T;
}

export interface DemoBResult {
  ok: boolean;
  run_dir: string;
  final_status: string;
  extraction_rate: number;
  kg_nodes: number;
  resource_count: number;
  plan_days: number;
}
export interface DemoAResult {
  ok: boolean;
  mode: string;
  run_dir: string;
  final_status?: string;
  outreach_count: number;
  email_segments: number;
  artifacts?: string[];
  error?: string;
  real_llm?: DemoStatus["llm"];
}
export interface DemoCResult {
  ok: boolean;
  mode: string;
  run_dir: string;
  recommendation?: string;
  days: number;
  quiz_questions: number;
  plan_md_head?: string;
  error?: string;
  real_llm?: DemoStatus["llm"];
}
export interface DemoStatus {
  ok: boolean;
  hermes_home: string;
  external_skill_dir: string;
  external_dirs: string[];
  external_dir_configured: boolean;
  vendor: string[];
  campus: string[];
  installed: string[];
  missing_core: string[];
  llm: {
    ok: boolean;
    mode: string;
    hermes_binary?: string;
    hermes_importable: boolean;
    hermes_import_error?: string;
    configured_keys: string[];
    readiness?: string;
    fixes?: string[];
    error?: string;
  };
}
export interface MemoryHit {
  key: string;
  score: number;
  snippet: string;
}
export interface Profile {
  ok: boolean;
  profile: { identity: string; major: string; persona: string };
}
export interface Task {
  id: string;
  title: string;
  status: string;
}
export interface CalEvent {
  id?: string;
  title: string;
  start: string;
  end?: string | null;
  rrule?: string | null;
  location?: string;
  note?: string;
}
export interface Anniversary {
  id?: string;
  name: string;
  date: string;       // "MM-DD"
  kind: string;       // "birthday" | "anniversary"
  note?: string;
}
export interface DailyLog {
  date: string;
  summary: string;
  entries: string[];
  tomorrow: string[];
}
export interface ResearchTopic {
  id: string;
  title: string;
  query: string;
  keywords?: string[];
  cadence?: string;
}
export interface ResearchDigest {
  ok: boolean;
  topic_id: string;
  summary: string;
  papers: { title: string; url: string; year?: number; score?: number; abstract?: string }[];
  questions: string[];
  source_mode?: string;
  source_error?: string;
  note_path?: string;
  topic?: ResearchTopic;
  error?: string;
}

export const api = {
  health: () => jget<{ ok: boolean; service: string }>("/health"),
  runs: () => jget<{ runs: string[] }>("/runs"),
  demoStatus: () => jget<DemoStatus>("/demo/status"),
  demoARun: (body: { sample_text?: string; topic: string; region: string; window: string; mode?: string }) =>
    jpost<DemoAResult>("/demo_a/run", body),
  demoBRun: (path: string, exam_date: string, opts: { free_minutes?: number; start_date?: string; topic?: string } = {}) =>
    jpost<DemoBResult>("/demo_b/run", { path, exam_date, ...opts }),
  demoCRun: (body: { goal: string; days?: number; minutes?: number; quiz_n?: number; mode?: string }) =>
    jpost<DemoCResult>("/demo_c/run", body),
  recall: (query: string, k = 5) => jpost<{ results: MemoryHit[] }>("/memory", { query, k }),
  onboard: (answers: Record<string, string>) => jpost<Profile>("/onboarding", { answers }),
  profile: () => jget<Profile>("/profile"),
  tasks: () => jget<{ tasks: Task[] }>("/tasks"),
  push: (channel: string, message: string, target?: string) =>
    jpost<{ ok: boolean; channel: string; target: string; error: string }>("/push", { channel, message, target }),
  // life (Phase 6)
  calendarAdd: (e: CalEvent) =>
    jpost<CalEvent & { ok: boolean; id: string }>("/calendar", e),
  calendarList: (start?: string, end?: string) =>
    jget<{ events: CalEvent[] }>(`/calendar${start ? `?start=${start}${end ? `&end=${end}` : ""}` : ""}`),
  calendarDelete: (id: string) =>
    jdel<{ ok: boolean; id: string }>(`/calendar/${id}`),
  annivAdd: (a: Anniversary) =>
    jpost<Anniversary & { ok: boolean }>(`/anniversaries`, a),
  annivList: () => jget<{ anniversaries: Anniversary[] }>("/anniversaries"),
  dailyLogGet: (date?: string, n = 7) =>
    jget<{ logs: DailyLog[] }>(`/daily_log${date ? `?date=${date}` : `?n=${n}`}`),
  dailyLogRun: () => jpost<{ ok: boolean; reminders_sent: number; log_id: string }>("/daily_log/run", {}),
  researchTopics: () => jget<{ topics: ResearchTopic[] }>("/research/topics"),
  researchAddTopic: (body: { title: string; query?: string; keywords?: string[]; cadence?: string }) =>
    jpost<{ ok: boolean; topic: ResearchTopic; error?: string }>("/research/topics", body),
  researchRefresh: (id: string, mode = "offline") =>
    jpost<ResearchDigest>(`/research/topics/${id}/refresh`, { mode }),
  researchRuns: () => jget<{ runs: ResearchDigest[] }>("/research/runs"),
  notionSync: (digest: ResearchDigest, mode = "local") =>
    jpost<{ ok: boolean; local_path: string; notion_ok: boolean; error?: string }>("/notes/notion/sync", { digest, mode }),
  notesStatus: () => jget<{ ok: boolean; token_configured: boolean; database_configured?: boolean; local_mirror_dir?: string }>("/notes/status"),
};
