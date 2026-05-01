import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { supabase } from "@/shared/auth/supabase";
import { Spinner } from "@/shared/components/Spinner";

const fadeUp = { hidden:{opacity:0,y:16}, visible:{opacity:1,y:0,transition:{duration:0.4,ease:[0.22,1,0.36,1]}} };

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
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <motion.div className="p-8 max-w-4xl" initial="hidden" animate="visible" variants={{ visible:{transition:{staggerChildren:0.08}} }}>
      <motion.div variants={fadeUp} className="mb-8">
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Simulation History</h1>
        <p className="mt-1 text-sm text-[#6B6560]">Review past Monte Carlo simulation runs.</p>
      </motion.div>

      {loading ? <Spinner size={24} /> : (
        <motion.div variants={fadeUp} className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] overflow-hidden">
          <table className="w-full text-left text-sm text-[#A89F95]">
            <thead className="bg-[#161412] text-xs uppercase tracking-wider text-[#6B6560]">
              <tr>
                <th className="px-6 py-4 font-medium">Date</th>
                <th className="px-6 py-4 font-medium">Source Document</th>
                <th className="px-6 py-4 font-medium">Scenario</th>
                <th className="px-6 py-4 font-medium">Horizon</th>
                <th className="px-6 py-4 font-medium text-right">P50 Runway</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1c1a]">
              {history.length === 0 && (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-[#6B6560]">No simulations run yet.</td></tr>
              )}
              {history.map(h => (
                <tr key={h.id} className="hover:bg-[#161412]/50 transition-colors">
                  <td className="px-6 py-4">{new Date(h.created_at).toLocaleString()}</td>
                  <td className="px-6 py-4 font-medium text-[#F5F0EB]">{h.uploads?.filename || "Default"}</td>
                  <td className="px-6 py-4 capitalize text-[#D97757]">{h.growth_scenario}</td>
                  <td className="px-6 py-4">{h.months_ahead} mos</td>
                  <td className="px-6 py-4 text-right font-bold text-[#F5F0EB]">{h.runway_p50} mos</td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      )}
    </motion.div>
  );
}
