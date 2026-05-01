import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { supabase } from "@/shared/auth/supabase";
import { Spinner } from "@/shared/components/Spinner";

const fadeUp = { hidden: { opacity:0, y:20 }, visible: { opacity:1, y:0, transition:{ duration:0.5, ease:[0.22,1,0.36,1] } } };

export function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm]   = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) { setError("Passwords do not match"); return; }
    setError(""); setLoading(true);
    const { error: err } = await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (err) { setError(err.message); return; }
    navigate("/dashboard");
  }

  return (
    <div className="flex h-screen items-center justify-center bg-black px-4">
      <motion.div className="w-full max-w-sm" initial="hidden" animate="visible"
        variants={{ visible: { transition: { staggerChildren: 0.08 } } }}>

        <motion.div variants={fadeUp} className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-white">FoundrAI</h1>
          <p className="mt-1 text-sm text-[#6B6560]">Start making smarter decisions</p>
        </motion.div>

        <motion.div variants={fadeUp}
          className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-8">
          <h2 className="mb-6 text-base font-semibold text-[#F5F0EB]">Create account</h2>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[#6B6560] uppercase tracking-wider">Email</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                className="w-full rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#F5F0EB] placeholder-[#6B6560] focus:border-[#D97757] focus:outline-none transition-colors"
                placeholder="you@startup.com" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[#6B6560] uppercase tracking-wider">Password</label>
              <input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)}
                className="w-full rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#F5F0EB] placeholder-[#6B6560] focus:border-[#D97757] focus:outline-none transition-colors"
                placeholder="Min 8 characters" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[#6B6560] uppercase tracking-wider">Confirm password</label>
              <input type="password" required value={confirm} onChange={e => setConfirm(e.target.value)}
                className="w-full rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#F5F0EB] focus:border-[#D97757] focus:outline-none transition-colors" />
            </div>
            {error && (
              <p className="rounded-xl border border-red-900/50 bg-red-950/30 px-4 py-2.5 text-xs text-red-400">{error}</p>
            )}
            <button type="submit" disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#D97757] py-2.5 text-sm font-semibold text-white hover:bg-[#C9623F] disabled:opacity-50 transition-colors mt-2">
              {loading ? <Spinner size={14} /> : "Create account"}
            </button>
          </form>
          <p className="mt-5 text-center text-xs text-[#6B6560]">
            Have an account?{" "}
            <Link to="/auth/login" className="text-[#D97757] hover:text-[#E8906B]">Sign in</Link>
          </p>
        </motion.div>

        <motion.p variants={fadeUp} className="mt-4 text-center text-xs text-[#6B6560]">
          <Link to="/" className="hover:text-[#A89F95] transition-colors">← Back to home</Link>
        </motion.p>
      </motion.div>
    </div>
  );
}
