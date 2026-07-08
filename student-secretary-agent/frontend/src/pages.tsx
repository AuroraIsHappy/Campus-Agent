import { useEffect, useState, type ReactNode } from "react";
import { api, type DemoStatus, type MemoryHit, type Profile, type Task, type CalEvent, type Anniversary, type DailyLog, type ResearchDigest, type ResearchTopic, type RunRecord, type AgentRunResult, type SettingsStatus } from "./api";

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

function SourceBadge({ mode }: { mode?: string }) {
  if (!mode) return null;
  const isLLM = mode.includes("llm") || mode.includes("real");
  return <span className={`ml-2 inline-block rounded-full px-2 py-0.5 text-xs ${isLLM ? "bg-emerald-100 text-emerald-700" : "bg-ink-100 text-ink-600"}`}>{isLLM ? "✨ AI 生成" : "模板"}</span>;
}

function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <svg className="h-4 w-4 animate-spin text-campus-500" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {label || "生成中…"}
    </span>
  );
}

function LinkList({ items }: { items: { name?: string; title?: string; url?: string; reason?: string; stars?: number }[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="space-y-2">
      {items.map((it, i) => (
        <div key={i} className="rounded-lg border border-ink-100 p-2.5 text-sm">
          <div className="flex items-center gap-2">
            {it.url ? (
              <a href={it.url} target="_blank" rel="noopener noreferrer" className="font-medium text-campus-600 underline decoration-campus-300 underline-offset-2 hover:text-campus-700">
                {it.name || it.title || it.url}
              </a>
            ) : (
              <span className="font-medium">{it.name || it.title}</span>
            )}
            {it.stars !== undefined && <span className="text-xs text-ink-400">★ {it.stars}</span>}
          </div>
          {it.reason && <p className="mt-1 text-ink-700/70">{it.reason}</p>}
        </div>
      ))}
    </div>
  );
}

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

function MonthCalendar({ events, onDelete }: { events: CalEvent[]; onDelete: (id: string) => void }) {
  const [viewDate, setViewDate] = useState(new Date());
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  // events grouped by date (YYYY-MM-DD)
  const byDate: Record<string, CalEvent[]> = {};
  for (const e of events) {
    const d = (e.start || "").slice(0, 10);
    if (d) (byDate[d] ||= []).push(e);
  }

  // build calendar grid: first day offset (Mon=0), days in month
  const firstDay = new Date(year, month, 1);
  let offset = firstDay.getDay() - 1; // Mon=0
  if (offset < 0) offset = 6;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < offset; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const monthLabel = `${year} 年 ${month + 1} 月`;
  const prevMonth = () => setViewDate(new Date(year, month - 1, 1));
  const nextMonth = () => setViewDate(new Date(year, month + 1, 1));

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <button onClick={prevMonth} className="rounded px-2 py-1 text-sm text-ink-600 hover:bg-ink-100">‹</button>
        <span className="font-medium text-ink-800">{monthLabel}</span>
        <button onClick={nextMonth} className="rounded px-2 py-1 text-sm text-ink-600 hover:bg-ink-100">›</button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center text-xs text-ink-500">
        {WEEKDAYS.map(w => <div key={w} className="py-1 font-medium">{w}</div>)}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((d, i) => {
          if (d === null) return <div key={i} className="min-h-16 rounded-lg bg-ink-50/50" />;
          const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
          const dayEvents = byDate[dateStr] || [];
          const isToday = dateStr === todayStr;
          return (
            <div key={i} className={`min-h-16 rounded-lg border p-1 text-xs ${isToday ? "border-campus-400 bg-campus-50" : "border-ink-100"}`}>
              <div className={`mb-0.5 font-medium ${isToday ? "text-campus-700" : "text-ink-600"}`}>{d}</div>
              {dayEvents.slice(0, 2).map((e, j) => (
                <div key={j} className="group relative truncate rounded bg-campus-100 px-1 py-0.5 text-campus-700" title={e.title}>
                  {e.title}
                  {e.id && <button onClick={() => onDelete(e.id!)} className="ml-1 hidden text-red-400 group-hover:inline">×</button>}
                </div>
              ))}
              {dayEvents.length > 2 && <div className="text-ink-400">+{dayEvents.length - 2} 更多</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---------------- Dashboard ---------------- */
export function DashboardPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
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
      <PageHeader title="仪表盘" subtitle="今日概览：任务、运行、集成状态。" />
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
          <p className="text-sm text-ink-700/70">个秘书运行记录</p>
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

/* ---------------- Secretary ---------------- */
export function SecretaryPage() {
  const [message, setMessage] = useState("我想学 Linux，帮我安排 30 天计划");
  const [result, setResult] = useState<AgentRunResult | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => api.agentRuns().then((r) => setRuns(r.runs)).catch((e: Error) => setErr(e.message));
  useEffect(() => { refresh(); }, []);
  const run = () => {
    setBusy(true); setErr(null);
    api.agentRun({ message })
      .then((r) => { setResult(r); return refresh(); })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };

  return (
    <>
      <PageHeader title="秘书" subtitle="一句话交给 Campus-Agent，自动路由到学习、科研、生活、社团或职业工作流。" />
      <Err e={err} />
      <Card title="新任务">
        <div className="grid gap-3 md:grid-cols-[1fr_auto]">
          <textarea className="campus-input min-h-28" value={message} onChange={(e) => setMessage(e.target.value)} />
          <button className="campus-btn" onClick={run} disabled={busy || !message.trim()}>{busy ? <Spinner /> : "开始"}</button>
        </div>
        {result && (
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <Metric label="领域" value={result.domain} />
            <Metric label="意图" value={result.intent} />
            <Metric label="状态" value={result.status} />
            <Metric label="产物" value={String(result.artifacts.length)} />
          </div>
        )}
        {result?.source_mode && <p className="mt-2 text-xs text-ink-700/50">来源：{result.source_mode}{result.multiagent ? " · 多智能体" : ""}</p>}
      </Card>
      <Card title="最近运行">
        <ul className="space-y-2 text-sm">
          {runs.slice(0, 8).map((r) => (
            <li key={r.id} className="rounded-lg border border-ink-100 p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">{r.message || r.selected_workflow}</span>
                <span className="campus-chip">{r.domain || "general"} · {r.status}</span>
              </div>
              <p className="mt-1 font-mono text-xs text-ink-700/60">{r.id}</p>
            </li>
          ))}
          {runs.length === 0 && <li className="text-ink-700/60">暂无运行。</li>}
        </ul>
      </Card>
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
export function LearningPage() {
  const [topic, setTopic] = useState("线性代数");
  const [source, setSource] = useState("矩阵乘法、线性变换、特征值、正交分解");
  const [deadlineTitle, setDeadlineTitle] = useState("完成第一章习题");
  const [deadlineDue, setDeadlineDue] = useState("2026-08-15");
  const [cards, setCards] = useState<{ id: string; front: string; back: string; due: string }[]>([]);
  const [questions, setQuestions] = useState<{ id: string; question: string; answer: string }[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [grade, setGrade] = useState<{ score: number; plan_adjustment: string } | null>(null);
  const [dashboard, setDashboard] = useState<{ today_tasks: Task[]; deadlines: Task[]; progress: { tasks: number; done: number } } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [cardSource, setCardSource] = useState<string | undefined>();
  const [quizSource, setQuizSource] = useState<string | undefined>();

  const refresh = () => api.learningDashboard().then(setDashboard).catch((e: Error) => setErr(e.message));
  useEffect(() => { refresh(); }, []);
  const makeCards = () => { setBusy(true); api.flashcards({ topic, source_text: source, count: 6 }).then((r) => { setCards(r.flashcards); setCardSource(r.source_mode); }).then(refresh).catch((e: Error) => setErr(e.message)).finally(() => setBusy(false)); };
  const addDeadline = () => api.addDeadline({ title: deadlineTitle, due: deadlineDue, course: topic }).then(refresh).catch((e: Error) => setErr(e.message));
  const runQuiz = () => { setBusy(true); api.quizRun({ topic, source_text: source, count: 4 }).then((r) => { setQuestions(r.questions); setQuizSource(r.source_mode); }).then(refresh).catch((e: Error) => setErr(e.message)).finally(() => setBusy(false)); };
  const gradeQuiz = () => api.quizGrade({ topic, answers: questions.map((q) => ({ question_id: q.id, answer: answers[q.id] || "" })) }).then((r) => setGrade(r)).then(refresh).catch((e: Error) => setErr(e.message));

  return (
    <>
      <PageHeader title="学习" subtitle="flashcards、deadline、每日 quiz 和复习反馈闭环。" />
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="概览">
          <Metric label="学习任务" value={String(dashboard?.progress.tasks || 0)} />
          <div className="mt-3 space-y-2 text-sm">
            {(dashboard?.deadlines || []).slice(0, 5).map((d) => <p key={d.id} className="rounded border border-ink-100 p-2">{d.due} · {d.title}</p>)}
          </div>
        </Card>
        <Card title="输入材料">
          <input className="campus-input mb-2" value={topic} onChange={(e) => setTopic(e.target.value)} />
          <textarea className="campus-input min-h-28" value={source} onChange={(e) => setSource(e.target.value)} />
        </Card>
        <Card title="Deadline">
          <input className="campus-input mb-2" value={deadlineTitle} onChange={(e) => setDeadlineTitle(e.target.value)} />
          <input className="campus-input mb-2" type="date" value={deadlineDue} onChange={(e) => setDeadlineDue(e.target.value)} />
          <button className="campus-btn" onClick={addDeadline}>添加 deadline</button>
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Flashcards">
          <button className="campus-btn" onClick={makeCards} disabled={busy}>{busy ? <Spinner /> : "生成卡片"}</button>
          <div className="mt-3 grid gap-2">
            {cards.length > 0 && <p className="text-xs text-ink-600"><SourceBadge mode={cardSource} /></p>}
            {cards.map((c) => <div key={c.id} className="rounded-lg border border-ink-100 p-3 text-sm"><p className="font-medium">{c.front}</p><p className="mt-1 text-ink-700/70">{c.back}</p><span className="campus-chip mt-2">due {c.due}</span></div>)}
          </div>
        </Card>
        <Card title="每日 Quiz">
          <button className="campus-btn" onClick={runQuiz} disabled={busy}>{busy ? <Spinner /> : "生成 quiz"}</button>
          {questions.length > 0 && <p className="mt-2 text-xs text-ink-600"><SourceBadge mode={quizSource} /></p>}
          <div className="mt-3 space-y-3">
            {questions.map((q) => (
              <label key={q.id} className="block text-sm">
                <span className="font-medium">{q.question}</span>
                <textarea className="campus-input mt-1" value={answers[q.id] || ""} onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })} />
              </label>
            ))}
          </div>
          {questions.length > 0 && <button className="campus-btn mt-3" onClick={gradeQuiz}>提交评分</button>}
          {grade && <p className="mt-3 rounded-lg bg-campus-50 p-3 text-sm text-campus-800">得分 {grade.score} · {grade.plan_adjustment}</p>}
        </Card>
      </div>
    </>
  );
}
export function ResearchPage() {
  const [topics, setTopics] = useState<ResearchTopic[]>([]);
  const [runs, setRuns] = useState<ResearchDigest[]>([]);
  const [latest, setLatest] = useState<ResearchDigest | null>(null);
  const [title, setTitle] = useState("LLM agents for students");
  const [query, setQuery] = useState("student secretary agent papers");
  const [note, setNote] = useState<string | null>(null);
  const [idea, setIdea] = useState("我想研究本科生个人秘书 agent 如何做长期记忆");
  const [githubTopic, setGithubTopic] = useState("student agent");
  const [githubItems, setGithubItems] = useState<{ name: string; url: string; stars: number; reason: string }[]>([]);
  const [formatTitle, setFormatTitle] = useState("Campus-Agent: A Personal Secretary for Students");
  const [manuscript, setManuscript] = useState("Abstract: ...\nFig. 1 shows the system.\nReferences\n[1] Author et al.");
  const [formatItems, setFormatItems] = useState<{ name: string; passed: boolean; detail: string }[]>([]);
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
  const runIdea = () => {
    setBusy(true); setErr(null);
    api.researchIdea({ idea })
      .then((d) => { setLatest(d); refreshAll(); })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };
  const runGithub = () => { setBusy(true); setErr(null); api.githubTrending({ topic: githubTopic }).then((r) => setGithubItems(r.items)).catch((e: Error) => setErr(e.message)).finally(() => setBusy(false)); };
  const runFormat = () => { setBusy(true); setErr(null); api.formatCheck({ title: formatTitle, manuscript }).then((r) => setFormatItems(r.items)).catch((e: Error) => setErr(e.message)).finally(() => setBusy(false)); };

  return (
    <>
      <PageHeader title="科研" subtitle="idea 调研、论文跟踪、GitHub 项目和格式检查。" />
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Idea 调研">
          <textarea className="campus-input min-h-24" value={idea} onChange={(e) => setIdea(e.target.value)} />
          <button className="campus-btn mt-2" onClick={runIdea} disabled={busy}>生成 digest</button>
        </Card>
        <Card title="GitHub 项目">
          <input className="campus-input" value={githubTopic} onChange={(e) => setGithubTopic(e.target.value)} />
          <button className="campus-btn mt-2" onClick={runGithub} disabled={busy}>{busy ? <Spinner /> : "找项目"}</button>
          {githubItems.length > 0 && <div className="mt-3"><LinkList items={githubItems} /></div>}
        </Card>
        <Card title="格式检查">
          <input className="campus-input mb-2" value={formatTitle} onChange={(e) => setFormatTitle(e.target.value)} />
          <textarea className="campus-input min-h-20" value={manuscript} onChange={(e) => setManuscript(e.target.value)} />
          <button className="campus-btn mt-2" onClick={runFormat} disabled={busy}>{busy ? <Spinner /> : "检查"}</button>
          <ul className="mt-3 space-y-1 text-sm">{formatItems.map((it) => <li key={it.name} className={it.passed ? "text-emerald-700" : "text-amber-700"}>{it.passed ? "✅ PASS" : "⚠️ TODO"} · {it.name} — {it.detail}</li>)}</ul>
        </Card>
      </div>
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
                    {p.url ? (
                      <a href={p.url} target="_blank" rel="noopener noreferrer" className="font-medium text-campus-600 underline decoration-campus-300 underline-offset-2 hover:text-campus-700">{p.title}</a>
                    ) : (
                      <p className="font-medium">{p.title}</p>
                    )}
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
  const [mood, setMood] = useState("还不错");
  const [sleep, setSleep] = useState(7);
  const [exercise, setExercise] = useState("散步 20 分钟");
  const [health, setHealth] = useState<Record<string, unknown>[]>([]);
  const [destination, setDestination] = useState("上海");
  const [trip, setTrip] = useState<Record<string, unknown>[]>([]);
  const [guideQuery, setGuideQuery] = useState("借教室");
  const [guides, setGuides] = useState<{ title: string; steps: string[] }[]>([]);
  const [busy, setBusy] = useState(false);

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
  const addHealth = () => api.healthAdd({ mood, sleep_hours: sleep, exercise }).then((r) => setHealth(r.records)).catch((e: Error) => setErr(e.message));
  const makeTrip = () => { setBusy(true); api.travelPlan({ destination, days: 2, budget: 800 }).then((r) => setTrip(r.itinerary)).catch((e: Error) => setErr(e.message)).finally(() => setBusy(false)); };
  const findGuide = () => api.campusGuide(guideQuery).then((r) => setGuides(r.guides)).catch((e: Error) => setErr(e.message));

  return (
    <>
      <PageHeader title="生活" subtitle="日程 · 生日纪念日提醒 · 每日秘书日志。" />
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="日程日历">
          <MonthCalendar events={events} onDelete={delEvent} />
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

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="健康 Check-in">
          <input className="campus-input mb-2" value={mood} onChange={(e) => setMood(e.target.value)} placeholder="心情" />
          <input className="campus-input mb-2" type="number" value={sleep} onChange={(e) => setSleep(Number(e.target.value))} placeholder="睡眠小时" />
          <input className="campus-input mb-2" value={exercise} onChange={(e) => setExercise(e.target.value)} placeholder="运动" />
          <button className="campus-btn" onClick={addHealth}>记录</button>
          <p className="mt-3 text-sm text-ink-700/70">最近 {health.length} 条健康记录。</p>
        </Card>
        <Card title="旅行 / 娱乐计划">
          <input className="campus-input mb-2" value={destination} onChange={(e) => setDestination(e.target.value)} />
          <button className="campus-btn" onClick={makeTrip} disabled={busy}>{busy ? <Spinner /> : "生成计划"}</button>
          <ul className="mt-3 space-y-2 text-sm">{trip.map((d, i) => <li key={i} className="rounded border border-ink-100 p-2">Day {String(d.day)} · {String(d.morning)} / {String(d.afternoon)}</li>)}</ul>
        </Card>
        <Card title="校园办事指南">
          <input className="campus-input mb-2" value={guideQuery} onChange={(e) => setGuideQuery(e.target.value)} />
          <button className="campus-btn" onClick={findGuide}>查询</button>
          <ul className="mt-3 space-y-2 text-sm">{guides.map((g) => <li key={g.title} className="rounded border border-ink-100 p-2"><span className="font-medium">{g.title}</span><p className="text-xs text-ink-700/70">{g.steps.join(" → ")}</p></li>)}</ul>
        </Card>
      </div>
    </>
  );
}

/* ---------------- Club / Practice ---------------- */
export function ClubPage() {
  const [topic, setTopic] = useState("暑期社会实践推进会");
  const [notes, setNotes] = useState("确定调研对象。下周完成预算表。小王负责联系社区。");
  const [org, setOrg] = useState("AI 学习社");
  const [purpose, setPurpose] = useState("邀请老师担任活动指导");
  const [minutes, setMinutes] = useState<string[]>([]);
  const [copy, setCopy] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  return (
    <>
      <PageHeader title="社团 / 实践" subtitle="会议纪要、招新文案、邮件草稿。" />
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="会议纪要">
          <input className="campus-input mb-2" value={topic} onChange={(e) => setTopic(e.target.value)} />
          <textarea className="campus-input min-h-24" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <button className="campus-btn mt-2" onClick={() => { setBusy("minutes"); api.meetingMinutes({ topic, notes }).then((r) => setMinutes(r.minutes.todo)).catch((e: Error) => setErr(e.message)).finally(() => setBusy(null)); }} disabled={busy !== null}>{busy === "minutes" ? <Spinner /> : "生成"}</button>
          <ul className="mt-3 space-y-1 text-sm">{minutes.map((m, i) => <li key={i}>- {m}</li>)}</ul>
        </Card>
        <Card title="招新文案">
          <input className="campus-input mb-2" value={org} onChange={(e) => setOrg(e.target.value)} />
          <button className="campus-btn" onClick={() => { setBusy("copy"); api.recruitingCopy({ org }).then((r) => setCopy(`${r.copy.headline}\n${r.copy.body}`)).catch((e: Error) => setErr(e.message)).finally(() => setBusy(null)); }} disabled={busy !== null}>{busy === "copy" ? <Spinner /> : "生成"}</button>
          {copy && <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-ink-900 p-3 text-xs text-ink-100">{copy}</pre>}
        </Card>
        <Card title="邮件草稿">
          <input className="campus-input mb-2" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
          <button className="campus-btn" onClick={() => { setBusy("email"); api.emailDraft({ purpose, recipient: "老师" }).then((r) => setEmail(r.email)).catch((e: Error) => setErr(e.message)).finally(() => setBusy(null)); }} disabled={busy !== null}>{busy === "email" ? <Spinner /> : "生成"}</button>
          {email && <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-ink-900 p-3 text-xs text-ink-100">{email}</pre>}
        </Card>
      </div>
    </>
  );
}

/* ---------------- Career ---------------- */
export function CareerPage() {
  const [query, setQuery] = useState("AI 产品经理");
  const [city, setCity] = useState("上海");
  const [jobs, setJobs] = useState<{ id: string; title: string; company: string; city: string; url?: string; fit: number; reason: string }[]>([]);
  const [role, setRole] = useState("AI 产品经理实习生");
  const [plan, setPlan] = useState<{ day: number; focus: string; task: string; minutes: number }[]>([]);
  const [questions, setQuestions] = useState<string[]>([]);
  const [saved, setSaved] = useState<Record<string, unknown>[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  useEffect(() => { api.savedJobs().then((r) => setSaved(r.jobs)).catch(() => undefined); }, []);
  const search = () => { setBusy("search"); setErr(null); api.jobSearch({ query, city }).then((r) => setJobs(r.jobs)).catch((e: Error) => setErr(e.message)).finally(() => setBusy(null)); };
  const makePlan = () => { setBusy("plan"); setErr(null); api.interviewPlan({ role, days: 7 }).then((r) => { setPlan(r.plan); setQuestions(r.questions); }).catch((e: Error) => setErr(e.message)).finally(() => setBusy(null)); };
  return (
    <>
      <PageHeader title="职业" subtitle="实习搜索、岗位保存和面试计划。" />
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="实习搜索">
          <div className="grid gap-2 md:grid-cols-[1fr_140px_auto]">
            <input className="campus-input" value={query} onChange={(e) => setQuery(e.target.value)} />
            <input className="campus-input" value={city} onChange={(e) => setCity(e.target.value)} />
            <button className="campus-btn" onClick={search} disabled={busy !== null}>{busy === "search" ? <Spinner /> : "搜索"}</button>
          </div>
          {jobs.length > 0 && <div className="mt-3"><LinkList items={jobs.map(j => ({ name: `${j.title} · ${j.company}`, url: j.url, reason: `${j.city} · 匹配度 ${j.fit} · ${j.reason}` }))} /></div>}
        </Card>
        <Card title="面试计划">
          <input className="campus-input mb-2" value={role} onChange={(e) => setRole(e.target.value)} />
          <button className="campus-btn" onClick={makePlan} disabled={busy !== null}>{busy === "plan" ? <Spinner /> : "生成 7 天计划"}</button>
          <ul className="mt-3 space-y-2 text-sm">{plan.map((p) => <li key={p.day} className="rounded border border-ink-100 p-2">Day {p.day} · {p.focus} · {p.minutes}min</li>)}</ul>
          {questions.length > 0 && <p className="mt-3 text-sm text-campus-700">练习题：{questions[0]}</p>}
        </Card>
      </div>
      <Card title="已保存岗位">
        <p className="text-sm text-ink-700/70">{saved.length} 个岗位已保存。</p>
      </Card>
    </>
  );
}

/* ---------------- Settings ---------------- */
export function SettingsPage() {
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [agentName, setAgentName] = useState("Campus");
  const [nameInput, setNameInput] = useState("");
  const [autoLearnReport, setAutoLearnReport] = useState<string | null>(null);
  useEffect(() => {
    api.settingsStatus().then(setStatus).catch((e: Error) => setErr(e.message));
    api.getAgentName().then(r => { setAgentName(r.name); setNameInput(r.name); }).catch(() => {});
  }, []);
  const saveName = () => {
    api.setAgentName(nameInput).then(r => setAgentName(r.name)).catch((e: Error) => setErr(e.message));
  };
  const runAutoLearn = () => {
    setAutoLearnReport("running...");
    api.triggerAutoLearn(false).then(r => {
      setAutoLearnReport(`processed: ${r.processed} | preferences: ${r.preferences_written} | skills: ${r.skills_created + r.skills_updated} | knowledge: ${r.knowledge_written}`);
    }).catch((e: Error) => setAutoLearnReport(`error: ${e.message}`));
  };
  const mobile = status?.mobile as { ok: boolean; channels?: { feishu?: { ok?: boolean; configured?: boolean }; qq?: { ok?: boolean; configured?: boolean } } } | undefined;
  return (
    <>
      <PageHeader title="设置" subtitle="本地路径、LLM、skills、Notion、移动推送和外部 provider readiness。" />
      <Err e={err} />
      <div className="mb-6 rounded-xl border border-campus-200 bg-campus-50/50 p-5">
        <h3 className="mb-3 font-semibold text-campus-800">Agent 名称</h3>
        <div className="flex gap-2">
          <input
            value={nameInput}
            onChange={e => setNameInput(e.target.value)}
            className="flex-1 rounded-lg border border-ink-200 px-3 py-2 text-sm focus:border-campus-400 focus:outline-none"
            placeholder="给你的秘书起个名字"
          />
          <button onClick={saveName} className="rounded-lg bg-campus-600 px-4 py-2 text-sm font-medium text-white hover:bg-campus-700 transition">保存</button>
        </div>
        <p className="mt-2 text-xs text-ink-700/60">当前名称「{agentName}」会显示在侧边栏。改名后刷新页面生效。</p>
      </div>
      <div className="mb-6 rounded-xl border border-ink-200 bg-white p-5">
        <h3 className="mb-3 font-semibold text-ink-800">Auto-Learn（从用户纠正学习）</h3>
        <p className="mb-3 text-sm text-ink-700/70">回顾用户对 run 产物的修正，自动写入偏好记忆或创建/更新 skill。每日定时运行，也可手动触发。</p>
        <button onClick={runAutoLearn} className="rounded-lg bg-ink-800 px-4 py-2 text-sm font-medium text-white hover:bg-ink-900 transition">手动触发 Auto-Learn</button>
        {autoLearnReport && <p className="mt-2 text-sm text-ink-700/80">{autoLearnReport}</p>}
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card title="CAMPUS_HOME">
          <pre className="overflow-x-auto text-xs">{status?.campus_home || "loading"}</pre>
          <p className="mt-2 text-sm text-ink-700/70">branch {status?.branch || "unknown"} · v{status?.version || ""}</p>
        </Card>
        <Card title="LLM">
          <p className="text-lg font-semibold">{status?.llm.ok ? "✅ ready" : "⚪ offline fallback"}</p>
          <p className="text-sm text-ink-700/70">{status?.llm.error || "真实模型可用"}</p>
        </Card>
        <Card title="Skills">
          <p className="text-3xl font-semibold">{(status?.skills.vendor.length || 0) + (status?.skills.campus.length || 0)}</p>
          <p className="text-sm text-ink-700/70">missing: {status?.skills.missing_core.join(", ") || "none"}</p>
        </Card>
        <Card title="Notion">
          <p className="text-lg font-semibold">{status?.notion.ok ? "✅ ready" : "⚪ local mirror"}</p>
          <p className="text-sm text-ink-700/70">{status?.notion.local_mirror_dir}</p>
        </Card>
        <Card title="Mobile">
          <p className="text-lg font-semibold">{status?.mobile.ok ? "✅ configured" : "⚪ not configured"}</p>
          <div className="mt-1 text-sm text-ink-700/70">
            <p>飞书: {mobile?.channels?.feishu?.ok ? "✅" : mobile?.channels?.feishu?.configured ? "⚠️ auth" : "⚪"}</p>
            <p>QQ: {mobile?.channels?.qq?.ok ? "✅" : mobile?.channels?.qq?.configured ? "⚠️ auth" : "⚪"}</p>
          </div>
        </Card>
        <Card title="Smoke">
          <pre className="whitespace-pre-wrap text-xs">{status?.smoke_command}</pre>
        </Card>
      </div>
    </>
  );
}
