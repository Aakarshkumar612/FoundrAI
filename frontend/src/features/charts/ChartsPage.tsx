import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getAccessToken } from "@/shared/auth/supabase";
import { streamQuery } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import {
  BarChart2, Sparkles, RefreshCcw, Send, MessageSquare, X, Download,
  Maximize2, TrendingUp, UploadCloud,
} from "lucide-react";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

// ── Loading stage indicator ───────────────────────────────────────────────────

const STAGES = [
  "Fetching your financial data",
  "Orchestrator Agent analyzing patterns",
  "Data Analyst Agent generating insights",
  "Building interactive HTML report",
];

function LoadingOverlay() {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const timers = STAGES.map((_, i) => setTimeout(() => setStage(i), i * 2800));
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[#0a0a0f]/90 backdrop-blur-sm gap-8">
      <div className="relative">
        <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
          <BarChart2 size={28} className="text-[#6366f1]" />
        </div>
        <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[#6366f1] animate-ping" />
      </div>

      <div className="text-center space-y-1">
        <p className="text-sm font-bold text-white">Generating Analytics Report</p>
        <p className="text-xs text-[#6366f1] uppercase tracking-[0.25em] animate-pulse">
          {STAGES[stage]}…
        </p>
      </div>

      <div className="flex flex-col gap-2 w-72">
        {STAGES.map((s, i) => (
          <div
            key={i}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-500 ${
              i === stage
                ? "bg-[#6366f1]/10 border border-[#6366f1]/30"
                : i < stage
                ? "opacity-40"
                : "opacity-15"
            }`}
          >
            <div
              className={`w-2 h-2 rounded-full shrink-0 ${
                i < stage
                  ? "bg-[#3ECF8E]"
                  : i === stage
                  ? "bg-[#6366f1] animate-pulse"
                  : "bg-[#4b5563]"
              }`}
            />
            <span className="text-[11px] text-[#94a3b8]">{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Ask AI panel (handles synthesis_chunk streaming) ─────────────────────────

function AskAIPanel({ onClose }: { onClose: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([{
    role: "assistant",
    content: "Ask me anything about this report — metrics, trends, burn rate, growth trajectory, or what any chart means.",
  }]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const q = input.trim();
    if (!q || streaming) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: q }]);
    setStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      await streamQuery(q, null, (event, rawData) => {
        try {
          const data = JSON.parse(rawData);
          if (event === "synthesis_chunk") {
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant" && last?.streaming) {
                return [...prev.slice(0, -1), { ...last, content: last.content + data.text }];
              }
              return [...prev, { role: "assistant", content: data.text, streaming: true }];
            });
          } else if (event === "final") {
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant" && last?.streaming) {
                return [...prev.slice(0, -1), { ...last, streaming: false }];
              }
              return prev;
            });
            setStreaming(false);
          } else if (event === "error") {
            setMessages(prev => [
              ...prev,
              { role: "assistant", content: data.message || "An error occurred." },
            ]);
            setStreaming(false);
          }
        } catch {
          /* non-JSON SSE line */
        }
      }, ctrl.signal);
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages(prev => [
          ...prev,
          { role: "assistant", content: "Could not connect. Ensure you are signed in." },
        ]);
      }
      setStreaming(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare size={14} className="text-[#6366f1]" />
          <span className="text-xs font-bold text-white uppercase tracking-wider">Ask AI</span>
        </div>
        <button onClick={onClose} className="text-[#4b5563] hover:text-white transition-colors">
          <X size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] px-3 py-2 rounded-xl text-xs leading-relaxed ${
                m.role === "user"
                  ? "bg-[#6366f1]/20 border border-[#6366f1]/30 text-white"
                  : "bg-white/5 border border-white/10 text-[#94a3b8]"
              }`}
            >
              {m.content}
              {m.streaming && (
                <span className="inline-block w-1.5 h-3 bg-[#6366f1] ml-0.5 align-middle animate-pulse" />
              )}
            </div>
          </div>
        ))}
        {streaming && messages[messages.length - 1]?.role !== "assistant" && (
          <div className="flex justify-start">
            <div className="bg-white/5 border border-white/10 px-3 py-2 rounded-xl">
              <div className="flex gap-1">
                {[0, 0.15, 0.3].map((d, i) => (
                  <div
                    key={i}
                    className="w-1 h-1 rounded-full bg-[#6366f1] animate-bounce"
                    style={{ animationDelay: `${d}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-3 pb-3 shrink-0">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Ask about this report..."
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-[#4b5563] focus:border-[#6366f1] focus:outline-none transition-colors"
            disabled={streaming}
          />
          <button
            onClick={send}
            disabled={!input.trim() || streaming}
            className="p-2 rounded-lg bg-[#6366f1]/20 border border-[#6366f1]/30 text-[#6366f1] hover:bg-[#6366f1]/30 disabled:opacity-40 transition-all"
          >
            <Send size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ChartsPage() {
  const [loading, setLoading] = useState(false);
  const [reportHtml, setReportHtml] = useState<string>("");
  const [error, setError] = useState("");
  const [aiOpen, setAiOpen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const generate = useCallback(async () => {
    setLoading(true);
    setError("");
    setReportHtml("");
    try {
      const token = await getAccessToken();
      const res = await fetch("/api/charts/auto-report", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(
          errBody?.detail?.message ?? errBody?.detail ?? `HTTP ${res.status}`
        );
      }
      const html = await res.text();
      setReportHtml(html);
    } catch (err: any) {
      setError(err.message || "Report generation failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    generate();
  }, [generate]);

  function downloadReport() {
    if (!reportHtml) return;
    const blob = new Blob([reportHtml], { type: "text/html" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `foundr-analytics-${Date.now()}.html`;
    a.click();
  }

  function openFullscreen() {
    const blob = new Blob([reportHtml], { type: "text/html" });
    window.open(URL.createObjectURL(blob), "_blank");
  }

  const noData = !reportHtml && !loading && !error;
  const isNoDataError = error.toLowerCase().includes("no financial") ||
    error.toLowerCase().includes("upload") ||
    error.toLowerCase().includes("no data");

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] animate-fade-up">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#d946ef]">
              <BarChart2 size={20} />
            </div>
            <h1 className="text-3xl font-bold text-white">
              Financial <span className="gradient-text">Report</span>
            </h1>
          </div>
          <p className="text-[#94a3b8] text-sm">
            AI-generated financial intelligence · DO / DON&apos;T advisor · Auto-generates on load
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={generate}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] text-white text-sm font-bold hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 transition-all shadow-lg shadow-[#6366f1]/20"
          >
            {loading ? <Spinner size={16} /> : <RefreshCcw size={16} />}
            {loading ? "Generating…" : "Regenerate"}
          </button>

          {reportHtml && (
            <>
              <button
                onClick={downloadReport}
                title="Download HTML"
                className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-[#94a3b8] hover:text-white transition-colors"
              >
                <Download size={15} />
              </button>
              <button
                onClick={openFullscreen}
                title="Open fullscreen"
                className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-[#94a3b8] hover:text-white transition-colors"
              >
                <Maximize2 size={15} />
              </button>
              <button
                onClick={() => setAiOpen(o => !o)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all border ${
                  aiOpen
                    ? "bg-[#6366f1]/20 border-[#6366f1]/40 text-[#a5b4fc]"
                    : "bg-white/5 border-white/10 text-[#94a3b8] hover:text-white"
                }`}
              >
                <MessageSquare size={14} /> Ask AI
              </button>
            </>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 flex gap-4 overflow-hidden">
        {/* Report iframe */}
        <div className="flex-1 glass-card overflow-hidden relative">
          {loading && <LoadingOverlay />}

          {error && !loading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-6 p-8">
              <TrendingUp size={48} className="text-[#4b5563]" />
              <div className="text-center">
                <p className="text-sm font-bold text-white mb-2">Could Not Generate Report</p>
                <p className="text-xs text-[#94a3b8] mb-5 max-w-sm leading-relaxed">{error}</p>
                {isNoDataError ? (
                  <Link
                    to="/upload"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] text-white text-sm font-bold hover:scale-[1.02] transition-all shadow-lg shadow-[#6366f1]/20"
                  >
                    <UploadCloud size={16} /> Upload Financial CSV
                  </Link>
                ) : (
                  <button
                    onClick={generate}
                    className="text-xs font-bold text-[#6366f1] uppercase tracking-widest hover:underline"
                  >
                    Retry
                  </button>
                )}
              </div>
            </div>
          )}

          {noData && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-6 p-8">
              <div className="relative">
                <BarChart2 size={56} className="text-[#4b5563]" />
                <Sparkles size={20} className="text-[#6366f1] absolute -top-1 -right-2" />
              </div>
              <div className="text-center">
                <p className="text-base font-bold text-white mb-2">No Financial Data Found</p>
                <p className="text-xs text-[#94a3b8] mb-6 max-w-xs leading-relaxed">
                  Upload a financial CSV with columns like <code className="text-[#a5b4fc]">revenue</code>,{" "}
                  <code className="text-[#a5b4fc]">burn_rate</code>,{" "}
                  <code className="text-[#a5b4fc]">headcount</code>, <code className="text-[#a5b4fc]">cac</code>,
                  and <code className="text-[#a5b4fc]">ltv</code> to generate your analytics dashboard.
                </p>
                <Link
                  to="/upload"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] text-white text-sm font-bold hover:scale-[1.02] transition-all shadow-lg shadow-[#6366f1]/20"
                >
                  <UploadCloud size={16} /> Upload CSV
                </Link>
              </div>
            </div>
          )}

          {reportHtml && !loading && (
            <iframe
              ref={iframeRef}
              srcDoc={reportHtml}
              className="w-full h-full border-none"
              title="AI Analytics Report"
              sandbox="allow-scripts allow-same-origin"
            />
          )}
        </div>

        {/* Ask AI panel */}
        {aiOpen && reportHtml && (
          <div className="w-80 glass-card overflow-hidden flex flex-col shrink-0">
            <AskAIPanel onClose={() => setAiOpen(false)} />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              reportHtml ? "bg-[#3ECF8E]" : loading ? "bg-[#6366f1] animate-pulse" : "bg-[#4b5563]"
            }`}
          />
          <span className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider">
            {loading ? "Generating Report" : reportHtml ? "Report Ready" : "No Data"}
          </span>
        </div>
        <p className="text-[10px] font-medium text-[#4b5563] uppercase">
          FoundrAI · Orchestrator + Analyst Agents · Powered by Groq
        </p>
      </div>
    </div>
  );
}
