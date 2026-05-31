import { Link } from "react-router-dom";
import { useAuth } from "../modules/auth/AuthContext";

const modules = [
  { name: "CO-PO Attainment", status: "Active", path: "/copo", link: true },
  { name: "Publications", status: "Active", path: "/publications/faculty", link: true },
  { name: "BTP / IP", status: "Active", path: "/projects", link: true },
  { name: "Analytics", status: "Planned", path: "#" },
  { name: "Reports", status: "Planned", path: "#" },
  { name: "Reminders", status: "Planned", path: "#" },
  { name: "LLM Workflows", status: "Planned", path: "#" },
];

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-xl font-semibold">Welcome, {user?.full_name}</h2>
        <p className="text-slate-600 mt-1">
          Role: <span className="font-medium capitalize">{user?.role}</span> — departmental
          automation hub (CO-PO is the first integrated module).
        </p>
      </section>
      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
          Modules
        </h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {modules.map((m) => {
            const inner = (
              <>
                <p className="font-medium">{m.name}</p>
                <p
                  className={`text-xs mt-1 ${
                    m.status === "Active" ? "text-teal-700" : "text-amber-700"
                  }`}
                >
                  {m.status}
                </p>
              </>
            );
            return "link" in m && m.link ? (
              <Link
                key={m.name}
                to={m.path}
                className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm hover:border-teal-400 hover:shadow transition-colors block"
              >
                {inner}
              </Link>
            ) : (
              <div
                key={m.name}
                className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm opacity-80"
              >
                {inner}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
