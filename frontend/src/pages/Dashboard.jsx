import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";
import StatCard from "../components/StatCard.jsx";
import AdviceWidget from "../components/AdviceWidget.jsx";
import AgentWidget from "../components/AgentWidget.jsx";
import FocusTrendChart from "../components/charts/FocusTrendChart.jsx";
import CategoryChart from "../components/charts/CategoryChart.jsx";
import { EmptyState, ErrorState, Loading } from "../components/StateViews.jsx";
import { useAuth } from "../auth/AuthContext.jsx";

function formatHours(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | error | ready
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setStatus("loading");
    api
      .get("/analytics/summary?range_days=30")
      .then((data) => {
        setSummary(data);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err.message);
        setStatus("error");
      });
  }, []);

  useEffect(load, [load]);

  if (status === "loading") return <Loading label="Gathering your insights…" />;
  if (status === "error") return <ErrorState message={error} onRetry={load} />;

  const hasFocusData = summary.total_focus_minutes > 0;
  const hasCategories = summary.category_distribution.length > 0;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-800">
          Hi {user?.full_name?.split(" ")[0] || "there"} 👋
        </h1>
        <p className="text-sm text-ink-muted">
          Your growth intelligence for the last {summary.range_days} days.
        </p>
      </header>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Focus time"
          value={formatHours(summary.total_focus_minutes)}
          sublabel="last 30 days"
        />
        <StatCard
          label="Current streak"
          value={`${summary.current_streak_days}d`}
          sublabel={`longest ${summary.longest_streak_days}d`}
          accent="emerald"
        />
        <StatCard
          label="Tasks completed"
          value={summary.completed_tasks}
          accent="amber"
        />
        <StatCard label="Active goals" value={summary.active_goals} accent="slate" />
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <AgentWidget />
        <div className="lg:col-span-2">
          <AdviceWidget />
        </div>
      </div>

      <section className="grid gap-6 lg:grid-cols-5">
        <div className="card lg:col-span-3">
          <h2 className="mb-4 font-semibold text-slate-700">Focus over time</h2>
          {hasFocusData ? (
            <FocusTrendChart data={summary.focus_by_day} />
          ) : (
            <EmptyState
              title="No focus sessions yet"
              description="Run your first focus block and this chart will come to life."
            />
          )}
        </div>
        <div className="card lg:col-span-2">
          <h2 className="mb-4 font-semibold text-slate-700">Where your time goes</h2>
          {hasCategories ? (
            <CategoryChart data={summary.category_distribution} />
          ) : (
            <EmptyState
              title="No category data yet"
              description="Attach focus sessions to goals to see your time distribution."
            />
          )}
        </div>
      </section>
    </div>
  );
}
