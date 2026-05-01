import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { supabase } from "@/shared/auth/supabase";
import { 
  LayoutDashboard, 
  UploadCloud, 
  MessageSquare, 
  TrendingUp, 
  PieChart, 
  Newspaper, 
  History, 
  Files, 
  UserCircle, 
  ShieldCheck,
  LogOut,
  ChevronRight
} from "lucide-react";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/upload",    label: "Upload",    icon: UploadCloud },
  { to: "/query",     label: "Ask AI",    icon: MessageSquare },
  { to: "/simulate",  label: "Simulate",  icon: TrendingUp },
  { to: "/charts",    label: "Charts",    icon: PieChart },
  { to: "/news",      label: "News Feed", icon: Newspaper },
  { to: "/history",   label: "History",   icon: History },
  { to: "/documents", label: "Documents", icon: Files },
  { to: "/profile",   label: "Profile",   icon: UserCircle },
  { to: "/mfa",       label: "Security",  icon: ShieldCheck },
];

export function Layout() {
  const navigate = useNavigate();
  const logout = async () => { await supabase.auth.signOut(); navigate("/"); };

  return (
    <div className="flex h-screen bg-[#0a0a0f] text-white overflow-hidden selection:bg-[#6366f1]/30">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 flex flex-col border-r border-white/5 bg-[#0d0d1a]/50 backdrop-blur-2xl">
        <div className="px-6 py-8 border-b border-white/5 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#6366f1] to-[#a855f7] flex items-center justify-center font-bold text-sm">F</div>
          <div>
            <span className="text-lg font-bold tracking-tight text-white block leading-none">FoundrAI</span>
            <span className="text-[10px] text-[#94a3b8] uppercase tracking-[0.2em] mt-1 block">Autonomous AI</span>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-6 space-y-1 custom-scrollbar">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) =>
                `flex items-center justify-between group rounded-xl px-4 py-3 text-sm transition-all duration-300 ${
                  isActive
                    ? "bg-gradient-to-r from-[#6366f1]/20 to-transparent text-[#8b5cf6] border border-white/5"
                    : "text-[#94a3b8] hover:bg-white/5 hover:text-white"
                }`
              }>
              <div className="flex items-center gap-3">
                <Icon size={18} className="transition-transform group-hover:scale-110" />
                <span className="font-medium">{label}</span>
              </div>
              <ChevronRight size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-white/5">
          <button onClick={logout}
            className="w-full flex items-center gap-3 rounded-xl px-4 py-3 text-sm text-[#94a3b8] hover:bg-red-500/10 hover:text-red-400 transition-all group"
          >
            <LogOut size={18} className="group-hover:translate-x-1 transition-transform" />
            <span className="font-semibold">Sign out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto bg-[#0a0a0f] relative">
        {/* Universal Background Glow */}
        <div className="fixed top-[-10%] right-[-10%] w-[600px] h-[600px] bg-[#6366f1]/5 rounded-full blur-[140px] pointer-events-none -z-10" />
        
        <div className="p-10 min-h-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
