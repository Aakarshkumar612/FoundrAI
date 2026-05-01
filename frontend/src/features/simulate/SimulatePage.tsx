import { useState } from "react";
import { motion } from "framer-motion";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { api } from "@/shared/api/client";
import { supabase } from "@/shared/auth/supabase";
import { Spinner } from "@/shared/components/Spinner";
import type { SimulationResult, ForecastMonth } from "@/shared/types";
import { useEffect } from "react";

const fadeUp = { hidden:{opacity:0,y:16}, visible:{opacity:1,y:0,transition:{duration:0.4,ease:[0.22,1,0.36,1]}} };

const SCENARIOS = ["bear","base","bull"] as const;
type Scenario = typeof SCENARIOS[number];

interface ChartRow { month: string; p10: number; p50: number; p90: number; }

function toChartData(forecast: ForecastMonth[]): ChartRow[] {
  return forecast.map(f => ({
    month: `M${f.month}`,
    p10: Math.round(f.p10),
    p50: Math.round(f.p50),
    p90: Math.round(f.p90),
  }));
}

function fmt(n: number) {
  if (n >= 1_000_000) return `$${(n/1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n/1_000).toFixed(0)}K`;
  return `$${n}`;
}

const TooltipContent = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[#1e1c1a] bg-[#0d0c0b] px-3 py-2 text-xs">
      <p className="text-[#A89F95] mb-1 font-medium">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{color:p.color}}>{p.name}: {fmt(p.value)}</p>
      ))}
    </div>
  );
};

