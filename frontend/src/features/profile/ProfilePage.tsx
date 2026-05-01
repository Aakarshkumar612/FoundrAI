import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import { UserCircle, Building2, Mail, Save, CheckCircle2, ShieldAlert, ArrowRight } from "lucide-react";

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
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    api.get<Profile>("/founders/profile")
      .then(p => { setProfile(p); setFullName(p.full_name || ""); setCompanyName(p.company_name || ""); })
      .finally(() => setLoading(false));
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setSuccessMsg(""); setErrorMsg("");
    try {
      const p = await api.patch<Profile>("/founders/profile", { full_name: fullName, company_name: companyName });
      setProfile(p);
      setSuccessMsg("Profile identity synchronized successfully.");
    } catch (err: any) { setErrorMsg(err.message || "Synchronization failed."); }
    finally { setSaving(false); }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-12 animate-fade-up">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#6366f1]">
            <UserCircle size={20} />
          </div>
          <h1 className="text-3xl font-bold text-white">Founder <span className="gradient-text">Profile</span></h1>
        </div>
        <p className="text-[#94a3b8]">Manage your personal and company metadata for the advisory engine</p>
      </div>

      <div className="grid md:grid-cols-5 gap-8">
        <div className="md:col-span-3">
          {loading ? <div className="flex justify-center py-20"><Spinner size={32} /></div> : (
            <form onSubmit={save} className="glass-card p-10 space-y-8 relative overflow-hidden">
               <div className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563] ml-1">Email (Immutable)</label>
                    <div className="relative group opacity-50">
                      <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-[#4b5563]" size={18} />
                      <input type="text" disabled value={profile?.email || ""} 
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white" 
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563] ml-1">Full Identity</label>
                    <div className="relative">
                      <UserCircle className="absolute left-4 top-1/2 -translate-y-1/2 text-[#4b5563]" size={18} />
                      <input 
                        type="text" value={fullName} onChange={e => setFullName(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white focus:border-[#6366f1] focus:outline-none transition-colors"
                        placeholder="Jane Doe"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563] ml-1">Company Entity</label>
                    <div className="relative">
                      <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 text-[#4b5563]" size={18} />
                      <input 
                        type="text" value={companyName} onChange={e => setCompanyName(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white focus:border-[#6366f1] focus:outline-none transition-colors"
                        placeholder="Acme Corp"
                      />
                    </div>
                  </div>
               </div>

               <div className="flex flex-col gap-4">
                  <button 
                    type="submit" disabled={saving}
                    className="w-full py-4 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold text-white hover:scale-[1.02] transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#6366f1]/20 disabled:opacity-50"
                  >
                    {saving ? <Spinner size={20} /> : <>Update Profile <Save size={18} /></>}
                  </button>

                  {successMsg && (
                    <div className="flex items-center gap-3 p-4 rounded-xl bg-[#3ECF8E]/10 border border-[#3ECF8E]/20 text-[#3ECF8E] text-xs font-bold">
                      <CheckCircle2 size={16} /> {successMsg}
                    </div>
                  )}

                  {errorMsg && (
                    <div className="flex items-center gap-3 p-4 rounded-xl bg-red-400/10 border border-red-400/20 text-red-400 text-xs">
                      <ShieldAlert size={16} /> {errorMsg}
                    </div>
                  )}
               </div>
            </form>
          )}
        </div>

        <div className="md:col-span-2 space-y-6">
           <div className="glass-card p-8 bg-gradient-to-br from-[#6366f1]/10 to-transparent border-[#6366f1]/20">
              <h3 className="text-sm font-bold text-white uppercase tracking-widest mb-4">Account Status</h3>
              <div className="flex items-center justify-between py-3 border-b border-white/5">
                <span className="text-xs text-[#94a3b8]">Plan</span>
                <span className="text-xs font-bold text-[#6366f1]">Founder Prototype</span>
              </div>
              <div className="flex items-center justify-between py-3 border-b border-white/5">
                <span className="text-xs text-[#94a3b8]">Security</span>
                <span className="text-xs font-bold text-[#3ECF8E]">Active</span>
              </div>
              <div className="flex items-center justify-between py-3">
                <span className="text-xs text-[#94a3b8]">Region</span>
                <span className="text-xs font-bold text-white uppercase">US-East</span>
              </div>
           </div>

           <div className="p-6">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-[#4b5563] mb-4">Security Actions</h4>
              <Link to="/mfa" className="flex items-center justify-between group">
                <span className="text-xs font-bold text-[#94a3b8] group-hover:text-white transition-colors">Enable Multi-Factor Auth</span>
                <ArrowRight size={14} className="text-[#4b5563] group-hover:text-[#6366f1] transition-all" />
              </Link>
           </div>
        </div>
      </div>
    </div>
  );
}
