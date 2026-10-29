"use client";
import { useState } from "react";
import Map, { Source, Layer, MapLayerMouseEvent } from "react-map-gl/maplibre";
import useSWR from "swr";
import { fetcher, BlockGroup } from "@/lib/api";

const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export function SaturationMap({ onPick }: { onPick?: (geoid: string) => void }) {
  const { data } = useSWR<BlockGroup[]>("/blockgroups?limit=5000", fetcher);
  const [hover, setHover] = useState<string | null>(null);

  const geojson = {
    type: "FeatureCollection" as const,
    features: (data ?? []).map((d) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [0, 0] },
      properties: d,
    })),
  };

  return (
    <div className="relative rounded-xl overflow-hidden border border-line" style={{ height: 560 }}>
      <Map
        initialViewState={{ longitude: -71.07, latitude: 42.32, zoom: 11 }}
        mapStyle={MAP_STYLE}
        onClick={(e: MapLayerMouseEvent) => {
          const f = e.features?.[0];
          if (f?.properties?.geoid && onPick) onPick(f.properties.geoid as string);
        }}
        onMouseMove={(e) => setHover(((e.features?.[0]?.properties?.geoid as string) ?? null))}
        interactiveLayerIds={["bg-fill"]}
      >
        <Source id="bg" type="geojson" data={geojson}>
          <Layer
            id="bg-fill"
            type="circle"
            paint={{
              "circle-radius": 6,
              "circle-color": [
                "interpolate", ["linear"],
                ["coalesce", ["get", "saturation_index"], 0],
                0, "#4ade80",
                1, "#f59e0b",
                1.5, "#ef4444",
              ],
              "circle-opacity": 0.8,
              "circle-stroke-color": "#000",
              "circle-stroke-width": 0.5,
            }}
          />
        </Source>
      </Map>
      {hover && (
        <div className="absolute top-3 left-3 bg-card/90 border border-line rounded px-3 py-2 text-xs">
          Block group {hover}
        </div>
      )}
      <div className="absolute bottom-3 right-3 bg-card/90 border border-line rounded px-3 py-2 text-xs space-y-1">
        <div className="font-semibold uppercase tracking-wider text-muted">Saturation</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-good inline-block" /> Underserved</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-warn inline-block" /> Balanced</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-bad inline-block" /> Oversaturated</div>
      </div>
    </div>
  );
}
