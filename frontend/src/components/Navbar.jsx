import React from 'react';
import { useNavigate } from 'react-router-dom';

export const Navbar = () => {
  const navigate = useNavigate();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 transition-all duration-300 border-b border-white/5 bg-[#0a0a0f]/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <div 
          className="flex items-center gap-2 cursor-pointer" 
          onClick={() => navigate('/')}
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#6366f1] to-[#a855f7] flex items-center justify-center font-bold">F</div>
          <span className="text-xl font-bold gradient-text text-white">FoundrAI</span>
        </div>
        
        <div className="hidden md:flex items-center gap-8">
          {['Features', 'How It Works', 'Stack', 'Architecture', 'Contact'].map((item) => (
            <a 
              key={item} 
              href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
              className="text-sm font-medium text-[#94a3b8] hover:text-white transition-colors"
            >
              {item}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/auth/login')}
            className="text-sm font-medium text-[#94a3b8] hover:text-white transition-colors px-4 py-2"
          >
            Sign In
          </button>
          <button 
            onClick={() => navigate('/auth/register')}
            className="px-6 py-2.5 text-sm font-semibold rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] hover:scale-105 transition-all shadow-lg shadow-[#6366f1]/20"
          >
            Get Started
          </button>
        </div>
      </div>
    </nav>
  );
};
