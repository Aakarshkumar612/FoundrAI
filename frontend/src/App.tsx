import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/shared/components/Layout";
import { ProtectedRoute } from "@/shared/components/ProtectedRoute";
import { LandingPage } from "@/features/landing";
import { LoginPage, RegisterPage } from "@/features/auth";
import { DashboardPage } from "@/features/dashboard";
import { UploadPage } from "@/features/upload";
import { QueryPage } from "@/features/query";
import { SimulatePage } from "@/features/simulate";
import { ChartsPage } from "@/features/charts";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/upload"    element={<UploadPage />} />
          <Route path="/query"     element={<QueryPage />} />
          <Route path="/simulate"  element={<SimulatePage />} />
          <Route path="/charts"    element={<ChartsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
