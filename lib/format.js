// Icelandic number and currency formatting helpers.

export function formatKr(amount) {
  if (amount == null || Number.isNaN(amount)) return "—";
  const n = Math.round(Number(amount));
  return n.toLocaleString("is-IS").replace(/,/g, ".") + " kr";
}

export function formatMillions(amount, digits = 1) {
  if (amount == null || Number.isNaN(amount)) return "—";
  const m = Number(amount) / 1_000_000;
  return m.toFixed(digits).replace(".", ",") + " M kr";
}

export function formatM2(einflm) {
  if (einflm == null || Number.isNaN(einflm)) return "—";
  return Number(einflm).toLocaleString("is-IS", { maximumFractionDigits: 1 }) + " m²";
}

export function formatPercent(frac, digits = 0) {
  if (frac == null || Number.isNaN(frac)) return "—";
  return (Number(frac) * 100).toFixed(digits) + "%";
}

export function formatDate(s) {
  if (!s) return "—";
  try {
    const d = new Date(s);
    return d.toLocaleDateString("is-IS", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return s;
  }
}

export function formatRelativeDate(s) {
  if (!s) return "—";
  const d = new Date(s);
  const now = new Date();
  const months = (now.getFullYear() - d.getFullYear()) * 12 + (now.getMonth() - d.getMonth());
  if (months < 1) return "í þessum mánuði";
  if (months < 12) return `${months} mán. síðan`;
  const years = Math.floor(months / 12);
  if (years === 1) return "1 ári síðan";
  return `${years} árum síðan`;
}

export function formatSegment(code) {
  const map = {
    APT_FLOOR: "Íbúð á hæð",
    APT_STANDARD: "Íbúð",
    APT_BASEMENT: "Kjallaraíbúð",
    APT_ATTIC: "Rishæð",
    APT_SENIOR: "Öryggisíbúð",
    APT_ROOM: "Íbúðarherbergi",
    APT_HOTEL: "Hótelíbúð",
    APT_MIXED: "Íbúð/vinnustofa",
    APT_UNAPPROVED: "Ósamþykkt íbúð",
    SFH_DETACHED: "Einbýli",
    SEMI_DETACHED: "Parhús",
    ROW_HOUSE: "Raðhús",
    SUMMERHOUSE: "Sumarhús",
    EXCLUDE: "Annað",
  };
  return map[code] || code;
}

export function formatFeatureName(name) {
  const map = {
    FASTNUM: "Fastanúmer",
    FASTEIGNAMAT: "Fasteignamat",
    EINFLM: "Stærð (m²)",
    LOD_FLM: "Lóðarstærð",
    BYGGAR: "Byggingarár",
    real_fasteignamat: "Raunvirði fasteignamats",
    age_at_sale: "Aldur eignar",
    matsvaedi_bucket: "Hverfi (matsvæði)",
    matsvaediNUMER: "Matsvæði (númer)",
    region_tier: "Svæði (tier)",
    canonical_code: "Gerð eignar",
    unit_category: "Einingarflokkur",
    is_main_unit: "Aðaleining",
    is_new_build: "Nýbygging",
    postnr: "Póstnúmer",
    sale_year: "Söluár",
    sale_month: "Sölumánuður",
    lat: "Breiddargráða",
    lon: "Lengdargráða",
    has_extraction_data: "Auglýsingalýsing",
  };
  return map[name] || name;
}

export function heatBucketLabel(bucket) {
  if (bucket === "hot") return "HEITT";
  if (bucket === "cold") return "KALT";
  return "HLUTLAUST";
}
