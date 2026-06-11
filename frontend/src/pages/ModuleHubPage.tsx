import { Link } from "react-router-dom";

export type HubLink = {
  label: string;
  path: string;
  description?: string;
};

type Props = {
  title: string;
  description: string;
  links: HubLink[];
};

export default function ModuleHubPage({ title, description, links }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">{title}</h2>
        <p className="text-sm text-slate-600 mt-1">{description}</p>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {links.map((link) => (
          <Link
            key={link.path}
            to={link.path}
            className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:border-teal-400 hover:shadow transition-colors block"
          >
            <p className="font-medium text-slate-900">{link.label}</p>
            {link.description && <p className="text-sm text-slate-600 mt-1">{link.description}</p>}
          </Link>
        ))}
      </div>
    </div>
  );
}
