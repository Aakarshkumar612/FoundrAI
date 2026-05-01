import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "@/shared/auth/supabase";
import { Shield, Mail, Lock, Loader2, ArrowRight } from "lucide-react";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function login(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError("");
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) { setError(error.message); setLoading(false); }
    else navigate("/dashboard");
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-[#6366f1]/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-[#a855f7]/10 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="w-full max-w-md relative z-10 animate-fade-up">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#6366f1] to-[#a855f7] mb-6 shadow-lg shadow-[#6366f1]/20">
            <Shield className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
          <p className="text-[#94a3b8]">Sign in to your advisory dashboard</p>
        </div>

        <form onSubmit={login} className="glass-card p-8 space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-[#94a3b8] ml-1">Work Email</label>
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-[#4b5563]" size={18} />
              <input 
                type="email" required value={email} onChange={e => setEmail(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white focus:border-[#6366f1] focus:outline-none transition-colors"
                placeholder="name@company.com"
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold uppercase tracking-wider text-[#94a3b8] ml-1">Password</label>
              <a href="#" className="text-xs text-[#6366f1] hover:underline">Forgot?</a>
            </div>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-[#4b5563]" size={18} />
              <input 
                type="password" required value={password} onChange={e => setPassword(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white focus:border-[#6366f1] focus:outline-none transition-colors"
                placeholder="••••••••"
              />
            </div>
          </div>

          {error && <p className="text-xs text-red-400 bg-red-400/10 p-3 rounded-lg border border-red-400/20">{error}</p>}

          <button 
            disabled={loading}
            className="w-full py-4 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold text-white hover:scale-[1.02] transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#6366f1]/20 disabled:opacity-50"
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : <>Sign In <ArrowRight size={20} /></>}
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-[#94a3b8]">
          Don't have an account? <Link to="/auth/register" className="text-[#6366f1] font-semibold hover:underline">Start free trial</Link>
        </p>
      </div>
    </div>
  );
}
