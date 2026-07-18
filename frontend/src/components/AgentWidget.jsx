import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

/**
 * AI Focus Agent recommendation card. Surfaces the suggested next goal, focus
 * duration, and nudge, with a one-click jump into a focus session.
 */
export default function AgentWidget() {
  const [rec, setRec] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .get("/agent/recommendation")
      .then(setRec)
      .catch(() => setRec(null));
  }, []);

  if (!rec) return null;

  return (
    <div className="card border-brand-100">
      <div className="flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-100 text-brand-700">
          ✦
        </span>
        <p className="text-sm font-semibold text-slate-700">Focus Agent</p>
      </div>
      <p className="mt-3 text-sm text-slate-700">{rec.nudge}</p>
      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-ink-soft">
          Suggested block: {rec.suggested_focus_minutes} min
        </span>
        <button
          className="btn-primary"
          onClick={() =>
            navigate("/focus", {
              state: {
                goalId: rec.suggested_goal_id,
                minutes: rec.suggested_focus_minutes,
              },
            })
          }
        >
          Start focusing
        </button>
      </div>
    </div>
  );
}
