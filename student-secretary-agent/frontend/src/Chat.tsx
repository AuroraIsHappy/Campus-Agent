import { useEffect, useRef, useState } from "react";
import { api, type CanvasPayload, type ChatReply, type ConversationSummary } from "./api";

type AgentKind = "secretary" | "poetry";
type Action = "message" | "compose" | "revise" | "finalize";
interface Message { role: "user" | "assistant"; content: string; reply?: ChatReply; ts: number }

export function ChatPage({ initialAgent = "secretary", onHome, onManage }: { initialAgent?: AgentKind; onHome?: () => void; onManage?: (view: string) => void }) {
  const [agent, setAgent] = useState<AgentKind>(initialAgent);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [conversationId, setConversationId] = useState("");
  const [workflowId, setWorkflowId] = useState("");
  const [canvas, setCanvas] = useState<CanvasPayload>({ type: "empty", title: "等待一次共同创作", data: {}, editable: false, actions: [] });
  const [actions, setActions] = useState<NonNullable<ChatReply["suggested_actions"]>>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [canvasOpen, setCanvasOpen] = useState(true);
  const [mobilePane, setMobilePane] = useState<"chat" | "canvas">("chat");
  const [navOpen, setNavOpen] = useState(false);
  const [split, setSplit] = useState(52);
  const scrollRef = useRef<HTMLDivElement>(null);

  const refresh = () => api.conversations().then(r => setConversations(r.conversations)).catch(() => {});
  useEffect(() => { refresh(); }, []);
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [messages, busy]);

  const reset = (nextAgent = agent) => {
    setAgent(nextAgent); setMessages([]); setConversationId(""); setWorkflowId(""); setActions([]);
    setCanvas({ type: "empty", title: nextAgent === "poetry" ? "诗稿尚未出现" : "等待 Agent 的下一件产物", data: {}, editable: false, actions: [] });
    setMobilePane("chat"); setNavOpen(false);
  };

  const loadConversation = (summary: ConversationSummary) => {
    api.conversation(summary.id).then(c => {
      setConversationId(c.id); setWorkflowId(c.workflow_id || ""); setAgent(c.active_agent || "secretary");
      setCanvas(c.canvas || { type: "empty", title: "这段对话还没有产物", data: {}, editable: false, actions: [] });
      setMessages(c.messages.map(m => ({ role: m.role as Message["role"], content: m.content, ts: m.ts * 1000 })));
      setActions([]); setNavOpen(false);
    });
  };

  const send = (action: Action = "message", override?: string, context: Record<string, unknown> = {}) => {
    const message = (override ?? input).trim();
    if (busy || (action === "message" && !message)) return;
    setBusy(true); setInput("");
    if (message) setMessages(m => [...m, { role: "user", content: message, ts: Date.now() }]);
    api.agentChat({ message: message || action, conversation_id: conversationId, agent, workflow_id: workflowId, action, context, mode: "auto" })
      .then(r => {
        if (!r.ok) throw new Error(r.error || "请求失败");
        setConversationId(r.conversation_id); setWorkflowId(r.workflow_id || workflowId);
        if (r.active_agent && r.active_agent !== agent) setAgent(r.active_agent);
        setMessages(m => [...m, { role: "assistant", content: r.reply, reply: r, ts: Date.now() }]);
        if (r.canvas) setCanvas(r.canvas); else if (r.artifacts?.length) setCanvas({ type: "artifact-list", title: "本次任务产物", data: { artifacts: r.artifacts }, editable: false, actions: [] });
        setActions(r.suggested_actions || []); refresh();
      })
      .catch((e: Error) => setMessages(m => [...m, { role: "assistant", content: `这一步没有完成：${e.message}`, ts: Date.now() }]))
      .finally(() => setBusy(false));
  };

  return <div className="workbench">
    <button className="mobile-menu" onClick={() => setNavOpen(true)} aria-label="打开导航">☰</button>
    <aside className={`workbench-nav ${navOpen ? "open" : ""}`}>
      <button className="brand-button" onClick={onHome}><span className="brand-orbit">C</span><span><b>Campus</b><small>PERSONAL AGENT OS</small></span></button>
      <button className="new-chat" onClick={() => reset()}>＋ 新对话</button>
      <p className="nav-label">同行的 Agent</p>
      <button className={`agent-row ${agent === "secretary" ? "active" : ""}`} onClick={() => reset("secretary")}><span>✦</span><span>Campus 秘书<small>学习、生活与长程任务</small></span></button>
      <button className={`agent-row poetry ${agent === "poetry" ? "active" : ""}`} onClick={() => reset("poetry")}><span>羽</span><span>诗隙<small>观察日常，共同写一首诗</small></span></button>
      <p className="nav-label history-label">最近对话</p>
      <div className="history-list">{conversations.slice(0, 12).map(c => <button key={c.id} onClick={() => loadConversation(c)} className={conversationId === c.id ? "current" : ""}><span>{c.active_agent === "poetry" ? "羽" : "·"}</span><span>{c.title || "新对话"}<small>{new Date(c.updated_at * 1000).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}</small></span></button>)}</div>
      <div className="manage-links"><button onClick={() => onManage?.("tasks")}>任务</button><button onClick={() => onManage?.("calendar")}>日历</button><button onClick={() => onManage?.("memory")}>记忆</button><button onClick={() => onManage?.("settings")}>设置</button></div>
      <button className="nav-dismiss" onClick={() => setNavOpen(false)}>收起导航</button>
    </aside>

    <main className={`conversation-pane ${mobilePane !== "chat" ? "mobile-hidden" : ""}`} style={{ width: canvasOpen ? `${split}%` : "100%" }}>
      <header className="pane-head"><div><span className="status-dot"/><div><b>{agent === "poetry" ? "诗隙" : "Campus 秘书"}</b><small>{workflowId ? `创作 ${workflowId.slice(-6)}` : "准备回应"}</small></div></div><button onClick={() => setCanvasOpen(v => !v)}>{canvasOpen ? "隐藏产物" : "显示产物"}</button></header>
      <div className="message-stream" ref={scrollRef}>
        {messages.length === 0 && <Empty agent={agent} choose={setInput}/>} 
        {messages.map((m, i) => <MessageBubble key={`${m.ts}-${i}`} msg={m}/>)}
        {busy && <div className="assistant-message thinking"><i/><i/><i/><span>{agent === "poetry" ? "正在听这一刻里的停顿" : "正在整理线索"}</span></div>}
      </div>
      <div className="composer-wrap">
        {actions.some(a => a.action !== "message") && <div className="action-strip">{actions.filter(a => a.action !== "message").map(a => <button key={a.action} onClick={() => send(a.action, a.label, a.action === "finalize" ? { content: canvas.data.content, accept_medium_risk: true } : {})}>{a.label}</button>)}</div>}
        <div className="composer"><textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder={agent === "poetry" ? "说一个刚刚发生的具体瞬间…" : "告诉我你现在想完成什么…"} rows={1}/><button onClick={() => send()} disabled={busy || !input.trim()} aria-label="发送">↑</button></div>
        <small className="composer-note">Enter 发送 · Shift + Enter 换行</small>
      </div>
    </main>

    {canvasOpen && <><div className="split-handle" onPointerDown={() => { const move = (ev: PointerEvent) => setSplit(Math.min(66, Math.max(38, ((ev.clientX - 240) / (window.innerWidth - 240)) * 100))); const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); }; window.addEventListener("pointermove", move); window.addEventListener("pointerup", up); }} /><section className={`canvas-pane ${mobilePane !== "canvas" ? "mobile-hidden" : ""}`}><Canvas payload={canvas} onChange={data => setCanvas(c => ({ ...c, data }))} onAction={(action, context) => send(action, action === "revise" ? String(context.instruction || "修改诗稿") : action, context)}/></section></>}
    <nav className="mobile-tabs"><button className={mobilePane === "chat" ? "active" : ""} onClick={() => setMobilePane("chat")}>对话</button><button className={mobilePane === "canvas" ? "active" : ""} onClick={() => { setCanvasOpen(true); setMobilePane("canvas"); }}>产物</button></nav>
  </div>;
}

