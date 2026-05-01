import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import type { Dashboard } from "@/shared/types";

const fadeUp = { hidden:{opacity:0,y:16}, visible:{opacity:1,y:0,transition:{duration:0.4,ease:[0.22,1,0.36,1]}} };

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
      .catch(() => setError("Could not load dashboard list."));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setToken(""); setError(""); setLoading(true);
    api.get<EmbedToken>(`/charts/embed-token?dashboard_id=${encodeURIComponent(selected)}`)
      .then(r => setToken(r.token))
      .catch(() => setError("Could not get embed token — check Superset configuration."))
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
    <motion.div className="p-8 flex flex-col gap-6 h-full" initial="hidden" animate="visible"
      variants={{ visible:{transition:{staggerChildren:0.07}} }}>

      <motion.div variants={fadeUp}>
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Charts</h1>
        <p className="mt-1 text-sm text-[#6B6560]">Embedded Superset dashboards powered by your financial data.</p>
      </motion.div>

      {/* Dashboard tabs */}
      {dashboards.length > 0 && (
        <motion.div variants={fadeUp} className="flex gap-2 flex-wrap">
          {dashboards.map(d => (
            <button key={d.id} onClick={() => setSelected(d.id)}
              className={`rounded-xl px-4 py-2 text-xs font-semibold transition-colors ${
                selected === d.id
                  ? "bg-[#D97757] text-white"
                  : "border border-[#1e1c1a] bg-[#161412] text-[#A89F95] hover:border-[#2a2520] hover:text-[#F5F0EB]"
              }`}>
              {d.title}
            </button>
          ))}
        </motion.div>
      )}

      {active && (
        <motion.p variants={fadeUp} className="text-xs text-[#6B6560] -mt-3">{active.description}</motion.p>
      )}

      {/* Embed area */}
      <motion.div variants={fadeUp} className="flex-1 min-h-[480px] rounded-2xl border border-[#1e1c1a] overflow-hidden bg-[#0d0c0b] relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center gap-3">
            <Spinner size={18} />
            <p className="text-sm text-[#6B6560]">Loading dashboard…</p>
          </div>
        )}

        {error && !loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-8 text-center">
            <p className="text-sm text-red-400">{error}</p>
            <p className="text-xs text-[#6B6560]">
              Start Superset with <code className="font-mono text-[#A89F95]">docker compose up</code> in the <code className="font-mono text-[#A89F95]">superset/</code> directory,
              then set <code className="font-mono text-[#A89F95]">VITE_SUPERSET_URL</code> and <code className="font-mono text-[#A89F95]">SUPERSET_PASSWORD</code>.
            </p>
          </div>
        )}

        {token && !loading && (
          <iframe
            ref={iframeRef}
            src={embedUrl}
            title={active?.title ?? "Dashboard"}
            className="w-full h-full border-0"
            allow="fullscreen"
          />
        )}

        {!token && !loading && !error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-[#6B6560]">Select a dashboard above</p>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
