import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { supabase } from "@/shared/auth/supabase";
import { VideoPlayer } from "./VideoPlayer";

// ── Animation variants ────────────────────────────────────────────────────────
const fadeUp = {
  hidden:  { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0,  transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] } },
};
const stagger = { visible: { transition: { staggerChildren: 0.1 } } };

// ── Marquee logos ─────────────────────────────────────────────────────────────
const LOGOS = ["Y Combinator", "Sequoia", "a16z", "Accel", "Benchmark", "Lightspeed",
               "Tiger Global", "SoftBank", "Kleiner", "GV", "Founders Fund", "Bessemer"];

// ── Badges ────────────────────────────────────────────────────────────────────
const BADGES = [
  { label: "Groq AI", icon: "⚡" },
  { label: "Supabase", icon: "⬡" },
  { label: "Superset", icon: "▤" },
];

// ── Nav links ─────────────────────────────────────────────────────────────────
const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "How it works", href: "#how-it-works" },
  { label: "Tech Stack", href: "#tech-stack" },
];

const FEATURES = [
  {
    title: "4-Agent AI Pipeline",
    desc: "Sequential analysis by Market, Risk, Revenue, and Strategy agents powered by Groq and Llama 3.3.",
    icon: "◇"
  },
  {
    title: "Vector-Based RAG",
    desc: "Your financial documents are chunked and embedded via sentence-transformers into pgvector for precise semantic search.",
    icon: "⬡"
  },
  {
    title: "Monte Carlo Simulation",
    desc: "Simulate 10,000 future paths in under 200ms using NumPy. View P10/P50/P90 confidence bands for revenue and runway.",
    icon: "∿"
  },
  {
    title: "Market Intelligence",
    desc: "Automated scheduled ingestion of global startup news, fully embedded to augment your strategic advisory.",
    icon: "📰"
  }
];

const STEPS = [
  { title: "Connect Your Data", desc: "Upload your financial CSVs, Excel files, or PDFs. We automatically extract and index the metrics." },
  { title: "Ask Complex Questions", desc: "Query your data in plain English. Our agents retrieve relevant context and synthesize actionable advice." },
  { title: "Simulate Scenarios", desc: "Adjust CAC, burn rates, and market conditions to forecast runway and evaluate strategic pivots." }
];

