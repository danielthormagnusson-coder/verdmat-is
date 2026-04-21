"use client";

import { useState } from "react";
import { createSupabaseBrowser } from "@/lib/supabase-browser";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("idle");
  const [msg, setMsg] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    if (!email || !email.includes("@")) return;
    setStatus("sending");
    setMsg("");
    const supabase = createSupabaseBrowser();
    const origin =
      typeof window !== "undefined" ? window.location.origin : "";
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim().toLowerCase(),
      options: {
        emailRedirectTo: `${origin}/auth/callback`,
        shouldCreateUser: false,
      },
    });
    if (error) {
      setStatus("error");
      setMsg(
        error.message.includes("not allowed") ||
          error.message.toLowerCase().includes("sign")
          ? "Netfang er ekki í boði. Hafðu samband ef þú heldur þetta sé mistök."
          : `Villa: ${error.message}`
      );
    } else {
      setStatus("sent");
      setMsg(
        'Tengill sendur — opnaðu póstinn þinn og smelltu á „Staðfesta“ til að skrá þig inn.'
      );
    }
  }

  return (
    <main
      className="vm-container-narrow"
      style={{ padding: "4rem 0 6rem", maxWidth: 520 }}
    >
      <p
        style={{
          fontSize: "0.85rem",
          color: "var(--vm-accent)",
          fontWeight: 600,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          marginBottom: "0.75rem",
        }}
      >
        PRO AÐGANGUR
      </p>
      <h1
        className="display"
        style={{ fontSize: "2.5rem", marginBottom: "0.75rem" }}
      >
        Skrá sig inn
      </h1>
      <p
        style={{
          color: "var(--vm-ink-muted)",
          marginBottom: "2rem",
          lineHeight: 1.55,
        }}
      >
        Þessi vettvangur er í boði með boði. Sláðu inn netfang sem þú varst
        boðaður með — þú færð tölvupóst með tengli til að staðfesta innskráningu.
      </p>

      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.85rem" }}>
        <input
          className="vm-input"
          type="email"
          placeholder="netfang@fyrirtaeki.is"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
        />
        <button
          type="submit"
          className="vm-btn"
          disabled={status === "sending" || status === "sent"}
          style={{ opacity: status === "sending" ? 0.7 : 1 }}
        >
          {status === "sending"
            ? "Sendi tengli..."
            : status === "sent"
            ? "Tengill sendur"
            : "Senda tengli"}
        </button>
      </form>

      {msg && (
        <div
          style={{
            marginTop: "1.25rem",
            padding: "0.9rem 1.1rem",
            background:
              status === "error"
                ? "rgba(176, 78, 78, 0.08)"
                : "rgba(93, 127, 86, 0.08)",
            border: `1px solid ${
              status === "error" ? "var(--vm-danger)" : "var(--vm-success)"
            }`,
            borderRadius: 8,
            fontSize: "0.92rem",
            color: status === "error" ? "var(--vm-danger)" : "var(--vm-success)",
            lineHeight: 1.55,
          }}
        >
          {msg}
        </div>
      )}

      <div
        style={{
          marginTop: "3rem",
          paddingTop: "1.5rem",
          borderTop: "1px solid var(--vm-border)",
          fontSize: "0.85rem",
          color: "var(--vm-ink-faint)",
        }}
      >
        Ertu fasteignasali eða bankastarfsmaður sem vill aðgang?{" "}
        <a href="/um#pro" style={{ color: "var(--vm-primary)" }}>
          Lærðu meira um Pro aðgang
        </a>
        .
      </div>
    </main>
  );
}
