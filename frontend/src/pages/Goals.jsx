import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";
import GoalCard from "../components/GoalCard.jsx";
import { EmptyState, ErrorState, Loading } from "../components/StateViews.jsx";

const CATEGORIES = ["general", "career", "health", "learning", "personal", "finance"];

export default function Goals() {
  const [goals, setGoals] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(() => {
    setStatus("loading");
    api
      .get("/goals")
      .then((data) => {
        setGoals(data);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err.message);
        setStatus("error");
      });
  }, []);

  useEffect(load, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Goals</h1>
          <p className="text-sm text-ink-muted">What are you working toward?</p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Close" : "New goal"}
        </button>
      </div>

      {showForm && (
        <GoalForm
          onCreated={() => {
            setShowForm(false);
            load();
          }}
        />
      )}

      {status === "loading" && <Loading />}
      {status === "error" && <ErrorState message={error} onRetry={load} />}
      {status === "ready" &&
        (goals.length === 0 ? (
          <EmptyState
            title="No goals yet"
            description="Set one meaningful goal and break it into milestones."
            action={
              <button className="btn-primary" onClick={() => setShowForm(true)}>
                Create your first goal
              </button>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {goals.map((goal) => (
              <GoalCard key={goal.id} goal={goal} />
            ))}
          </div>
        ))}
    </div>
  );
}

function GoalForm({ onCreated }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("general");
  const [targetDate, setTargetDate] = useState("");
  const [tags, setTags] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/goals", {
        title,
        description: description || null,
        category,
        target_date: targetDate || null,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card space-y-4">
      <div>
        <label className="label" htmlFor="title">Title</label>
        <input
          id="title"
          className="input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="label" htmlFor="description">Description</label>
        <textarea
          id="description"
          className="input"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div>
          <label className="label" htmlFor="category">Category</label>
          <select
            id="category"
            className="input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="targetDate">Target date</label>
          <input
            id="targetDate"
            type="date"
            className="input"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="tags">Tags</label>
          <input
            id="tags"
            className="input"
            placeholder="comma, separated"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
        </div>
      </div>
      {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
      <div className="flex justify-end">
        <button className="btn-primary" disabled={busy}>
          {busy ? "Saving…" : "Create goal"}
        </button>
      </div>
    </form>
  );
}
