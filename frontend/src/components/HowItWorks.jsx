import React from 'react';

const Step = ({ num, title, desc, delay }) => (
  <div className="relative pl-12 reveal" style={{ transitionDelay: `${delay}ms` }}>
    <div className="absolute left-0 top-0 w-8 h-8 rounded-full bg-gradient-to-tr from-[#6366f1] to-[#a855f7] flex items-center justify-center font-bold text-sm z-10">
      {num}
    </div>
    <h3 className="text-xl font-bold mb-3">{title}</h3>
    <p className="text-muted text-sm leading-relaxed mb-12">{desc}</p>
  </div>
);

export const HowItWorks = () => {
  const steps = [
    {
      title: "Data Integration",
      desc: "Securely upload your monthly financial CSVs. We automatically extract key metrics like MRR, CAC, and Burn Rate."
    },
    {
      title: "RAG Knowledge Indexing",
      desc: "Your data is encoded via ColBERT and stored in pgvector, alongside live market news, creating a private knowledge base."
    },
    {
      title: "Multi-Agent Synthesis",
      desc: "Our specialized Market, Risk, Revenue, and Strategy agents analyze the retrieved context to answer your strategic questions."
    },
    {
      title: "Strategic Decision Support",
      desc: "Receive structured advice, Monte Carlo forecasts, and interactive BI dashboards to finalize your roadmap."
    }
  ];

  return (
    <section id="how-it-works" className="py-32 px-6 bg-white/[0.01]">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-20 reveal">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">From Data to <span className="gradient-text">Clarity</span></h2>
          <p className="text-muted">A streamlined autonomous workflow that transforms raw data into actionable advice.</p>
        </div>
        
        <div className="relative border-l border-white/10 ml-4 pt-4">
           {steps.map((s, i) => (
             <Step key={i} num={i+1} {...s} delay={i*100} />
           ))}
           {/* Animated line indicator */}
           <div className="absolute left-[-1px] top-0 w-px h-full bg-gradient-to-b from-[#6366f1] to-transparent animate-pulse" />
        </div>
      </div>
    </section>
  );
};
