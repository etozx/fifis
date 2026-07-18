import { Link } from "react-router-dom";

const STATUS_STYLES = {
  active: "bg-brand-50 text-brand-700",
  completed: "bg-emerald-50 text-emerald-700",
  paused: "bg-amber-50 text-amber-700",
  archived: "bg-slate-100 text-slate-500",
};

function formatDate(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Compact goal summary linking to its detail page. */
export default function GoalCard({ goal }) {
  return (
    <Link
      to={`/goals/${goal.id}`}
      className="card block transition hover:shadow-md focus-visible:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-slate-800">{goal.title}</h3>
        <span className={`badge ${STATUS_STYLES[goal.status] || ""}`}>
          {goal.status}
        </span>
      </div>
      {goal.description && (
        <p className="mt-1 line-clamp-2 text-sm text-ink-muted">
          {goal.description}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-ink-soft">
        <span className="badge bg-slate-100 text-slate-600">{goal.category}</span>
        {goal.target_date && <span>Due {formatDate(goal.target_date)}</span>}
        {goal.tags?.map((tag) => (
          <span key={tag} className="badge bg-brand-50 text-brand-600">
            #{tag}
          </span>
        ))}
      </div>
    </Link>
  );
}
