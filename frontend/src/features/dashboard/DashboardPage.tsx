import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { supabase } from "@/shared/auth/supabase";
import { Spinner } from "@/shared/components/Spinner";

const fadeUp = { hidden:{opacity:0,y:16}, visible:{opacity:1,y:0,transition:{duration:0.4,ease:[0.22,1,0.36,1]}} };

interface RecentUpload { id:string; filename:string; file_type:string; created_at:string; }

const ACTIONS = [
  { to:"/upload",   label:"Upload Document",  desc:"CSV, PDF, Excel, Word, images",  icon:"⬆" },
  { to:"/query",    label:"Ask AI",            desc:"Multi-agent advisory analysis",  icon:"◇" },
  { to:"/simulate", label:"Run Simulation",    desc:"10k Monte Carlo scenarios",       icon:"∿" },
  { to:"/charts",   label:"View Dashboards",   desc:"Embedded Superset BI charts",    icon:"▤" },
];

export function DashboardPage() {
  const [email, setEmail]             = useState("");
  const [uploads, setUploads]         = useState<RecentUpload[]>([]);
  const [uploadCount, setUploadCount] = useState(0);
  const [simCount, setSimCount]       = useState(0);
  const [loading, setLoading]         = useState(true);

  useEffect(() => {
    (async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setEmail(user?.email ?? "");
      const [uRes, sRes] = await Promise.all([
        supabase.from("uploads").select("id,filename,file_type,created_at", { count:"exact" })
          .order("created_at",{ascending:false}).limit(5),
        supabase.from("simulation_results").select("id",{count:"exact"}).limit(1),
      ]);
      setUploads(uRes.data ?? []);
      setUploadCount(uRes.count ?? 0);
      setSimCount(sRes.count ?? 0);
      setLoading(false);
    })();
  }, []);

  return (
    <motion.div className="p-8 max-w-5xl" initial="hidden" animate="visible"
      variants={{ visible:{transition:{staggerChildren:0.08}} }}>

      <motion.div variants={fadeUp} className="mb-8">
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Dashboard</h1>
        {email && <p className="mt-1 text-sm text-[#6B6560]">{email}</p>}
      </motion.div>

      {/* Stats */}
      <motion.div variants={fadeUp} className="grid grid-cols-2 gap-4 mb-8">
        {[{label:"Total uploads",value:uploadCount},{label:"Simulations run",value:simCount}].map(s => (
          <div key={s.label} className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-5">
            {loading ? <Spinner size={16} /> : (
              <>
                <p className="text-3xl font-bold text-[#F5F0EB]">{s.value}</p>
                <p className="mt-1 text-xs text-[#6B6560] uppercase tracking-wider">{s.label}</p>
              </>
            )}
          </div>
        ))}
      </motion.div>

      {/* Quick actions */}
      <motion.div variants={fadeUp}>
        <p className="mb-3 text-xs text-[#6B6560] uppercase tracking-widest">Quick actions</p>
        <div className="grid grid-cols-2 gap-3 mb-8">
          {ACTIONS.map(a => (
            <Link key={a.to} to={a.to}
              className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-5 hover:border-[#D97757]/40 hover:bg-[#161412] transition-all group">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-lg text-[#D97757] group-hover:scale-110 transition-transform">{a.icon}</span>
                <p className="text-sm font-semibold text-[#F5F0EB]">{a.label}</p>
              </div>
              <p className="text-xs text-[#6B6560]">{a.desc}</p>
            </Link>
          ))}
        </div>
      </motion.div>

      {/* Recent uploads */}
      <motion.div variants={fadeUp}>
        <p className="mb-3 text-xs text-[#6B6560] uppercase tracking-widest">Recent uploads</p>
        <div className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] divide-y divide-[#1e1c1a]">
          {loading ? (
            <div className="p-6 flex justify-center"><Spinner size={20} /></div>
          ) : uploads.length === 0 ? (
            <div className="p-6 text-sm text-[#6B6560] text-center">
              No uploads yet —{" "}
              <Link to="/upload" className="text-[#D97757] hover:text-[#E8906B]">upload your first document</Link>
            </div>
          ) : uploads.map(u => (
            <div key={u.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="text-sm font-medium text-[#F5F0EB]">{u.filename}</p>
                <p className="text-xs text-[#6B6560]">{u.file_type}</p>
              </div>
              <p className="text-xs text-[#6B6560]">{new Date(u.created_at).toLocaleDateString()}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}
