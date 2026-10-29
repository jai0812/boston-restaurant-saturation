"use client";
import { useState } from "react";
import { postWhatIf, WhatIfResult } from "@/lib/api";

export function WhatIfPanel() {
  const [lat, setLat] = useState(42.32);
  const [lon, setLon] = useState(-71.07);
  const [cuisine, setCuisine] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setErr(null);
    try {
      const r = await postWhatIf({ lat, lon, cuisine: cuisine || null });
      setResult(r);
    } catch (e: any) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  const verdictColor = {
    go: "bg-good/20 text-good border-good/40",
    risky: "bg-warn/20 text-warn border-warn/40",
    avoid: "bg-bad/20 text-bad border-bad/40",
  };

  return (
    <div className="card space-y-4">
      <div>
        <h3 className="text-lg font-semibold">What-if simulator</h3>
        <p className="text-muted text-sm">
          Drop coordinates + cuisine → survival probability, saturation shift, and nearby cannibalization.
        </p>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <label className="text-sm">
          <span className="text-muted">Latitude</span>
          <input
            type="number"
            step="0.0001"
            value={lat}
            onChange={(e) => setLat(parseFloat(e.target.value))}
            className="mt-1 w-full rounded bg-black/30 border border-line px-2 py-1.5"
          />
        </label>
        <label className="text-sm">
          <span className="text-muted">Longitude</span>
          <input
            type="number"
            step="0.0001"
            value={lon}
            onChange={(e) => setLon(parseFloat(e.target.value))}
            className="mt-1 w-full rounded bg-black/30 border border-line px-2 py-1.5"
          />
        </label>
        <label className="text-sm">
          <span className="text-muted">Cuisine</span>
          <input
            value={cuisine}
            onChange={(e) => setCuisine(e.target.value)}
            placeholder="e.g. vietnamese"
            className="mt-1 w-full rounded bg-black/30 border border-line px-2 py-1.5"
          />
        </label>
      </div>
      <button
        onClick={run}
        disabled={loading}
        className="w-full bg-accent hover:bg-accent/90 disabled:opacity-50 text-white font-semibold py-2.5 rounded transition"
      >
        {loading ? "Running…" : "Run simulation"}
      </button>
      {err && <div className="text-bad text-sm">{err}</div>}
      {result && (
        <div className="space-y-3">
          <div className={`rounded-lg border px-4 py-3 text-center text-lg font-bold uppercase tracking-wider ${verdictColor[result.verdict]}`}>
            {result.verdict}
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Stat label="Survival (24 mo)" value={`${(result.survival_probability * 100).toFixed(1)}%`} />
            <Stat label="Cuisine fit" value={result.cuisine_fit.toFixed(2)} />
            <Stat
              label="Saturation"
              value={`${result.saturation_before.toFixed(2)} → ${result.saturation_after.toFixed(2)}`}
            />
            <Stat label="Cannibalized" value={result.cannibalized_restaurants} />
          </div>
          <div className="text-muted text-xs">Nearest block group: {result.geoid}</div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-black/20 border border-line rounded px-3 py-2">
      <div className="text-muted text-xs">{label}</div>
      <div className="metric text-lg font-semibold">{value}</div>
    </div>
  );
}
