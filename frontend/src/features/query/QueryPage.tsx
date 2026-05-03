import { useEffect, useRef, useState } from "react";
import { api, streamQuery } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import {
  Send, Bot, User, Sparkles, Database, ChevronDown, ChevronRight,
  Globe, AlertTriangle, BarChart, Target, FileText,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentDetail {
  name: string;
  content: string;
  timestamp: string;
}

interface Message {
  role: "user" | "assistant" | "error";
  content: string;
  streaming?: boolean;
  agentDetails?: AgentDetail[];
  timestamp: string;
}

// ── Inline markdown renderer ──────────────────────────────────────────────────

function renderInline(text: string) {
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return parts.map((p, i) =>
    i % 2 === 1
      ? <strong key={i} className="text-white font-semibold">{p}</strong>
      : <span key={i}>{p}</span>
  );
}

function MarkdownBlock({ text }: { text: string }) {
  const lines = text.split("\n");
  const out: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];
  let key = 0;

  const flushList = () => {
    if (listItems.length) {
      out.push(<ul key={key++} className="my-2 space-y-1 list-none pl-0">{listItems}</ul>);
      listItems = [];
    }
  };

  for (const line of lines) {
    const s = line.trim();
    if (!s) { flushList(); continue; }

    if (s.startsWith("### ")) {
      flushList();
      out.push(<h3 key={key++} className="text-sm font-bold text-[#a5b4fc] mt-5 mb-2 border-l-2 border-[#6366f1] pl-3">{s.slice(4)}</h3>);
    } else if (s.startsWith("## ")) {
      flushList();
      out.push(<h2 key={key++} className="text-base font-bold text-white mt-6 mb-2">{s.slice(3)}</h2>);
    } else if (s.startsWith("# ")) {
      flushList();
      out.push(<h1 key={key++} className="text-lg font-bold text-white mt-6 mb-3">{s.slice(2)}</h1>);
    } else if (s.startsWith("- ") || s.startsWith("* ")) {
      listItems.push(
        <li key={key++} className="flex items-start gap-2 text-[#cbd5e1] text-sm leading-relaxed">
          <span className="text-[#6366f1] mt-1 shrink-0">→</span>
          <span>{renderInline(s.slice(2))}</span>
        </li>
      );
    } else {
      flushList();
      out.push(<p key={key++} className="text-[#cbd5e1] text-sm leading-relaxed my-1">{renderInline(s)}</p>);
    }
  }
  flushList();
  return <div className="space-y-0.5">{out}</div>;
}

// ── Agent detail card ─────────────────────────────────────────────────────────

const AGENT_ICONS: Record<string, React.ReactNode> = {
  MarketAgent:   <Globe size={13} className="text-blue-400" />,
  RiskAgent:     <AlertTriangle size={13} className="text-orange-400" />,
  RevenueAgent:  <BarChart size={13} className="text-emerald-400" />,
  StrategyAgent: <Target size={13} className="text-purple-400" />,
};

