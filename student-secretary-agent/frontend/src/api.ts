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
  domain?: string;
  due?: string;
  run_id?: string;
  body?: string;
}
export interface RunRecord {
  id: string;
  message: string;
  intent: string;
  domain: string;
  selected_workflow: string;
  status: string;
  artifacts?: { name: string; path: string; kind: string }[];
  error?: string;
}
export interface AgentRunResult {
  ok: boolean;
  run_id: string;
  intent: string;
  domain: string;
  selected_workflow: string;
  status: string;
  artifacts: { name: string; path: string; kind: string }[];
  error: string;
  multiagent?: boolean;
  source_mode?: string;
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
export interface SettingsStatus {
  ok: boolean;
  version: string;
  branch: string;
  campus_home: string;
  llm: DemoStatus["llm"];
  skills: DemoStatus;
  notion: { ok: boolean; token_configured: boolean; database_configured?: boolean; mode?: string; local_mirror_dir?: string };
  mobile: { ok: boolean; channels: Record<string, { ok?: boolean; configured?: boolean; error?: string; target?: string; channel?: string } | boolean> };
  providers: Record<string, boolean>;
  smoke_command: string;
}

export const api = {
  health: () => jget<{ ok: boolean; service: string }>("/health"),
  runs: () => jget<{ runs: RunRecord[] }>("/runs"),
  agentRun: (body: { message: string; context?: Record<string, unknown> }) =>
    jpost<AgentRunResult>("/agent/run", body),
  agentRuns: () => jget<{ runs: RunRecord[] }>("/agent/runs"),
  agentRunDetail: (id: string) => jget<RunRecord & { ok: boolean }>(`/agent/runs/${id}`),
  settingsStatus: () => jget<SettingsStatus>("/settings/status"),
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
  flashcards: (body: { topic: string; source_text?: string; count?: number }) =>
    jpost<{ ok: boolean; topic: string; flashcards: { id: string; front: string; back: string; tags: string[]; due: string }[]; run_id: string; source_mode?: string; review_nodes?: number }>("/learning/flashcards", body),
  addDeadline: (body: { title: string; due: string; course?: string; note?: string }) =>
    jpost<{ ok: boolean; deadline: Task; run_id: string }>("/learning/deadlines", body),
  learningDeadlines: () => jget<{ deadlines: Task[] }>("/learning/deadlines"),
  quizRun: (body: { topic: string; count?: number; source_text?: string }) =>
    jpost<{ ok: boolean; topic: string; questions: { id: string; question: string; answer: string }[]; run_id: string; source_mode?: string }>("/learning/quiz/run", body),
  quizGrade: (body: { topic: string; answers: { question_id: string; answer: string; review_node_id?: string }[] }) =>
    jpost<{ ok: boolean; score: number; graded: { question_id: string; score: number; feedback: string; ebbinghaus_advanced?: boolean }[]; plan_adjustment: string; run_id: string }>("/learning/quiz/grade", body),
  learningDashboard: () => jget<{ ok: boolean; today_tasks: Task[]; deadlines: Task[]; due_reviews: Task[]; progress: { tasks: number; done: number } }>("/learning/dashboard"),
  researchIdea: (body: { idea: string }) => jpost<ResearchDigest & { run_id: string }>("/research/idea", body),
  githubTrending: (body: { topic: string; language?: string }) =>
    jpost<{ ok: boolean; summary: string; items: { name: string; url: string; stars: number; reason: string }[]; run_id: string; source_mode?: string }>("/research/github/trending", body),
  formatCheck: (body: { title: string; target?: string; manuscript?: string }) =>
    jpost<{ ok: boolean; summary: string; items: { name: string; passed: boolean; detail: string }[]; run_id: string; source_mode?: string }>("/research/format/check", body),
  healthAdd: (body: { mood?: string; sleep_hours?: number; exercise?: string; note?: string }) =>
    jpost<{ ok: boolean; record: Record<string, unknown>; records: Record<string, unknown>[]; run_id: string }>("/life/health", body),
  healthList: () => jget<{ records: Record<string, unknown>[] }>("/life/health"),
  travelPlan: (body: { destination: string; days?: number; budget?: number; preferences?: string }) =>
    jpost<{ ok: boolean; destination: string; itinerary: Record<string, unknown>[]; run_id: string; source_mode?: string }>("/life/travel_plan", body),
  campusGuide: (query = "") => jget<{ ok: boolean; guides: { title: string; steps: string[] }[] }>(`/life/campus_guide${query ? `?query=${encodeURIComponent(query)}` : ""}`),
  meetingMinutes: (body: { topic: string; notes?: string }) =>
    jpost<{ ok: boolean; topic: string; summary: string; minutes: { decisions: string[]; todo: string[]; next_meeting: string }; run_id: string; source_mode?: string }>("/club/meeting_minutes", body),
  recruitingCopy: (body: { org: string; audience?: string; tone?: string }) =>
    jpost<{ ok: boolean; copy: { headline: string; body: string; poster_points: string[] }; run_id: string; source_mode?: string }>("/club/recruiting_copy", body),
  emailDraft: (body: { purpose: string; recipient?: string; context?: string }) =>
    jpost<{ ok: boolean; email: string; recipient: string; run_id: string; source_mode?: string }>("/club/email_draft", body),
  jobSearch: (body: { query: string; city?: string }) =>
    jpost<{ ok: boolean; jobs: { id: string; title: string; company: string; city: string; fit: number; reason: string }[]; run_id: string; source_mode?: string }>("/career/jobs/search", body),
  saveJob: (job: Record<string, unknown>) => jpost<{ ok: boolean; jobs: Record<string, unknown>[] }>("/career/jobs/save", { job }),
  savedJobs: () => jget<{ jobs: Record<string, unknown>[] }>("/career/jobs"),
  interviewPlan: (body: { role: string; days?: number; background?: string }) =>
    jpost<{ ok: boolean; role: string; plan: { day: number; focus: string; task: string; minutes: number }[]; questions: string[]; run_id: string; source_mode?: string }>("/career/interview_plan", body),
  // Phase 8: interview practice + reflect
  interviewPractice: (body: { role: string; question?: string; answer?: string; background?: string }) =>
    jpost<{ ok: boolean; score: number; rubric: string[]; improvement_cues: string[]; model_answer_outline: string[]; follow_ups: string[]; run_id: string }>("/career/interview/practice", body),
  interviewReflect: (body: { role: string; reflection: string; practice_run_id?: string; tags?: string }) =>
    jpost<{ ok: boolean; reflection: Record<string, unknown>; reflections_total: number; run_id: string }>("/career/interview/reflect", body),
  // Phase 8: Ebbinghaus daily quiz
  quizDaily: (body: { topic?: string; count?: number }) =>
    jpost<{ ok: boolean; topic: string; questions: { id: string; question: string; answer: string; review_node_id?: string }[]; due_review_count: number; total_review_nodes: number; run_id: string }>("/learning/quiz/daily", body),
  // Phase 8: export status
  exportStatus: () => jget<{ ok: boolean; formats: Record<string, { available: boolean; library: string }>; any_available: boolean }>("/club/export_status"),
  // Phase 8: auto-learn
  submitCorrection: (runId: string, body: { domain?: string; original?: string; corrected: string; reason?: string }) =>
    jpost<{ ok: boolean; correction: Record<string, unknown>; total_corrections: number }>(`/agent/runs/${runId}/correction`, body),
  listCorrections: (includeProcessed = true) =>
    jget<{ corrections: Record<string, unknown>[]; total: number }>(`/agent/corrections?include_processed=${includeProcessed}`),
  triggerAutoLearn: (useLlm = true) =>
    jpost<{ ok: boolean; processed: number; preferences_written: number; skills_created: number; skills_updated: number; knowledge_written: number }>(`/admin/auto-learn?use_llm=${useLlm}`, {}),
  listAutoSkills: () => jget<{ skills: string[] }>("/agent/skills"),
  // Phase 8: agent name
  getAgentName: () => jget<{ ok: boolean; name: string; config: Record<string, unknown> }>("/agent/name"),
  setAgentName: (name: string) => jpost<{ ok: boolean; name: string }>("/agent/name", { name }),
  // Phase 8: Notion list
  notionList: (limit = 20) => jget<{ ok: boolean; notes: Record<string, unknown>[]; source?: string }>(`/notes/notion/list?limit=${limit}`),
};
