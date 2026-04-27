"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";

// Fasi E Addendum 1 (2026-04-27): graduated-symbol map — circles at postnr
// centroids, color = pct_unregistered_space_sqm_gt5, size = sqrt(n) so the
// reader sees both the rate and the sample-size confidence in one glance.
//
// Implementation note: tree dep is react-leaflet (Danni's brief said
// "Mapbox base layer" but the existing map dep is Leaflet 1.9 / react-leaflet
// 5.0). Same paint-style capability via CircleMarker; no new package added.
// Polygon choropleth deferred to v1.1 once LMÍ shapefile is fetched (see
// PLANNING_BACKLOG Sprint 3 polygon-upgrade item).

const COLOR_RAMP = [
  // [stop_pct, hex] — sequential light-yellow → terracotta-deep, 0 to 45
  [0,  "#fef9e7"],
  [10, "#fae5a8"],
  [20, "#f1c277"],
  [30, "#e08a4c"],
  [45, "#a64419"],
];

function colorFor(pct) {
  if (pct == null || Number.isNaN(pct)) return "#cccccc";
  const v = Math.max(0, Math.min(45, Number(pct)));
  for (let i = 0; i < COLOR_RAMP.length - 1; i++) {
    const [a, ca] = COLOR_RAMP[i];
    const [b, cb] = COLOR_RAMP[i + 1];
    if (v >= a && v <= b) {
      const t = (v - a) / (b - a);
      return mix(ca, cb, t);
    }
  }
  return COLOR_RAMP[COLOR_RAMP.length - 1][1];
}
function mix(hexA, hexB, t) {
  const a = [parseInt(hexA.slice(1, 3), 16), parseInt(hexA.slice(3, 5), 16), parseInt(hexA.slice(5, 7), 16)];
  const b = [parseInt(hexB.slice(1, 3), 16), parseInt(hexB.slice(3, 5), 16), parseInt(hexB.slice(5, 7), 16)];
  const r = a.map((c, i) => Math.round(c + (b[i] - c) * t));
  return `rgb(${r[0]}, ${r[1]}, ${r[2]})`;
}

function radiusFor(n) {
  // sqrt scale: 50 listings → 8 px, 200 → 14 px, 415 → 20 px
  return 5 + Math.sqrt(Math.max(n, 1)) * 0.7;
}

// Capital-region bbox: tight enough that the map opens looking at Stór-RVK.
const CAPITAL_CENTER = [64.11, -21.85];
const CAPITAL_ZOOM = 11;

function Legend() {
  const stops = [0, 10, 20, 30, 45];
  return (
    <div
      style={{
        background: "var(--vm-surface-elevated)",
        border: "1px solid var(--vm-border-strong)",
        borderRadius: 6,
        padding: "0.5rem 0.75rem",
        fontSize: "0.78rem",
        color: "var(--vm-ink-muted)",
        display: "inline-flex",
        flexDirection: "column",
        gap: "0.35rem",
      }}
    >
      <span style={{ fontWeight: 600, color: "var(--vm-ink)" }}>
        Hlutfall með óskráðu rými &gt; 5 m²
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
        {stops.map((s) => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span
              aria-hidden
              style={{
                display: "inline-block",
                width: 14,
                height: 14,
                borderRadius: "50%",
                background: colorFor(s),
                border: "1px solid rgba(19,36,59,0.15)",
              }}
            />
            <span className="tabular">{s} %</span>
          </div>
        ))}
      </div>
      <span style={{ fontSize: "0.72rem", color: "var(--vm-ink-faint)" }}>
        Stærð hringsins ∝ √n auglýsinga
      </span>
    </div>
  );
}

export default function UnregisteredSpaceMap() {
  const [points, setPoints] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/data/unregistered_space_by_postnr.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then((d) => {
        if (!cancelled) setPoints(d.data || []);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <div
        style={{
          height: 380,
          borderRadius: 10,
          overflow: "hidden",
          border: "1px solid var(--vm-border)",
          position: "relative",
        }}
      >
        <MapContainer
          center={CAPITAL_CENTER}
          zoom={CAPITAL_ZOOM}
          scrollWheelZoom={false}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {points &&
            points.map((p) => (
              <CircleMarker
                key={p.postnr}
                center={[p.lat, p.lng]}
                radius={radiusFor(p.n)}
                pathOptions={{
                  color: "rgba(19,36,59,0.45)",
                  weight: 1,
                  fillColor: colorFor(p.pct),
                  fillOpacity: 0.85,
                }}
              >
                <Tooltip
                  direction="top"
                  offset={[0, -4]}
                  opacity={1}
                  sticky
                >
                  <div style={{ fontSize: "0.85rem", lineHeight: 1.45 }}>
                    <div style={{ fontWeight: 600 }}>
                      {p.postnr} {p.heiti}
                    </div>
                    <div className="tabular">
                      {p.pct.toString().replace(".", ",")} % auglýsinga
                    </div>
                    <div style={{ color: "var(--vm-ink-muted)", fontSize: "0.78rem" }}>
                      n = {p.n.toLocaleString("is-IS")} (kvalifíseraðar: {p.n_qual})
                    </div>
                  </div>
                </Tooltip>
              </CircleMarker>
            ))}
        </MapContainer>
      </div>
      <div style={{ marginTop: "0.6rem" }}>
        <Legend />
      </div>
      {error && (
        <p
          style={{
            fontSize: "0.85rem",
            color: "var(--vm-danger)",
            marginTop: "0.5rem",
          }}
        >
          Mistókst að sækja kortgögn: {error}
        </p>
      )}
    </div>
  );
}