export function LandingPage() {
  const navigate = useNavigate();
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) { setAuthed(true); navigate("/dashboard"); }
    });
  }, [navigate]);

  if (authed) return null;

  return (
    <div className="relative min-h-screen bg-black overflow-x-hidden text-[#F5F0EB]">

      {/* ── Navbar ──────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/8 bg-black/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="text-base font-bold tracking-tight text-white">FoundrAI</span>
          <div className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map(({ label, href }) => (
              <a key={label} href={href}
                className="px-3 py-1.5 text-sm rounded-lg text-[#6B6560] hover:text-[#F5F0EB] transition-colors">
                {label}
              </a>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <Link to="/auth/login"
              className="text-sm text-[#A89F95] hover:text-white transition-colors">
              Sign in
            </Link>
            <Link to="/auth/register"
              className="rounded-xl bg-white px-4 py-1.5 text-sm font-semibold text-black hover:bg-white/90 transition-colors">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero Section ─────────────────────────────────────────────────────── */}
      <div className="relative flex flex-col items-center justify-center min-h-screen px-6 pt-20 text-center border-b border-white/8 overflow-hidden">
        {/* Background Video */}
        <div className="absolute inset-0 z-0">
          <VideoPlayer />
          <div className="absolute inset-0 bg-black/40" />
          <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-black to-transparent" />
          <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black to-transparent" />
        </div>

        <motion.div
          className="relative z-10 flex flex-col items-center gap-6 max-w-3xl"
          variants={stagger}
          initial="hidden"
          animate="visible"
        >
          <motion.div variants={fadeUp} className="flex flex-wrap items-center justify-center gap-2">
            {BADGES.map(({ label, icon }) => (
              <span key={label}
                className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm px-4 py-1.5 text-xs text-[#A89F95]">
                <span>{icon}</span>
                <span className="text-[#6B6560]">Powered by</span>
                <span className="text-[#F5F0EB] font-medium">{label}</span>
              </span>
            ))}
          </motion.div>

          <motion.h1 variants={fadeUp}
            className="text-[clamp(44px,8vw,80px)] font-bold leading-[1.05] tracking-tight text-[#F5F0EB]">
            Where Founders Make{" "}
            <span className="text-[#D97757]">Smarter Decisions</span>
          </motion.h1>

          <motion.p variants={fadeUp}
            className="text-base text-[#A89F95] max-w-xl leading-relaxed">
            FoundrAI is your private AI analyst. Upload financials, simulate 10,000 scenarios,
            and get structured advice grounded in your data and live market news.
          </motion.p>

          <motion.div variants={fadeUp} className="flex flex-wrap items-center justify-center gap-3 mt-2">
            <Link to="/auth/register"
              className="rounded-xl border border-white bg-black px-6 py-3 text-sm font-semibold text-white hover:bg-white/5 transition-colors">
              Get Started for Free
            </Link>
            <Link to="/auth/login"
              className="rounded-xl border border-white/15 bg-white/5 backdrop-blur-sm px-6 py-3 text-sm font-semibold text-white hover:bg-white/10 transition-colors">
              Sign In
            </Link>
          </motion.div>
        </motion.div>

        {/* Logo Marquee */}
        <div className="absolute bottom-0 left-0 right-0 z-10 border-t border-white/8 bg-black/60 backdrop-blur-sm py-5">
          <div className="flex w-max animate-marquee gap-16">
            {[...LOGOS, ...LOGOS].map((name, i) => (
              <span key={i} className="text-sm font-medium text-white/20 whitespace-nowrap tracking-widest uppercase">
                {name}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── Features Section ────────────────────────────────────────────────── */}
      <div id="features" className="py-32 px-6 max-w-7xl mx-auto border-b border-[#1e1c1a]">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Enterprise-Grade Capabilities</h2>
          <p className="text-[#A89F95] max-w-2xl mx-auto">
            A comprehensive suite of tools designed to replace expensive financial modeling and strategic consulting.
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          {FEATURES.map((f, i) => (
            <motion.div key={i} initial={{opacity:0, y:20}} whileInView={{opacity:1, y:0}} viewport={{once:true}} transition={{delay: i*0.1}}
              className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-8 hover:border-[#D97757]/40 transition-colors">
              <span className="text-3xl text-[#D97757] mb-4 block">{f.icon}</span>
              <h3 className="text-xl font-semibold mb-2">{f.title}</h3>
              <p className="text-[#A89F95] text-sm leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* ── How It Works Section ────────────────────────────────────────────── */}
      <div id="how-it-works" className="py-32 px-6 max-w-7xl mx-auto border-b border-[#1e1c1a]">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">How FoundrAI Works</h2>
          <p className="text-[#A89F95]">From raw data to strategic clarity in seconds.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8 relative">
          <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-[1px] bg-[#1e1c1a] z-0" />
          {STEPS.map((step, i) => (
            <motion.div key={i} initial={{opacity:0, y:20}} whileInView={{opacity:1, y:0}} viewport={{once:true}} transition={{delay: i*0.2}}
              className="relative z-10 flex flex-col items-center text-center">
              <div className="w-24 h-24 rounded-full bg-[#161412] border border-[#2a2520] flex items-center justify-center text-2xl font-bold text-[#D97757] mb-6">
                {i + 1}
              </div>
              <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
              <p className="text-[#A89F95] text-sm px-4">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* ── Tech Stack Section ──────────────────────────────────────────────── */}
      <div id="tech-stack" className="py-32 px-6 max-w-7xl mx-auto text-center border-b border-[#1e1c1a]">
         <h2 className="text-3xl font-bold mb-10">Built with Modern Primitives</h2>
         <div className="flex flex-wrap justify-center gap-4">
           {['FastAPI', 'Python 3.12', 'React 18', 'TailwindCSS', 'Supabase', 'PostgreSQL', 'pgvector', 'Groq', 'Llama 3.3', 'Recharts'].map(tech => (
             <span key={tech} className="px-5 py-2.5 rounded-full border border-[#1e1c1a] bg-[#0d0c0b] text-[#A89F95] text-sm">
               {tech}
             </span>
           ))}
         </div>
      </div>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="py-16 px-6 max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
        <div>
          <span className="text-lg font-bold text-white">FoundrAI</span>
          <p className="text-xs text-[#6B6560] mt-2">© 2026 FoundrAI Inc. All rights reserved.</p>
        </div>
        <div className="flex gap-6 text-sm text-[#A89F95]">
          <a href="#" className="hover:text-white transition-colors">Privacy</a>
          <a href="#" className="hover:text-white transition-colors">Terms</a>
          <a href="#" className="hover:text-white transition-colors">Contact Support</a>
        </div>
      </footer>

    </div>
  );
}
