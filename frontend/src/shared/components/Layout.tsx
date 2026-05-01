import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { supabase } from "@/shared/auth/supabase";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: "⊞" },
  { to: "/upload",    label: "Upload",    icon: "⬆" },
  { to: "/query",     label: "Ask AI",    icon: "◇" },
  { to: "/simulate",  label: "Simulate",  icon: "∿" },
  { to: "/charts",    label: "Charts",    icon: "▤" },
  { to: "/news",      label: "News Feed", icon: "📰" },
  { to: "/history",   label: "History",   icon: "◷" },
  { to: "/documents", label: "Documents", icon: "📄" },
  { to: "/profile",   label: "Profile",   icon: "👤" },
  { to: "/mfa",       label: "Security",  icon: "🔒" },
];

export function Layout() {
  const navigate = useNavigate();
  const logout = async () => { await supabase.auth.signOut(); navigate("/"); };

  return (
    <div className="flex h-screen bg-black text-[#F5F0EB] overflow-hidden">
      <aside className="w-56 shrink-0 flex flex-col border-r border-[#1e1c1a] bg-[#0d0c0b]/80">
        <div className="px-5 py-5 border-b border-[#1e1c1a]">
          <span className="text-base font-bold tracking-tight text-white">FoundrAI</span>
          <p className="text-[11px] text-[#6B6560] mt-0.5 uppercase tracking-wider">AI Advisor</p>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
          {NAV.map(({ to, label, icon }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition-all ${
                  isActive
                    ? "bg-[#D97757]/15 text-[#D97757] font-medium"
                    : "text-[#6B6560] hover:bg-[#161412] hover:text-[#F5F0EB]"
                }`
              }>
              <span className="text-xs w-4 text-center">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-2 py-3 border-t border-[#1e1c1a]">
          <button onClick={logout}
            className="w-full rounded-xl px-3 py-2 text-sm text-[#6B6560] hover:bg-[#161412] hover:text-[#F5F0EB] text-left transition-all">
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-black">
        <Outlet />
      </main>
    </div>
  );
}
