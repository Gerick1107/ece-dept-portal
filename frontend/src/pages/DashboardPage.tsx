import { Link } from "react-router-dom";
import { useAuth } from "../modules/auth/AuthContext";

const modules = [
  { name: "CO-PO Attainment", status: "Active", path: "/copo", link: true, adminOnly: false },
  { name: "Publications", status: "Active", path: "/publications/faculty", link: true, adminOnly: false },
  { name: "BTP / IP", status: "Active", path: "/projects", link: true, adminOnly: false },
  { name: "Analytics", status: "Active", path: "/analytics", link: true, adminOnly: false },
  { name: "Notifications", status: "Active", path: "/admin/notifications", link: true, adminOnly: true },
  { name: "LLM Workflows", status: "Planned", path: "#", link: false, adminOnly: false },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const visibleModules = modules.filter((m) => !m.adminOnly || isAdmin);

  return (
    <div className="space-y-6">
      <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-xl font-semibold">Welcome, {user?.full_name}</h2>
        <p className="text-slate-600 mt-1">
          Role: <span className="font-medium capitalize">{user?.role}</span> — departmental automation hub.
        </p>
      </section>
      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Modules</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {visibleModules.map((m) => {
            const inner = (
              <>
                <p className="font-medium">{m.name}</p>
                <p className={`text-xs mt-1 ${m.status === "Active" ? "text-teal-700" : "text-amber-700"}`}>{m.status}</p>
              </>
            );
            return m.link ? (
              <Link
                key={m.name}
                to={m.path}
                className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm hover:border-teal-400 hover:shadow transition-colors block"
              >
                {inner}
              </Link>
            ) : (
              <div key={m.name} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm opacity-80">
                {inner}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
