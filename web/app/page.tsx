/* ============================================================================
                           __        __
                          /  \______/  \         ~  JAI  SHARMA  ~
                          \  (o)  (o)  /
                           \    ~~    /              WEB  DRAGON
                            \___||___/
                             /||  ||\         ~ guards the dashboard ~
                            / ||  || \
                           '  ))  ((  '
                              ~~  ~~
                            Jai  Sharma
============================================================================ */
"use client";
import useSWR from "swr";
import { fetcher, Stats } from "@/lib/api";
import { MetricCard } from "@/components/MetricCard";
import { SaturationMap } from "@/components/SaturationMap";
import { SaturationHistogram } from "@/components/SaturationHistogram";
import { WhatIfPanel } from "@/components/WhatIfPanel";

export default function Home() {
  const { data: stats } = useSWR<Stats>("/stats", fetcher);

  return (
    <main className="max-w-7xl mx-auto px-6 py-10 space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <div className="text-accent text-xs uppercase tracking-[0.3em] font-semibold">
            Boston · Carrying-capacity model
          </div>
          <h1 className="text-4xl font-bold mt-2">Restaurant Saturation</h1>
          <p className="text-muted mt-1 max-w-2xl">
            Per-block-group recommended counts, cuisine fit, and 24-month survival probability —
            backed by Census ACS, LEHD LODES, and Boston food-inspection data.
          </p>
        </div>
      </header>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Block groups" value={stats?.block_groups.toLocaleString() ?? "—"} />
        <MetricCard label="Restaurants" value={stats?.restaurants_total.toLocaleString() ?? "—"} />
        <MetricCard
          label="Oversaturated"
          value={stats?.oversaturated.toLocaleString() ?? "—"}
          tone="bad"
          sub="Saturation > 1.1"
        />
        <MetricCard
          label="Underserved"
          value={stats?.underserved.toLocaleString() ?? "—"}
          tone="good"
          sub="Saturation < 0.5"
        />
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <SaturationMap />
          <SaturationHistogram />
        </div>
        <div className="space-y-6">
          <WhatIfPanel />
        </div>
      </section>

      <footer className="text-muted text-xs text-center pt-6 border-t border-line space-y-1">
        <div>Data: Census ACS 2022 · LEHD LODES · data.boston.gov · OpenStreetMap · Model: LightGBM</div>
        <div className="text-accent font-semibold tracking-wider">~ built by JAI SHARMA ~</div>
      </footer>
    </main>
  );
}
