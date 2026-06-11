import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import { useAuth } from "./modules/auth/AuthContext";
import CopoBulkPage from "./modules/copo/CopoBulkPage";
import CopoComparePage from "./modules/copo/CopoComparePage";
import CopoEvaluatePage from "./modules/copo/CopoEvaluatePage";
import CopoResultsPage from "./modules/copo/CopoResultsPage";
import FacultyDirectoryPage from "./modules/publications/pages/FacultyDirectoryPage";
import FacultyAffiliationsPage from "./modules/publications/pages/FacultyAffiliationsPage";
import FacultyProfilePage from "./modules/publications/pages/FacultyProfilePage";
import ModuleHubPage from "./pages/ModuleHubPage";
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

function AdminOnly({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== "admin") return <Navigate to="/dashboard" replace />;
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
        <Route
          path="/modules/copo"
          element={
            <ModuleHubPage
              title="CO-PO Attainment"
              description="Generate attainment reports, compare evaluations, and run bulk processing."
              links={[
                { label: "CO-PO Generator", path: "/copo", description: "End-of-semester consolidated marks evaluation" },
                { label: "Compare Evaluation", path: "/copo/compare", description: "Compare two evaluation runs" },
                { label: "Bulk Evaluation", path: "/copo/bulk", description: "Process multiple courses at once" },
              ]}
            />
          }
        />
        <Route
          path="/modules/publications"
          element={
            <ModuleHubPage
              title="Publications"
              description="Browse faculty profiles, search publications, and export data."
              links={[
                { label: "Faculty Directory", path: "/publications/faculty", description: "View all faculty members" },
                { label: "Publications Search", path: "/publications/search", description: "Search across publications" },
                { label: "Publication Exports", path: "/publications/exports", description: "Export CSV, Excel, or PDF" },
              ]}
            />
          }
        />
        <Route
          path="/modules/analytics"
          element={
            <ModuleHubPage
              title="Analytics"
              description="Departmental analytics for awards and CO-PO attainment trends."
              links={[
                { label: "Faculty Awards", path: "/awards", description: "Awards and recognitions" },
                { label: "Analytics", path: "/analytics", description: "CO-PO, projects, and publication analytics" },
              ]}
            />
          }
        />
        <Route
          path="/modules/admin"
          element={
            <AdminOnly>
              <ModuleHubPage
                title="Admin"
                description="Administrative tools for publications, users, and archived data."
                links={[
                  { label: "Publications Admin", path: "/publications/admin", description: "Manage faculty and scraping" },
                  { label: "Users", path: "/admin/users", description: "User accounts and roles" },
                  { label: "Data & Archives", path: "/admin/data", description: "Data management and archives" },
                ]}
              />
            </AdminOnly>
          }
        />
        <Route path="/copo" element={<CopoEvaluatePage />} />
        <Route path="/copo/compare" element={<CopoComparePage />} />
        <Route path="/copo/bulk" element={<CopoBulkPage />} />
        <Route path="/copo/results/:publicId" element={<CopoResultsPage />} />
        <Route path="/publications/faculty" element={<FacultyDirectoryPage />} />
        <Route path="/publications/faculty/:facultyId" element={<FacultyProfilePage />} />
        <Route path="/publications/faculty/:facultyId/affiliations" element={<FacultyAffiliationsPage />} />
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
