"use client";

import { useReducer, useState } from "react";
import { useRouter } from "next/navigation";

const SCREENS = [
  {
    key: "condition",
    label: "Ástand eignar",
    questions: ["condition_overall", "kitchen_renovated", "bathroom_renovated"],
  },
  {
    key: "interior",
    label: "Innréttingar og frágangur",
    questions: ["flooring"],
  },
  {
    key: "location",
    label: "Staðsetning og útsýni",
    questions: ["view", "proximity_school", "proximity_store"],
  },
  {
    key: "outside",
    label: "Útiþættir",
    questions: ["balcony", "garage"],
  },
  {
    key: "building",
    label: "Byggingareiginleikar",
    questions: ["elevator", "floor_position"],
    apt_only: true,
  },
];

const Q = {
  condition_overall: {
    label: "Hvert er heildarástand eignarinnar?",
    help: "Miðað við útlit, ástand innréttinga og viðhald.",
    options: [
      { value: "gott", label: "Gott — vel viðhaldið, lítið sem ekkert þarf að gera" },
      { value: "medal", label: "Meðal — stendst kröfur, einhver slit eðlilegt" },
      { value: "thorfVidgerd", label: "Þarf viðgerða — stærri endurbætur nauðsynlegar" },
    ],
    default: "medal",
  },
  kitchen_renovated: {
    label: "Hefur eldhúsið verið endurnýjað síðustu 5 ár?",
    options: [
      { value: "ja", label: "Já" },
      { value: "nei", label: "Nei" },
      { value: "ovisst", label: "Ekki viss" },
    ],
    default: "ovisst",
  },
  bathroom_renovated: {
    label: "Hefur baðherbergið verið endurnýjað síðustu 5 ár?",
    options: [
      { value: "ja", label: "Já" },
      { value: "nei", label: "Nei" },
      { value: "ovisst", label: "Ekki viss" },
    ],
    default: "ovisst",
  },
  flooring: {
    label: "Hvernig er gólfefni eignarinnar?",
    options: [
      { value: "parket", label: "Parket (einkum)" },
      { value: "flisar", label: "Flísar (einkum)" },
      { value: "teppi", label: "Teppi (einkum)" },
      { value: "blanda", label: "Blanda af mismunandi" },
    ],
    default: "blanda",
  },
  view: {
    label: "Hvernig er útsýnið?",
    options: [
      { value: "sjor", label: "Sjór eða sjóbakki" },
      { value: "fjoll", label: "Fjöll" },
      { value: "borg", label: "Borgarmynd" },
      { value: "gras", label: "Gras eða garður" },
      { value: "takmarkat", label: "Takmarkað (í annað hús, gata)" },
    ],
    default: "gras",
  },
  proximity_school: {
    label: "Er grunnskóli innan 1 km?",
    options: [
      { value: "ja", label: "Já" },
      { value: "nei", label: "Nei" },
      { value: "ovisst", label: "Ekki viss" },
    ],
    default: "ovisst",
  },
  proximity_store: {
    label: "Er matvöruverslun innan 500 m?",
    options: [
      { value: "ja", label: "Já" },
      { value: "nei", label: "Nei" },
      { value: "ovisst", label: "Ekki viss" },
    ],
    default: "ovisst",
  },
  balcony: {
    label: "Svalir eða verönd?",
    options: [
      { value: "engar", label: "Engar svalir" },
      { value: "litlar", label: "Litlar svalir" },
      { value: "storar", label: "Stórar svalir" },
      { value: "verond", label: "Verönd/pallur á jörð" },
    ],
    default: "litlar",
  },
  garage: {
    label: "Bílgeymsla eða bílskúr?",
    options: [
      { value: "enginn", label: "Enginn" },
      { value: "einstaett", label: "Einstætt bilstæði/bílskúr" },
      { value: "tvofalt", label: "Tvöfaldur bílskúr" },
      { value: "sameign", label: "Bílastæði í sameign" },
    ],
    default: "enginn",
  },
  elevator: {
    label: "Er lyfta í húsinu?",
    options: [
      { value: "ja", label: "Já" },
      { value: "nei", label: "Nei" },
      { value: "na", label: "Á ekki við" },
    ],
    default: "nei",
  },
  floor_position: {
    label: "Hvar í byggingunni er íbúðin?",
    options: [
      { value: "kjallari", label: "Kjallari" },
      { value: "jardhed", label: "Jarðhæð" },
      { value: "floor1_3", label: "1. til 3. hæð" },
      { value: "floor4plus", label: "4. hæð eða hærra" },
      { value: "ris", label: "Rishæð" },
    ],
    default: "floor1_3",
  },
};

function reducer(state, action) {
  if (action.type === "set")
    return { ...state, [action.question]: action.value };
  if (action.type === "reset") return {};
  return state;
}

