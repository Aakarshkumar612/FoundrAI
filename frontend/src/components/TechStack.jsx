import React from 'react';

const TechPill = ({ name, color }) => (
  <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 reveal">
    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
    <span className="text-sm font-medium">{name}</span>
  </div>
);

export const TechStack = () => {
  const stack = [
    { name: "FastAPI", color: "#009688" },
    { name: "React 18", color: "#61DAFB" },
    { name: "Supabase", color: "#3ECF8E" },
    { name: "PostgreSQL", color: "#336791" },
    { name: "Groq API", color: "#F55036" },
    { name: "Llama 3.3", color: "#000000" },
    { name: "pgvector", color: "#FF6F61" },
    { name: "Vite", color: "#646CFF" },
    { name: "TailwindCSS", color: "#38B2AC" },
    { name: "Apache Superset", color: "#ED1B24" },
    { name: "Render", color: "#46E3B7" },
    { name: "Vercel", color: "#FFFFFF" }
  ];

  return (
    <section id="stack" className="py-32 px-6">
      <div className="max-w-7xl mx-auto grid md:grid-cols-2 gap-20 items-center">
        <div className="reveal">
          <h2 className="text-4xl md:text-5xl font-bold mb-8">Modern <span className="gradient-text">Architecture</span></h2>
          <p className="text-muted leading-relaxed mb-6 text-lg">
            FoundrAI is built on a highly modular Python/React architecture. Our backend 
            is powered by FastAPI and Uvicorn, enabling fast asynchronous SSE streaming 
            from our AI agents.
          </p>
          <p className="text-muted leading-relaxed text-lg">
            We leverage pgvector for semantic retrieval and FLAML for automatic time-series 
            forecasting, ensuring the platform is both technically robust and highly scalable.
          </p>
        </div>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 relative">
          {stack.map((t, i) => <TechPill key={i} {...t} />)}
          {/* Subtle Glow */}
          <div className="absolute inset-0 bg-blue-500/5 blur-[100px] -z-10" />
        </div>
      </div>
    </section>
  );
};
