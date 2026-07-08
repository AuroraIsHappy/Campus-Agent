import { useState } from "react";
import {
  DashboardPage, SecretaryPage, OnboardingPage, LearningPage, DemoBPage, DemoCenterPage, KanbanPage, PersonaPage, MemoryPage, LifePage, ResearchPage,
  ClubPage, CareerPage, SettingsPage,
} from "./pages";

type View = "dashboard" | "secretary" | "learning" | "research" | "life" | "club" | "career" | "kanban" | "memory" | "settings" | "onboarding" | "demo" | "demob" | "persona";

const NAV: { key: View; label: string; icon: string }[] = [
  { key: "dashboard", label: "仪表盘", icon: "◆" },
  { key: "secretary", label: "秘书", icon: "◎" },
  { key: "learning", label: "学习", icon: "▣" },
  { key: "research", label: "科研", icon: "◇" },
  { key: "life", label: "生活", icon: "◷" },
  { key: "club", label: "社团实践", icon: "▥" },
  { key: "career", label: "职业", icon: "◈" },
  { key: "kanban", label: "任务", icon: "▦" },
  { key: "memory", label: "记忆", icon: "❖" },
  { key: "settings", label: "设置", icon: "⚙" },
  { key: "onboarding", label: "新手引导", icon: "✦" },
  { key: "demo", label: "Demo 中心", icon: "△" },
];

export default function App() {
  const [view, setView] = useState<View>("dashboard");
  return (
    <div className="flex min-h-screen bg-ink-50">
      <aside className="w-60 shrink-0 border-r border-ink-200 bg-white">
        <div className="px-5 py-6">
          <div className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-lg bg-campus-600 font-bold text-white">C</div>
            <div>
              <p className="font-semibold leading-tight">Campus</p>
              <p className="text-xs text-ink-700/60">你的专属秘书</p>
            </div>
          </div>
        </div>
        <nav className="px-3">
          {NAV.map((n) => (
            <button
              key={n.key}
              onClick={() => setView(n.key)}
              className={`mb-1 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                view === n.key ? "bg-campus-50 font-medium text-campus-700" : "text-ink-700 hover:bg-ink-100"
              }`}
            >
              <span className="w-5 text-center">{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>
        <p className="px-5 py-4 text-xs text-ink-700/50">Phase 7 · 本地产品闭环</p>
      </aside>
      <main className="flex-1 overflow-x-hidden p-8">
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
      </main>
    </div>
  );
}
