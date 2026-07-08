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

export interface DemoBResult {
  ok: boolean;
  run_dir: string;
  final_status: string;
  extraction_rate: number;
  kg_nodes: number;
  resource_count: number;
  plan_days: number;
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

export const api = {
  health: () => jget<{ ok: boolean; service: string }>("/health"),
  runs: () => jget<{ runs: string[] }>("/runs"),
  demoBRun: (path: string, exam_date: string, opts: { free_minutes?: number; start_date?: string; topic?: string } = {}) =>
    jpost<DemoBResult>("/demo_b/run", { path, exam_date, ...opts }),
  recall: (query: string, k = 5) => jpost<{ results: MemoryHit[] }>("/memory", { query, k }),
  onboard: (answers: Record<string, string>) => jpost<Profile>("/onboarding", { answers }),
  profile: () => jget<Profile>("/profile"),
  tasks: () => jget<{ tasks: Task[] }>("/tasks"),
  push: (channel: string, message: string, target?: string) =>
    jpost<{ ok: boolean; channel: string; target: string; error: string }>("/push", { channel, message, target }),
};
