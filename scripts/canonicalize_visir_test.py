"""Unit tests for canonicalize_visir (§2.1.1 visir rule). stdlib unittest, NO pytest.

    python -m unittest scripts.canonicalize_visir_test -v

T1-T8 use synthetic inline HTML. T9-T10 load a real probe sample if present and
self.skipTest gracefully otherwise (so the suite passes on a clean checkout).
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canonicalize_visir as cz  # noqa: E402

REAL_SAMPLE = Path(r"D:\verdmat-is\scraper_data\probe_visir_samples\property_REAL_sale_993646.html")

# Shared identical "listing content" used to prove ad-only diffs collapse to one hash.
LISTING_BODY = (
    '<div class="listing">'
    '<h1>Lautarmói 1, 603 Akureyri</h1>'
    '<span class="price">99.900.000 kr.</span>'
    '<span class="area">120 m²</span>'
    '<p class="lysing">Falleg íbúð á rólegum stað með bílskúr og svölum til suðurs.</p>'
    '<span class="fastnum">fasteignanúmer: 1021848</span>'
    '</div>'
)


def page(listing: str, ad: str) -> bytes:
    return ("<html><body>%s%s</body></html>" % (listing, ad)).encode("utf-8")


class TestCanonicalizeVisir(unittest.TestCase):

    # T1 — ad anchor with a NON-matching parent: href normalized, element kept.
    def test_t1_strip_ad_redirect_href_only(self):
        html = b'<html><body><div class="content"><a href="/ads/redirect/4632">x</a></div></body></html>'
        out = cz.canonicalize_visir_html(html).decode("utf-8")
        self.assertIn("/ads/redirect/__ID__", out)
        self.assertNotIn("/ads/redirect/4632", out)
        self.assertIn(">x<", out)              # anchor text kept (not decomposed)

    # T2 — ad anchor under a matching parent class: whole parent decomposed.
    def test_t2_drop_ad_block_by_class(self):
        html = (b'<html><body><div class="Reklama__img">'
                b'<a href="/ads/redirect/4632"><img src="/banner/abc.jpg"></a>'
                b'</div><p>keep</p></body></html>')
        out = cz.canonicalize_visir_html(html).decode("utf-8")
        self.assertNotIn("ads/redirect", out)  # entire block gone
        self.assertNotIn("banner/abc.jpg", out)
        self.assertIn(">keep<", out)

    # T3 — each of the four target classes drops; partial + hyphen-insensitive match.
    def test_t3_drop_for_each_target_class(self):
        for cls in ("Reklama__img", "ad-banner-mobile", "details-ad-block",
                    "b-partnerlink-something"):
            html = ('<html><body><div class="%s">'
                    '<a href="/ads/redirect/1"><img src="/x.jpg"></a></div>'
                    '<p>kept</p></body></html>' % cls).encode("utf-8")
            out = cz.canonicalize_visir_html(html).decode("utf-8")
            self.assertNotIn("ads/redirect", out, "class %r should have dropped the block" % cls)
            self.assertNotIn("x.jpg", out, "class %r" % cls)
            self.assertIn(">kept<", out, "class %r" % cls)

    # T4 — same listing, different ad redirect ids AND img srcs -> SAME hash.
    def test_t4_same_listing_different_ads_same_hash(self):
        a = page(LISTING_BODY, '<div class="ad-banner-mobile">'
                 '<a href="/ads/redirect/3306"><img src="/b/111.jpg"></a></div>')
        b = page(LISTING_BODY, '<div class="ad-banner-mobile">'
                 '<a href="/ads/redirect/4940"><img src="/b/222.jpg"></a></div>')
        self.assertNotEqual(a, b)                                   # raw bytes differ
        self.assertEqual(cz.content_hash_visir(a), cz.content_hash_visir(b))

    # T5 — different listing content (price) -> DIFFERENT hash.
    def test_t5_different_listing_different_hash(self):
        a = page(LISTING_BODY, "")
        b = page(LISTING_BODY.replace("99.900.000", "143.900.000"), "")
        self.assertNotEqual(cz.content_hash_visir(a), cz.content_hash_visir(b))

    # T6 — idempotent.
    def test_t6_idempotent(self):
        html = page(LISTING_BODY, '<div class="Reklama__img">'
                    '<a href="/ads/redirect/55"><img src="/q.jpg"></a></div>'
                    '<div class="content"><a href="/ads/redirect/77">leftover</a></div>')
        once = cz.canonicalize_visir_html(html)
        twice = cz.canonicalize_visir_html(once)
        self.assertEqual(once, twice)

    # T7 — non-HTML content_type bypasses untouched.
    def test_t7_non_html_bypass(self):
        body = b'{"ads":"/ads/redirect/4632","price":99}'
        out = cz.canonicalize_visir_html(body, content_type="application/json")
        self.assertEqual(out, body)                                # byte-for-byte unchanged

    # T8 — empty input.
    def test_t8_empty_input(self):
        self.assertEqual(cz.canonicalize_visir_html(b""), b"")
        self.assertEqual(len(cz.content_hash_visir(b"")), 64)      # still a valid digest

    # T9 — real sample: mutating one /ads/redirect/N leaves the hash unchanged.
    def test_t9_real_sample_stability(self):
        if not REAL_SAMPLE.is_file():
            self.skipTest("real sample not present: %s" % REAL_SAMPLE)
        raw = REAL_SAMPLE.read_bytes()
        h_a = cz.content_hash_visir(raw)
        mutated = raw.replace(b"/ads/redirect/", b"/ads/redirect/9", 1)  # perturb first id
        self.assertNotEqual(mutated, raw)
        h_b = cz.content_hash_visir(mutated)
        self.assertEqual(h_a, h_b, "ad-redirect mutation must not change the content hash")

    # T10 — real sample: listing content survives canonicalization.
    def test_t10_real_sample_content_preservation(self):
        if not REAL_SAMPLE.is_file():
            self.skipTest("real sample not present: %s" % REAL_SAMPLE)
        out = cz.canonicalize_visir_html(REAL_SAMPLE.read_bytes()).decode("utf-8", "replace")
        low = out.lower()
        self.assertIn("kr", low)
        self.assertIn("fasteignan", low)          # 'fasteignanúmer' label preserved
        self.assertGreater(len(out), 50_000)      # body not gutted (sample was ~120 KB)


if __name__ == "__main__":
    unittest.main(verbosity=2)
