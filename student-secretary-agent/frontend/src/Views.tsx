/** Sidebar view components (Phase 9 — read-only views, not form modules). */

import { useEffect, useState, type ReactNode } from "react";
import { api, type Task, type CalEvent, type SettingsStatus, type MemoryRecord } from "./api";

/* ============ shared ============ */
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

/* ============ Tasks (with search) ============ */
export function TasksView() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.tasks().then((t) => setTasks(t.tasks)).catch((e: Error) => setErr(e.message));
  }, []);

  const filtered = tasks.filter((t) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return [t.title, t.body, t.domain, t.status, t.run_id, t.due]
      .filter(Boolean).some((f) => f!.toLowerCase().includes(q));
  });

  const tone = (s: string) =>
    s === "done" ? "bg-emerald-100 text-emerald-700" :
    s === "awaiting_human" ? "bg-amber-100 text-amber-700" :
    s === "todo" ? "bg-campus-100 text-campus-700" : "bg-ink-100 text-ink-700";

  return (
    <div className="mx-auto max-w-4xl p-8">
      <PageHeader title="任务" subtitle="搜索并查看你的所有学习/社团/科研任务。" />
      {err && <p className="text-sm text-red-600">{err}</p>}
      <div className="mb-4">
        <input
          className="campus-input"
          placeholder="🔍 搜索任务（标题、内容、领域、状态、关联运行…）"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <p className="mt-1 text-xs text-ink-700/50">{filtered.length} / {tasks.length} 个任务</p>
      </div>
      <Card>
        {filtered.length === 0 ? (
          <p className="text-sm text-ink-700/60">{tasks.length === 0 ? "暂无任务。" : "没有匹配的任务。"}</p>
        ) : (
          <ul className="divide-y divide-ink-100">
            {filtered.slice(0, 100).map((t) => (
              <li key={t.id} className="py-3">
                <button
                  className="flex w-full items-center justify-between text-left"
                  onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                >
                  <span className="font-medium text-ink-900">{t.title}</span>
                  <span className="flex gap-2">
                    {t.domain && <span className="campus-chip">{t.domain}</span>}
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${tone(t.status)}`}>{t.status}</span>
                  </span>
                </button>
                {expanded === t.id && (
                  <div className="mt-2 space-y-1 rounded-lg bg-ink-50 p-3 text-xs text-ink-700">
                    {t.body && <p><span className="font-semibold">内容：</span>{t.body}</p>}
                    {t.due && <p><span className="font-semibold">截止：</span>{t.due}</p>}
                    {t.run_id && <p><span className="font-semibold">关联运行：</span><span className="font-mono">{t.run_id}</span></p>}
                    <p><span className="font-semibold">ID：</span><span className="font-mono">{t.id}</span></p>
                    {t.metadata && Object.keys(t.metadata).length > 0 && (
                      <div>
                        <p className="font-semibold">元数据：</p>
                        <pre className="mt-1 overflow-x-auto rounded bg-ink-100 p-2 text-xs">{JSON.stringify(t.metadata, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

/* ============ Calendar (read-only view) ============ */
export function CalendarView() {
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.calendarList().then((r) => setEvents(r.events)).catch((e: Error) => setErr(e.message));
  }, []);
  return (
    <div className="mx-auto max-w-4xl p-8">
      <PageHeader title="日历" subtitle="查看你的日程（由秘书自动同步或手动添加）。" />
      {err && <p className="text-sm text-red-600">{err}</p>}
      <Card>
        {events.length === 0 ? (
          <p className="text-sm text-ink-700/60">暂无日程。让秘书帮你安排复习计划时会自动同步到这里。</p>
        ) : (
          <ul className="divide-y divide-ink-100">
            {events.sort((a, b) => (a.start || "").localeCompare(b.start || "")).map((e) => (
              <li key={e.id} className="flex items-center justify-between py-3">
                <div>
                  <span className="font-medium text-ink-900">{e.title}</span>
                  {e.rrule && <span className="campus-chip ml-2">{e.rrule}</span>}
                  {e.location && <span className="ml-2 text-xs text-ink-700/60">📍 {e.location}</span>}
                </div>
                <span className="text-xs text-ink-700/60 font-mono">{e.start}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

/* ============ Persona (view + switch) ============ */
export function PersonaView() {
  const [persona, setPersona] = useState("default");
  const [profile, setProfile] = useState<{ identity: string; major: string; persona: string } | null>(null);
  useEffect(() => {
    api.profile().then((r) => { setProfile(r.profile); setPersona(r.profile.persona || "default"); }).catch(() => {});
  }, []);
  const personas: Record<string, { label: string; desc: string }> = {
    default: { label: "默认秘书", desc: "简洁友好务实，先结论后依据" },
    feynman: { label: "费曼（启发式）", desc: "用类比和反问帮你理解" },
    lu_xun: { label: "鲁迅（犀利）", desc: "说真话，哪怕刺耳" },
  };
  return (
    <div className="mx-auto max-w-3xl p-8">
      <PageHeader title="人格设置" subtitle="选择你的秘书回复风格。" />
      <Card>
        <div className="grid gap-3">
          {Object.entries(personas).map(([key, p]) => (
            <button
              key={key}
              onClick={() => setPersona(key)}
              className={`flex items-center justify-between rounded-xl border p-4 text-left transition ${
                persona === key ? "border-campus-400 bg-campus-50" : "border-ink-200 bg-[#fffef9] hover:bg-ink-100"
              }`}
            >
              <div>
                <p className="font-semibold text-ink-900">{p.label}</p>
                <p className="text-sm text-ink-700/70">{p.desc}</p>
              </div>
              {persona === key && <span className="text-campus-600">✓</span>}
            </button>
          ))}
        </div>
        {profile && (
          <p className="mt-4 text-sm text-ink-700/60">
            当前身份：{profile.identity || "未设置"} · {profile.major || "未设置"}
          </p>
        )}
        <p className="mt-3 text-xs text-ink-700/50">
          人格风格会体现在主对话框的助手回复中。完整配置请前往新手引导。
        </p>
      </Card>
    </div>
  );
}

/* ============ Memory (browse + search + delete) ============ */
const LAYER_LABELS: Record<string, string> = {
  preferences: "偏好", task_log: "任务日志", task_board: "看板",
  knowledge: "知识", daily_log: "日志",
};

export function MemoryView() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<{ key: string; score: number; snippet: string; layer: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [allRecords, setAllRecords] = useState<MemoryRecord[]>([]);
  const [filterLayer, setFilterLayer] = useState<string>("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const loadAll = (layer?: string) => {
    setBusy(true);
    api.memoryAll(layer || undefined).then((r) => setAllRecords(r.records)).catch(() => {}).finally(() => setBusy(false));
  };
  useEffect(() => { loadAll(); }, []);

  const search = () => {
    if (!query.trim()) { loadAll(filterLayer); return; }
    setBusy(true);
    api.recall(query, 20).then((r) => setHits(r.results as never)).catch(() => {}).finally(() => setBusy(false));
  };

  const doDelete = (id: string) => {
    api.memoryDelete(id).then(() => {
      setAllRecords((rs) => rs.filter((r) => r.id !== id));
      setDeleteConfirm(null);
    }).catch(() => {});
  };

  const layers = ["", "preferences", "task_log", "task_board", "knowledge", "daily_log"];
  const totalSize = allRecords.reduce((s, r) => s + (r.content?.length || 0), 0);

  return (
    <div className="mx-auto max-w-4xl p-8">
      <PageHeader title="记忆" subtitle="浏览、搜索和管理秘书存储的记忆。可手动删除以释放空间。" />
      <Card>
        {/* search bar */}
        <div className="flex gap-2">
          <input className="campus-input" placeholder="搜索记忆…" value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()} />
          <button className="campus-btn shrink-0" onClick={search} disabled={busy}>{busy ? "…" : "搜索"}</button>
        </div>

        {/* search results */}
        {hits.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-700/50">搜索结果</p>
            <ul className="space-y-2">
              {hits.map((h, i) => (
                <li key={i} className="rounded-lg border border-ink-100 p-3 text-sm">
                  <div className="flex justify-between">
                    <span className="font-medium text-ink-900">{h.key}</span>
                    <span className="campus-chip">{LAYER_LABELS[h.layer] || h.layer}</span>
                  </div>
                  <p className="mt-1 text-ink-700/70">{h.snippet}</p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* all records browser */}
        <div className="mt-6 border-t border-ink-100 pt-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-ink-700/50">
              全部记忆（{allRecords.length} 条 · {Math.round(totalSize / 1024)}KB）
            </p>
            <div className="flex gap-2">
              <select
                className="campus-input w-auto text-xs"
                value={filterLayer}
                onChange={(e) => { setFilterLayer(e.target.value); loadAll(e.target.value); }}
              >
                {layers.map((l) => <option key={l} value={l}>{l ? LAYER_LABELS[l] || l : "全部层级"}</option>)}
              </select>
              <button className="campus-btn-ghost text-xs" onClick={() => loadAll(filterLayer)}>刷新</button>
            </div>
          </div>

          {allRecords.length === 0 ? (
            <p className="py-8 text-center text-sm text-ink-700/50">{busy ? "加载中…" : "暂无记忆记录。"}</p>
          ) : (
            <ul className="space-y-1.5">
              {allRecords.map((r) => (
                <li key={r.id} className="rounded-lg border border-ink-100 p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <button
                      className="flex flex-1 items-center gap-2 text-left"
                      onClick={() => setExpanded(expanded === r.id ? null : r.id)}
                    >
                      <span className="font-medium text-ink-900">{r.key}</span>
                      {r.pinned && <span className="text-campus-500" title="pinned">📌</span>}
                      <span className="campus-chip">{LAYER_LABELS[r.layer] || r.layer}</span>
                    </button>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-ink-700/40">
                        {new Date((r.created_at || 0) * 1000).toLocaleDateString()}
                      </span>
                      {deleteConfirm === r.id ? (
                        <div className="flex gap-1">
                          <button
                            className="rounded bg-red-500 px-2 py-0.5 text-xs text-white hover:bg-red-600"
                            onClick={() => doDelete(r.id)}
                          >确认删除</button>
                          <button
                            className="rounded bg-ink-200 px-2 py-0.5 text-xs text-ink-700 hover:bg-ink-300"
                            onClick={() => setDeleteConfirm(null)}
                          >取消</button>
                        </div>
                      ) : (
                        <button
                          className="rounded px-2 py-0.5 text-xs text-red-500 hover:bg-red-50"
                          onClick={() => setDeleteConfirm(r.id)}
                          title="删除此记忆"
                        >🗑</button>
                      )}
                    </div>
                  </div>
                  {expanded === r.id && (
                    <div className="mt-2 space-y-1 rounded-lg bg-ink-50 p-3 text-xs text-ink-700">
                      <p><span className="font-semibold">内容：</span>{r.content}</p>
                      <p><span className="font-semibold">ID：</span><span className="font-mono">{r.id}</span></p>
                      {r.metadata && Object.keys(r.metadata).length > 0 && (
                        <div>
                          <p className="font-semibold">元数据：</p>
                          <pre className="mt-1 overflow-x-auto rounded bg-ink-100 p-2 text-xs">{JSON.stringify(r.metadata, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>
    </div>
  );
}

/* ============ Settings (status) ============ */
export function SettingsView() {
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  useEffect(() => { api.settingsStatus().then(setStatus).catch(() => {}); }, []);
  const llm = status?.llm;
  const mobile = status?.mobile;
  return (
    <div className="mx-auto max-w-3xl p-8">
      <PageHeader title="设置" subtitle="系统状态与集成配置。" />
      <Card title="LLM">
        <p className="text-sm">模式：{llm?.mode || "?"} · {llm?.ok ? "✅ 可用" : "❌ 未就绪"}</p>
        {llm?.error && <p className="mt-1 text-xs text-red-600">{llm.error}</p>}
      </Card>
      <div className="mt-4" />
      <Card title="移动端推送">
        <div className="grid gap-2 text-sm">
          <p>飞书：{mobile?.channels?.feishu && typeof mobile.channels.feishu === "object" && "ok" in (mobile.channels.feishu as object)
            ? ((mobile.channels.feishu as { ok?: boolean }).ok ? "✅" : "❌") : "❌"}</p>
          <p>QQ：{mobile?.channels?.qq && typeof mobile.channels.qq === "object" && "ok" in (mobile.channels.qq as object)
            ? ((mobile.channels.qq as { ok?: boolean }).ok ? "✅" : "❌") : "❌"}</p>
        </div>
      </Card>
      <div className="mt-4" />
      <Card title="集成">
        <div className="grid gap-1 text-sm">
          <p>Notion：{status?.notion?.ok ? "✅" : "❌"}</p>
          <p>GitHub：{status?.providers?.github ? "✅" : "❌"}</p>
          <p>搜索：{status?.providers?.search ? "✅" : "❌"}</p>
        </div>
      </Card>
    </div>
  );
}
