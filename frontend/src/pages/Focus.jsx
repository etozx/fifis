import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api/client.js";
import { Loading } from "../components/StateViews.jsx";

function formatClock(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export default function Focus() {
  const location = useLocation();
  const suggested = location.state || {};

  const [goals, setGoals] = useState([]);
  const [goalId, setGoalId] = useState(suggested.goalId || "");
  const [block, setBlock] = useState(null); // active/paused block
  const [displaySeconds, setDisplaySeconds] = useState(0);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  // Local ticking: base elapsed synced from the server + wall-clock delta.
  const baseRef = useRef(0);
  const syncedAtRef = useRef(0);

  const loadHistory = useCallback(() => {
    api.get("/focus/history").then(setHistory).catch(() => {});
  }, []);

  useEffect(() => {
    Promise.all([api.get("/goals").catch(() => [])]).then(([g]) => {
      setGoals(g);
      setLoading(false);
    });
    loadHistory();
  }, [loadHistory]);

  // Sync the display baseline whenever the block changes.
  function syncFrom(b) {
    setBlock(b);
    baseRef.current = b ? b.elapsed_seconds : 0;
    syncedAtRef.current = Date.now();
    setDisplaySeconds(b ? b.elapsed_seconds : 0);
  }

  // Tick once a second while running.
  useEffect(() => {
    if (!block || block.status !== "active") return;
    const id = setInterval(() => {
      const delta = (Date.now() - syncedAtRef.current) / 1000;
      setDisplaySeconds(baseRef.current + delta);
    }, 1000);
    return () => clearInterval(id);
  }, [block]);

  async function start() {
    const b = await api.post("/focus/start", {
      goal_id: goalId ? Number(goalId) : null,
    });
    syncFrom(b);
  }
  async function pause() {
    syncFrom(await api.post(`/focus/${block.id}/pause`));
  }
  async function resume() {
    syncFrom(await api.post(`/focus/${block.id}/resume`));
  }
  async function complete() {
    await api.post(`/focus/${block.id}/complete`, {});
    setBlock(null);
    setDisplaySeconds(0);
    loadHistory();
  }

  if (loading) return <Loading />;

  const running = block?.status === "active";
  const paused = block?.status === "paused";

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <div className="card flex flex-col items-center py-10">
          <p className="text-sm font-medium text-ink-muted">
            {suggested.minutes
              ? `Suggested block: ${suggested.minutes} min`
              : "Focus session"}
          </p>
          <div
            className="my-6 font-mono text-7xl font-bold tabular-nums text-slate-800"
            aria-live="polite"
          >
            {formatClock(displaySeconds)}
          </div>

          {!block && (
            <div className="w-full max-w-xs space-y-4">
              <div>
                <label className="label" htmlFor="goal">Link to a goal (optional)</label>
                <select
                  id="goal"
                  className="input"
                  value={goalId}
                  onChange={(e) => setGoalId(e.target.value)}
                >
                  <option value="">No goal</option>
                  {goals.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.title}
                    </option>
                  ))}
                </select>
              </div>
              <button className="btn-primary w-full" onClick={start}>
                Start focus block
              </button>
            </div>
          )}

          {block && (
            <div className="flex gap-3">
              {running && (
                <button className="btn-ghost" onClick={pause}>
                  Pause
                </button>
              )}
              {paused && (
                <button className="btn-primary" onClick={resume}>
                  Resume
                </button>
              )}
              <button
                className="btn bg-emerald-600 text-white hover:bg-emerald-700"
                onClick={complete}
              >
                Complete
              </button>
            </div>
          )}
          {paused && (
            <p className="mt-4 text-sm text-amber-600">Paused — time is banked.</p>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="mb-4 font-semibold text-slate-700">Recent sessions</h2>
        {history.length === 0 ? (
          <p className="text-sm text-ink-muted">No sessions yet. Start one!</p>
        ) : (
          <ul className="space-y-3">
            {history.slice(0, 8).map((b) => (
              <li key={b.id} className="flex items-center justify-between text-sm">
                <span className="text-slate-600">
                  {new Date(b.started_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })}
                </span>
                <span className="font-medium text-slate-800">
                  {Math.round(b.accumulated_seconds / 60)} min
                </span>
                <span className="badge bg-slate-100 text-slate-500">{b.status}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
