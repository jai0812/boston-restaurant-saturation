const BASE = typeof window === "undefined" ? "http://127.0.0.1:8000" : "/api";

export async function fetcher<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export async function postWhatIf(body: {
  lat: number;
  lon: number;
  cuisine?: string | null;
  cannibalization_radius_m?: number;
}) {
  const r = await fetch(`${BASE}/whatif`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export type Stats = {
  block_groups: number;
  restaurants_total: number;
  oversaturated: number;
  underserved: number;
};

export type BlockGroup = {
  geoid: string;
  total_pop: number | null;
  median_income: number | null;
  restaurant_count: number;
  recommended_min: number;
  recommended_max: number;
  saturation_index: number | null;
  risk_flag: "balanced" | "oversaturated" | "underserved";
};

export type WhatIfResult = {
  geoid: string;
  survival_probability: number;
  saturation_before: number;
  saturation_after: number;
  cuisine_fit: number;
  cannibalized_restaurants: number;
  verdict: "go" | "risky" | "avoid";
};
