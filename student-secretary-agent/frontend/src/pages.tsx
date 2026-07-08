import { useEffect, useState, type ReactNode } from "react";
import { api, type DemoBResult, type MemoryHit, type Profile, type Task } from "./api";

function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-semibold text-ink-900">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-ink-700/70">{subtitle}</p>}
    </header>
  );
}

function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="campus-card">
      {title && <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-campus-700">{title}</h2>}
      {children}
    </section>
  );
}

function Err({ e }: { e: string | null }) {
  return e ? <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{e}</p> : null;
}

/* ---------------- Dashboard ---------------- */
export function DashboardPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [runs, setRuns] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.profile(), api.tasks(), api.runs()])
      .then(([p, t, r]) => {
        setProfile(p);
        setTasks(t.tasks);
        setRuns(r.runs);
      })
      .catch((e: Error) => setErr(e.message));
  }, []);

  return (
    <>
      <PageHeader title="仪表盘" subtitle="今日概览：身份、任务、最近运行。" />
      <Err e={err} />
      <div className="grid gap-4 md:grid-cols-3">
        <Card title="身份">
          <p className="text-lg font-medium">{profile?.profile.identity || "未配置"}</p>
          <p className="text-sm text-ink-700/70">{profile?.profile.major || "—"}</p>
          <span className="campus-chip mt-2">{profile?.profile.persona || "default"}</span>
        </Card>
        <Card title="任务">
          <p className="text-3xl font-semibold">{tasks.length}</p>
          <p className="text-sm text-ink-700/70">个任务在看板上</p>
        </Card>
        <Card title="最近运行">
          <p className="text-3xl font-semibold">{runs.length}</p>
          <p className="text-sm text-ink-700/70">个 demo 运行记录</p>
        </Card>
      </div>
    </>
  );
}

/* ---------------- Onboarding ---------------- */
export function OnboardingPage() {
  const [identity, setIdentity] = useState("");
  const [major, setMajor] = useState("");
  const [persona, setPersona] = useState("default");
  const [out, setOut] = useState<Profile | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = () => {
    setBusy(true);
    setErr(null);
    api.onboard({ identity, major, persona })
      .then(setOut)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };

  return (
    <>
      <PageHeader title="新手引导" subtitle="5 分钟配置你的专属秘书。" />
      <Card>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm">
            身份 / 昵称
            <input className="campus-input mt-1" value={identity} onChange={(e) => setIdentity(e.target.value)} placeholder="例如：小明" />
          </label>
          <label className="text-sm">
            专业
            <input className="campus-input mt-1" value={major} onChange={(e) => setMajor(e.target.value)} placeholder="例如：计算机" />
          </label>
          <label className="text-sm">
            人格风格
            <select className="campus-input mt-1" value={persona} onChange={(e) => setPersona(e.target.value)}>
              <option value="default">默认</option>
              <option value="feynman">费曼（启发式）</option>
              <option value="lu_xun">鲁迅（犀利）</option>
            </select>
          </label>
        </div>
        <button className="campus-btn mt-4" onClick={submit} disabled={busy}>{busy ? "配置中…" : "完成配置"}</button>
        <Err e={err} />
        {out && <p className="mt-3 text-sm text-emerald-700">已保存：{out.profile.identity} · {out.profile.persona}</p>}
      </Card>
    </>
  );
}

