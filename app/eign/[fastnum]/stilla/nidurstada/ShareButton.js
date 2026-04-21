"use client";

import { useState } from "react";

export default function ShareButton({ packed }) {
  const [copied, setCopied] = useState(false);

  async function onClick() {
    if (typeof window === "undefined") return;
    const url = `${window.location.origin}${window.location.pathname}?a=${encodeURIComponent(packed)}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback: select+prompt
      prompt("Afritaðu tengilinn:", url);
    }
  }

  return (
    <button className="vm-btn-secondary" onClick={onClick}>
      {copied ? "Afritað!" : "Deila"}
    </button>
  );
}
