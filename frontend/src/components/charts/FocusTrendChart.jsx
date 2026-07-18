import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const fmtDay = (iso) =>
  new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });

/** Focus minutes per day, as a filled trend line. */
export default function FocusTrendChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <defs>
          <linearGradient id="focusFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
        <XAxis
          dataKey="date"
          tickFormatter={fmtDay}
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          minTickGap={24}
        />
        <YAxis tick={{ fontSize: 12, fill: "#94a3b8" }} width={40} />
        <Tooltip
          labelFormatter={fmtDay}
          formatter={(v) => [`${v} min`, "Focus"]}
          contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }}
        />
        <Area
          type="monotone"
          dataKey="minutes"
          stroke="#6366f1"
          strokeWidth={2}
          fill="url(#focusFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
