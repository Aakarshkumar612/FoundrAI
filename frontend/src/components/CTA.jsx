import React from 'react';
import { useNavigate } from 'react-router-dom';

export const CTA = () => {
  const navigate = useNavigate();

  return (
    <section id="contact" className="py-40 px-6 relative overflow-hidden">
      {/* Background Aura */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#6366f1]/10 rounded-full blur-[140px] -z-10" />
      
      <div className="max-w-4xl mx-auto text-center reveal">
        <h2 className="text-5xl md:text-6xl font-bold mb-8 text-white">Ready to Build Your <br /><span className="gradient-text">Future?</span></h2>
        <p className="text-[#94a3b8] text-lg mb-12 max-w-xl mx-auto">
          Join hundreds of founders who use FoundrAI to simulate their growth and 
          validate their strategic pivots with enterprise-grade intelligence.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto">
          <button 
            onClick={() => navigate('/auth/register')}
            className="w-full px-8 py-4 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold hover:scale-105 transition-transform shadow-lg shadow-[#6366f1]/20 text-white"
          >
            Get Started Now
          </button>
          <button 
            onClick={() => navigate('/auth/login')}
            className="w-full px-8 py-4 rounded-xl bg-white/5 border border-white/10 font-bold hover:bg-white/10 transition-colors text-white"
          >
            Existing User? Sign In
          </button>
        </div>
        
        <p className="mt-6 text-xs text-[#94a3b8]">No credit card required. Free prototype access enabled for 2026.</p>
      </div>
    </section>
  );
};
