import { useEffect, useRef, useState } from "react";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import type { Dashboard } from "@/shared/types";
import { PieChart, Layout, ExternalLink, RefreshCcw, Info, ArrowRight } from "lucide-react";

const SUPERSET_URL = (import.meta.env.VITE_SUPERSET_URL as string | undefined) ?? "http://localhost:8088";

interface EmbedToken { token: string; expires_in: number; }

export function ChartsPage() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [selected, setSelected]     = useState<string>("");
  const [token, setToken]           = useState<string>("");
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const iframeRef                   = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    api.get<{dashboards: Dashboard[]}>("/charts/dashboards")
      .then(r => { setDashboards(r.dashboards); if (r.dashboards.length) setSelected(r.dashboards[0].id); })
      .catch(() => setError("Could not load intelligence dashboards."));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setToken(""); setError(""); setLoading(true);
    api.get<EmbedToken>(`/charts/embed-token?dashboard_id=${encodeURIComponent(selected)}`)
      .then(r => setToken(r.token))
      .catch(() => setError("Handshake with Supabase BI failed. Ensure Superset is online."))
      .finally(() => setLoading(false));
  }, [selected]);

  useEffect(() => {
    if (!token || !iframeRef.current) return;
    const send = () => {
      iframeRef.current?.contentWindow?.postMessage(
        { type: "GUEST_TOKEN_REFRESH", guestToken: token },
        SUPERSET_URL
      );
    };
    const iframe = iframeRef.current;
    iframe.addEventListener("load", send);
    return () => iframe.removeEventListener("load", send);
  }, [token]);

  const embedUrl = token
    ? `${SUPERSET_URL}/superset/embedded/${selected}?guest_token=${token}`
    : "";

  const active = dashboards.find(d => d.id === selected);

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] animate-fade-up">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#d946ef]">
              <PieChart size={20} />
            </div>
            <h1 className="text-3xl font-bold text-white">Visual <span className="gradient-text">Analytics</span></h1>
          </div>
          <p className="text-[#94a3b8]">Embedded BI dashboards powered by Apache Superset</p>
        </div>

        <div className="flex items-center gap-2 p-1 rounded-xl bg-white/5 border border-white/10">
           {dashboards.map(d => (
             <button 
                key={d.id} onClick={() => setSelected(d.id)}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  selected === d.id ? "bg-white text-black shadow-lg" : "text-[#94a3b8] hover:text-white"
                }`}
             >
               {d.title}
             </button>
           ))}
        </div>
      </div>

      {/* Main View */}
      <div className="flex-1 glass-card overflow-hidden relative group">
        {loading && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[#0a0a0f]/80 backdrop-blur-sm gap-4">
             <Spinner size={32} />
             <p className="text-xs font-bold text-[#6366f1] uppercase tracking-[0.3em] animate-pulse">Establishing Secure Session...</p>
          </div>
        )}

        {error ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-10">
             <div className="w-16 h-16 rounded-full bg-red-400/10 flex items-center justify-center mb-6">
                <Info className="text-red-400" size={32} />
             </div>
             <h2 className="text-xl font-bold text-white mb-2 italic">Connection Offline</h2>
             <p className="text-[#94a3b8] max-w-sm text-sm mb-8">{error}</p>
             <button onClick={() => window.location.reload()} className="flex items-center gap-2 px-6 py-3 rounded-xl bg-white/5 border border-white/10 text-white font-bold text-sm hover:bg-white/10 transition-all">
                <RefreshCcw size={16} /> Retry Handshake
             </button>
          </div>
        ) : token ? (
          <iframe 
            ref={iframeRef}
            src={embedUrl}
            className="w-full h-full border-none"
            title="Embedded Dashboard"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          />
        ) : !loading && (
           <div className="h-full flex flex-col items-center justify-center opacity-40">
              <Layout size={64} className="mb-4" />
              <p className="text-sm font-medium">Select a data layer from the navigation above</p>
           </div>
        )}

        {/* Floating Action Button */}
        {token && (
          <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity">
             <button 
                onClick={() => window.open(SUPERSET_URL, '_blank')}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-black/60 border border-white/10 backdrop-blur-xl text-[10px] font-bold uppercase tracking-widest text-white hover:border-[#6366f1]/50 transition-all"
             >
                Open in Fullscreen <ExternalLink size={12} />
             </button>
          </div>
        )}
      </div>

      <div className="mt-6 flex items-center justify-between px-2">
        <div className="flex items-center gap-6">
           <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#3ECF8E]" />
              <span className="text-[10px] font-bold text-[#94a3b8] uppercase">Session Secured</span>
           </div>
           <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#6366f1]" />
              <span className="text-[10px] font-bold text-[#94a3b8] uppercase">RLS Context: {selected}</span>
           </div>
        </div>
        <p className="text-[10px] font-medium text-[#4b5563] uppercase">Built with Apache Superset · Encrypted Tunnel</p>
      </div>
    </div>
  );
}
