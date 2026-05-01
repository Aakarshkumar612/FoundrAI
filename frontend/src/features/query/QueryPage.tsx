import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { supabase } from "@/shared/auth/supabase";
import { streamQuery } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";

const AGENT_COLORS: Record<string, string> = {
  MarketAgent:   "#D97757",
  RiskAgent:     "#E8A838",
  RevenueAgent:  "#4CAF84",
  StrategyAgent: "#7C9EF8",
};

interface Message { agent: string; content: Record<string, unknown>; }

function AgentCard({ msg }: { msg: Message }) {
  const color = AGENT_COLORS[msg.agent] ?? "#A89F95";
  const label = msg.agent.replace("Agent", "");
  const summary = (msg.content.summary ?? msg.content.recommendation ?? msg.content.strategy
    ?? msg.content.error ?? JSON.stringify(msg.content)) as string;

  return (
    <motion.div initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{duration:0.35,ease:[0.22,1,0.36,1]}}
      className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2 h-2 rounded-full" style={{background:color}} />
        <span className="text-xs font-semibold uppercase tracking-wider" style={{color}}>{label}</span>
      </div>
      <p className="text-sm text-[#A89F95] leading-relaxed whitespace-pre-wrap">{String(summary)}</p>
    </motion.div>
  );
}

export function QueryPage() {
  const [question, setQuestion]       = useState("");
  const [uploadId, setUploadId]       = useState("");
  const [uploads, setUploads]         = useState<{id:string;filename:string}[]>([]);
  const [messages, setMessages]       = useState<Message[]>([]);
  const [streaming, setStreaming]     = useState(false);
  const [done, setDone]               = useState(false);
  const abortRef                      = useRef<AbortController|null>(null);
  const bottomRef                     = useRef<HTMLDivElement>(null);

  useEffect(() => {
    supabase.from("uploads").select("id,filename").order("created_at",{ascending:false}).limit(20)
      .then(({data}) => setUploads(data ?? []));
  }, []);

  useEffect(() => { bottomRef.current?.scrollIntoView({behavior:"smooth"}); }, [messages]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || streaming) return;
    setMessages([]); setDone(false); setStreaming(true);
    abortRef.current = new AbortController();
    try {
      await streamQuery(question, uploadId||null, (event, data) => {
        if (event === "agent_update") {
          try {
            const p = JSON.parse(data);
            setMessages(prev => [...prev, { agent: p.agent_name, content: JSON.parse(p.content || "{}") }]);
          } catch {}
        } else if (event === "final" || event === "complete") {
          setStreaming(false); setDone(true);
        } else if (event === "error") {
          try { const p = JSON.parse(data); setMessages(prev => [...prev, {agent:"Error",content:{error:p.message}}]); } catch {}
          setStreaming(false);
        }
      }, abortRef.current.signal);
    } catch (e: any) {
      if (e.name !== "AbortError") setMessages(prev => [...prev, {agent:"Error",content:{error:e.message}}]);
      setStreaming(false);
    }
  }

  return (
    <div className="flex flex-col h-full max-w-3xl p-8 gap-6">
      <div>
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Ask AI</h1>
        <p className="mt-1 text-sm text-[#6B6560]">4 specialist agents — Market, Risk, Revenue, Strategy — answer in sequence.</p>
      </div>

      {/* Messages */}
      {messages.length > 0 && (
        <div className="flex flex-col gap-3 overflow-y-auto max-h-[55vh]">
          <AnimatePresence initial={false}>
            {messages.map((m, i) => <AgentCard key={i} msg={m} />)}
          </AnimatePresence>
          {streaming && (
            <motion.div initial={{opacity:0}} animate={{opacity:1}}
              className="flex items-center gap-3 px-5 py-3 rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b]">
              <Spinner size={14} />
              <p className="text-xs text-[#6B6560]">Agent pipeline running…</p>
            </motion.div>
          )}
          {done && <p className="text-xs text-[#4CAF84] text-center">Analysis complete</p>}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input form */}
      <form onSubmit={submit} className="mt-auto space-y-3">
        <select value={uploadId} onChange={e => setUploadId(e.target.value)}
          className="w-full rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#A89F95] focus:border-[#D97757] focus:outline-none transition-colors">
          <option value="">No document — general question</option>
          {uploads.map(u => <option key={u.id} value={u.id}>{u.filename}</option>)}
        </select>
        <div className="flex gap-3">
          <textarea value={question} onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => { if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();submit(e as any);} }}
            placeholder="e.g. What's my biggest growth risk based on my financials?"
            rows={3}
            className="flex-1 resize-none rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-3 text-sm text-[#F5F0EB] placeholder-[#6B6560] focus:border-[#D97757] focus:outline-none transition-colors" />
          <button type="submit" disabled={streaming || !question.trim()}
            className="self-end rounded-xl bg-[#D97757] px-5 py-3 text-sm font-semibold text-white hover:bg-[#C9623F] disabled:opacity-40 transition-colors">
            {streaming ? <Spinner size={14} /> : "Ask"}
          </button>
        </div>
        <p className="text-xs text-[#6B6560]">Enter to send · Shift+Enter for new line</p>
      </form>
    </div>
  );
}
