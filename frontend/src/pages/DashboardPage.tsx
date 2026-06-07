import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../modules/auth/AuthContext";
import { fetchUnreadCount } from "../modules/notifications/services/notificationsApi";

const modules = [
  { name: "CO-PO Attainment", status: "Active", path: "/copo", link: true },
  { name: "Publications", status: "Active", path: "/publications/faculty", link: true },
  { name: "BTP / IP", status: "Active", path: "/projects", link: true },
  { name: "Analytics", status: "Active", path: "/analytics", link: true },
  { name: "Notifications", status: "Active", path: "/notifications", link: true },
  { name: "LLM Workflows", status: "Planned", path: "#", link: false },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    fetchUnreadCount()
      .then((r) => setUnread(r.count))
      .catch(() => setUnread(0));
  }, []);

  return (
    <div className="space-y-6">
      <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-xl font-semibold">Welcome, {user?.full_name}</h2>
        <p className="text-slate-600 mt-1">
          Role: <span className="font-medium capitalize">{user?.role}</span> — departmental automation hub.
        </p>
        {unread > 0 && (
          <Link
            to="/notifications"
            className="inline-flex mt-3 text-sm font-medium text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2 hover:bg-teal-100"
          >
            {unread} unread notification{unread === 1 ? "" : "s"} — view now
          </Link>
        )}
      </section>
      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Modules</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {modules.map((m) => {
            const inner = (
              <>
                <p className="font-medium">{m.name}</p>
                <p className={`text-xs mt-1 ${m.status === "Active" ? "text-teal-700" : "text-amber-700"}`}>
                  {m.status}
                  {m.name === "Notifications" && unread > 0 && ` · ${unread} unread`}
                </p>
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
