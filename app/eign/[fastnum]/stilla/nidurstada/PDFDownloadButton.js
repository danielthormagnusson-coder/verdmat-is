"use client";

import { useState } from "react";

export default function PDFDownloadButton({
  property,
  baseline,
  adjusted,
  breakdown,
  answerLabels,
  model,
}) {
  const [loading, setLoading] = useState(false);

  async function onClick() {
    setLoading(true);
    try {
      const [{ pdf }, { default: PDFReport }] = await Promise.all([
        import("@react-pdf/renderer"),
        import("./PDFReport"),
      ]);
      const blob = await pdf(
        <PDFReport
          property={property}
          baseline={baseline}
          adjusted={adjusted}
          breakdown={breakdown}
          answerLabels={answerLabels}
          model={model}
        />
      ).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `verdmat_${property.fastnum}_${new Date()
        .toISOString()
        .slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Gat ekki búið til PDF. Reyndu aftur.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      className="vm-btn-secondary"
      onClick={onClick}
      disabled={loading}
      style={{ opacity: loading ? 0.6 : 1 }}
    >
      {loading ? "Býr til PDF..." : "Sækja PDF"}
    </button>
  );
}
