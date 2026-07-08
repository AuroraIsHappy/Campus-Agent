/** Chat-first main panel (Phase 9 — GOAL.md 飞书式聊天).

The primary interface: a Feishu-mobile-style chat dialog where the user types
any request and gets a natural-language assistant reply. Assistant bubbles
render markdown + clickable artifact links + mind-map tree + search evidence.
Supports multi-turn context (conversation_id) and clarification flows.
*/
import { useEffect, useRef, useState } from "react";
import { api, type ChatReply, type ConversationSummary } from "./api";

interface Message {
  role: "user" | "assistant";
  content: string;
  reply?: ChatReply;
  ts: number;
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [conversationId, setConversationId] = useState("");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const refreshConversations = () =>
    api.conversations().then((r) => setConversations(r.conversations)).catch(() => {});
  useEffect(() => { refreshConversations(); }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = () => {
    const msg = input.trim();
    if (!msg || busy) return;
    setBusy(true);
    setInput("");
    const userMsg: Message = { role: "user", content: msg, ts: Date.now() };
    setMessages((m) => [...m, userMsg]);
    api.agentChat({ message: msg, conversation_id: conversationId, mode: "auto" })
      .then((r) => {
        setConversationId(r.conversation_id);
        setMessages((m) => [...m, { role: "assistant", content: r.reply, reply: r, ts: Date.now() }]);
        refreshConversations();
      })
      .catch((e: Error) => {
        setMessages((m) => [...m, { role: "assistant", content: `⚠️ 出错了：${e.message}`, ts: Date.now() }]);
      })
      .finally(() => setBusy(false));
  };

  const loadConversation = (id: string) => {
    api.conversation(id).then((c) => {
      setConversationId(c.id);
      setMessages(c.messages.map((m) => ({ role: m.role as "user" | "assistant", content: m.content, ts: m.ts * 1000 })));
      setShowHistory(false);
    }).catch(() => {});
  };

  const newChat = () => {
    setMessages([]);
    setConversationId("");
  };

  return (
    <div className="flex h-full flex-col">
      {/* chat header */}
      <div className="flex items-center justify-between border-b border-ink-200 bg-[#fffef9] px-5 py-3">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold text-ink-900">秘书对话</h2>
          {conversationId && <span className="campus-chip">会话 {conversationId.slice(-8)}</span>}
        </div>
        <div className="flex gap-2">
          <button className="campus-btn-ghost text-xs" onClick={() => setShowHistory(!showHistory)}>
            历史
          </button>
          <button className="campus-btn-ghost text-xs" onClick={newChat}>
            新对话
          </button>
        </div>
      </div>

      {/* conversation history drawer */}
      {showHistory && (
        <div className="border-b border-ink-200 bg-[#fffef9] px-5 py-3 max-h-48 overflow-y-auto">
          {conversations.length === 0 ? (
            <p className="text-xs text-ink-700/50">暂无历史会话</p>
          ) : (
            <ul className="space-y-1">
              {conversations.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => loadConversation(c.id)}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-left text-xs hover:bg-ink-100"
                  >
                    <span className="font-medium text-ink-800">{c.title || "新对话"}</span>
                    <span className="text-ink-700/50">{c.message_count} 条</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center text-ink-700/50">
            <p className="text-2xl mb-2">💬</p>
            <p className="text-sm">和你的秘书聊聊吧 —— 任何需求都可以直接说</p>
            <div className="mt-4 grid gap-2 text-xs">
              <Suggestion text="总结桌面上那个数据结构讲义" onClick={() => setInput("总结桌面上那个数据结构讲义")} />
              <Suggestion text="下周机器学习考试帮我安排复习" onClick={() => setInput("下周机器学习考试帮我安排复习")} />
              <Suggestion text="找几篇 RLHF 论文存到 Zotero" onClick={() => setInput("找几篇 RLHF 论文存到 Zotero")} />
              <Suggestion text="每天8点提醒我背单词" onClick={() => setInput("每天8点提醒我背单词")} />
              <Suggestion text="帮我找学 Linux 的 GitHub 项目和公开课" onClick={() => setInput("帮我找学 Linux 的 GitHub 项目和公开课")} />
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} msg={m} />
        ))}
        {busy && (
          <div className="chat-assistant inline-flex items-center gap-2">
            <span className="animate-pulse">●</span>
            <span className="animate-pulse" style={{ animationDelay: "0.2s" }}>●</span>
            <span className="animate-pulse" style={{ animationDelay: "0.4s" }}>●</span>
            <span className="ml-1 text-ink-700/50">正在思考…</span>
          </div>
        )}
      </div>

      {/* input */}
      <div className="border-t border-ink-200 bg-[#fffef9] px-5 py-3">
        <div className="flex gap-2">
          <textarea
            className="campus-input min-h-[44px] max-h-32 resize-none"
            placeholder="输入任何需求…（Enter 发送，Shift+Enter 换行）"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
            }}
            rows={1}
          />
          <button className="campus-btn shrink-0" onClick={send} disabled={busy || !input.trim()}>
            {busy ? "…" : "发送"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Suggestion({ text, onClick }: { text: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-lg border border-ink-200 bg-[#fffef9] px-3 py-1.5 text-left text-ink-700 hover:border-campus-300 hover:bg-campus-50"
    >
      💡 {text}
    </button>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  if (msg.role === "user") {
    return <div className="chat-user">{msg.content}</div>;
  }
  return (
    <div className="chat-assistant">
      <MarkdownText text={msg.content} />
      {msg.reply?.artifacts && msg.reply.artifacts.length > 0 && (
        <div className="mt-2 border-t border-ink-100 pt-2">
          <p className="text-xs font-semibold text-ink-700/50 mb-1">产物（{msg.reply.artifacts.length}）</p>
          <ul className="space-y-0.5">
            {msg.reply.artifacts.slice(0, 6).map((a, i) => (
              <li key={i} className="text-xs text-campus-700">
                📎 {a.name}
              </li>
            ))}
          </ul>
        </div>
      )}
      {msg.reply?.source_mode && (
        <p className="mt-1 text-xs text-ink-700/40">
          {msg.reply.source_mode === "real_llm" ? "🤖 AI 生成" : msg.reply.source_mode}
          {msg.reply.multiagent ? " · 多智能体" : ""}
        </p>
      )}
    </div>
  );
}

/** Minimal markdown renderer (headings, bold, lists, links, code, paragraphs). */
function MarkdownText({ text }: { text: string }) {
  const lines = text.split("\n");
  const out: JSX.Element[] = [];
  let listItems: string[] = [];
  let listType: "ul" | "ol" | null = null;

  const flushList = () => {
    if (listItems.length > 0 && listType) {
      const Tag = listType;
      out.push(
        <Tag key={`list-${out.length}`}>
          {listItems.map((li, i) => <li key={i}><InlineMd text={li} /></li>)}
        </Tag>
      );
      listItems = [];
      listType = null;
    }
  };

  lines.forEach((line, i) => {
    const trimmed = line.trim();
    // heading
    const hm = trimmed.match(/^(#{1,3})\s+(.+)/);
    if (hm) {
      flushList();
      const level = hm[1].length;
      const cls = level === 1 ? "text-base font-bold" : level === 2 ? "text-sm font-bold" : "text-sm font-semibold";
      out.push(<p key={i} className={cls}><InlineMd text={hm[2]} /></p>);
      return;
    }
    // ordered list
    const om = trimmed.match(/^\d+\.\s+(.+)/);
    if (om) {
      if (listType !== "ol") { flushList(); listType = "ol"; }
      listItems.push(om[1]);
      return;
    }
    // unordered list
    const um = trimmed.match(/^[-*]\s+(.+)/);
    if (um) {
      if (listType !== "ul") { flushList(); listType = "ul"; }
      listItems.push(um[1]);
      return;
    }
    // blank line
    if (!trimmed) {
      flushList();
      return;
    }
    // paragraph
    flushList();
    out.push(<p key={i}><InlineMd text={trimmed} /></p>);
  });
  flushList();
  return <>{out}</>;
}

/** Inline markdown: **bold**, `code`, [link](url), URLs. */
function InlineMd({ text }: { text: string }) {
  const parts: JSX.Element[] = [];
  let remaining = text;
  let key = 0;
  const patterns: { re: RegExp; render: (m: RegExpExecArray) => JSX.Element }[] = [
    { re: /\*\*(.+?)\*\*/, render: (m) => <strong key={key++}>{m[1]}</strong> },
    { re: /`(.+?)`/, render: (m) => <code key={key++}>{m[1]}</code> },
    { re: /\[([^\]]+)\]\(([^)]+)\)/, render: (m) => <a key={key++} href={m[2]} target="_blank" rel="noopener noreferrer">{m[1]}</a> },
    { re: /(https?:\/\/[^\s]+)/, render: (m) => <a key={key++} href={m[1]} target="_blank" rel="noopener noreferrer">{m[1]}</a> },
  ];
  while (remaining) {
    let earliest: { idx: number; match: RegExpExecArray; render: (m: RegExpExecArray) => JSX.Element } | null = null;
    for (const p of patterns) {
      const m = p.re.exec(remaining);
      if (m && (earliest === null || m.index < earliest.idx)) {
        earliest = { idx: m.index, match: m, render: p.render };
      }
    }
    if (!earliest) {
      parts.push(<span key={key++}>{remaining}</span>);
      break;
    }
    if (earliest.idx > 0) {
      parts.push(<span key={key++}>{remaining.slice(0, earliest.idx)}</span>);
    }
    parts.push(earliest.render(earliest.match));
    remaining = remaining.slice(earliest.idx + earliest.match[0].length);
  }
  return <>{parts}</>;
}
