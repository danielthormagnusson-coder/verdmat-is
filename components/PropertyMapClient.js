"use client";

import dynamic from "next/dynamic";

const PropertyMap = dynamic(() => import("./PropertyMap"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        height: 360,
        background: "var(--vm-surface)",
        borderRadius: 10,
        border: "1px solid var(--vm-border)",
      }}
    />
  ),
});

export default function PropertyMapClient(props) {
  return <PropertyMap {...props} />;
}
