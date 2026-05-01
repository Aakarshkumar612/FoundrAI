import { useEffect, useRef, useState } from "react";
import { supabase } from "@/shared/auth/supabase";
import { streamQuery } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import { 
  Send, 
  Bot, 
  User, 
  Terminal, 
  Sparkles, 
  Database, 
  Globe, 
  BarChart, 
  Target,
  AlertTriangle
} from "lucide-react";

export function QueryPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [context, setContext] = useState<any[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || streaming) return;

    const userMsg = { role: "user", content: question, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setQuestion("");
    setStreaming(true);
    setContext([]);

    try {
      await streamQuery(userMsg.content, (event, data) => {
        if (event === "rag_context") {
          setContext(data.chunks || []);
        } else if (event === "agent_update") {
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last?.agent === data.agent_name) {
              return [...prev.slice(0, -1), { ...last, content: data.content }];
            }
            return [...prev, { role: "assistant", agent: data.agent_name, content: data.content }];
          });
        } else if (event === "final") {
          setStreaming(false);
        } else if (event === "error") {
          setMessages(prev => [...prev, { role: "error", content: data.message }]);
          setStreaming(false);
        }
      });
    } catch (err) {
      setStreaming(false);
    }
  }

  const getAgentIcon = (name: string) => {
    switch (name) {
      case "MarketAgent": return <Globe size={16} className="text-blue-400" />;
      case "RiskAgent": return <AlertTriangle size={16} className="text-orange-400" />;
      case "RevenueAgent": return <BarChart size={16} className="text-emerald-400" />;
      case "StrategyAgent": return <Target size={16} className="text-purple-400" />;
      default: return <Bot size={16} className="text-[#6366f1]" />;
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#6366f1]">
            <Sparkles size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">AI Advisory <span className="gradient-text">Chat</span></h1>
            <p className="text-[10px] text-[#94a3b8] uppercase tracking-[0.2em]">4-Agent Multi-Stage Analysis</p>
          </div>
        </div>
        {context.length > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#3ECF8E]/10 border border-[#3ECF8E]/20 text-[#3ECF8E] text-[10px] font-bold uppercase tracking-wider">
            <Database size={12} /> {context.length} Sources Linked
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-8 pr-4 custom-scrollbar mb-8">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center px-10">
            <div className="w-20 h-20 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center text-[#6366f1] mb-6 animate-float">
              <Bot size={40} />
            </div>
            <h2 className="text-2xl font-bold text-white mb-4">How can I help you today?</h2>
            <p className="text-[#94a3b8] max-w-md text-sm leading-relaxed mb-8">
              Ask about your latest financial trends, market risks, or request a 30-60-90 day strategic roadmap.
            </p>
            <div className="grid grid-cols-2 gap-3 w-full max-w-xl">
              {[
                "What is my current runway?",
                "What are the biggest market threats?",
                "Analyze my burn rate trends",
                "Generate a 90-day growth plan"
              ].map(q => (
                <button key={q} onClick={() => setQuestion(q)} className="p-4 rounded-xl glass-card text-xs text-[#94a3b8] hover:text-white hover:border-[#6366f1]/40 transition-all text-left">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex gap-6 ${m.role === 'user' ? 'justify-end' : ''} animate-fade-up`}>
            {m.role !== 'user' && (
              <div className="w-10 h-10 shrink-0 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#6366f1]">
                {m.agent ? getAgentIcon(m.agent) : <Bot size={20} />}
              </div>
            )}
            
            <div className={`max-w-2xl space-y-2 ${m.role === 'user' ? 'order-first' : ''}`}>
              {m.agent && (
                <div className="flex items-center gap-2">
                   <span className="text-[10px] font-bold uppercase tracking-widest text-[#6366f1]">{m.agent}</span>
                   <div className="h-px flex-1 bg-gradient-to-r from-[#6366f1]/20 to-transparent" />
                </div>
              )}
              <div className={`p-5 rounded-2xl ${m.role === 'user' ? 'bg-[#6366f1] text-white shadow-lg shadow-[#6366f1]/20' : 'glass-card text-[#cbd5e1]'}`}>
                {m.role === 'error' ? <p className="text-red-400 text-sm">{m.content}</p> : (
                  <div className="text-sm leading-relaxed whitespace-pre-wrap">
                    {/* Parse JSON if it's an agent update */}
                    {m.agent ? (
                      <div className="font-mono text-[11px] opacity-90">
                        {m.content.startsWith('{') ? (
                          <div className="space-y-4 font-sans text-sm">
                            {Object.entries(JSON.parse(m.content)).map(([k, v]: any) => (
                              <div key={k}>
                                <div className="text-[10px] font-bold uppercase text-[#94a3b8] mb-1">{k.replace(/_/g, ' ')}</div>
                                <div className="text-[#e2e8f0]">{Array.isArray(v) ? v.join(', ') : (typeof v === 'object' ? JSON.stringify(v) : v)}</div>
                              </div>
                            ))}
                          </div>
                        ) : m.content}
                      </div>
                    ) : m.content}
                  </div>
                )}
              </div>
              <p className="text-[10px] text-[#4b5563] font-medium tracking-tighter px-1">
                {m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : 'Just now'}
              </p>
            </div>

            {m.role === 'user' && (
              <div className="w-10 h-10 shrink-0 rounded-xl bg-gradient-to-tr from-[#6366f1] to-[#a855f7] flex items-center justify-center text-white shadow-lg shadow-[#6366f1]/20">
                <User size={20} />
              </div>
            )}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={ask} className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-[#6366f1]/10 via-[#a855f7]/10 to-[#6366f1]/10 blur-xl opacity-50 -z-10" />
        <div className="relative glass-card p-2 flex items-center gap-2">
          <div className="p-3 text-[#4b5563]">
            {streaming ? <Spinner size={20} /> : <Terminal size={20} />}
          </div>
          <input 
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder={streaming ? "Analyzing through agents..." : "Ask your advisor anything..."}
            disabled={streaming}
            className="flex-1 bg-transparent border-none focus:ring-0 text-white placeholder-[#4b5563] text-sm py-4"
          />
          <button 
            type="submit"
            disabled={streaming || !question.trim()}
            className="p-3 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] text-white hover:scale-105 transition-all shadow-lg shadow-[#6366f1]/20 disabled:opacity-50"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="mt-3 text-[10px] text-center text-[#4b5563] font-medium uppercase tracking-[0.2em]">Press Enter to dispatch query · Data grounded via ColBERT RAG</p>
      </form>
    </div>
  );
}
