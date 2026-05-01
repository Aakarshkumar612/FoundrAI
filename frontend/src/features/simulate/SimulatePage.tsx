import { useEffect, useState } from "react";
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend 
} from "recharts";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import type { SimulationResult, Upload } from "@/shared/types";
import { TrendingUp, Settings2, Info, ArrowRight, Zap, FileText } from "lucide-react";

export function SimulatePage() {
  const [months, setMonths] = useState(12);
  const [scenario, setScenario] = useState<"bear" | "base" | "bull">("base");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [selectedUpload, setSelectedUpload] = useState<string>("");

  useEffect(() => {
    api.get<{uploads: any[]}>("/founders/uploads")
      .then(res => {
        const docs = res.uploads || [];
        setUploads(docs);
        if (docs.length > 0) {
          setSelectedUpload(docs[0].id);
        }
      });
  }, []);

  async function run() {
    if (!selectedUpload) return;
    setLoading(true);
    try {
      const res = await api.post<SimulationResult>("/simulate", {
        upload_id: selectedUpload,
        months_ahead: months,
        growth_scenario: scenario,
      });
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8 animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Monte Carlo <span className="gradient-text">Simulation</span></h1>
          <p className="text-[#94a3b8] mt-1">Stochastic forecasting across 10,000 future paths</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#06b6d4]/10 border border-[#06b6d4]/20 text-[#06b6d4] text-[10px] font-bold uppercase tracking-wider">
          <Zap size={14} /> Powered by NumPy
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Controls */}
        <div className="glass-card p-8 space-y-8 h-fit">
          <div className="flex items-center gap-3 mb-2">
            <Settings2 className="text-[#6366f1]" size={20} />
            <h2 className="text-lg font-bold text-white">Parameters</h2>
          </div>

          <div className="space-y-6">
            <div className="space-y-4">
              <label className="text-xs font-bold uppercase tracking-widest text-[#94a3b8]">Source Document</label>
              {uploads.length === 0 ? (
                <div className="p-4 rounded-xl border border-dashed border-white/10 text-center">
                  <p className="text-[10px] text-[#94a3b8]">No financial documents found.</p>
                </div>
              ) : (
                <select 
                  value={selectedUpload}
                  onChange={e => setSelectedUpload(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:border-[#6366f1] focus:outline-none transition-colors"
                >
                  {uploads.map(u => (
                    <option key={u.id} value={u.id} className="bg-[#0a0a0f]">{u.filename}</option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <div className="flex justify-between mb-4">
                <label className="text-xs font-bold uppercase tracking-widest text-[#94a3b8]">Horizon</label>
                <span className="text-xs font-bold text-[#6366f1]">{months} Months</span>
              </div>
              <input 
                type="range" min="3" max="24" value={months} onChange={e => setMonths(parseInt(e.target.value))}
                className="w-full h-1.5 bg-white/5 rounded-lg appearance-none cursor-pointer accent-[#6366f1]"
              />
            </div>

            <div className="space-y-4">
              <label className="text-xs font-bold uppercase tracking-widest text-[#94a3b8]">Growth Scenario</label>
              <div className="grid grid-cols-1 gap-2">
                {(['bear', 'base', 'bull'] as const).map(s => (
                  <button key={s} onClick={() => setScenario(s)}
                    className={`px-4 py-3 rounded-xl border text-sm font-bold capitalize transition-all text-left flex justify-between items-center ${
                      scenario === s 
                        ? "bg-[#6366f1]/20 border-[#6366f1] text-[#8b5cf6]" 
                        : "bg-white/5 border-white/5 text-[#94a3b8] hover:bg-white/10"
                    }`}
                  >
                    {s}
                    {scenario === s && <div className="w-2 h-2 rounded-full bg-[#8b5cf6] shadow-[0_0_8px_#8b5cf6]" />}
                  </button>
                ))}
              </div>
            </div>

            <button 
              onClick={run} disabled={loading || !selectedUpload}
              className="w-full py-4 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold text-white hover:scale-[1.02] transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#6366f1]/20 disabled:opacity-50 mt-4"
            >
              {loading ? <Spinner size={20} /> : <>Execute Simulation <ArrowRight size={18} /></>}
            </button>
          </div>
        </div>

        {/* Chart Area */}
        <div className="lg:col-span-2 glass-card p-8 min-h-[500px] flex flex-col">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <TrendingUp className="text-[#6366f1]" size={20} />
              <h2 className="text-lg font-bold text-white">Revenue Projection</h2>
            </div>
            {result && (
              <div className="flex gap-4">
                <div className="text-right">
                  <p className="text-[10px] text-[#94a3b8] uppercase">P50 Runway</p>
                  <p className="text-sm font-bold text-[#3ECF8E]">{result.runway_months} Mo</p>
                </div>
              </div>
            )}
          </div>

          <div className="flex-1 w-full min-h-[350px]">
            {result ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={result.forecast} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorP50" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                  <XAxis dataKey="month" stroke="#4b5563" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v) => `M${v}`} />
                  <YAxis stroke="#4b5563" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v/1000}k`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0d0d1a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                    itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                  />
                  <Area type="monotone" dataKey="p90" stroke="#8b5cf6" strokeWidth={1} strokeDasharray="5 5" fill="transparent" />
                  <Area type="monotone" dataKey="p50" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorP50)" />
                  <Area type="monotone" dataKey="p10" stroke="#4b5563" strokeWidth={1} strokeDasharray="5 5" fill="transparent" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center opacity-40">
                <TrendingUp className="mb-4" size={48} />
                <p className="text-sm font-medium">Configure parameters and run to <br />visualize stochastic forecast</p>
              </div>
            )}
          </div>

          <div className="mt-8 grid grid-cols-3 gap-4 pt-8 border-t border-white/5">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] uppercase font-bold text-[#94a3b8] flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-[#8b5cf6]" /> Bull Case (P90)
              </span>
              <p className="text-xs text-white/60">Optimistic growth with lower CAC volatility.</p>
            </div>
            <div className="flex flex-col gap-1 text-center">
              <span className="text-[10px] uppercase font-bold text-[#6366f1] flex items-center justify-center gap-1.5">
                 Base Case (P50)
              </span>
              <p className="text-xs text-white/60">The most probable outcome path.</p>
            </div>
            <div className="flex flex-col gap-1 text-right">
              <span className="text-[10px] uppercase font-bold text-[#4b5563] flex items-center justify-end gap-1.5">
                Bear Case (P10) <div className="w-2 h-2 rounded-full bg-[#4b5563]" />
              </span>
              <p className="text-xs text-white/60">Worst-case scenario with high churn risk.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
