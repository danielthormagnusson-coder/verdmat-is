"use client";

import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
  Font,
} from "@react-pdf/renderer";

// Google Fonts direct TTF links — cover Icelandic latin-ext (þ æ ð ö á ú)
Font.register({
  family: "Inter",
  fonts: [
    {
      src: "https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7.ttf",
      fontWeight: 400,
    },
    {
      src: "https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa2ZL7.ttf",
      fontWeight: 500,
    },
    {
      src: "https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1pL7.ttf",
      fontWeight: 700,
    },
  ],
});

Font.register({
  family: "Fraunces",
  fonts: [
    {
      src: "https://fonts.gstatic.com/s/fraunces/v39/6NUh8FyLNQOQZAnv9ZwNjucMHVn85Ni7emAe_A.ttf",
      fontWeight: 500,
    },
    {
      src: "https://fonts.gstatic.com/s/fraunces/v39/6NUh8FyLNQOQZAnv9ZwNjucMHVn85Ni7f2Ae_A.ttf",
      fontWeight: 700,
    },
  ],
});

const C = {
  ink: "#13243b",
  inkMuted: "#526375",
  inkFaint: "#8a95a3",
  bg: "#f5f0e6",
  surface: "#fbf7ef",
  accent: "#c87146",
  primary: "#1f3a5f",
  border: "#e3d9c5",
  success: "#5d7f56",
  danger: "#b04e4e",
};

