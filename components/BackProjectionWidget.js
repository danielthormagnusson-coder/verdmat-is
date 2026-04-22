"use client";

import { useEffect, useRef, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { supabase } from "@/lib/supabase";
import { formatMillions, formatSegment } from "@/lib/format";

// Spec §4.6 — property back-projection. Minimal inline autocomplete + chart.

function formatPct(pct) {
  if (pct == null || Number.isNaN(pct)) return "—";
  const sign = pct > 0 ? "+" : pct < 0 ? "−" : "";
  return `${sign}${Math.abs(pct).toFixed(1).replace(".", ",")} %`;
}
function formatMonthLabel(m) {
  const months = ["jan","feb","mar","apr","maí","jún","júl","ágú","sep","okt","nóv","des"];
  if (!m) return "";
  const [, mm] = m.split("-");
  return months[Number(mm) - 1];
}

function SearchBox({ onSelect }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const timer = useRef(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (!q || q.trim().length < 2) {
      setResults([]);
      return;
    }
    timer.current = setTimeout(async () => {
      setLoading(true);
      const term = q.trim();
      let query = supabase
        .from("properties")
        .select("fastnum, heimilisfang, postnr, postheiti, canonical_code, einflm")
        .eq("is_residential", true)
        .limit(8);
      if (/^\d+$/.test(term)) {
        query = supabase
          .from("properties")
          .select("fastnum, heimilisfang, postnr, postheiti, canonical_code, einflm")
          .eq("fastnum", Number(term))
          .limit(1);
      } else {
        query = query.ilike("heimilisfang", `%${term}%`);
      }
      const { data } = await query;
      setResults(data || []);
      setLoading(false);
    }, 250);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [q]);

  return (
    <div style={{ position: "relative" }}>
      <input
        type="text"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Heimilisfang eða fastanúmer"
        className="vm-input"
        aria-label="Finna eign"
        style={{ fontSize: "0.95rem", padding: "0.7rem 1rem" }}
      />
      {results.length > 0 && (
        <ul
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            zIndex: 8,
            listStyle: "none",
            padding: 0,
            margin: 0,
            background: "var(--vm-surface-elevated)",
            border: "1px solid var(--vm-border-strong)",
            borderRadius: 6,
            boxShadow: "0 4px 16px rgba(19,36,59,0.08)",
            maxHeight: 260,
            overflowY: "auto",
          }}
        >
          {results.map((r) => (
            <li key={r.fastnum}>
              <button
                type="button"
                onClick={() => {
                  onSelect(r);
                  setResults([]);
                  setQ("");
                }}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: "0.55rem 0.85rem",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  borderBottom: "1px solid var(--vm-border)",
                  fontSize: "0.9rem",
                  color: "var(--vm-ink)",
                }}
              >
                <div style={{ fontWeight: 500 }}>{r.heimilisfang}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--vm-ink-muted)" }}>
                  {r.postnr} {r.postheiti} · {formatSegment(r.canonical_code)}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
      {loading && (
        <span
          style={{
            position: "absolute",
            top: "50%",
            right: 12,
            transform: "translateY(-50%)",
            fontSize: "0.75rem",
            color: "var(--vm-ink-faint)",
          }}
        >
          leita...
        </span>
      )}
    </div>
  );
}

export default function BackProjectionWidget() {
  const [selected, setSelected] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    fetch(`/api/backproj/${selected.fastnum}`)
      .then((r) => r.json().then((j) => ({ ok: r.ok, body: j })))
      .then(({ ok, body }) => {
        if (cancelled) return;
        if (!ok) setError(body.error || "Mistókst að sækja gögn");
        else setData(body);
      })
      .catch(() => !cancelled && setError("Nettenging brást"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selected]);

  return (
    <section style={{ marginBottom: "2.5rem" }}>
      <h2 className="display" style={{ fontSize: "1.25rem", marginBottom: "0.35rem" }}>
        Back-projection á eign
      </h2>
      <p style={{ fontSize: "0.85rem", color: "var(--vm-ink-muted)", marginBottom: "1rem" }}>
        Sláðu inn heimilisfang til að sjá áætlaða verðþróun síðustu 12 mánuði.
      </p>

      <SearchBox onSelect={setSelected} />

      {selected && (
        <div
          className="vm-card"
          style={{ marginTop: "1rem", padding: "1.25rem 1.5rem" }}
        >
          <p style={{ margin: 0, fontSize: "0.95rem", fontWeight: 500 }}>
            {selected.heimilisfang}, {selected.postnr} {selected.postheiti} —{" "}
            {formatSegment(selected.canonical_code)}
          </p>

          {loading && (
            <p style={{ color: "var(--vm-ink-muted)", marginTop: "0.5rem" }}>
              Reikna...
            </p>
          )}
          {error && (
            <p style={{ color: "var(--vm-danger)", marginTop: "0.5rem" }}>{error}</p>
          )}

          {data && data.summary && data.monthly_values?.length > 0 && (
            <>
              <p
                style={{
                  fontSize: "0.85rem",
                  color: "var(--vm-ink-muted)",
                  margin: "0.6rem 0",
                }}
              >
                Núverandi iter4 mat:{" "}
                <strong className="tabular" style={{ color: "var(--vm-ink)" }}>
                  {data.prediction && data.prediction.real_pred_mean != null
                    ? formatMillions(Number(data.prediction.real_pred_mean) * 1000)
                    : "—"}
                </strong>
              </p>
              <div style={{ width: "100%", height: 180 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={data.monthly_values.map((m) => ({
                      ...m,
                      value: m.value != null ? Number(m.value) : null,
                    }))}
                    margin={{ top: 4, right: 8, bottom: 18, left: 0 }}
                  >
                    <XAxis
                      dataKey="month"
                      tickFormatter={formatMonthLabel}
                      tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
                      axisLine={{ stroke: "var(--vm-border)" }}
                      tickLine={false}
                    />
                    <YAxis
                      tickFormatter={(v) => formatMillions(v * 1000, 0)}
                      tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
                      axisLine={{ stroke: "var(--vm-border)" }}
                      tickLine={false}
                      width={70}
                      domain={["auto", "auto"]}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--vm-surface-elevated)",
                        border: "1px solid var(--vm-border-strong)",
                        borderRadius: 6,
                        fontSize: "0.8rem",
                      }}
                      formatter={(v) => [formatMillions(Number(v) * 1000), "Áætlað mat"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="var(--vm-primary)"
                      strokeWidth={2}
                      dot
                      connectNulls={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <dl
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                  gap: "0.75rem",
                  margin: "0.75rem 0 0",
                  fontSize: "0.85rem",
                }}
              >
                <div>
                  <dt style={{ color: "var(--vm-ink-muted)" }}>Hæst</dt>
                  <dd className="tabular" style={{ margin: 0 }}>
                    {formatMillions(Number(data.summary.hi) * 1000)}
                  </dd>
                </div>
                <div>
                  <dt style={{ color: "var(--vm-ink-muted)" }}>Lægst</dt>
                  <dd className="tabular" style={{ margin: 0 }}>
                    {formatMillions(Number(data.summary.lo) * 1000)}
                  </dd>
                </div>
                <div>
                  <dt style={{ color: "var(--vm-ink-muted)" }}>Breyting</dt>
                  <dd
                    className="tabular"
                    style={{
                      margin: 0,
                      color:
                        data.summary.pct > 0
                          ? "var(--vm-success)"
                          : data.summary.pct < 0
                          ? "var(--vm-danger)"
                          : "var(--vm-ink)",
                    }}
                  >
                    {formatPct(data.summary.pct)}
                  </dd>
                </div>
              </dl>
            </>
          )}

          {data && data.message && !data.monthly_values?.length && (
            <p style={{ color: "var(--vm-ink-muted)", marginTop: "0.5rem" }}>
              {data.message}
            </p>
          )}

          <p
            style={{
              fontSize: "0.75rem",
              color: "var(--vm-ink-faint)",
              marginTop: "0.75rem",
              lineHeight: 1.45,
            }}
          >
            ⚠ Áætlun byggir á raunverðs vísitölu per segment × svæði. Ekki
            nákvæm spá á sölu — einstök eign getur vikið frá markaðsmeðaltali.
          </p>
        </div>
      )}
    </section>
  );
}