export function SimulatePage() {
  const [uploads, setUploads]         = useState<{id:string;filename:string}[]>([]);
  const [uploadId, setUploadId]       = useState("");
  const [months, setMonths]           = useState(12);
  const [scenario, setScenario]       = useState<Scenario>("base");
  const [cacChange, setCacChange]     = useState(0);
  const [burnChange, setBurnChange]   = useState(0);
  const [loading, setLoading]         = useState(false);
  const [result, setResult]           = useState<SimulationResult | null>(null);
  const [error, setError]             = useState("");

  useEffect(() => {
    supabase.from("uploads").select("id,filename").order("created_at",{ascending:false}).limit(20)
      .then(({data}) => setUploads(data ?? []));
  }, []);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!uploadId || loading) return;
    setError(""); setResult(null); setLoading(true);
    try {
      const data = await api.post<SimulationResult>("/simulate", {
        upload_id: uploadId,
        months_ahead: months,
        growth_scenario: scenario,
        cac_change_pct: cacChange / 100,
        burn_change_pct: burnChange / 100,
      });
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div className="p-8 max-w-4xl" initial="hidden" animate="visible"
      variants={{ visible:{transition:{staggerChildren:0.07}} }}>

      <motion.div variants={fadeUp} className="mb-8">
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Monte Carlo Simulation</h1>
        <p className="mt-1 text-sm text-[#6B6560]">10,000 paths · P10/P50/P90 confidence bands · seeded from your financials</p>
      </motion.div>

      <motion.form variants={fadeUp} onSubmit={run} className="grid grid-cols-2 gap-4 mb-8">
        {/* Document */}
        <div className="col-span-2">
          <label className="block text-xs text-[#6B6560] mb-1.5 uppercase tracking-wider">Financial Document</label>
          <select value={uploadId} onChange={e => setUploadId(e.target.value)} required
            className="w-full rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#A89F95] focus:border-[#D97757] focus:outline-none transition-colors">
            <option value="">Select a document…</option>
            {uploads.map(u => <option key={u.id} value={u.id}>{u.filename}</option>)}
          </select>
        </div>

        {/* Months */}
        <div>
          <label className="block text-xs text-[#6B6560] mb-1.5 uppercase tracking-wider">Forecast Months: {months}</label>
          <input type="range" min={1} max={24} value={months} onChange={e => setMonths(+e.target.value)}
            className="w-full accent-[#D97757]" />
          <div className="flex justify-between text-[10px] text-[#6B6560] mt-0.5"><span>1</span><span>24</span></div>
        </div>

        {/* Scenario */}
        <div>
          <label className="block text-xs text-[#6B6560] mb-1.5 uppercase tracking-wider">Growth Scenario</label>
          <div className="flex gap-2">
            {SCENARIOS.map(s => (
              <button key={s} type="button" onClick={() => setScenario(s)}
                className={`flex-1 rounded-xl py-2.5 text-xs font-semibold capitalize transition-colors ${
                  scenario === s
                    ? "bg-[#D97757] text-white"
                    : "border border-[#1e1c1a] bg-[#161412] text-[#A89F95] hover:border-[#2a2520]"
                }`}>{s}</button>
            ))}
          </div>
        </div>

        {/* CAC change */}
        <div>
          <label className="block text-xs text-[#6B6560] mb-1.5 uppercase tracking-wider">CAC Change: {cacChange > 0 ? "+" : ""}{cacChange}%</label>
          <input type="range" min={-50} max={100} value={cacChange} onChange={e => setCacChange(+e.target.value)}
            className="w-full accent-[#D97757]" />
          <div className="flex justify-between text-[10px] text-[#6B6560] mt-0.5"><span>-50%</span><span>+100%</span></div>
        </div>

        {/* Burn change */}
        <div>
          <label className="block text-xs text-[#6B6560] mb-1.5 uppercase tracking-wider">Burn Change: {burnChange > 0 ? "+" : ""}{burnChange}%</label>
          <input type="range" min={-50} max={100} value={burnChange} onChange={e => setBurnChange(+e.target.value)}
            className="w-full accent-[#D97757]" />
          <div className="flex justify-between text-[10px] text-[#6B6560] mt-0.5"><span>-50%</span><span>+100%</span></div>
        </div>

        <div className="col-span-2">
          <button type="submit" disabled={loading || !uploadId}
            className="rounded-xl bg-[#D97757] px-6 py-3 text-sm font-semibold text-white hover:bg-[#C9623F] disabled:opacity-40 transition-colors flex items-center gap-2">
            {loading ? <><Spinner size={14} /> Running simulation…</> : "Run Simulation"}
          </button>
        </div>
      </motion.form>

      {error && (
        <motion.div variants={fadeUp} initial="hidden" animate="visible"
          className="mb-6 rounded-2xl border border-red-900/40 bg-red-950/20 px-5 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </motion.div>
      )}

      {result && (
        <motion.div variants={fadeUp} initial="hidden" animate="visible" className="space-y-5">
          {/* Runway stats */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Runway P10 (Bear)", value: `${result.runway_p10.toFixed(1)} mo`, color: "#C9623F" },
              { label: "Runway P50 (Base)", value: `${result.runway_months.toFixed(1)} mo`, color: "#D97757" },
              { label: "Runway P90 (Bull)", value: `${result.runway_p90.toFixed(1)} mo`, color: "#4CAF84" },
            ].map(s => (
              <div key={s.label} className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-4">
                <p className="text-xs text-[#6B6560] mb-1">{s.label}</p>
                <p className="text-2xl font-bold" style={{color:s.color}}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Chart */}
          <div className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-5">
            <p className="text-sm font-semibold text-[#F5F0EB] mb-4">Cash Runway Forecast</p>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={toChartData(result.forecast)} margin={{top:4,right:4,bottom:0,left:0}}>
                <defs>
                  <linearGradient id="gP90" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4CAF84" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#4CAF84" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="gP50" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#D97757" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#D97757" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="gP10" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#C9623F" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#C9623F" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1c1a" />
                <XAxis dataKey="month" tick={{fill:"#6B6560",fontSize:11}} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={fmt} tick={{fill:"#6B6560",fontSize:11}} axisLine={false} tickLine={false} width={60} />
                <Tooltip content={<TooltipContent />} />
                <Legend wrapperStyle={{fontSize:11,color:"#A89F95"}} />
                <Area type="monotone" dataKey="p90" name="P90 (Bull)" stroke="#4CAF84" strokeWidth={1.5} fill="url(#gP90)" dot={false} />
                <Area type="monotone" dataKey="p50" name="P50 (Base)" stroke="#D97757" strokeWidth={2} fill="url(#gP50)" dot={false} />
                <Area type="monotone" dataKey="p10" name="P10 (Bear)" stroke="#C9623F" strokeWidth={1.5} fill="url(#gP10)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <p className="text-[11px] text-[#6B6560] text-right">
            {result.simulation_runs.toLocaleString()} paths · model: {result.model_used}
            {result.simulation_id && <> · ID: <span className="font-mono">{result.simulation_id.slice(0,8)}</span></>}
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}