const s = StyleSheet.create({
  page: {
    padding: 44,
    fontFamily: "Inter",
    fontSize: 10,
    color: C.ink,
    backgroundColor: "#ffffff",
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    marginBottom: 18,
    paddingBottom: 12,
    borderBottom: `1px solid ${C.border}`,
  },
  brand: {
    fontFamily: "Fraunces",
    fontSize: 18,
    fontWeight: 500,
    color: C.ink,
  },
  brandAccent: { color: C.accent },
  metaRight: { fontSize: 8, color: C.inkFaint, textAlign: "right" },

  section: { marginBottom: 16 },
  sectionLabel: {
    fontSize: 8,
    fontWeight: 700,
    letterSpacing: 1.5,
    color: C.accent,
    marginBottom: 6,
    textTransform: "uppercase",
  },
  h1: { fontFamily: "Fraunces", fontSize: 20, fontWeight: 500, marginBottom: 2 },
  h2: {
    fontFamily: "Fraunces",
    fontSize: 13,
    fontWeight: 500,
    marginBottom: 6,
    marginTop: 10,
  },
  sub: { fontSize: 10, color: C.inkMuted, marginBottom: 10 },

  summaryRow: {
    flexDirection: "row",
    gap: 14,
    marginTop: 8,
    marginBottom: 8,
  },
  summaryCol: {
    flex: 1,
    padding: 12,
    backgroundColor: C.surface,
    border: `1px solid ${C.border}`,
    borderRadius: 6,
  },
  summaryColAccent: {
    borderTopWidth: 2,
    borderTopColor: C.accent,
  },
  summaryLabel: {
    fontSize: 8,
    color: C.inkMuted,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 4,
  },
  summaryValue: { fontFamily: "Fraunces", fontSize: 20, fontWeight: 500 },
  summaryValueMuted: { color: C.inkMuted },

  deltaBox: {
    padding: 10,
    backgroundColor: C.surface,
    borderRadius: 4,
    marginTop: 6,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  deltaLabel: { fontSize: 10, color: C.inkMuted },
  deltaValuePositive: { fontSize: 10, color: C.success, fontWeight: 700 },
  deltaValueNegative: { fontSize: 10, color: C.danger, fontWeight: 700 },

  propertyTable: { flexDirection: "column", gap: 4 },
  propertyRow: {
    flexDirection: "row",
    paddingVertical: 3,
  },
  propertyLabel: { width: 120, fontSize: 9, color: C.inkMuted },
  propertyValue: { flex: 1, fontSize: 10 },

  qaRow: {
    flexDirection: "row",
    paddingVertical: 5,
    borderBottom: `0.5px solid ${C.border}`,
  },
  qaLabel: { flex: 2, fontSize: 9, color: C.ink },
  qaValue: { flex: 1, fontSize: 9, color: C.inkMuted },
  qaImpact: {
    flex: 0.8,
    fontSize: 9,
    textAlign: "right",
    fontWeight: 500,
  },
  qaImpactPositive: { color: C.success },
  qaImpactNegative: { color: C.danger },
  qaImpactZero: { color: C.inkFaint },

  piTable: {
    marginTop: 6,
    flexDirection: "column",
  },
  piRow: {
    flexDirection: "row",
    paddingVertical: 4,
    borderBottom: `0.5px solid ${C.border}`,
  },
  piCell: { flex: 1, fontSize: 9 },
  piHeader: { color: C.inkMuted, textTransform: "uppercase", fontSize: 7, letterSpacing: 1 },

  disclaimer: {
    marginTop: 18,
    padding: 10,
    backgroundColor: C.surface,
    borderRadius: 4,
    fontSize: 8,
    color: C.inkMuted,
    lineHeight: 1.5,
  },
  footer: {
    position: "absolute",
    bottom: 24,
    left: 44,
    right: 44,
    flexDirection: "row",
    justifyContent: "space-between",
    fontSize: 7,
    color: C.inkFaint,
    paddingTop: 8,
    borderTop: `0.5px solid ${C.border}`,
  },
});

function formatKr(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const m = Math.round(n / 100000) / 10;
  return `${m.toFixed(1).replace(".", ",")} M kr`;
}
function formatKrFull(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return Math.round(n).toLocaleString("is-IS").replace(/,/g, ".") + " kr";
}

const SEGMENT_LABELS = {
  APT_FLOOR: "Íbúð á hæð",
  APT_STANDARD: "Íbúð",
  APT_BASEMENT: "Kjallaraíbúð",
  APT_ATTIC: "Rishæð",
  SFH_DETACHED: "Einbýli",
  SEMI_DETACHED: "Parhús",
  ROW_HOUSE: "Raðhús",
  APT_HOTEL: "Hótelíbúð",
  APT_SENIOR: "Öryggisíbúð",
  APT_MIXED: "Íbúð/vinnustofa",
  APT_ROOM: "Íbúðarherbergi",
  APT_UNAPPROVED: "Ósamþykkt íbúð",
  SUMMERHOUSE: "Sumarhús",
};

export default function PDFReport({
  property,
  baseline,
  adjusted,
  breakdown,
  answerLabels,
  model,
}) {
  const delta = adjusted.mean - baseline.mean;
  const deltaPct = (delta / baseline.mean) * 100;
  const now = new Date();
  const dateStr = now.toLocaleDateString("is-IS", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const addressLine = `${property.heimilisfang || `Fastnum ${property.fastnum}`}, ${property.postnr || ""} ${property.postheiti || ""}`.trim();

  return (
    <Document>
      <Page size="A4" style={s.page}>
        {/* Header */}
        <View style={s.headerRow}>
          <View>
            <Text style={s.brand}>
              verdmat<Text style={s.brandAccent}>.is</Text>
            </Text>
            <Text style={{ fontSize: 9, color: C.inkMuted, marginTop: 3 }}>
              Persónulegt verðmat
            </Text>
          </View>
          <View style={s.metaRight}>
            <Text>Útgefið: {dateStr}</Text>
            <Text>Fastanúmer: {property.fastnum}</Text>
            <Text>Model: {model?.version || "iter4"}</Text>
          </View>
        </View>

        {/* Address */}
        <View style={s.section}>
          <Text style={s.h1}>{addressLine}</Text>
          <Text style={s.sub}>
            {SEGMENT_LABELS[property.canonical_code] || property.canonical_code}
            {property.einflm ? ` · ${Number(property.einflm).toLocaleString("is-IS", { maximumFractionDigits: 1 })} m²` : ""}
            {property.byggar ? ` · byggt ${Math.round(property.byggar)}` : ""}
            {property.fjherb ? ` · ${Math.round(property.fjherb)} herb.` : ""}
          </Text>
        </View>

        {/* Summary */}
        <View style={s.section}>
          <Text style={s.sectionLabel}>VERÐMAT</Text>
          <View style={s.summaryRow}>
            <View style={s.summaryCol}>
              <Text style={s.summaryLabel}>Grunnverðmat</Text>
              <Text style={[s.summaryValue, s.summaryValueMuted]}>
                {formatKr(baseline.mean)}
              </Text>
            </View>
            <View style={[s.summaryCol, s.summaryColAccent]}>
              <Text style={[s.summaryLabel, { color: C.accent }]}>Persónulegt</Text>
              <Text style={s.summaryValue}>{formatKr(adjusted.mean)}</Text>
            </View>
          </View>
          <View style={s.deltaBox}>
            <Text style={s.deltaLabel}>Breyting miðað við grunn</Text>
            <Text style={delta >= 0 ? s.deltaValuePositive : s.deltaValueNegative}>
              {delta >= 0 ? "+" : ""}
              {formatKr(delta)} ({delta >= 0 ? "+" : ""}
              {deltaPct.toFixed(1).replace(".", ",")}%)
            </Text>
          </View>
        </View>

        {/* PI Table */}
        <View style={s.section}>
          <Text style={s.sectionLabel}>LÍKLEGASTA BIL</Text>
          <View style={s.piTable}>
            <View style={s.piRow}>
              <Text style={[s.piCell, s.piHeader]}>Vissubil</Text>
              <Text style={[s.piCell, s.piHeader]}>Neðri mörk</Text>
              <Text style={[s.piCell, s.piHeader]}>Efri mörk</Text>
            </View>
            <View style={s.piRow}>
              <Text style={s.piCell}>80%</Text>
              <Text style={s.piCell}>{formatKr(adjusted.lo80)}</Text>
              <Text style={s.piCell}>{formatKr(adjusted.hi80)}</Text>
            </View>
            <View style={s.piRow}>
              <Text style={s.piCell}>95%</Text>
              <Text style={s.piCell}>{formatKr(adjusted.lo95)}</Text>
              <Text style={s.piCell}>{formatKr(adjusted.hi95)}</Text>
            </View>
          </View>
        </View>

        {/* Breakdown */}
        {breakdown && breakdown.length > 0 && (
          <View style={s.section}>
            <Text style={s.sectionLabel}>SUNDURLIÐUN</Text>
            <Text style={s.sub}>
              Áhrif svara á grunnverðmatið, raðað eftir stærð.
            </Text>
            {breakdown.map((b, i) => {
              const imp = b.impact_isk;
              const impStyle =
                imp > 0
                  ? s.qaImpactPositive
                  : imp < 0
                  ? s.qaImpactNegative
                  : s.qaImpactZero;
              return (
                <View key={i} style={s.qaRow}>
                  <Text style={s.qaLabel}>{b.label}</Text>
                  <Text style={s.qaValue}>
                    {answerLabels[b.question]?.[b.value] || b.value}
                  </Text>
                  <Text style={[s.qaImpact, impStyle]}>
                    {imp >= 0 ? "+" : ""}
                    {formatKr(imp)}
                  </Text>
                </View>
              );
            })}
          </View>
        )}

        {/* Market context placeholder */}
        <View style={s.section} wrap={false}>
          <Text style={s.sectionLabel}>MARKAÐSSAMHENGI</Text>
          <Text style={s.sub}>
            Verðþróun í {property.postheiti || property.canonical_code}{" "}
            — ítarlegt markaðsyfirlit og repeat-sale vísitala í boði á
            verdmat.is/markadur.
          </Text>
        </View>

        {/* Disclaimer */}
        <View style={s.disclaimer}>
          <Text style={{ fontWeight: 700, marginBottom: 4 }}>Fyrirvari</Text>
          <Text>
            Þetta er líkansbundið AI-verðmat reiknað úr opinberum þinglýstum
            kaupsamningum (HMS kaupskrá) og fasteignaskrá. Það er ekki staðfest
            verðmat og er ekki bindandi fyrir kaupsamninga, lánveitingar eða
            dómstóla. Persónulega álagið byggir á svörum notanda og hardcoded
            marginal effects (v1.1). Sjá aðferðafræði á verdmat.is/um.
          </Text>
        </View>

        {/* Footer */}
        <View style={s.footer} fixed>
          <Text>verdmat.is</Text>
          <Text>
            Model {model?.version || "iter4"} · {model?.calibration || "iter4_conformal_v1"} · unnið{" "}
            {now.toISOString().slice(0, 10)}
          </Text>
        </View>
      </Page>
    </Document>
  );
}
