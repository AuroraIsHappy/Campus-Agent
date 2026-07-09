import { useEffect, useState } from "react";
import { ChatPage } from "./Chat";
import { TasksView, CalendarView, PersonaView, MemoryView, SettingsView } from "./Views";
import { OnboardingPage, DashboardPage } from "./pages";
import { api } from "./api";

type View = "chat" | "dashboard" | "tasks" | "calendar" | "persona" | "memory" | "settings" | "onboarding";

interface NavSection {
  title: string;
  items: { key: View; label: string; icon: string }[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "对话",
    items: [
      { key: "chat", label: "秘书", icon: "💬" },
    ],
  },
  {
    title: "查看",
    items: [
      { key: "tasks", label: "任务", icon: "📋" },
      { key: "calendar", label: "日历", icon: "📅" },
      { key: "memory", label: "记忆", icon: "❖" },
      { key: "dashboard", label: "仪表盘", icon: "◆" },
    ],
  },
  {
    title: "配置",
    items: [
      { key: "persona", label: "人格", icon: "🎭" },
      { key: "settings", label: "设置", icon: "⚙" },
    ],
  },
  {
    title: "引导",
    items: [
      { key: "onboarding", label: "新手引导", icon: "✦" },
    ],
  },
];

export default function App() {
  const [view, setView] = useState<View>("chat");
  const [agentName, setAgentName] = useState("Campus");

  useEffect(() => {
    api.getAgentName().then((r) => setAgentName(r.name)).catch(() => {});
  }, []);

  const initial = agentName.charAt(0).toUpperCase() || "C";
  const isChat = view === "chat";

  return (
    <div className="flex h-screen bg-[#fdf6e3]">
      <aside className="w-60 shrink-0 border-r border-ink-200 bg-[#fffef9] flex flex-col">
        <div className="px-5 py-6">
          <div className="flex items-center gap-2.5">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-campus-400 to-campus-600 font-bold text-white text-lg shadow-sm">{initial}</div>
            <div>
              <p className="font-semibold leading-tight text-ink-900">{agentName}</p>
              <p className="text-xs text-ink-700/60">你的专属秘书</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto px-3">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="mb-4">
              <p className="mb-1.5 px-3 text-xs font-semibold uppercase tracking-wider text-ink-700/40">{section.title}</p>
              {section.items.map((n) => (
                <button
                  key={n.key}
                  onClick={() => setView(n.key)}
                  className={`mb-0.5 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                    view === n.key ? "bg-campus-100 font-medium text-campus-800 shadow-sm" : "text-ink-700 hover:bg-ink-100"
                  }`}
                >
                  <span className="w-5 text-center">{n.icon}</span>
                  {n.label}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="border-t border-ink-200 px-5 py-3">
          <p className="text-xs text-ink-700/50">Phase 9 · v0.9.0</p>
        </div>
      </aside>
      <main className="flex-1 overflow-hidden">
        {isChat ? (
          <ChatPage />
        ) : (
          <div className="h-full overflow-y-auto">
            {view === "dashboard" && <DashboardPage />}
            {view === "tasks" && <TasksView />}
            {view === "calendar" && <CalendarView />}
            {view === "persona" && <PersonaView />}
            {view === "memory" && <MemoryView />}
            {view === "settings" && <SettingsView />}
            {view === "onboarding" && <OnboardingPage />}
          </div>
        )}
      </main>
    </div>
  );
}
