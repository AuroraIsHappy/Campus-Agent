import { useEffect, useState } from "react";
import { ChatPage } from "./Chat";
import { TasksView, CalendarView, PersonaView, MemoryView, SettingsView } from "./Views";
import { OnboardingPage, DashboardPage } from "./pages";
import { api, type ConversationSummary } from "./api";

type AgentKind = "secretary" | "poetry";
type View = "entry" | "chat" | "dashboard" | "tasks" | "calendar" | "persona" | "memory" | "settings" | "onboarding";

export default function App() {
  const [view, setView] = useState<View>("entry");
  const [agent, setAgent] = useState<AgentKind>("secretary");
  const [recent, setRecent] = useState<ConversationSummary[]>([]);
  useEffect(() => { api.conversations().then(r => setRecent(r.conversations.slice(0, 3))).catch(() => {}); }, [view]);
  const enter = (kind: AgentKind) => { setAgent(kind); setView("chat"); };

  if (view === "entry") return <Entry recent={recent} enter={enter}/>;
  if (view === "chat") return <ChatPage initialAgent={agent} onHome={() => setView("entry")} onManage={v => setView(v as View)}/>;
  return <div className="management-shell"><aside><button className="brand-button" onClick={() => setView("entry")}><span className="brand-orbit">C</span><span><b>Campus</b><small>PERSONAL AGENT OS</small></span></button><button onClick={() => setView("chat")}>← 返回对话</button>{(["dashboard", "tasks", "calendar", "memory", "persona", "settings", "onboarding"] as View[]).map(v => <button key={v} className={view === v ? "active" : ""} onClick={() => setView(v)}>{({ dashboard: "仪表盘", tasks: "任务", calendar: "日历", memory: "记忆", persona: "人格", settings: "设置", onboarding: "新手引导" } as Record<string, string>)[v]}</button>)}</aside><main>{view === "dashboard" && <DashboardPage/>}{view === "tasks" && <TasksView/>}{view === "calendar" && <CalendarView/>}{view === "memory" && <MemoryView/>}{view === "persona" && <PersonaView/>}{view === "settings" && <SettingsView/>}{view === "onboarding" && <OnboardingPage/>}</main></div>;
}

function Entry({ recent, enter }: { recent: ConversationSummary[]; enter: (agent: AgentKind) => void }) {
  return <main className="agent-entry"><header><div className="entry-brand"><span className="brand-orbit">C</span><div><b>Campus</b><small>PERSONAL AGENT OS</small></div></div><span>{new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" })}</span></header><section className="entry-copy"><span className="eyebrow">CHOOSE A COMPANION</span><h1>今天，想和谁<br/>一起完成一件事？</h1><p>每个 Agent 都保留同一份关于你的记忆，但用不同的方式陪你抵达结果。</p></section><section className="agent-cards"><button onClick={() => enter("secretary")}><span className="card-index">01 / GENERALIST</span><i>✦</i><h2>Campus 秘书</h2><p>把学习、生活和长程任务交给一位了解你的行动伙伴。</p><b>开始对话 <em>↗</em></b></button><button className="poetry-card" onClick={() => enter("poetry")}><span className="card-index">02 / POETRY</span><i>羽</i><h2>诗隙</h2><p>从日常的一道缝隙出发，观察、追问，与你共同写一首诗。</p><b>沿着缝隙继续 <em>↗</em></b></button></section>{recent.length > 0 && <section className="recent-strip"><span>最近继续</span>{recent.map(c => <button key={c.id} onClick={() => enter(c.active_agent || "secretary")}><i>{c.active_agent === "poetry" ? "羽" : "✦"}</i><span>{c.title}<small>{c.message_count} 条消息</small></span><b>→</b></button>)}</section>}</main>;
}
