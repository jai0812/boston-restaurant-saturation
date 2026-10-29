export function MetricCard({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: string | number;
  sub?: string;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  const toneClass = {
    default: "text-text",
    good: "text-good",
    warn: "text-warn",
    bad: "text-bad",
  }[tone];
  return (
    <div className="card">
      <div className="text-muted text-xs uppercase tracking-wider">{label}</div>
      <div className={`metric mt-2 text-3xl font-bold ${toneClass}`}>{value}</div>
      {sub && <div className="text-muted text-xs mt-1">{sub}</div>}
    </div>
  );
}
