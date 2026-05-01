import { useState } from "react";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import { ShieldCheck, Smartphone, CheckCircle2, AlertCircle, ArrowRight } from "lucide-react";

export function MfaPage() {
  const [qrCode, setQrCode] = useState("");
  const [factorId, setFactorId] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [success, setSuccess] = useState(false);

  async function startEnroll() {
    setLoading(true); setMsg("");
    try {
      const res = await api.post<any>("/auth/mfa/enroll", {});
      setQrCode(res.qr_code_uri);
      setFactorId(res.factor_id);
      setChallengeId(res.challenge_id);
    } catch (e: any) { setMsg(e.message); }
    finally { setLoading(false); }
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setMsg("");
    try {
      await api.post("/auth/mfa/verify", { factor_id: factorId, challenge_id: challengeId, code });
      setSuccess(true);
      setMsg("MFA successfully enabled!");
    } catch (e: any) { setMsg(e.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-12 animate-fade-up">
      <div className="text-center space-y-4">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/5 border border-white/10 text-[#3ECF8E] mb-2 shadow-lg">
          <ShieldCheck size={32} />
        </div>
        <h1 className="text-4xl font-bold text-white tracking-tight">Account <span className="gradient-text">Hardening</span></h1>
        <p className="text-[#94a3b8] max-w-lg mx-auto leading-relaxed">
          Enable Multi-Factor Authentication to protect your startup's sensitive financial data.
        </p>
      </div>

      <div className="max-w-2xl mx-auto">
        <div className="glass-card p-10 relative overflow-hidden">
          {success ? (
            <div className="text-center py-10 space-y-6">
               <div className="w-20 h-20 rounded-full bg-[#3ECF8E]/10 border border-[#3ECF8E]/20 flex items-center justify-center mx-auto">
                  <CheckCircle2 className="text-[#3ECF8E]" size={40} />
               </div>
               <h2 className="text-2xl font-bold text-white">Security Enabled</h2>
               <p className="text-[#94a3b8]">Your account is now protected with AAL2 tier security.</p>
               <button onClick={() => window.history.back()} className="px-8 py-3 rounded-xl bg-white/5 border border-white/10 font-bold hover:bg-white/10 transition-all text-white">
                  Return to Profile
               </button>
            </div>
          ) : !qrCode ? (
            <div className="text-center space-y-8">
              <div className="p-8 border border-white/5 rounded-2xl bg-white/[0.01]">
                <Smartphone className="mx-auto mb-4 text-[#4b5563]" size={48} />
                <p className="text-sm text-[#94a3b8] leading-relaxed">
                  We use the industry-standard TOTP protocol. You'll need an app like Google Authenticator, Microsoft Authenticator, or Authy.
                </p>
              </div>
              <button 
                onClick={startEnroll} disabled={loading}
                className="w-full py-4 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold text-white hover:scale-[1.02] transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#6366f1]/20 disabled:opacity-50"
              >
                {loading ? <Spinner size={20} /> : <>Initialize Enrollment <ArrowRight size={18} /></>}
              </button>
              {msg && <p className="text-xs text-red-400 bg-red-400/10 p-3 rounded-lg border border-red-400/20">{msg}</p>}
            </div>
          ) : (
            <form onSubmit={verify} className="space-y-10">
              <div className="space-y-6 text-center">
                <p className="text-sm text-[#94a3b8] font-bold uppercase tracking-widest">1. Scan Enrollment Secret</p>
                <div className="bg-white p-6 inline-block rounded-3xl shadow-2xl shadow-black/50" dangerouslySetInnerHTML={{__html: qrCode}}></div>
              </div>
              
              <div className="space-y-4">
                <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563] block text-center">2. Dispatch 6-Digit Token</label>
                <input 
                  type="text" required value={code} onChange={e => setCode(e.target.value)} maxLength={6} pattern="\d{6}"
                  className="w-full max-w-[280px] mx-auto block bg-white/5 border border-white/10 rounded-2xl py-5 text-center text-3xl font-mono tracking-[0.5em] text-white focus:border-[#6366f1] focus:outline-none transition-all"
                  placeholder="000000"
                />
              </div>

              <div className="flex flex-col gap-4">
                <button 
                  type="submit" disabled={loading || code.length < 6}
                  className="w-full py-4 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold text-white hover:scale-[1.02] transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#6366f1]/20 disabled:opacity-50"
                >
                  {loading ? <Spinner size={20} /> : <>Verify and Secure <ShieldCheck size={18} /></>}
                </button>
                {msg && <p className="text-xs text-red-400 text-center">{msg}</p>}
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
