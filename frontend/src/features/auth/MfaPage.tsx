import { useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";

const fadeUp = { hidden:{opacity:0,y:16}, visible:{opacity:1,y:0,transition:{duration:0.4,ease:[0.22,1,0.36,1]}} };

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
    <motion.div className="p-8 max-w-2xl" initial="hidden" animate="visible" variants={{ visible:{transition:{staggerChildren:0.08}} }}>
      <motion.div variants={fadeUp} className="mb-8">
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Two-Factor Authentication</h1>
        <p className="mt-1 text-sm text-[#6B6560]">Secure your account with an authenticator app.</p>
      </motion.div>

      <motion.div variants={fadeUp} className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-8">
        {success ? (
           <p className="text-[#4CAF84]">Two-factor authentication is active on your account.</p>
        ) : !qrCode ? (
          <div>
            <p className="text-sm text-[#A89F95] mb-4">Click below to generate a QR code for your authenticator app.</p>
            <button onClick={startEnroll} disabled={loading} className="rounded-xl bg-[#D97757] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#C9623F] disabled:opacity-50 transition-colors">
              {loading ? <Spinner size={14} /> : "Enable MFA"}
            </button>
            {msg && <p className="text-xs text-red-400 mt-3">{msg}</p>}
          </div>
        ) : (
          <form onSubmit={verify} className="space-y-6">
            <div>
              <p className="text-sm text-[#A89F95] mb-4">1. Scan this QR code with your authenticator app (e.g. Google Authenticator, Authy).</p>
              {/* Note: since backend returns SVG text, we render it directly */}
              <div className="bg-white p-4 inline-block rounded-xl mb-4" dangerouslySetInnerHTML={{__html: qrCode}}></div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[#6B6560] uppercase tracking-wider">2. Enter 6-digit code</label>
              <input type="text" required value={code} onChange={e => setCode(e.target.value)} maxLength={6} pattern="\d{6}" className="w-full max-w-xs rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#F5F0EB] focus:border-[#D97757] focus:outline-none transition-colors tracking-widest text-center text-lg" placeholder="000000" />
            </div>
            {msg && <p className="text-xs text-red-400">{msg}</p>}
            <button type="submit" disabled={loading || code.length < 6} className="rounded-xl bg-[#D97757] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#C9623F] disabled:opacity-50 transition-colors">
              {loading ? <Spinner size={14} /> : "Verify and Enable"}
            </button>
          </form>
        )}
      </motion.div>
    </motion.div>
  );
}
