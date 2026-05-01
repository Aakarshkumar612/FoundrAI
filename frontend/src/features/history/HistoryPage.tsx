import { useEffect, useState } from "react";
import { supabase } from "@/shared/auth/supabase";
import { Spinner } from "@/shared/components/Spinner";
import { History, Calendar, FileText, TrendingUp, Info } from "lucide-react";

interface SimHistory {
  id: string;
  months_ahead: number;
  growth_scenario: string;
  runway_p50: number;
  created_at: string;
  uploads?: { filename: string };
}

export function HistoryPage() {
  const [history, setHistory] = useState<SimHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const { data } = await supabase.from("simulation_results")
          .select("id, months_ahead, growth_scenario, runway_p50, created_at, uploads(filename)")
          .order("created_at", { ascending: false })
          .limit(30);
        setHistory((data as any) || []);
      } catch (err) { console.error(err); }
      finally { setLoading(false); }
    }
    load();
  }, []);

  return (
    <div className="space-y-8 animate-fade-up">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#a855f7]">
            <History size={20} />
          </div>
          <h1 className="text-3xl font-bold text-white">Simulation <span className="gradient-text">History</span></h1>
        </div>
        <p className="text-[#94a3b8]">Review and compare your past Monte Carlo forecasting runs</p>
      </div>

      {loading ? <div className="flex justify-center py-20"><Spinner size={32} /></div> : (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 bg-white/[0.02]">
                  <th className="px-8 py-5 text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">Timestamp</th>
                  <th className="px-8 py-5 text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">Source Context</th>
                  <th className="px-8 py-5 text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">Strategy</th>
                  <th className="px-8 py-5 text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">Horizon</th>
                  <th className="px-8 py-5 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">P50 Runway</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {history.length === 0 && (
                  <tr><td colSpan={5} className="px-8 py-20 text-center text-[#94a3b8] text-sm">No simulations executed yet. Head to the Simulate page to start.</td></tr>
                )}
                {history.map(h => (
                  <tr key={h.id} className="hover:bg-white/[0.01] transition-colors group">
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-2 text-sm text-white font-medium">
                        <Calendar size={14} className="text-[#4b5563]" />
                        {new Date(h.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center border border-white/10 group-hover:border-[#6366f1]/40 transition-colors">
                          <FileText size={14} className="text-[#94a3b8]" />
                        </div>
                        <span className="text-sm font-bold text-white">{h.uploads?.filename || "Default Profile"}</span>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <span className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-widest ${
                        h.growth_scenario === 'bull' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        h.growth_scenario === 'bear' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                        'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                      }`}>
                        {h.growth_scenario}
                      </span>
                    </td>
                    <td className="px-8 py-5 text-sm text-[#94a3b8] font-bold tracking-tight">
                      {h.months_ahead} Months
                    </td>
                    <td className="px-8 py-5 text-right">
                      <div className="flex items-center justify-end gap-2 text-sm font-bold text-white">
                        <TrendingUp size={14} className="text-[#3ECF8E]" />
                        {h.runway_p50} Mo
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
