import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import { useAuth } from "./modules/auth/AuthContext";
import CopoBulkPage from "./modules/copo/CopoBulkPage";
import CopoComparePage from "./modules/copo/CopoComparePage";
import CopoEvaluatePage from "./modules/copo/CopoEvaluatePage";
import CopoResultsPage from "./modules/copo/CopoResultsPage";
import FacultyDirectoryPage from "./modules/publications/pages/FacultyDirectoryPage";
import FacultyProfilePage from "./modules/publications/pages/FacultyProfilePage";
import GlobalPublicationsPage from "./modules/publications/pages/GlobalPublicationsPage";
import PublicationExportsPage from "./modules/publications/pages/PublicationExportsPage";
import PublicationsAdminPage from "./modules/publications/pages/PublicationsAdminPage";
import ProjectsPage from "./modules/projects/pages/ProjectsPage";
import AwardsPage from "./modules/awards/pages/AwardsPage";
import AnalyticsPage from "./modules/analytics/pages/AnalyticsPage";
import LlmInsightsPage from "./modules/llm/pages/LlmInsightsPage";
import NotificationsPage from "./modules/notifications/pages/NotificationsPage";
import AdminNotificationsPage from "./modules/notifications/pages/AdminNotificationsPage";
import AdminDataPage from "./pages/AdminDataPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading, mustChangePassword } = useAuth();
  const path = window.location.pathname;
  if (loading) return <p className="p-8 text-center text-slate-500">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (mustChangePassword && path !== "/profile") {
    return <Navigate to="/profile" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <Protected>
            <AppLayout />
          </Protected>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/copo" element={<CopoEvaluatePage />} />
        <Route path="/copo/compare" element={<CopoComparePage />} />
        <Route path="/copo/bulk" element={<CopoBulkPage />} />
        <Route path="/copo/results/:publicId" element={<CopoResultsPage />} />
        <Route path="/publications/faculty" element={<FacultyDirectoryPage />} />
        <Route path="/publications/faculty/:facultyId" element={<FacultyProfilePage />} />
        <Route path="/publications/search" element={<GlobalPublicationsPage />} />
        <Route path="/publications/exports" element={<PublicationExportsPage />} />
        <Route path="/publications/admin" element={<PublicationsAdminPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/awards" element={<AwardsPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/llm-insights" element={<LlmInsightsPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/admin/notifications" element={<AdminNotificationsPage />} />
        <Route path="/admin/users" element={<AdminUsersPage />} />
        <Route path="/admin/data" element={<AdminDataPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
