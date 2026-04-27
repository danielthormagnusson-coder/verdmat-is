"use client";

import dynamic from "next/dynamic";

// Thin client-only wrapper. Mirrors the PropertyMapClient.js pattern: Next.js
// 16 forbids `ssr: false` inside server-component dynamic imports, so the
// page imports this client wrapper directly and the wrapper handles the
// dynamic-with-no-SSR call.
const Map = dynamic(() => import("./UnregisteredSpaceMap"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        height: 380,
        background: "var(--vm-surface)",
        borderRadius: 10,
        border: "1px solid var(--vm-border)",
      }}
    />
  ),
});

export default function UnregisteredSpaceMapClient() {
  return <Map />;
}