/* ---------------- Demo B ---------------- */
export function DemoBPage() {
  const [path, setPath] = useState("");
  const [exam, setExam] = useState("");
  const [free, setFree] = useState(300);
  const [res, setRes] = useState<DemoBResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = () => {
    setBusy(true);
    setErr(null);
    api.demoBRun(path, exam, { free_minutes: free })
      .then(setRes)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };

  return (
    <>
      <PageHeader title="Demo B · 讲义复习计划" subtitle="扫描讲义 → 知识图谱 → 期末复习计划 + 每日 quiz。" />
      <Card>
        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-sm md:col-span-2">
            讲义路径
            <input className="campus-input mt-1" value={path} onChange={(e) => setPath(e.target.value)} placeholder="~/Courses/.../lectures" />
          </label>
          <label className="text-sm">
            考试日期
            <input className="campus-input mt-1" type="date" value={exam} onChange={(e) => setExam(e.target.value)} />
          </label>
          <label className="text-sm">
            可用时间（分钟/天）
            <input className="campus-input mt-1" type="number" value={free} onChange={(e) => setFree(Number(e.target.value))} />
          </label>
        </div>
        <button className="campus-btn mt-4" onClick={run} disabled={busy || !path || !exam}>{busy ? "生成中…" : "生成复习计划"}</button>
        <Err e={err} />
        {res && (
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <Metric label="状态" value={res.ok ? "成功" : "失败"} />
            <Metric label="知识节点" value={String(res.kg_nodes)} />
            <Metric label="资源" value={String(res.resource_count)} />
            <Metric label="计划天数" value={String(res.plan_days)} />
            <pre className="md:col-span-4 overflow-x-auto rounded-lg bg-ink-900 p-3 text-xs text-ink-100">{res.run_dir}</pre>
          </div>
        )}
      </Card>
    </>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-ink-50 p-3">
      <p className="text-xs uppercase tracking-wide text-ink-700/60">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

/* ---------------- Kanban ---------------- */
export function KanbanPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.tasks().then((t) => setTasks(t.tasks)).catch((e: Error) => setErr(e.message));
  }, []);
  const tone = (s: string) =>
    s === "done" ? "bg-emerald-100 text-emerald-700" :
    s === "awaiting_human" ? "bg-amber-100 text-amber-700" : "bg-ink-100 text-ink-700";
  return (
    <>
      <PageHeader title="任务看板" subtitle="Odyssey / Kanban 任务流。" />
      <Err e={err} />
      <Card>
        {tasks.length === 0 ? <p className="text-sm text-ink-700/60">暂无任务。</p> : (
          <ul className="divide-y divide-ink-100">
            {tasks.map((t) => (
              <li key={t.id} className="flex items-center justify-between py-3">
                <span className="font-medium">{t.title}</span>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${tone(t.status)}`}>{t.status}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

/* ---------------- Persona ---------------- */
export function PersonaPage() {
  const [persona, setPersona] = useState("feynman");
  const [msg, setMsg] = useState("");
  const [out, setOut] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const sample: Record<string, string> = {
    feynman: "把复杂概念拆成最简单的比喻 —— 来，我们打个比方。",
    lu_xun: "说真话，哪怕刺耳。问题不解决，废话再多也没用。",
    default: "好的，我来帮你处理。",
  };
  const preview = () => {
    setErr(null);
    api.onboard({ persona })
      .then(() => setOut(sample[persona] ?? sample.default))
      .catch((e: Error) => setErr(e.message));
  };
  return (
    <>
      <PageHeader title="人格面板" subtitle="选择秘书的回复风格。" />
      <Card>
        <div className="flex flex-wrap gap-2">
          {["default", "feynman", "lu_xun"].map((p) => (
            <button key={p} onClick={() => setPersona(p)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${persona === p ? "bg-campus-600 text-white" : "border border-ink-200 text-ink-700 hover:bg-ink-100"}`}>
              {p}
            </button>
          ))}
        </div>
        <input className="campus-input mt-4" value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="试一句话，预览人格回复" />
        <button className="campus-btn mt-3" onClick={preview}>预览风格</button>
        <Err e={err} />
        {out && <p className="mt-3 rounded-lg bg-campus-50 px-3 py-2 text-sm text-campus-800">{out}{msg ? `（你说的：${msg}）` : ""}</p>}
      </Card>
    </>
  );
}

/* ---------------- Memory ---------------- */
export function MemoryPage() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<MemoryHit[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const search = () => {
    setBusy(true);
    setErr(null);
    api.recall(q, 8)
      .then((r) => setHits(r.results))
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };
  return (
    <>
      <PageHeader title="记忆" subtitle="跨 session 记忆召回（长期偏好 / 任务日志 / 知识库）。" />
      <Card>
        <div className="flex gap-2">
          <input className="campus-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索记忆…" onKeyDown={(e) => e.key === "Enter" && search()} />
          <button className="campus-btn" onClick={search} disabled={busy || !q}>{busy ? "…" : "召回"}</button>
        </div>
        <Err e={err} />
        <ul className="mt-4 space-y-2">
          {hits.map((h, i) => (
            <li key={i} className="rounded-lg border border-ink-100 p-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-campus-700">{h.key}</span>
                <span className="text-xs text-ink-700/60">score {h.score.toFixed(2)}</span>
              </div>
              <p className="mt-1 text-sm">{h.snippet}</p>
            </li>
          ))}
          {hits.length === 0 && <li className="text-sm text-ink-700/60">无结果。</li>}
        </ul>
      </Card>
    </>
  );
}
