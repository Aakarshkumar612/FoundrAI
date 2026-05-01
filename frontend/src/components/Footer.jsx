import React from 'react';

export const Footer = () => {
  return (
    <footer className="py-20 px-6 border-t border-white/5">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start gap-12">
        <div className="reveal">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#6366f1] to-[#a855f7] flex items-center justify-center font-bold">F</div>
            <span className="text-xl font-bold gradient-text">FoundrAI</span>
          </div>
          <p className="text-muted text-sm max-w-xs leading-relaxed">
            The world's first autonomous AI advisory platform built specifically for high-growth startup founders.
          </p>
        </div>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-16 reveal">
          <div className="flex flex-col gap-4">
            <span className="text-sm font-bold uppercase tracking-widest text-white">Product</span>
            <a href="#features" className="text-sm text-muted hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="text-sm text-muted hover:text-white transition-colors">Workflow</a>
            <a href="#stack" className="text-sm text-muted hover:text-white transition-colors">Architecture</a>
          </div>
          <div className="flex flex-col gap-4">
            <span className="text-sm font-bold uppercase tracking-widest text-white">Company</span>
            <a href="#" className="text-sm text-muted hover:text-white transition-colors">About Us</a>
            <a href="#" className="text-sm text-muted hover:text-white transition-colors">Privacy</a>
            <a href="#" className="text-sm text-muted hover:text-white transition-colors">Terms</a>
          </div>
          <div className="flex flex-col gap-4">
            <span className="text-sm font-bold uppercase tracking-widest text-white">Social</span>
            <a href="#" className="text-sm text-muted hover:text-white transition-colors">Twitter</a>
            <a href="#" className="text-sm text-muted hover:text-white transition-colors">LinkedIn</a>
            <a href="#" className="text-sm text-muted hover:text-white transition-colors">GitHub</a>
          </div>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto mt-20 pt-8 border-t border-white/5 flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-muted reveal">
        <p>© 2026 FoundrAI Inc. All rights reserved.</p>
        <p>Built with FastAPI, React 18, and Groq Inference.</p>
      </div>
    </footer>
  );
};
