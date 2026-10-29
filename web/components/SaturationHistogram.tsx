"use client";
import useSWR from "swr";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { fetcher, BlockGroup } from "@/lib/api";

export function SaturationHistogram() {
  const { data } = useSWR<BlockGroup[]>("/blockgroups?limit=5000", fetcher);
  if (!data) return <div className="card">Loading…</div>;

  const bins: { bin: string; count: number; sat: number }[] = [];
  const edges = Array.from({ length: 20 }, (_, i) => i * 0.15);
  edges.forEach((e, i) => {
    const next = edges[i + 1] ?? e + 0.15;
    const label = `${e.toFixed(1)}`;
    const count = data.filter(
      (d) => (d.saturation_index ?? 0) >= e && (d.saturation_index ?? 0) < next
    ).length;
    bins.push({ bin: label, count, sat: e });
  });

  return (
    <div className="card">
      <div className="flex items-baseline justify-between">
        <h3 className="text-lg font-semibold">Saturation distribution</h3>
        <span className="text-muted text-xs">Red bars = oversaturated (&gt;1.0)</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={bins}>
          <XAxis dataKey="bin" tick={{ fill: "#8b90a3", fontSize: 11 }} />
          <YAxis tick={{ fill: "#8b90a3", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#13151c", border: "1px solid #232634", borderRadius: 8 }}
            labelStyle={{ color: "#e8eaf0" }}
          />
          <Bar dataKey="count">
            {bins.map((b, i) => (
              <Cell key={i} fill={b.sat >= 1.1 ? "#ef4444" : b.sat >= 0.6 ? "#f59e0b" : "#4ade80"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
