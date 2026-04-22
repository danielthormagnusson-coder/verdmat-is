import Link from "next/link";
import { supabase } from "@/lib/supabase";
import SearchAutocomplete from "@/components/SearchAutocomplete";
import SearchDataGapBanner from "@/components/SearchDataGapBanner";
import FeaturedProperties from "@/components/FeaturedProperties";
import { formatSegment, formatM2, formatMillions } from "@/lib/format";

export const revalidate = 600;

async function loadFeatured() {
  // Three handpicked canonical codes across three regions for the hero strip.
  const picks = [
    { code: "APT_FLOOR", region: "RVK_core" },
    { code: "SFH_DETACHED", region: "Capital_sub" },
    { code: "ROW_HOUSE", region: "Country" },
  ];
  const results = [];
  for (const p of picks) {
    const { data } = await supabase
      .from("properties")
      .select(
        "fastnum, heimilisfang, postnr, postheiti, canonical_code, einflm, first_photo_url, n_photos"
      )
      .eq("canonical_code", p.code)
      .eq("region_tier", p.region)
      .not("first_photo_url", "is", null)
      .order("n_photos", { ascending: false })
      .limit(1);
    if (data && data.length) {
      const prop = data[0];
      const { data: pred } = await supabase
        .from("predictions")
        .select("real_pred_mean, real_pred_lo80, real_pred_hi80")
        .eq("fastnum", prop.fastnum)
        .maybeSingle();
      results.push({ ...prop, prediction: pred });
    }
  }
  return results;
}

export default async function Home() {
  let featured = [];
  try {
    featured = await loadFeatured();
  } catch {
    // Supabase not configured yet — show empty state.
  }

  return (
    <main>
      <section
        style={{
          padding: "5rem 0 4rem",
          background:
            "linear-gradient(180deg, var(--vm-bg) 0%, rgba(245,240,230,0.4) 100%)",
        }}
      >
        <div className="vm-container-narrow" style={{ textAlign: "left" }}>
          <p
            style={{
              fontSize: "0.85rem",
              color: "var(--vm-accent)",
              fontWeight: 600,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              marginBottom: "1rem",
            }}
          >
            ÍSLENSKT FASTEIGNAVERÐMAT · 2026
          </p>
          <h1
            className="display"
            style={{
              fontSize: "clamp(2.5rem, 5.5vw, 4.2rem)",
              marginBottom: "1.25rem",
              fontWeight: 500,
            }}
          >
            Hvað kostar eignin þín?
          </h1>
          <p
            style={{
              fontSize: "1.15rem",
              color: "var(--vm-ink-muted)",
              marginBottom: "2.5rem",
              maxWidth: 620,
              lineHeight: 1.55,
            }}
          >
            AI-studdur verðmatsvettvangur byggður á 226.000 þinglýstum
            kaupsamningum og LightGBM-módelum kvarðaðum á íslenska markaðnum.
            Fáðu verðmat með raunverulegu vissubili — ekki bara tölu.
          </p>
          <SearchAutocomplete />
          <SearchDataGapBanner />
          <p
            style={{
              marginTop: "1rem",
              fontSize: "0.8rem",
              color: "var(--vm-ink-faint)",
              fontStyle: "italic",
            }}
          >
            iter4 standalone módel — óháður fasteignamati HMS.
          </p>
        </div>
      </section>

      {featured.length > 0 && (
        <section style={{ padding: "2rem 0 3rem" }}>
          <div className="vm-container">
            <h2
              className="display"
              style={{ fontSize: "1.6rem", marginBottom: "1.5rem" }}
            >
              Dæmi um nýleg verðmöt
            </h2>
            <FeaturedProperties items={featured} />
          </div>
        </section>
      )}

      <section style={{ padding: "4rem 0", background: "var(--vm-surface)" }}>
        <div className="vm-container">
          <h2
            className="display"
            style={{
              fontSize: "1.9rem",
              marginBottom: "2.5rem",
              textAlign: "center",
            }}
          >
            Hvað getur verdmat.is?
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "1.75rem",
            }}
          >
            <FeatureCard
              title="Raunsæ spágildi"
              body="Verðmat per eign með 80% og 95% vissubilum — byggt á 124.835 þinglýstum sölum og quantile-módelum kvarðaðum per segment."
            />
            <FeatureCard
              title="Feature attribution"
              body="Sjáðu nákvæmlega hvers vegna verðið er þetta. SHAP-greining sýnir hvaða eiginleikar hækka og lækka matið, mældir í krónum."
            />
            <FeatureCard
              title="Markaðsyfirlit"
              body="Repeat-sale vísitala frá 2006, markaðshiti per segment og hverfi. Skoðaðu raunverulegt verðhrun 2008–2011 á rauntölum."
            />
          </div>
        </div>
      </section>
    </main>
  );
}

function FeatureCard({ title, body }) {
  return (
    <div className="vm-card vm-card-elevated">
      <h3
        className="display"
        style={{ fontSize: "1.2rem", marginBottom: "0.75rem", fontWeight: 600 }}
      >
        {title}
      </h3>
      <p
        style={{
          color: "var(--vm-ink-muted)",
          fontSize: "0.95rem",
          lineHeight: 1.6,
        }}
      >
        {body}
      </p>
    </div>
  );
}
