import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

// A categorical palette that stays distinguishable and legible on white.
const COLORS = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"];

/** Time distribution across goal categories, as a donut. */
export default function CategoryChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="minutes"
          nameKey="category"
          innerRadius={55}
          outerRadius={90}
          paddingAngle={2}
        >
          {data.map((entry, i) => (
            <Cell key={entry.category} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(v, name) => [`${v} min`, name]}
          contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12 }}
          iconType="circle"
          verticalAlign="bottom"
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
