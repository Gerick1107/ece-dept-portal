import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../modules/auth/AuthContext";

const nav = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/copo", label: "CO-PO Generator", exact: true },
  { to: "/copo/compare", label: "Compare Evaluation" },
  { to: "/copo/bulk", label: "Bulk Evaluation" },
  { to: "/publications/faculty", label: "Faculty Directory", exact: true },
  { to: "/publications/search", label: "Publications Search" },
  { to: "/publications/exports", label: "Publication Exports" },
  { to: "/projects", label: "BTP / IP Projects", exact: true },
  { to: "/awards", label: "Faculty Awards", exact: true },
];

function isNavActive(pathname: string, to: string, exact?: boolean): boolean {
  if (exact) {
    return (
      pathname === to ||
      pathname.startsWith(`${to}/results/`) ||
      (to === "/publications/faculty" && pathname.startsWith("/publications/faculty/"))
    );
  }
  return pathname === to || pathname.startsWith(`${to}/`);
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <header className="bg-teal-800 text-white shadow-md">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <img
              src="/logo.png"
              alt="ECE Department"
              className="h-12 w-auto bg-white rounded-md p-1 shrink-0"
            />
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wide text-teal-100">ECE Department</p>
              <h1 className="text-lg font-semibold truncate">CO-PO Automation Portal</h1>
            </div>
          </div>
          <div className="flex items-center gap-3 text-sm shrink-0">
            <span className="hidden sm:inline text-teal-100">
              {user?.full_name} · {user?.role}
            </span>
            <button
              type="button"
              onClick={logout}
              className="rounded-lg bg-teal-700 px-3 py-1.5 hover:bg-teal-600 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
        <nav className="max-w-6xl mx-auto px-4 flex gap-1 pb-2 flex-wrap">
          {nav.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                isNavActive(location.pathname, item.to, item.exact)
                  ? "bg-white text-teal-900 font-medium shadow-sm"
                  : "text-teal-50 hover:bg-teal-700/80"
              }`}
            >
              {item.label}
            </Link>
          ))}
          <Link
            to="/profile"
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              location.pathname === "/profile"
                ? "bg-white text-teal-900 font-medium shadow-sm"
                : "text-teal-50 hover:bg-teal-700/80"
            }`}
          >
            Profile
          </Link>
          {user?.role === "admin" && (
            <>
              <Link
                to="/publications/admin"
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  location.pathname === "/publications/admin"
                    ? "bg-white text-teal-900 font-medium shadow-sm"
                    : "text-teal-50 hover:bg-teal-700/80"
                }`}
              >
                Publications Admin
              </Link>
              <Link
                to="/admin/users"
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  location.pathname === "/admin/users"
                    ? "bg-white text-teal-900 font-medium shadow-sm"
                    : "text-teal-50 hover:bg-teal-700/80"
                }`}
              >
                Users
              </Link>
              <Link
                to="/admin/data"
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  location.pathname === "/admin/data"
                    ? "bg-white text-teal-900 font-medium shadow-sm"
                    : "text-teal-50 hover:bg-teal-700/80"
                }`}
              >
                Data & Archives
              </Link>
            </>
          )}
        </nav>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-3 text-center text-xs text-slate-500">
        ECE Department · Academic use only · Student marks are not retained after cleanup
      </footer>
    </div>
  );
}
