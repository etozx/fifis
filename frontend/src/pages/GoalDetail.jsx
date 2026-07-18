import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { ErrorState, Loading } from "../components/StateViews.jsx";

const GOAL_STATUSES = ["active", "paused", "completed", "archived"];
const NEXT_TASK_STATUS = { todo: "in_progress", in_progress: "done", done: "todo" };
const TASK_STATUS_STYLES = {
  todo: "bg-slate-100 text-slate-600",
  in_progress: "bg-amber-50 text-amber-700",
  done: "bg-emerald-50 text-emerald-700",
};

export default function GoalDetail() {
  const { goalId } = useParams();
  const navigate = useNavigate();
  const [goal, setGoal] = useState(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [newTask, setNewTask] = useState("");

  const load = useCallback(() => {
    setStatus("loading");
    api
      .get(`/goals/${goalId}`)
      .then((data) => {
        setGoal(data);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err.message);
        setStatus("error");
      });
  }, [goalId]);

  useEffect(load, [load]);

  async function addTask(e) {
    e.preventDefault();
    if (!newTask.trim()) return;
    await api.post(`/goals/${goalId}/tasks`, { title: newTask.trim() });
    setNewTask("");
    load();
  }

  async function cycleTask(task) {
    await api.patch(`/goals/${goalId}/tasks/${task.id}`, {
      status: NEXT_TASK_STATUS[task.status],
    });
    load();
  }

  async function deleteTask(taskId) {
    await api.del(`/goals/${goalId}/tasks/${taskId}`);
    load();
  }

  async function changeGoalStatus(newStatus) {
    await api.patch(`/goals/${goalId}`, { status: newStatus });
    load();
  }

  async function deleteGoal() {
    if (!confirm("Delete this goal and all its tasks?")) return;
    await api.del(`/goals/${goalId}`);
    navigate("/goals");
  }

  if (status === "loading") return <Loading />;
  if (status === "error") return <ErrorState message={error} onRetry={load} />;

  const doneCount = goal.tasks.filter((t) => t.status === "done").length;
  const progress = goal.tasks.length
    ? Math.round((doneCount / goal.tasks.length) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <Link to="/goals" className="text-sm text-brand-600 hover:underline">
        ← Back to goals
      </Link>

      <div className="card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">{goal.title}</h1>
            {goal.description && (
              <p className="mt-1 text-sm text-ink-muted">{goal.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <select
              className="input w-auto"
              value={goal.status}
              onChange={(e) => changeGoalStatus(e.target.value)}
              aria-label="Goal status"
            >
              {GOAL_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <button
              className="btn-ghost text-red-600 hover:bg-red-50"
              onClick={deleteGoal}
            >
              Delete
            </button>
          </div>
        </div>

        <div className="mt-4">
          <div className="mb-1 flex justify-between text-xs text-ink-muted">
            <span>
              {doneCount}/{goal.tasks.length} milestones
            </span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="mb-4 font-semibold text-slate-700">Milestones</h2>
        <form onSubmit={addTask} className="mb-4 flex gap-2">
          <input
            className="input"
            placeholder="Add a milestone…"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
          />
          <button className="btn-primary shrink-0">Add</button>
        </form>

        {goal.tasks.length === 0 ? (
          <p className="py-6 text-center text-sm text-ink-muted">
            No milestones yet — break this goal into concrete steps.
          </p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {goal.tasks.map((task) => (
              <li key={task.id} className="flex items-center gap-3 py-2.5">
                <button
                  onClick={() => cycleTask(task)}
                  className={`badge ${TASK_STATUS_STYLES[task.status]}`}
                  title="Click to advance status"
                >
                  {task.status.replace("_", " ")}
                </button>
                <span
                  className={`flex-1 text-sm ${
                    task.status === "done"
                      ? "text-ink-soft line-through"
                      : "text-slate-700"
                  }`}
                >
                  {task.title}
                </span>
                <button
                  onClick={() => deleteTask(task.id)}
                  className="text-xs text-ink-soft hover:text-red-600"
                  aria-label={`Delete ${task.title}`}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
