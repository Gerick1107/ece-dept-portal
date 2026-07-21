import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../modules/auth/AuthContext";
import { fetchUnreadCount } from "../modules/notifications/services/notificationsApi";

type ModuleCard = {
  name: string;
  path: string;
  status: string;
};

export default function DashboardPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const notificationsPath = isAdmin ? "/admin/notifications" : "/notifications";
  const [unread, setUnread] = useState(0);

  const modules = useMemo<ModuleCard[]>(() => {
    const base: ModuleCard[] = [
      { name: "CO-PO Attainment", path: "/modules/copo", status: "Active" },
      { name: "Publications", path: "/modules/publications", status: "Active" },
      { name: "Projects and Theses", path: "/projects", status: "Active" },
      { name: "Budget", path: "/modules/budget", status: "Active" },
      { name: "Course Allocation", path: "/course-allocation", status: "Active" },
      { name: "Minutes", path: "/modules/minutes", status: "Active" },
      { name: "Analytics", path: "/modules/analytics", status: "Active" },
      { name: "LLM Insights", path: "/llm-insights", status: "Active" },
      {
        name: isAdmin ? "Send Notifications" : "Notifications",
        path: notificationsPath,
        status: "Active",
      },
    ];
    if (isAdmin) {
      base.push({ name: "Admin", path: "/modules/admin", status: "Active" });
    }
    return base;
  }, [isAdmin, notificationsPath]);

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
        {unread > 0 && !isAdmin && (
          <Link
            to={notificationsPath}
            className="inline-flex mt-3 text-sm font-medium text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2 hover:bg-teal-100"
          >
            {unread} unread notification{unread === 1 ? "" : "s"} — view now
          </Link>
        )}
        {isAdmin && (
          <Link
            to={notificationsPath}
            className="inline-flex mt-3 text-sm font-medium text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2 hover:bg-teal-100"
          >
            Send notifications to faculty
          </Link>
        )}
      </section>
      <section>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Modules</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {modules.map((m) => (
            <Link
              key={m.name}
              to={m.path}
              className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm hover:border-teal-400 hover:shadow transition-colors block"
            >
              <p className="font-medium">{m.name}</p>
              <p className="text-xs mt-1 text-teal-700">
                {m.status}
                {m.name === "Notifications" && !isAdmin && unread > 0 && ` · ${unread} unread`}
              </p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
