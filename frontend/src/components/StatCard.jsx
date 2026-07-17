/**
 * A single headline metric. Big number + label + optional sublabel — the
 * "personal growth intelligence" framing: each stat is an insight, not a log.
 */
export default function StatCard({ label, value, sublabel, accent = "brand" }) {
  const accents = {
    brand: "text-brand-600",
    emerald: "text-emerald-600",
    amber: "text-amber-600",
    slate: "text-slate-700",
  };
  return (
    <div className="card">
      <p className="text-sm font-medium text-ink-muted">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${accents[accent] || accents.brand}`}>
        {value}
      </p>
      {sublabel && <p className="mt-1 text-xs text-ink-soft">{sublabel}</p>}
    </div>
  );
}
