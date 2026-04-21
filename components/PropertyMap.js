"use client";

import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
// NB: leaflet.css loaded via CDN <link> tag in app/layout.js to avoid postcss
// bundling issues in Next.js 16 / Turbopack.

const icon = L.divIcon({
  html: `<div style="
    width: 28px; height: 28px;
    background: #c87146;
    border: 3px solid #ffffff;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(19, 36, 59, 0.3);
  "></div>`,
  className: "vm-map-marker",
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

export default function PropertyMap({ lat, lng, label }) {
  if (!lat || !lng) return null;
  return (
    <div
      style={{
        height: 360,
        borderRadius: 10,
        overflow: "hidden",
        border: "1px solid var(--vm-border)",
      }}
    >
      <MapContainer
        center={[lat, lng]}
        zoom={15}
        scrollWheelZoom={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={[lat, lng]} icon={icon}>
          <Popup>{label}</Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}
