import { useEffect, useRef, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../modules/auth/AuthContext";

type NavLink = { to: string; label: string; exact?: boolean };

type NavItem =
  | { kind: "link"; to: string; label: string; exact?: boolean }
  | { kind: "group"; label: string; links: NavLink[] };

const navItems: NavItem[] = [
  { kind: "link", to: "/dashboard", label: "Dashboard", exact: true },
  {
    kind: "group",
    label: "CO-PO Attainment",
    links: [
      { to: "/copo", label: "CO-PO Generator", exact: true },
      { to: "/copo/compare", label: "Compare Evaluation" },
      { to: "/copo/bulk", label: "Bulk Evaluation" },
    ],
  },
  {
    kind: "group",
    label: "Publications",
    links: [
      { to: "/publications/faculty", label: "Faculty Directory", exact: true },
      { to: "/publications/search", label: "Publications Search" },
      { to: "/publications/exports", label: "Publication Exports" },
    ],
  },
  { kind: "link", to: "/projects", label: "BTP / IP Projects", exact: true },
  {
    kind: "group",
    label: "Course Allocation",
    links: [
      { to: "/course-allocation", label: "Allocations", exact: true },
      { to: "/course-allocation/catalog", label: "Course Catalog", exact: true },
    ],
  },
  {
    kind: "group",
    label: "Minutes",
    links: [
      { to: "/all-meetings", label: "All Meetings", exact: true },
      { to: "/senate-minutes", label: "Senate Meetings", exact: true },
      { to: "/ece-faculty-meets", label: "ECE Faculty Meetings", exact: true },
      { to: "/aac-meetings", label: "AAC Meetings", exact: true },
      { to: "/ugc-meetings", label: "UGC Meetings", exact: true },
      { to: "/pgc-meetings", label: "PGC Meetings", exact: true },
    ],
  },
  {
    kind: "group",
    label: "Analytics",
    links: [
      { to: "/awards", label: "Faculty Awards", exact: true },
      { to: "/contributions", label: "Faculty Contributions", exact: true },
      { to: "/analytics", label: "Analytics Dashboard", exact: true },
    ],
  },
  { kind: "link", to: "/llm-insights", label: "LLM Insights", exact: true },
  { kind: "link", to: "/notifications", label: "Notifications", exact: true },
];

const adminNavGroup: NavItem = {
  kind: "group",
  label: "Admin",
  links: [
    { to: "/publications/admin", label: "Publications Admin", exact: true },
    { to: "/admin/users", label: "Users", exact: true },
    { to: "/admin/notifications", label: "Send Notifications", exact: true },
    { to: "/admin/requirement-tracker", label: "Requirement Tracker", exact: true },
    { to: "/admin/data", label: "Data & Archives", exact: true },
  ],
};

function isNavActive(pathname: string, to: string, exact?: boolean): boolean {
  if (exact) {
    return (
      pathname === to ||
      pathname.startsWith(`${to}/results/`) ||
      (to === "/publications/faculty" && pathname.startsWith("/publications/faculty/")) ||
      (to === "/course-allocation" && pathname.startsWith("/course-allocation/"))
    );
  }
  return pathname === to || pathname.startsWith(`${to}/`);
}

function isGroupActive(pathname: string, links: NavLink[]): boolean {
  return links.some((link) => isNavActive(pathname, link.to, link.exact));
}

function NavDropdown({ label, links, pathname }: { label: string; links: NavLink[]; pathname: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const active = isGroupActive(pathname, links);

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={`px-3 py-1.5 rounded-lg text-sm transition-colors inline-flex items-center gap-1 ${
          active ? "bg-white text-teal-900 font-medium shadow-sm" : "text-teal-50 hover:bg-teal-700/80"
        }`}
        aria-expanded={open}
        aria-haspopup="true"
      >
        {label}
        <span className="text-xs opacity-80">{open ? "▴" : "▾"}</span>
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[12rem] rounded-lg border border-teal-700/30 bg-white py-1 shadow-lg">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              onClick={() => setOpen(false)}
              className={`block px-3 py-2 text-sm transition-colors ${
                isNavActive(pathname, link.to, link.exact)
                  ? "bg-teal-50 text-teal-900 font-medium"
                  : "text-slate-700 hover:bg-slate-50"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const isAdmin = user?.role === "admin";
  const isFaculty = user?.role === "faculty";

  const visibleNavItems: NavItem[] = navItems.map((item) => {
    if (item.kind !== "group" || item.label !== "Course Allocation" || !isFaculty) {
      return item;
    }
    return {
      ...item,
      links: item.links.filter((link) => link.to !== "/course-allocation/catalog"),
    };
  });

  const items = isAdmin
    ? visibleNavItems
        .filter((item) => !(item.kind === "link" && item.to === "/notifications"))
        .concat(adminNavGroup)
    : visibleNavItems;

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
              <h1 className="text-lg font-semibold truncate">Automation Portal</h1>
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
        <nav className="max-w-6xl mx-auto px-4 flex gap-1 pb-2 flex-wrap items-center">
          {items.map((item) =>
            item.kind === "link" ? (
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
            ) : (
              <NavDropdown
                key={item.label}
                label={item.label}
                links={item.links}
                pathname={location.pathname}
              />
            ),
          )}
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
        </nav>
      </header>
      <main
        className={`flex-1 w-full mx-auto px-4 py-6 ${
          location.pathname.startsWith("/analytics") ? "max-w-7xl" : "max-w-6xl"
        }`}
      >
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-3 text-center text-xs text-slate-500">
        ECE Department · Academic use only · Student marks are not retained after cleanup
      </footer>
    </div>
  );
}
