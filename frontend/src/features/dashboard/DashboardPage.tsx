import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { supabase } from "@/shared/auth/supabase";
import { Spinner } from "@/shared/components/Spinner";
import { 
  BarChart3, 
  Clock, 
  FileText, 
  Plus, 
  ArrowUpRight, 
  ArrowRight,
  TrendingUp,
  BrainCircuit,
  Zap
} from "lucide-react";

const StatCard = ({ label, value, icon: Icon, color, trend }) => (
  <div className="glass-card p-6 reveal">
    <div className="flex justify-between items-start mb-4">
      <div className={`w-12 h-12 rounded-xl bg-gradient-to-tr ${color} flex items-center justify-center shadow-lg`}>
        <Icon className="text-white" size={24} />
      </div>
      {trend && (
        <span className="flex items-center gap-1 text-[10px] font-bold text-[#3ECF8E] bg-[#3ECF8E]/10 px-2 py-1 rounded-full border border-[#3ECF8E]/20">
          <ArrowUpRight size={10} /> {trend}
        </span>
      )}
    </div>
    <div className="text-2xl font-bold text-white mb-1">{value}</div>
    <div className="text-xs font-semibold uppercase tracking-wider text-[#94a3b8]">{label}</div>
  </div>
);

export function DashboardPage() {
  const [uploads, setUploads] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ simulations: 0, uploads: 0 });

  useEffect(() => {
    async function loadData() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const [upRes, simRes] = await Promise.all([
        supabase.from("uploads").select("*").order("created_at", { ascending: false }).limit(5),
        supabase.from("simulation_results").select("id", { count: "exact" })
      ]);

      setUploads(upRes.data || []);
      setStats({
        simulations: simRes.count || 0,
        uploads: upRes.data?.length || 0
      });
      setLoading(false);
    }
    loadData();
  }, []);

  return (
    <div className="space-y-10 animate-fade-up">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white">Founder <span className="gradient-text">Insights</span></h1>
          <p className="text-[#94a3b8] mt-1">Real-time overview of your startup intelligence</p>
        </div>
        <Link to="/upload" className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold text-sm hover:scale-105 transition-all shadow-lg shadow-[#6366f1]/20">
          <Plus size={18} /> New Document
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard label="Total Uploads" value={stats.uploads} icon={FileText} color="from-[#6366f1] to-[#8b5cf6]" trend="+12%" />
        <StatCard label="Simulations Run" value={stats.simulations} icon={TrendingUp} color="from-[#8b5cf6] to-[#a855f7]" trend="+5" />
        <StatCard label="AI Confidence" value="98.2%" icon={BrainCircuit} color="from-[#a855f7] to-[#d946ef]" />
        <StatCard label="Compute Power" value="Groq Llama 3" icon={Zap} color="from-[#06b6d4] to-[#3b82f6]" />
      </div>

      {/* Main Grid */}
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Recent Activity */}
        <div className="lg:col-span-2 glass-card p-8">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <Clock className="text-[#6366f1]" size={20} />
              <h2 className="text-xl font-bold text-white">Recent Activity</h2>
            </div>
            <Link to="/history" className="text-xs text-[#6366f1] font-bold hover:underline uppercase tracking-widest">View All</Link>
          </div>

          {loading ? <div className="flex justify-center py-10"><Spinner size={24} /></div> : (
            <div className="space-y-4">
              {uploads.length === 0 && <p className="text-[#94a3b8] text-sm text-center py-6 border border-dashed border-white/10 rounded-xl">No recent uploads detected.</p>}
              {uploads.map((u, i) => (
                <div key={u.id} className="flex items-center justify-between p-4 rounded-xl hover:bg-white/5 transition-colors border border-transparent hover:border-white/5 group">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center border border-white/10 text-white font-bold group-hover:bg-[#6366f1]/20 group-hover:text-[#6366f1] transition-colors">
                      {u.file_type.slice(0,1).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-bold text-white leading-tight">{u.filename}</p>
                      <p className="text-[10px] text-[#94a3b8] uppercase tracking-wider mt-1">{new Date(u.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right hidden sm:block">
                      <p className="text-xs font-bold text-white">{u.row_count || 'N/A'}</p>
                      <p className="text-[10px] text-[#94a3b8] uppercase tracking-tighter">Rows Extracted</p>
                    </div>
                    <Link to="/query" className="p-2 rounded-lg bg-white/5 hover:bg-[#6366f1]/20 text-[#94a3b8] hover:text-[#6366f1] transition-colors">
                      <Plus size={16} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions / Integration */}
        <div className="space-y-8">
          <div className="glass-card p-8 bg-gradient-to-br from-[#6366f1]/10 to-transparent border-[#6366f1]/20 relative overflow-hidden">
            <BrainCircuit className="absolute -right-4 -bottom-4 text-[#6366f1]/20" size={120} />
            <h3 className="text-lg font-bold text-white mb-2 relative z-10">AI Power On</h3>
            <p className="text-xs text-[#94a3b8] mb-6 relative z-10 leading-relaxed">Your 4-agent strategic advisor is ready. Ask about your runway, market size, or growth risks.</p>
            <Link to="/query" className="w-full inline-flex items-center justify-center gap-2 py-3 rounded-xl bg-white text-black font-bold text-xs hover:bg-white/90 transition-all relative z-10">
              Launch AI Advisor <ArrowRight size={14} />
            </Link>
          </div>

          <div className="glass-card p-8">
            <h3 className="text-sm font-bold uppercase tracking-widest text-[#94a3b8] mb-6">Market Trends</h3>
            <div className="space-y-6">
              {[
                { title: 'SaaS Multiples 2026', source: 'Crunchbase', date: '2h ago' },
                { title: 'Fintech Funding Shifts', source: 'TechCrunch', date: '5h ago' },
              ].map((news, i) => (
                <div key={i} className="flex flex-col gap-1 border-l-2 border-[#6366f1]/30 pl-4 py-1">
                  <p className="text-xs font-bold text-white hover:text-[#6366f1] cursor-pointer transition-colors leading-snug">{news.title}</p>
                  <p className="text-[10px] text-[#94a3b8] uppercase">{news.source} · {news.date}</p>
                </div>
              ))}
              <Link to="/news" className="block text-center text-[10px] font-bold text-[#6366f1] hover:underline uppercase tracking-[0.2em] mt-2">More Intelligence</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
