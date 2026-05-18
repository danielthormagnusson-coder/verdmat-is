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

// Long-form Icelandic date: "15. mars 2024" — full month name.
// Used in A4 skodags freshness signal where the long form reads better
// inline with prose.
export function formatDateLong(s) {
  if (!s) return null;
  try {
    const d = new Date(s);
    return d.toLocaleDateString("is-IS", { year: "numeric", month: "long", day: "numeric" });
  } catch {
    return null;
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

// SHAP / feature-attribution label mapping. Keys are lower-cased so the
// lookup is case-insensitive on the underlying raw column name (training
// data uses uppercase BYGGAR/EINFLM/LOD_FLM, runtime sometimes uses
// lowercase variants). Add iter5 HMS features here once train_iteration5.py
// surfaces them in the attribution rows.
const FEATURE_NAME_MAP = {
  // Identity / valuation anchors
  fastnum: "Fastanúmer",
  fasteignamat: "Fasteignamat",
  real_fasteignamat: "Raunvirði fasteignamats",
  // Property structural attributes
  einflm: "Stærð (m²)",
  lod_flm: "Lóðarstærð (m²)",         // A5: added "(m²)" suffix for consistency
  byggar: "Byggingarár",
  age_at_sale: "Aldur við sölu",
  merking_floor: "Hæð í byggingu",     // A5: new mapping (was raw)
  // Property classification
  canonical_code: "Gerð eignar",
  unit_category: "Notkunarflokkur",    // A5: was "Einingarflokkur"
  is_main_unit: "Aðaleining",
  is_new_build: "Nýbygging",
  // Geo
  matsvaedinumer: "Matsvæði (númer)",  // A5: label kept; value-line suppressed in AttributionWaterfall
  matsvaedi_bucket: "Hverfi",          // A5: simplified from "Hverfi (matsvæði)"
  region_tier: "Svæði (tier)",
  postnr: "Póstnúmer",
  lat: "Breiddargráða",
  lon: "Lengdargráða",
  // Temporal anchors (filtered out of default waterfall but reconciled in footer)
  sale_year: "Söluár",
  sale_month: "Sölumánuður",
  // LLM-extracted signals
  has_extraction_data: "Auglýsingalýsing",
  // Future-proof: iter5 HMS-feature additions (post Phase D Supabase sync).
  // These will start firing when train_iteration5.py includes them in the
  // feature_attributions table; until then, every row null-coalesces and
  // these entries simply sit unused.
  brunabotamat: "Brunabótamat",
  lhlmat: "Lóðarhluti í mati",
  byggingarstig: "Byggingarstig",
  fasteignamat_naesta_ar: "HMS spá næsta árs",
  gerd: "HMS undirflokkur",
  matsstig: "HMS matsstig",
};

// Features whose entire SHAP row is hidden from the top-10 default render —
// internal IDs that carry no narrative value for the user. Filtered in
// AttributionWaterfall before slicing top-10.
export const HIDDEN_SHAP_FEATURES = new Set([
  "landnum",
]);

export function formatFeatureName(name) {
  if (!name) return name;
  const key = String(name).toLowerCase();
  return FEATURE_NAME_MAP[key] || name;
}

// Used by AttributionWaterfall to decide whether to drop a row entirely
// from the top-10 default view. ?mode=debug still shows hidden rows.
export function isHiddenShapFeature(name) {
  if (!name) return false;
  return HIDDEN_SHAP_FEATURES.has(String(name).toLowerCase());
}

export function heatBucketLabel(bucket) {
  if (bucket === "hot") return "HEITT";
  if (bucket === "cold") return "KALT";
  return "HLUTLAUST";
}

// HMS byggingarstig (construction stage) labels. B4 = Fullbúið is intentionally
// omitted from suppressed-render call sites; see A3 badge logic.
const BYGGINGARSTIG_LABELS = {
  B0: "Ekki byrjað",
  B1: "Frumstig",
  B2: "Lokað, óbúið",
  B3: "Klárast",
  B4: "Fullbúið",
};

export function byggingarstigLabel(stage) {
  if (!stage) return null;
  return BYGGINGARSTIG_LABELS[stage] ?? null;
}

// True iff stage is set and not full — A1 spec-card filler + A3 badge use this.
export function isByggingarstigVisible(stage) {
  if (!stage) return false;
  if (stage === "B4") return false;
  return stage in BYGGINGARSTIG_LABELS;
}
