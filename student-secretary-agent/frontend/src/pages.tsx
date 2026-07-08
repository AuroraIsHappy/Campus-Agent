import { useEffect, useState, type ReactNode } from "react";
import { api, type DemoAResult, type DemoBResult, type DemoCResult, type DemoStatus, type MemoryHit, type Profile, type Task, type CalEvent, type Anniversary, type DailyLog, type ResearchDigest, type ResearchTopic } from "./api";

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
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [notes, setNotes] = useState<{ ok: boolean; token_configured: boolean; database_configured?: boolean; local_mirror_dir?: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.profile(), api.tasks(), api.runs(), api.demoStatus(), api.notesStatus()])
      .then(([p, t, r, s, n]) => {
        setProfile(p);
        setTasks(t.tasks);
        setRuns(r.runs);
        setStatus(s);
        setNotes(n);
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
        <Card title="LLM">
          <p className="text-lg font-semibold">{status?.llm.ok ? "真实模式可用" : "离线优先"}</p>
          <p className="text-sm text-ink-700/70">{status?.llm.hermes_importable ? "hermes_cli 可导入" : "hermes_cli 未就绪"}</p>
          {status?.llm.configured_keys?.length ? <span className="campus-chip mt-2">{status.llm.configured_keys.join(", ")}</span> : null}
        </Card>
        <Card title="Skills">
          <p className="text-3xl font-semibold">{(status?.vendor.length || 0) + (status?.campus.length || 0)}</p>
          <p className="text-sm text-ink-700/70">{status?.external_dir_configured ? "仓库技能已挂载" : "仓库技能未挂载"}</p>
        </Card>
        <Card title="Notion">
          <p className="text-lg font-semibold">{notes?.ok ? "可同步" : "本地镜像"}</p>
          <p className="text-sm text-ink-700/70">{notes?.local_mirror_dir || "notes/research"}</p>
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
export function DemoCenterPage() {
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [mode, setMode] = useState("offline");
  const [topic, setTopic] = useState("校园低碳实践");
  const [region, setRegion] = useState("北京高校社区");
  const [goal, setGoal] = useState("7 天入门机器学习");
  const [days, setDays] = useState(7);
  const [aRes, setARes] = useState<DemoAResult | null>(null);
  const [cRes, setCRes] = useState<DemoCResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    api.demoStatus().then(setStatus).catch((e: Error) => setErr(e.message));
  }, []);

  const runA = () => {
    setBusy("a"); setErr(null);
    api.demoARun({ topic, region, window: "2026 暑期", mode })
      .then(setARes).catch((e: Error) => setErr(e.message)).finally(() => setBusy(null));
  };
  const runC = () => {
    setBusy("c"); setErr(null);
    api.demoCRun({ goal, days, minutes: 20, quiz_n: 3, mode })
      .then(setCRes).catch((e: Error) => setErr(e.message)).finally(() => setBusy(null));
  };

  return (
    <>
      <PageHeader title="Demo 中心" subtitle="社会实践策划、学习计划、真实 LLM 状态检查。" />
      <Err e={err} />
      <div className="mb-4 grid gap-4 lg:grid-cols-3">
        <Card title="运行模式">
          <select className="campus-input" value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="offline">offline</option>
            <option value="auto">auto</option>
            <option value="real">real</option>
          </select>
          {status && (
            <div className="mt-3 text-sm text-ink-700/70">
              <p>LLM：{status.llm.ok ? "可用" : "未就绪"}</p>
              <p>Hermes：{status.llm.hermes_importable ? "import ok" : "不可导入"}</p>
              <p>Skills dir：{status.external_dir_configured ? "已挂载" : "未挂载"}</p>
              <p>内置技能：{status.vendor.length + status.campus.length}</p>
              {status.missing_core.length > 0 && <p className="text-amber-700">缺少：{status.missing_core.join(", ")}</p>}
              {!status.llm.ok && status.llm.fixes && status.llm.fixes.length > 0 && (
                <p className="mt-2 text-amber-700">{status.llm.fixes[0]}</p>
              )}
            </div>
          )}
        </Card>
        <Card title="Demo A 社会实践">
          <div className="grid gap-2 text-sm">
            <input className="campus-input" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="实践主题" />
            <input className="campus-input" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="地区" />
            <button className="campus-btn" onClick={runA} disabled={busy !== null}>{busy === "a" ? "生成中..." : "生成策划案"}</button>
          </div>
          {aRes && (
            <div className="mt-3 grid gap-2 text-sm">
              <Metric label="状态" value={aRes.ok ? "成功" : "失败"} />
              <Metric label="外联对象" value={String(aRes.outreach_count)} />
              <Metric label="邮件草稿" value={String(aRes.email_segments)} />
              <Metric label="模式" value={aRes.mode} />
              <pre className="overflow-x-auto rounded-lg bg-ink-900 p-2 text-xs text-ink-100">{aRes.error || aRes.run_dir}</pre>
              {aRes.artifacts && aRes.artifacts.length > 0 && (
                <p className="text-xs text-ink-700/60">产物 {aRes.artifacts.length} 个，已写入 run 目录。</p>
              )}
            </div>
          )}
        </Card>
        <Card title="Demo C 学习计划">
          <div className="grid gap-2 text-sm">
            <input className="campus-input" value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="学习目标" />
            <input className="campus-input" type="number" value={days} onChange={(e) => setDays(Number(e.target.value))} />
            <button className="campus-btn" onClick={runC} disabled={busy !== null}>{busy === "c" ? "生成中..." : "生成学习计划"}</button>
          </div>
          {cRes && (
            <div className="mt-3 grid gap-2 text-sm">
              <Metric label="状态" value={cRes.ok ? "成功" : "失败"} />
              <Metric label="天数" value={String(cRes.days)} />
              <Metric label="Quiz" value={String(cRes.quiz_questions)} />
              <Metric label="模式" value={cRes.mode} />
              <pre className="overflow-x-auto rounded-lg bg-ink-900 p-2 text-xs text-ink-100">{cRes.error || cRes.run_dir}</pre>
              {cRes.plan_md_head && <p className="text-xs text-ink-700/60">{cRes.plan_md_head}</p>}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}

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

/* ---------------- Research + Notes ---------------- */
export function ResearchPage() {
  const [topics, setTopics] = useState<ResearchTopic[]>([]);
  const [runs, setRuns] = useState<ResearchDigest[]>([]);
  const [latest, setLatest] = useState<ResearchDigest | null>(null);
  const [title, setTitle] = useState("LLM agents for students");
  const [query, setQuery] = useState("student secretary agent papers");
  const [note, setNote] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshAll = () => {
    Promise.all([api.researchTopics(), api.researchRuns()])
      .then(([t, r]) => { setTopics(t.topics); setRuns(r.runs); })
      .catch((e: Error) => setErr(e.message));
  };
  useEffect(refreshAll, []);

  const addTopic = () => {
    setBusy(true); setErr(null);
    api.researchAddTopic({ title, query })
      .then(refreshAll)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };
  const runRefresh = (id: string) => {
    setBusy(true); setErr(null);
    api.researchRefresh(id, "auto")
      .then((d) => { setLatest(d); refreshAll(); })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };
  const sync = () => {
    if (!latest) return;
    api.notionSync(latest, "local")
      .then((r) => setNote(r.local_path))
      .catch((e: Error) => setErr(e.message));
  };

  return (
    <>
      <PageHeader title="科研笔记" subtitle="论文主题跟踪、候选论文 digest、本地 Notion 镜像。" />
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="主题">
          <div className="grid gap-2 text-sm">
            <input className="campus-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="主题名称" />
            <input className="campus-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="检索 query" />
            <button className="campus-btn" onClick={addTopic} disabled={busy || !title}>{busy ? "处理中..." : "添加主题"}</button>
          </div>
          <ul className="mt-4 space-y-2 text-sm">
            {topics.map((t) => (
              <li key={t.id} className="flex items-center justify-between rounded-lg border border-ink-100 p-2">
                <span>
                  <span className="font-medium">{t.title}</span>
                  <span className="ml-2 text-ink-700/60">{t.query}</span>
                </span>
                <button className="campus-btn" onClick={() => runRefresh(t.id)} disabled={busy}>刷新</button>
              </li>
            ))}
            {topics.length === 0 && <li className="text-ink-700/60">暂无主题。</li>}
          </ul>
        </Card>
        <Card title="Digest">
          {latest ? (
            <div className="text-sm">
              <p className="mb-3 text-ink-700/80">{latest.summary}</p>
              <div className="mb-3 flex flex-wrap gap-2">
                <span className="campus-chip">{latest.source_mode || "offline"}</span>
                {latest.note_path && <span className="campus-chip">note ready</span>}
              </div>
              {latest.source_error && <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">{latest.source_error}</p>}
              <ul className="space-y-2">
                {latest.papers.map((p, i) => (
                  <li key={i} className="rounded-lg border border-ink-100 p-2">
                    <p className="font-medium">{p.title}</p>
                    <p className="text-xs text-ink-700/60">{p.year || ""} · score {p.score || ""}</p>
                    {p.abstract && <p className="mt-1 text-xs text-ink-700/70">{p.abstract}</p>}
                  </li>
                ))}
              </ul>
              <button className="campus-btn mt-3" onClick={sync}>同步笔记</button>
              {(note || latest.note_path) && <pre className="mt-3 overflow-x-auto rounded-lg bg-ink-900 p-2 text-xs text-ink-100">{note || latest.note_path}</pre>}
            </div>
          ) : (
            <p className="text-sm text-ink-700/60">刷新一个主题后会显示摘要。</p>
          )}
        </Card>
      </div>
      <Card title="历史运行">
        <ul className="space-y-2 text-sm">
          {runs.slice().reverse().slice(0, 5).map((r, i) => (
            <li key={i} className="rounded-lg border border-ink-100 p-2">{r.summary}</li>
          ))}
          {runs.length === 0 && <li className="text-ink-700/60">暂无运行记录。</li>}
        </ul>
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

/* ---------------- Life (Phase 6) ---------------- */
export function LifePage() {
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [annivs, setAnnivs] = useState<Anniversary[]>([]);
  const [logs, setLogs] = useState<DailyLog[]>([]);
  const [err, setErr] = useState<string | null>(null);

  // add-event form
  const [title, setTitle] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [location, setLocation] = useState("");
  const [rrule, setRrule] = useState("");
  // add-anniv form
  const [aName, setAName] = useState("");
  const [aDate, setADate] = useState("");
  const [aKind, setAKind] = useState("birthday");

  const refresh = () => {
    Promise.all([api.calendarList(), api.annivList(), api.dailyLogGet(undefined, 5)])
      .then(([e, a, l]) => { setEvents(e.events); setAnnivs(a.anniversaries); setLogs(l.logs); })
      .catch((e: Error) => setErr(e.message));
  };
  useEffect(refresh, []);

  const addEvent = () => {
    if (!title || !start) return;
    api.calendarAdd({ title, start, end: end || null, rrule: rrule || null, location })
      .then(refresh).then(() => { setTitle(""); setStart(""); setEnd(""); setLocation(""); setRrule(""); })
      .catch((e: Error) => setErr(e.message));
  };
  const delEvent = (id: string) => api.calendarDelete(id).then(refresh).catch((e: Error) => setErr(e.message));

  const addAnniv = () => {
    if (!aName || !aDate) return;
    api.annivAdd({ name: aName, date: aDate, kind: aKind })
      .then(refresh).then(() => { setAName(""); setADate(""); })
      .catch((e: Error) => setErr(e.message));
  };

  const runDaily = () => api.dailyLogRun().then(refresh).catch((e: Error) => setErr(e.message));

  return (
    <>
      <PageHeader title="生活" subtitle="日程 · 生日纪念日提醒 · 每日秘书日志。" />
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="日程">
          <ul className="space-y-1 text-sm">
            {events.map((e, i) => (
              <li key={i} className="flex items-center justify-between rounded border border-ink-100 px-2 py-1">
                <span>
                  <span className="font-mono text-xs text-campus-700">{e.start}</span>{" "}
                  {e.title}{e.location ? `（${e.location}）` : ""}
                  {e.rrule ? <span className="campus-chip ml-2">{e.rrule}</span> : null}
                </span>
                <button className="text-xs text-red-500 hover:underline" onClick={() => e.id && delEvent(e.id)}>删除</button>
              </li>
            ))}
            {events.length === 0 && <li className="text-ink-700/60">暂无日程。</li>}
          </ul>
          <div className="mt-4 grid gap-2 border-t border-ink-100 pt-3 text-sm">
            <input className="campus-input" placeholder="标题（如：高数课）" value={title} onChange={(e) => setTitle(e.target.value)} />
            <div className="grid grid-cols-2 gap-2">
              <input className="campus-input" placeholder="开始 2026-07-09T08:00" value={start} onChange={(e) => setStart(e.target.value)} />
              <input className="campus-input" placeholder="结束（可空）" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input className="campus-input" placeholder="地点（可空）" value={location} onChange={(e) => setLocation(e.target.value)} />
              <select className="campus-input" value={rrule} onChange={(e) => setRrule(e.target.value)}>
                <option value="">不重复</option>
                <option value="DAILY">每天</option>
                <option value="WEEKLY">每周</option>
              </select>
            </div>
            <button className="campus-btn" onClick={addEvent} disabled={!title || !start}>添加日程</button>
          </div>
        </Card>

        <Card title="生日 / 纪念日">
          <ul className="space-y-1 text-sm">
            {annivs.map((a, i) => (
              <li key={i} className="rounded border border-ink-100 px-2 py-1">
                <span className="font-mono text-xs text-campus-700">{a.date}</span>{" "}
                {a.name}
                <span className="campus-chip ml-2">{a.kind === "birthday" ? "生日" : "纪念日"}</span>
              </li>
            ))}
            {annivs.length === 0 && <li className="text-ink-700/60">暂无。会提前 1 天 + 当天提醒。</li>}
          </ul>
          <div className="mt-4 grid gap-2 border-t border-ink-100 pt-3 text-sm">
            <input className="campus-input" placeholder="名称（如：小明）" value={aName} onChange={(e) => setAName(e.target.value)} />
            <div className="grid grid-cols-2 gap-2">
              <input className="campus-input" placeholder="日期 MM-DD" value={aDate} onChange={(e) => setADate(e.target.value)} />
              <select className="campus-input" value={aKind} onChange={(e) => setAKind(e.target.value)}>
                <option value="birthday">生日</option>
                <option value="anniversary">纪念日</option>
              </select>
            </div>
            <button className="campus-btn" onClick={addAnniv} disabled={!aName || !aDate}>添加</button>
          </div>
        </Card>
      </div>

      <Card title="每日秘书日志">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm text-ink-700/70">每晚自动汇总当日日程 + 任务 + 提醒。也可手动触发：</p>
          <button className="campus-btn" onClick={runDaily}>立即生成</button>
        </div>
        <div className="space-y-3">
          {logs.map((lg) => (
            <div key={lg.date} className="rounded-lg border border-ink-100 p-3">
              <div className="flex items-center justify-between">
                <span className="font-medium">{lg.date}</span>
              </div>
              <p className="mt-1 text-sm">{lg.summary}</p>
              {lg.entries.length > 0 && (
                <ul className="mt-2 list-inside list-disc text-sm text-ink-700/80">
                  {lg.entries.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              )}
              {lg.tomorrow.length > 0 && (
                <p className="mt-2 text-xs text-campus-700">明日：{lg.tomorrow.join("；")}</p>
              )}
            </div>
          ))}
          {logs.length === 0 && <p className="text-sm text-ink-700/60">暂无日志。</p>}
        </div>
      </Card>
    </>
  );
}
