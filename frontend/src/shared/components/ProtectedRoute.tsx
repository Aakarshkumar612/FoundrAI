import { Navigate, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { supabase } from "@/shared/auth/supabase";
import { Spinner } from "./Spinner";

export function ProtectedRoute() {
  const [loading, setLoading] = useState(true);
  const [authed, setAuthed]   = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => { setAuthed(!!data.session); setLoading(false); });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_, s) => setAuthed(!!s));
    return () => subscription.unsubscribe();
  }, []);

  if (loading) return (
    <div className="flex h-screen items-center justify-center bg-black">
      <Spinner size={32} />
    </div>
  );
  return authed ? <Outlet /> : <Navigate to="/auth/login" replace />;
}
