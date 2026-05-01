import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Play } from 'lucide-react';

export const Hero = () => {
  const navigate = useNavigate();

  return (
    <section className="relative min-h-screen pt-32 pb-20 overflow-hidden flex flex-col items-center justify-center text-center px-6">
      {/* Background Orbs */}
      <div className="absolute top-1/4 -left-20 w-96 h-96 bg-[#6366f1]/20 rounded-full blur-[100px] animate-float" />
      <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-[#a855f7]/20 rounded-full blur-[100px] animate-float [animation-delay:2s]" />
      
      <div className="relative z-10 max-w-4xl mx-auto reveal">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-[#8b5cf6] mb-8">
          <span className="w-2 h-2 rounded-full bg-[#8b5cf6] animate-pulse" />
          AI-Powered Decision Intelligence for Founders
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold leading-tight mb-6 text-white">
          The Autonomous <span className="gradient-text">AI Advisory</span> <br />
          Platform for Startup Founders
        </h1>
        
        <p className="text-lg md:text-xl text-[#94a3b8] max-w-2xl mx-auto mb-10 leading-relaxed">
          FoundrAI combines multi-agent orchestration, RAG, and AutoML to help you 
          make data-driven strategic decisions. Upload financials, simulate 10,000 scenarios, 
          and get structured advice grounded in your data.
        </p>
        
        <div className="flex flex-wrap items-center justify-center gap-4">
          <button 
            onClick={() => navigate('/auth/register')}
            className="px-8 py-4 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold hover:scale-105 transition-transform flex items-center gap-2 shadow-lg shadow-[#6366f1]/20"
          >
            Get Started <ArrowRight size={20} />
          </button>
          <button 
            onClick={() => navigate('/auth/login')}
            className="px-8 py-4 rounded-xl bg-white/5 border border-white/10 font-bold hover:bg-white/10 transition-colors flex items-center gap-2 text-white"
          >
            Sign In <ArrowRight size={20} />
          </button>
        </div>

        {/* Animated Architecture Visual */}
        <div className="mt-20 relative reveal [transition-delay:200ms]">
          <div className="glass-card p-1 max-w-5xl mx-auto bg-gradient-to-tr from-white/10 to-transparent">
             <div className="bg-[#0a0a0f] rounded-xl p-8 flex flex-col md:flex-row items-center justify-around gap-8 border border-white/5">
                {[
                  { name: 'Upload', color: '#6366f1', icon: '📁' },
                  { name: 'Index', color: '#8b5cf6', icon: '⬡' },
                  { name: 'Query', color: '#a855f7', icon: '◇' },
                  { name: 'Agents', color: '#06b6d4', icon: '🤖' },
                  { name: 'Strategy', color: '#D97757', icon: '🎯' },
                ].map((step, i, arr) => (
                  <React.Fragment key={step.name}>
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center text-2xl border border-white/10" style={{ color: step.color }}>
                        {step.icon}
                      </div>
                      <span className="text-sm font-semibold text-white">{step.name}</span>
                    </div>
                    {i < arr.length - 1 && (
                      <div className="hidden md:block w-12 h-[1px] bg-gradient-to-r from-white/10 to-white/10" />
                    )}
                  </React.Fragment>
                ))}
             </div>
          </div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-1/2 bg-blue-500/10 blur-[120px] -z-10" />
        </div>
      </div>
    </section>
  );
};
