import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/shared/components/Layout";
import { ProtectedRoute } from "@/shared/components/ProtectedRoute";
import { LandingPage } from "@/features/landing/LandingPage";
import { LoginPage, RegisterPage } from "@/features/auth";
import { MfaPage } from "@/features/auth/MfaPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { UploadPage } from "@/features/upload/UploadPage";
import { QueryPage } from "@/features/query/QueryPage";
import { SimulatePage } from "@/features/simulate/SimulatePage";
import { ChartsPage } from "@/features/charts/ChartsPage";
import { ProfilePage } from "@/features/profile/ProfilePage";
import { DocumentsPage } from "@/features/documents/DocumentsPage";
import { NewsPage } from "@/features/news/NewsPage";
import { HistoryPage } from "@/features/history/HistoryPage";

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
          <Route path="/profile"   element={<ProfilePage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/news"      element={<NewsPage />} />
          <Route path="/history"   element={<HistoryPage />} />
          <Route path="/mfa"       element={<MfaPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
