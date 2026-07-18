import { useEffect, useState } from "react";
import { api } from "../api/client.js";

/** Daily advice-of-the-day card. Fails quietly (advice is a nicety, not core). */
export default function AdviceWidget() {
  const [advice, setAdvice] = useState(null);

  useEffect(() => {
    api
      .get("/advice/today")
      .then(setAdvice)
      .catch(() => setAdvice(null));
  }, []);

  if (!advice) return null;

  return (
    <div className="card bg-gradient-to-br from-brand-600 to-brand-700 text-white">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-100">
        Today’s nudge
      </p>
      <p className="mt-2 text-lg font-medium leading-snug">{advice.text}</p>
      <p className="mt-3 text-xs text-brand-200">#{advice.category}</p>
    </div>
  );
}
