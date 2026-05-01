import React from 'react';
import { Bot, BarChart3, Database, Globe, ShieldAlert, Zap } from 'lucide-react';

const FeatureCard = ({ icon: Icon, title, desc, delay }) => (
  <div className="glass-card p-8 hover:-translate-y-2 transition-all duration-500 group reveal" style={{ transitionDelay: `${delay}ms` }}>
    <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#6366f1] to-[#a855f7] flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
      <Icon className="text-white" size={24} />
    </div>
    <h3 className="text-xl font-bold mb-4">{title}</h3>
    <p className="text-muted text-sm leading-relaxed">{desc}</p>
    <div className="mt-6 w-full h-px bg-gradient-to-r from-white/10 to-transparent group-hover:from-[#6366f1]/50" />
  </div>
);

export const Features = () => {
  const features = [
    {
      icon: Bot,
      title: "Multi-Agent Orchestration",
      desc: "Four specialist agents (Market, Risk, Revenue, Strategy) work together to analyze your data and provide a holistic strategic outlook.",
      delay: 0
    },
    {
      icon: Database,
      title: "Vector-Based RAG",
      desc: "Connect your financial documents and news feeds. Our Haystack-powered ColBERT pipeline ensures precise context retrieval for every query.",
      delay: 100
    },
    {
      icon: BarChart3,
      title: "Monte Carlo Simulations",
      desc: "Generate 10,000 future paths using stochastic modeling. Understand P10/P50/P90 confidence intervals for your revenue and runway.",
      delay: 200
    },
    {
      icon: Zap,
      title: "Fast AutoML Selection",
      desc: "Uses FLAML to automatically select and train the best time-series models for your specific startup metrics in under 60 seconds.",
      delay: 300
    },
    {
      icon: Globe,
      title: "Market Intelligence",
      desc: "Continuous background news ingestion from global sources keeps your AI advisor up-to-date with relevant startup and tech trends.",
      delay: 400
    },
    {
      icon: ShieldAlert,
      title: "Risk Assessment",
      desc: "Automatic identification of primary growth risks, runway warnings, and actionable mitigation recommendations based on your real financials.",
      delay: 500
    }
  ];

  return (
    <section id="features" className="py-32 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-20 reveal">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Enterprise-Grade <span className="gradient-text">AI advisory</span></h2>
          <p className="text-muted max-w-2xl mx-auto">A comprehensive suite of intelligence tools designed to replace expensive consulting with real-time, data-driven analysis.</p>
        </div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((f, i) => (
            <FeatureCard key={i} {...f} />
          ))}
        </div>
      </div>
    </section>
  );
};