function AgentCard({ detail }: { detail: AgentDetail }) {
  const [open, setOpen] = useState(false);

  let parsed: Record<string, any> | null = null;
  try { parsed = JSON.parse(detail.content); } catch { /* not JSON */ }

  return (
    <div className="border border-white/5 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors text-left"
      >
        {AGENT_ICONS[detail.name] ?? <Bot size={13} className="text-[#6366f1]" />}
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#94a3b8] flex-1">{detail.name}</span>
        {open ? <ChevronDown size={12} className="text-[#4b5563]" /> : <ChevronRight size={12} className="text-[#4b5563]" />}
      </button>
      {open && parsed && (
        <div className="px-3 pb-3 pt-1 bg-white/2 space-y-2">
          {Object.entries(parsed).map(([k, v]) => (
            <div key={k}>
              <div className="text-[9px] font-bold uppercase text-[#4b5563] mb-0.5 tracking-wider">
                {k.replace(/_/g, " ")}
              </div>
              <div className="text-[11px] text-[#94a3b8] leading-relaxed">
                {Array.isArray(v)
                  ? v.map((item: any, i: number) => (
                    <div key={i} className="flex items-start gap-1">
                      <span className="text-[#6366f1] shrink-0">·</span>
                      <span>{typeof item === "object" ? JSON.stringify(item) : String(item)}</span>
                    </div>
                  ))
                  : typeof v === "object"
                    ? JSON.stringify(v)
                    : String(v)
                }
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Typing cursor ─────────────────────────────────────────────────────────────

function Cursor() {
  return (
    <span
      className="inline-block w-0.5 h-4 bg-[#6366f1] ml-0.5 align-middle animate-pulse"
      style={{ verticalAlign: "text-bottom" }}
    />
  );
}

// ── Progress indicator while agents run ──────────────────────────────────────

const AGENT_LABELS = ["MarketAgent", "RiskAgent", "RevenueAgent", "StrategyAgent"];

function AnalysisProgress({ currentAgent }: { currentAgent: string }) {
  const idx = AGENT_LABELS.indexOf(currentAgent);
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/3 border border-white/8">
      <Spinner size={14} />
      <div className="flex items-center gap-1.5">
        {AGENT_LABELS.map((name, i) => (
          <span
            key={name}
            className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full transition-all ${
              i < idx
                ? "bg-[#3ECF8E]/15 text-[#3ECF8E]"
                : i === idx
                  ? "bg-[#6366f1]/20 text-[#a5b4fc] animate-pulse"
                  : "text-[#4b5563]"
            }`}
          >
            {name.replace("Agent", "")}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const SUGGESTIONS = [
  "What is my current runway and burn rate?",
  "Show total revenue and month-over-month growth",
  "Which month had the highest CAC and why?",
  "Give me a 90-day strategic growth plan",
];

interface ActiveUpload {
  id: string;
  filename: string;
  row_count: number | null;
}

export function QueryPage() {
  const [question, setQuestion]     = useState("");
  const [messages, setMessages]     = useState<Message[]>([]);
  const [streaming, setStreaming]   = useState(false);
  const [contextLen, setContextLen] = useState(0);
  const [currentAgent, setCurrentAgent] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [activeUpload, setActiveUpload] = useState<ActiveUpload | null>(null);
  const agentBufferRef = useRef<AgentDetail[]>([]);
  const chatEndRef     = useRef<HTMLDivElement>(null);

  // ── Load history + active upload on mount ─────────────────────────────────
  useEffect(() => {
    async function loadHistory() {
      try {
        const history = await api.get<any[]>("/query/history");
        const mapped = history.map(h => ({
          role: h.role,
          content: h.content,
          agentDetails: h.agent_details || [],
          timestamp: h.created_at,
        }));
        setMessages(mapped);
      } catch (err) {
        console.error("Failed to load chat history:", err);
      } finally {
        setLoadingHistory(false);
      }
    }

    async function loadActiveUpload() {
      try {
        const res = await api.get<any>("/founders/uploads?page_size=1");
        const latest = res.uploads?.[0];
        if (latest && latest.upload_status !== "deleted") {
          setActiveUpload({ id: latest.id, filename: latest.filename, row_count: latest.row_count });
        }
      } catch {
        // non-critical — chatbot still works without it
      }
    }

    loadHistory();
    loadActiveUpload();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || streaming) return;

    setMessages(prev => [...prev, { role: "user", content: q, timestamp: new Date().toISOString() }]);
    setQuestion("");
    setStreaming(true);
    setContextLen(0);
    setCurrentAgent("MarketAgent");
    agentBufferRef.current = [];

    try {
      await streamQuery(q, activeUpload?.id ?? null, (event, rawData) => {
        try {
          const data = JSON.parse(rawData);

          if (event === "rag_context") {
            setContextLen((data.chunks || []).length);

          } else if (event === "agent_update") {
            agentBufferRef.current.push({
              name: data.agent_name,
              content: data.content,
              timestamp: data.timestamp || new Date().toISOString(),
            });
            // Advance progress indicator
            const idx = AGENT_LABELS.indexOf(data.agent_name);
            setCurrentAgent(AGENT_LABELS[idx + 1] ?? "Synthesizing");

          } else if (event === "synthesis_chunk") {
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant" && last?.streaming) {
                return [
                  ...prev.slice(0, -1),
                  { ...last, content: last.content + data.text },
                ];
              }
              // Start new synthesis message
              return [
                ...prev,
                {
                  role: "assistant",
                  content: data.text,
                  streaming: true,
                  agentDetails: [],
                  timestamp: new Date().toISOString(),
                },
              ];
            });

          } else if (event === "final") {
            // Finalize synthesis message — attach agent details, stop streaming
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [
                  ...prev.slice(0, -1),
                  {
                    ...last,
                    streaming: false,
                    agentDetails: agentBufferRef.current,
                  },
                ];
              }
              return prev;
            });
            agentBufferRef.current = [];
            setCurrentAgent("");
            setStreaming(false);

          } else if (event === "error") {
            setMessages(prev => [...prev, {
              role: "error",
              content: data.message || "An error occurred.",
              timestamp: new Date().toISOString(),
            }]);
            setCurrentAgent("");
            setStreaming(false);
          }
        } catch { /* non-JSON line */ }
      });
    } catch {
      setMessages(prev => [...prev, {
        role: "error",
        content: "Connection failed. Is the backend running?",
        timestamp: new Date().toISOString(),
      }]);
      setCurrentAgent("");
      setStreaming(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#6366f1]">
            <Sparkles size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">AI <span className="gradient-text">Advisory</span></h1>
            <p className="text-[10px] text-[#94a3b8] uppercase tracking-[0.2em]">4-Agent Analysis · Streaming Synthesis</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {activeUpload && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#6366f1]/10 border border-[#6366f1]/20 text-[#a5b4fc] text-[10px] font-bold uppercase tracking-wider max-w-[200px]">
              <FileText size={12} className="shrink-0" />
              <span className="truncate">{activeUpload.filename}</span>
              {activeUpload.row_count ? <span className="shrink-0 text-[#6366f1]">· {activeUpload.row_count}r</span> : null}
            </div>
          )}
          {contextLen > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#3ECF8E]/10 border border-[#3ECF8E]/20 text-[#3ECF8E] text-[10px] font-bold uppercase tracking-wider">
              <Database size={12} /> {contextLen} Sources
            </div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-2 custom-scrollbar mb-6">
        {/* Loading state */}
        {loadingHistory && messages.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <Spinner size={32} />
          </div>
        )}

        {/* Empty state */}
        {!loadingHistory && messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center px-8">
            <div className="w-20 h-20 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center text-[#6366f1] mb-6 animate-float">
              <Bot size={40} />
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">How can I help you today?</h2>
            <p className="text-[#94a3b8] max-w-md text-sm leading-relaxed mb-8">
              Ask anything about your business — financials, risks, strategy, or market dynamics.
              I run a 4-specialist analysis then synthesize a comprehensive advisory response.
            </p>
            <div className="grid grid-cols-2 gap-3 w-full max-w-xl">
              {SUGGESTIONS.map(q => (
                <button
                  key={q}
                  onClick={() => setQuestion(q)}
                  className="p-4 rounded-xl glass-card text-xs text-[#94a3b8] hover:text-white hover:border-[#6366f1]/40 transition-all text-left leading-relaxed"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-4 animate-fade-up ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            {/* Avatar — AI side */}
            {m.role !== "user" && (
              <div className="w-9 h-9 shrink-0 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#6366f1] mt-1">
                <Bot size={18} />
              </div>
            )}

            <div className={`max-w-[75%] space-y-2 ${m.role === "user" ? "order-first" : ""}`}>
              {/* Message bubble */}
              <div className={`px-5 py-4 rounded-2xl ${
                m.role === "user"
                  ? "bg-gradient-to-br from-[#6366f1] to-[#7c3aed] text-white shadow-lg shadow-[#6366f1]/20 ml-auto"
                  : m.role === "error"
                    ? "bg-red-500/10 border border-red-500/20 text-red-400"
                    : "glass-card"
              }`}>
                {m.role === "user" ? (
                  <p className="text-sm leading-relaxed">{m.content}</p>
                ) : m.role === "error" ? (
                  <p className="text-sm">{m.content}</p>
                ) : (
                  <>
                    <MarkdownBlock text={m.content} />
                    {m.streaming && <Cursor />}
                  </>
                )}
              </div>

              {/* Collapsible agent details */}
              {m.role === "assistant" && !m.streaming && (m.agentDetails?.length ?? 0) > 0 && (
                <AgentDetailsSection details={m.agentDetails!} />
              )}

              <p className="text-[10px] text-[#4b5563] px-1">
                {new Date(m.timestamp).toLocaleTimeString()}
              </p>
            </div>

            {/* Avatar — user side */}
            {m.role === "user" && (
              <div className="w-9 h-9 shrink-0 rounded-xl bg-gradient-to-tr from-[#6366f1] to-[#a855f7] flex items-center justify-center text-white shadow-lg shadow-[#6366f1]/20 mt-1">
                <User size={18} />
              </div>
            )}
          </div>
        ))}

        {/* In-progress indicator */}
        {streaming && currentAgent && (
          <div className="flex gap-4 animate-fade-up">
            <div className="w-9 h-9 shrink-0 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#6366f1] mt-1">
              <Bot size={18} />
            </div>
            <div className="max-w-[75%]">
              <AnalysisProgress currentAgent={currentAgent} />
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={ask} className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-[#6366f1]/8 via-[#a855f7]/8 to-[#6366f1]/8 blur-xl -z-10 rounded-2xl" />
        <div className="relative glass-card p-2 flex items-center gap-2 rounded-2xl">
          <div className="p-3 text-[#4b5563] shrink-0">
            {streaming ? <Spinner size={18} /> : <Sparkles size={18} />}
          </div>
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder={streaming ? "Analyzing your question…" : "Ask your AI advisor anything…"}
            disabled={streaming}
            className="flex-1 bg-transparent border-none focus:ring-0 text-white placeholder-[#4b5563] text-sm py-4 outline-none"
          />
          <button
            type="submit"
            disabled={streaming || !question.trim()}
            className="p-3 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] text-white hover:scale-105 active:scale-95 transition-all shadow-lg shadow-[#6366f1]/20 disabled:opacity-40 disabled:scale-100 shrink-0"
          >
            <Send size={17} />
          </button>
        </div>
        <p className="mt-2 text-[10px] text-center text-[#4b5563] uppercase tracking-[0.2em]">
          4-Agent pipeline · RAG-grounded · Streaming synthesis
        </p>
      </form>
    </div>
  );
}

// ── Collapsible agent details ─────────────────────────────────────────────────

function AgentDetailsSection({ details }: { details: AgentDetail[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-[10px] font-bold text-[#4b5563] hover:text-[#94a3b8] transition-colors uppercase tracking-wider"
      >
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        Agent Analysis Details ({details.length})
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          {details.map((d, i) => <AgentCard key={i} detail={d} />)}
        </div>
      )}
    </div>
  );
}
