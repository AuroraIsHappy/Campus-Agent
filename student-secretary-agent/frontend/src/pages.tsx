import { useEffect, useState, type ReactNode } from "react";
import { api, type DemoAResult, type DemoBResult, type DemoCResult, type DemoStatus, type MemoryHit, type Profile, type Task, type CalEvent, type Anniversary, type DailyLog, type ResearchDigest, type ResearchTopic, type RunRecord, type AgentRunResult, type SettingsStatus } from "./api";

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
  const [mode, setMode] = useState("offline");
  const [result, setResult] = useState<AgentRunResult | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => api.agentRuns().then((r) => setRuns(r.runs)).catch((e: Error) => setErr(e.message));
  useEffect(() => { refresh(); }, []);
  const run = () => {
    setBusy(true); setErr(null);
    api.agentRun({ message, mode })
      .then((r) => { setResult(r); return refresh(); })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };

  return (
    <>
      <PageHeader title="秘书" subtitle="一句话交给 Campus-Agent，自动路由到学习、科研、生活、社团或职业工作流。" />
      <Err e={err} />
      <Card title="新任务">
        <div className="grid gap-3 md:grid-cols-[1fr_160px]">
          <textarea className="campus-input min-h-28" value={message} onChange={(e) => setMessage(e.target.value)} />
          <div className="grid content-start gap-2">
            <select className="campus-input" value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="offline">offline</option>
              <option value="auto">auto</option>
              <option value="real">real</option>
            </select>
            <button className="campus-btn" onClick={run} disabled={busy || !message.trim()}>{busy ? "运行中..." : "开始"}</button>
          </div>
        </div>
        {result && (
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <Metric label="领域" value={result.domain} />
            <Metric label="意图" value={result.intent} />
            <Metric label="状态" value={result.status} />
            <Metric label="产物" value={String(result.artifacts.length)} />
          </div>
        )}
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

  const refresh = () => api.learningDashboard().then(setDashboard).catch((e: Error) => setErr(e.message));
  useEffect(() => { refresh(); }, []);
  const makeCards = () => { setBusy(true); api.flashcards({ topic, source_text: source, count: 6 }).then((r) => setCards(r.flashcards)).then(refresh).catch((e: Error) => setErr(e.message)).finally(() => setBusy(false)); };
  const addDeadline = () => api.addDeadline({ title: deadlineTitle, due: deadlineDue, course: topic }).then(refresh).catch((e: Error) => setErr(e.message));
  const runQuiz = () => { setBusy(true); api.quizRun({ topic, source_text: source, count: 4 }).then((r) => setQuestions(r.questions)).then(refresh).catch((e: Error) => setErr(e.message)).finally(() => setBusy(false)); };
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
          <button className="campus-btn" onClick={makeCards} disabled={busy}>生成卡片</button>
          <div className="mt-3 grid gap-2">
            {cards.map((c) => <div key={c.id} className="rounded-lg border border-ink-100 p-3 text-sm"><p className="font-medium">{c.front}</p><p className="mt-1 text-ink-700/70">{c.back}</p><span className="campus-chip mt-2">due {c.due}</span></div>)}
          </div>
        </Card>
        <Card title="每日 Quiz">
          <button className="campus-btn" onClick={runQuiz} disabled={busy}>生成 quiz</button>
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
      <DemoBPage />
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
  const [idea, setIdea] = useState("我想研究本科生个人秘书 agent 如何做长期记忆");
  const [githubTopic, setGithubTopic] = useState("student agent");
  const [githubItems, setGithubItems] = useState<{ name: string; url: string; stars: number; reason: string }[]>([]);
  const [formatTitle, setFormatTitle] = useState("Campus-Agent: A Personal Secretary for Students");
  const [manuscript, setManuscript] = useState("Abstract: ...\nFig. 1 shows the system.\nReferences\n[1] Demo.");
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
    api.researchIdea({ idea, mode: "auto" })
      .then((d) => { setLatest(d); refreshAll(); })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };
  const runGithub = () => api.githubTrending({ topic: githubTopic }).then((r) => setGithubItems(r.items)).catch((e: Error) => setErr(e.message));
  const runFormat = () => api.formatCheck({ title: formatTitle, manuscript }).then((r) => setFormatItems(r.items)).catch((e: Error) => setErr(e.message));

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
          <button className="campus-btn mt-2" onClick={runGithub}>找项目</button>
          <ul className="mt-3 space-y-2 text-sm">{githubItems.map((g) => <li key={g.name} className="rounded border border-ink-100 p-2">{g.name} · {g.stars} stars<p className="text-xs text-ink-700/60">{g.reason}</p></li>)}</ul>
        </Card>
        <Card title="格式检查">
          <input className="campus-input mb-2" value={formatTitle} onChange={(e) => setFormatTitle(e.target.value)} />
          <textarea className="campus-input min-h-20" value={manuscript} onChange={(e) => setManuscript(e.target.value)} />
          <button className="campus-btn mt-2" onClick={runFormat}>检查</button>
          <ul className="mt-3 space-y-1 text-sm">{formatItems.map((it) => <li key={it.name} className={it.passed ? "text-emerald-700" : "text-amber-700"}>{it.passed ? "PASS" : "TODO"} · {it.name}</li>)}</ul>
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
  const [mood, setMood] = useState("还不错");
  const [sleep, setSleep] = useState(7);
  const [exercise, setExercise] = useState("散步 20 分钟");
  const [health, setHealth] = useState<Record<string, unknown>[]>([]);
  const [destination, setDestination] = useState("上海");
  const [trip, setTrip] = useState<Record<string, unknown>[]>([]);
  const [guideQuery, setGuideQuery] = useState("借教室");
  const [guides, setGuides] = useState<{ title: string; steps: string[] }[]>([]);

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
  const makeTrip = () => api.travelPlan({ destination, days: 2, budget: 800 }).then((r) => setTrip(r.itinerary)).catch((e: Error) => setErr(e.message));
  const findGuide = () => api.campusGuide(guideQuery).then((r) => setGuides(r.guides)).catch((e: Error) => setErr(e.message));

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
          <button className="campus-btn" onClick={makeTrip}>生成计划</button>
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
  return (
    <>
      <PageHeader title="社团 / 实践" subtitle="会议纪要、招新文案、邮件草稿和社会实践 Demo。" />
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="会议纪要">
          <input className="campus-input mb-2" value={topic} onChange={(e) => setTopic(e.target.value)} />
          <textarea className="campus-input min-h-24" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <button className="campus-btn mt-2" onClick={() => api.meetingMinutes({ topic, notes }).then((r) => setMinutes(r.minutes.todo)).catch((e: Error) => setErr(e.message))}>生成</button>
          <ul className="mt-3 space-y-1 text-sm">{minutes.map((m, i) => <li key={i}>- {m}</li>)}</ul>
        </Card>
        <Card title="招新文案">
          <input className="campus-input mb-2" value={org} onChange={(e) => setOrg(e.target.value)} />
          <button className="campus-btn" onClick={() => api.recruitingCopy({ org }).then((r) => setCopy(`${r.copy.headline}\n${r.copy.body}`)).catch((e: Error) => setErr(e.message))}>生成</button>
          {copy && <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-ink-900 p-3 text-xs text-ink-100">{copy}</pre>}
        </Card>
        <Card title="邮件草稿">
          <input className="campus-input mb-2" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
          <button className="campus-btn" onClick={() => api.emailDraft({ purpose, recipient: "老师" }).then((r) => setEmail(r.email)).catch((e: Error) => setErr(e.message))}>生成</button>
          {email && <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-ink-900 p-3 text-xs text-ink-100">{email}</pre>}
        </Card>
      </div>
      <DemoCenterPage />
    </>
  );
}

/* ---------------- Career ---------------- */
export function CareerPage() {
  const [query, setQuery] = useState("AI 产品经理");
  const [city, setCity] = useState("上海");
  const [jobs, setJobs] = useState<{ id: string; title: string; company: string; city: string; fit: number; reason: string }[]>([]);
  const [role, setRole] = useState("AI 产品经理实习生");
  const [plan, setPlan] = useState<{ day: number; focus: string; task: string; minutes: number }[]>([]);
  const [questions, setQuestions] = useState<string[]>([]);
  const [saved, setSaved] = useState<Record<string, unknown>[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api.savedJobs().then((r) => setSaved(r.jobs)).catch(() => undefined); }, []);
  const search = () => api.jobSearch({ query, city }).then((r) => setJobs(r.jobs)).catch((e: Error) => setErr(e.message));
  const save = (job: Record<string, unknown>) => api.saveJob(job).then((r) => setSaved(r.jobs)).catch((e: Error) => setErr(e.message));
  const makePlan = () => api.interviewPlan({ role, days: 7 }).then((r) => { setPlan(r.plan); setQuestions(r.questions); }).catch((e: Error) => setErr(e.message));
  return (
    <>
      <PageHeader title="职业" subtitle="实习 fallback 搜索、岗位保存和面试计划。" />
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="实习搜索">
          <div className="grid gap-2 md:grid-cols-[1fr_140px_auto]">
            <input className="campus-input" value={query} onChange={(e) => setQuery(e.target.value)} />
            <input className="campus-input" value={city} onChange={(e) => setCity(e.target.value)} />
            <button className="campus-btn" onClick={search}>搜索</button>
          </div>
          <ul className="mt-3 space-y-2 text-sm">{jobs.map((j) => <li key={j.id} className="rounded border border-ink-100 p-3"><div className="flex justify-between gap-2"><span className="font-medium">{j.title} · {j.company}</span><button className="text-campus-700" onClick={() => save(j)}>保存</button></div><p className="text-xs text-ink-700/60">{j.city} · fit {j.fit} · {j.reason}</p></li>)}</ul>
        </Card>
        <Card title="面试计划">
          <input className="campus-input mb-2" value={role} onChange={(e) => setRole(e.target.value)} />
          <button className="campus-btn" onClick={makePlan}>生成 7 天计划</button>
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
  useEffect(() => { api.settingsStatus().then(setStatus).catch((e: Error) => setErr(e.message)); }, []);
  return (
    <>
      <PageHeader title="设置" subtitle="本地路径、LLM、skills、Notion、移动推送和外部 provider readiness。" />
      <Err e={err} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card title="CAMPUS_HOME">
          <pre className="overflow-x-auto text-xs">{status?.campus_home || "loading"}</pre>
          <p className="mt-2 text-sm text-ink-700/70">branch {status?.branch || "unknown"} · v{status?.version || ""}</p>
        </Card>
        <Card title="LLM">
          <p className="text-lg font-semibold">{status?.llm.ok ? "ready" : "offline fallback"}</p>
          <p className="text-sm text-ink-700/70">{status?.llm.error || "真实模型可用"}</p>
        </Card>
        <Card title="Skills">
          <p className="text-3xl font-semibold">{(status?.skills.vendor.length || 0) + (status?.skills.campus.length || 0)}</p>
          <p className="text-sm text-ink-700/70">missing: {status?.skills.missing_core.join(", ") || "none"}</p>
        </Card>
        <Card title="Notion">
          <p className="text-lg font-semibold">{status?.notion.ok ? "ready" : "local mirror"}</p>
          <p className="text-sm text-ink-700/70">{status?.notion.local_mirror_dir}</p>
        </Card>
        <Card title="Mobile">
          <p className="text-lg font-semibold">{status?.mobile.ok ? "configured" : "not configured"}</p>
          <p className="text-sm text-ink-700/70">{JSON.stringify(status?.mobile.channels || {})}</p>
        </Card>
        <Card title="Smoke">
          <pre className="whitespace-pre-wrap text-xs">{status?.smoke_command}</pre>
        </Card>
      </div>
    </>
  );
}
