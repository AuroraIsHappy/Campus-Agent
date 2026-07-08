import { useEffect, useState } from "react";
import {
  DashboardPage, SecretaryPage, OnboardingPage, LearningPage, DemoBPage, DemoCenterPage, KanbanPage, PersonaPage, MemoryPage, LifePage, ResearchPage,
  ClubPage, CareerPage, SettingsPage,
} from "./pages";
import { api } from "./api";

type View = "dashboard" | "secretary" | "learning" | "research" | "life" | "club" | "career" | "kanban" | "memory" | "settings" | "onboarding" | "demo" | "demob" | "persona";

interface NavSection {
  title: string;
  items: { key: View; label: string; icon: string }[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "概览",
    items: [
      { key: "dashboard", label: "仪表盘", icon: "◆" },
      { key: "secretary", label: "秘书", icon: "◎" },
    ],
  },
  {
    title: "任务域",
    items: [
      { key: "learning", label: "学习", icon: "▣" },
      { key: "research", label: "科研", icon: "◇" },
      { key: "life", label: "生活", icon: "◷" },
      { key: "club", label: "社团实践", icon: "▥" },
      { key: "career", label: "职业", icon: "◈" },
    ],
  },
  {
    title: "系统",
    items: [
      { key: "kanban", label: "任务", icon: "▦" },
      { key: "memory", label: "记忆", icon: "❖" },
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
  const [view, setView] = useState<View>("dashboard");
  const [agentName, setAgentName] = useState("Campus");

  useEffect(() => {
    api.getAgentName().then(r => setAgentName(r.name)).catch(() => {});
  }, []);

  const initial = agentName.charAt(0).toUpperCase() || "C";

  return (
    <div className="flex min-h-screen bg-ink-50">
      <aside className="w-64 shrink-0 border-r border-ink-200 bg-white flex flex-col">
        <div className="px-5 py-6">
          <div className="flex items-center gap-2.5">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-campus-500 to-campus-700 font-bold text-white text-lg shadow-sm">{initial}</div>
            <div>
              <p className="font-semibold leading-tight text-ink-900">{agentName}</p>
              <p className="text-xs text-ink-700/60">你的专属秘书</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto px-3">
          {NAV_SECTIONS.map(section => (
            <div key={section.title} className="mb-4">
              <p className="mb-1.5 px-3 text-xs font-semibold uppercase tracking-wider text-ink-700/40">{section.title}</p>
              {section.items.map(n => (
                <button
                  key={n.key}
                  onClick={() => setView(n.key)}
                  className={`mb-0.5 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                    view === n.key ? "bg-campus-50 font-medium text-campus-700 shadow-sm" : "text-ink-700 hover:bg-ink-100"
                  }`}
                >
                  <span className="w-5 text-center text-ink-700/60">{n.icon}</span>
                  {n.label}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="border-t border-ink-200 px-5 py-3">
          <p className="text-xs text-ink-700/50">Phase 8 · v0.8.0</p>
        </div>
      </aside>
      <main className="flex-1 overflow-x-hidden">
        <div className="mx-auto max-w-6xl p-8">
          {view === "dashboard" && <DashboardPage />}
          {view === "secretary" && <SecretaryPage />}
          {view === "learning" && <LearningPage />}
          {view === "onboarding" && <OnboardingPage />}
          {view === "demo" && <DemoCenterPage />}
          {view === "demob" && <DemoBPage />}
          {view === "research" && <ResearchPage />}
          {view === "life" && <LifePage />}
          {view === "club" && <ClubPage />}
          {view === "career" && <CareerPage />}
          {view === "kanban" && <KanbanPage />}
          {view === "persona" && <PersonaPage />}
          {view === "memory" && <MemoryPage />}
          {view === "settings" && <SettingsPage />}
        </div>
      </main>
    </div>
  );
}
