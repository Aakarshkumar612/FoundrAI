import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";

const fadeUp = { hidden:{opacity:0,y:16}, visible:{opacity:1,y:0,transition:{duration:0.4,ease:[0.22,1,0.36,1]}} };

interface Profile {
  id: string;
  email: string;
  full_name: string;
  company_name: string;
}

export function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.get<Profile>("/founders/profile")
      .then(p => { setProfile(p); setFullName(p.full_name || ""); setCompanyName(p.company_name || ""); })
      .finally(() => setLoading(false));
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setMsg("");
    try {
      const p = await api.patch<Profile>("/founders/profile", { full_name: fullName, company_name: companyName });
      setProfile(p); setMsg("Profile updated successfully");
    } catch (err: any) { setMsg(err.message); }
    finally { setSaving(false); }
  }

  return (
    <motion.div className="p-8 max-w-2xl" initial="hidden" animate="visible" variants={{ visible:{transition:{staggerChildren:0.08}} }}>
      <motion.div variants={fadeUp} className="mb-8">
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Founder Profile</h1>
        <p className="mt-1 text-sm text-[#6B6560]">Manage your personal and company details.</p>
      </motion.div>

      {loading ? <Spinner size={24} /> : (
        <motion.form variants={fadeUp} onSubmit={save} className="space-y-4 rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-8">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[#6B6560] uppercase tracking-wider">Email</label>
            <input type="text" disabled value={profile?.email || ""} className="w-full rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#A89F95] opacity-50" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[#6B6560] uppercase tracking-wider">Full Name</label>
            <input type="text" value={fullName} onChange={e => setFullName(e.target.value)} className="w-full rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#F5F0EB] focus:border-[#D97757] focus:outline-none transition-colors" placeholder="e.g. Jane Doe" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[#6B6560] uppercase tracking-wider">Company Name</label>
            <input type="text" value={companyName} onChange={e => setCompanyName(e.target.value)} className="w-full rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#F5F0EB] focus:border-[#D97757] focus:outline-none transition-colors" placeholder="e.g. Acme Corp" />
          </div>
          {msg && <p className={msg.includes("success") ? "text-xs text-[#4CAF84]" : "text-xs text-[#D97757]"}>{msg}</p>}
          <button type="submit" disabled={saving} className="rounded-xl bg-[#D97757] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#C9623F] disabled:opacity-50 transition-colors mt-4">
            {saving ? <Spinner size={14} /> : "Save Changes"}
          </button>
        </motion.form>
      )}
    </motion.div>
  );
}
