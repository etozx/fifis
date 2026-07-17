/**
 * Reusable loading / empty / error states.
 *
 * UX principle: every data surface must handle all three states explicitly, so
 * the user is never left staring at a blank screen wondering what happened.
 */

export function Loading({ label = "Loading…" }) {
  return (
    <div className="grid place-items-center py-12 text-ink-muted" role="status">
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="card border-red-100 bg-red-50" role="alert">
      <p className="text-sm font-medium text-red-700">
        {message || "Something went wrong."}
      </p>
      {onRetry && (
        <button className="btn-ghost mt-3" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="card grid place-items-center py-12 text-center">
      <h3 className="text-base font-semibold text-slate-700">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-ink-muted">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