export default function QuestionnaireClient({ fastnum, isApt }) {
  const router = useRouter();
  const [screenIdx, setScreenIdx] = useState(0);
  const [answers, dispatch] = useReducer(reducer, {});
  const [submitting, setSubmitting] = useState(false);

  const applicableScreens = SCREENS.filter(
    (s) => !s.apt_only || isApt
  );
  const screen = applicableScreens[screenIdx];
  const totalScreens = applicableScreens.length;

  const questionsOnScreen = screen.questions.filter(
    (q) => Q[q] != null
  );
  const allAnswered = questionsOnScreen.every(
    (q) => answers[q] != null || Q[q].default != null
  );

  async function onSubmit() {
    setSubmitting(true);
    // Fill in defaults for anything not explicitly answered
    const finalAnswers = {};
    for (const s of applicableScreens) {
      for (const q of s.questions) {
        if (Q[q]) {
          finalAnswers[q] = answers[q] ?? Q[q].default;
        }
      }
    }
    // Pack into short query string: q1=v1,q2=v2...
    const packed = Object.entries(finalAnswers)
      .map(([k, v]) => `${k}:${v}`)
      .join(",");
    router.push(
      `/eign/${fastnum}/stilla/nidurstada?a=${encodeURIComponent(packed)}`
    );
  }

  function next() {
    if (screenIdx < totalScreens - 1) {
      setScreenIdx(screenIdx + 1);
      if (typeof window !== "undefined") window.scrollTo({ top: 0 });
    } else {
      onSubmit();
    }
  }
  function back() {
    if (screenIdx > 0) {
      setScreenIdx(screenIdx - 1);
      if (typeof window !== "undefined") window.scrollTo({ top: 0 });
    }
  }

  return (
    <div>
      {/* Progress */}
      <div
        style={{
          marginBottom: "2rem",
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          fontSize: "0.85rem",
          color: "var(--vm-ink-muted)",
        }}
      >
        <span>
          Skref {screenIdx + 1} af {totalScreens}:{" "}
          <strong style={{ color: "var(--vm-ink)" }}>{screen.label}</strong>
        </span>
        <div
          style={{
            flex: 1,
            height: 4,
            background: "var(--vm-border)",
            borderRadius: 2,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${((screenIdx + 1) / totalScreens) * 100}%`,
              background: "var(--vm-accent)",
              transition: "width 250ms ease",
            }}
          />
        </div>
      </div>

      {/* Questions on this screen */}
      <div style={{ display: "grid", gap: "2rem", marginBottom: "2.5rem" }}>
        {questionsOnScreen.map((qKey) => (
          <Question
            key={qKey}
            qKey={qKey}
            def={Q[qKey]}
            current={answers[qKey] ?? Q[qKey].default}
            onChange={(v) =>
              dispatch({ type: "set", question: qKey, value: v })
            }
          />
        ))}
      </div>

      {/* Nav */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          paddingTop: "1.5rem",
          borderTop: "1px solid var(--vm-border)",
        }}
      >
        <button
          className="vm-btn-secondary"
          onClick={back}
          disabled={screenIdx === 0}
          style={{ opacity: screenIdx === 0 ? 0.4 : 1 }}
        >
          Til baka
        </button>
        <button
          className="vm-btn"
          onClick={next}
          disabled={!allAnswered || submitting}
        >
          {screenIdx === totalScreens - 1
            ? submitting
              ? "Reikna..."
              : "Reikna verðmat"
            : "Áfram"}
        </button>
      </div>
    </div>
  );
}

function Question({ qKey, def, current, onChange }) {
  return (
    <div className="vm-card vm-card-elevated" style={{ padding: "1.5rem 1.75rem" }}>
      <h3
        className="display"
        style={{
          fontSize: "1.25rem",
          marginBottom: def.help ? "0.35rem" : "1rem",
        }}
      >
        {def.label}
      </h3>
      {def.help && (
        <p
          style={{
            fontSize: "0.9rem",
            color: "var(--vm-ink-muted)",
            marginBottom: "1rem",
          }}
        >
          {def.help}
        </p>
      )}
      <div style={{ display: "grid", gap: "0.5rem" }}>
        {def.options.map((opt) => {
          const selected = current === opt.value;
          return (
            <label
              key={opt.value}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.75rem 1rem",
                border: `1px solid ${
                  selected
                    ? "var(--vm-primary)"
                    : "var(--vm-border-strong)"
                }`,
                borderRadius: 8,
                cursor: "pointer",
                background: selected
                  ? "rgba(31, 58, 95, 0.04)"
                  : "transparent",
                transition: "background 120ms, border-color 120ms",
              }}
            >
              <input
                type="radio"
                name={qKey}
                value={opt.value}
                checked={selected}
                onChange={(e) => onChange(e.target.value)}
                style={{ accentColor: "var(--vm-primary)" }}
              />
              <span style={{ fontSize: "0.95rem", color: "var(--vm-ink)" }}>
                {opt.label}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