function Empty({ agent, choose }: { agent: AgentKind; choose: (x: string) => void }) {
  const suggestions = agent === "poetry" ? ["深夜回宿舍，便利店的灯还亮着", "把今天的雨写成一首诗"] : ["帮我安排下周的复习", "总结桌面上的数据结构讲义", "每天八点提醒我背单词"];
  return <div className="empty-conversation"><span>{agent === "poetry" ? "羽" : "✦"}</span><h1>{agent === "poetry" ? "从一道生活的缝隙开始。" : "今天，先完成哪一件事？"}</h1><p>{agent === "poetry" ? "不必完整。一个动作、一种颜色，或者一盏还亮着的灯就够了。" : "直接说出目标。复杂的部分交给我整理。"}</p><div>{suggestions.map(x => <button key={x} onClick={() => choose(x)}>{x}<b>↗</b></button>)}</div></div>;
}

function MessageBubble({ msg }: { msg: Message }) {
  return <div className={msg.role === "user" ? "user-message" : "assistant-message"}><MarkdownText text={msg.content}/>{msg.reply?.source_mode && <small>{msg.reply.active_agent === "poetry" ? "诗隙工作流" : msg.reply.multiagent ? "多智能体协作" : "Campus Agent"}</small>}</div>;
}

function Canvas({ payload, onChange, onAction }: { payload: CanvasPayload; onChange: (data: Record<string, any>) => void; onAction: (action: Action, context: Record<string, unknown>) => void }) {
  const [instruction, setInstruction] = useState("让语言更克制，保留我的具体细节");
  const poem = payload.data;
  return <div className="artifact-window"><header><span className="window-lights"><i/><i/><i/></span><span>{payload.title}</span><small>{payload.type === "poem" ? `POEM · V${poem.version || 1}` : "LIVE ARTIFACT"}</small></header><div className="artifact-body">
    {payload.type === "empty" && <div className="canvas-empty"><span>⌁</span><h2>{payload.title}</h2><p>Agent 的产物会在这里展开，保持对话和结果同时可见。</p></div>}
    {payload.type === "poem" && <div className="poem-canvas"><div className="poem-meta"><span className={`risk ${poem.originality_risk}`}>{poem.originality_risk === "low" ? "原创性低风险" : poem.originality_risk === "medium" ? "需要确认相似性" : "需要改写"}</span><span>版本 {poem.version || 1}</span></div><input className="poem-title" value={poem.title || ""} readOnly={!payload.editable} onChange={e => onChange({ ...poem, title: e.target.value })}/><textarea className="poem-editor" value={poem.content || ""} readOnly={!payload.editable} onChange={e => onChange({ ...poem, content: e.target.value })}/><div className="poem-notes"><span>创作策略</span><p>{poem.inspiration?.notes || "保留具体物件，让情绪从动作中出现。"}</p></div>{payload.editable && <><label className="revision-field"><span>编辑希望</span><input value={instruction} onChange={e => setInstruction(e.target.value)}/></label><div className="canvas-actions"><button onClick={() => onAction("revise", { content: poem.content, instruction })}>请诗隙修改</button><button className="primary" disabled={poem.originality_risk === "high"} onClick={() => onAction("finalize", { content: poem.content, accept_medium_risk: true })}>确认并收入档案</button></div></>}</div>}
    {payload.type === "artifact-list" && <div className="artifact-list"><h2>{payload.title}</h2>{(payload.data.artifacts || []).map((a: any, i: number) => <div key={i}><span>0{i + 1}</span><p>{a.name}<small>{a.kind}</small></p></div>)}</div>}
    {payload.type === "markdown" && <div className="markdown-canvas"><MarkdownText text={String(payload.data.content || "")}/></div>}
    {payload.type === "mindmap" && <div className="mindmap-canvas"><MindNode node={payload.data.tree || payload.data}/></div>}
    {!(["empty", "poem", "artifact-list", "markdown", "mindmap"].includes(payload.type)) && <div className="markdown-canvas"><MarkdownText text={String(payload.data.content || JSON.stringify(payload.data, null, 2))}/></div>}
  </div></div>;
}

function MindNode({ node }: { node: any }) {
  if (!node || typeof node !== "object") return <span>{String(node || "")}</span>;
  const title = node.title || node.name || node.label || "主题";
  const children = node.children || node.items || [];
  return <div className="mind-node"><span>{title}</span>{Array.isArray(children) && children.length > 0 && <div>{children.map((child: any, i: number) => <MindNode node={child} key={i}/>)}</div>}</div>;
}

function MarkdownText({ text }: { text: string }) {
  return <>{text.split("\n").map((line, i) => line.trim() ? <p key={i}>{inline(line)}</p> : <br key={i}/>)}</>;
}
function inline(text: string) {
  const chunks = text.split(/(\*\*.*?\*\*|`.*?`|https?:\/\/\S+)/g);
  return chunks.map((part, i) => part.startsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part.startsWith("`") ? <code key={i}>{part.slice(1, -1)}</code> : /^https?:/.test(part) ? <a key={i} href={part} target="_blank" rel="noreferrer">{part}</a> : part);
}
