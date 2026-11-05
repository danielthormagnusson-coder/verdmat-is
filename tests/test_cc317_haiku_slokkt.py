"""cc317: Haiku slökkt í næturkeðjunni, verðmat heldur áfram.

Engin DB, ekkert API. Tvö lög:
  A. run_extraction.main() með staðgengli fyrir vélina: hvað kallast með hvaða rofum.
  B. run_extract() úr raunverulegri nightly_delta_chain.sh, með staðgengli fyrir python:
     hvaða rofar eru sendir og hvað fer í næturloggið. EXTRACT_FORWARD er stökkbreytt
     til að sanna að prófið geti fallið og að bakkleiðin í einni línu virki.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "scripts"))
KEDJA = ROT / "scripts" / "nightly_delta_chain.sh"


def _keyra_main(*rofar, lykill_leyfdur=False):
    """Keyrir run_extraction.main() með fölsuðum vélarhluta; skilar lista af köllum."""
    fake_mq = mock.MagicMock()
    if not lykill_leyfdur:
        fake_mq.anthropic_key.side_effect = AssertionError("lykill lesinn þótt Haiku sé slökkt")
    with mock.patch.dict(sys.modules, {"model_quality_eval": fake_mq}):
        sys.modules.pop("run_extraction", None)
        fake_engine = mock.MagicMock()
        fake_engine.PER_CALL_USD_EST = 0.0225
        fake_engine.fetch_extracted_listings_to_value.return_value = [{"r": 1}]
        fake_engine.fetch_listings_needing_extraction.return_value = []
        fake_engine.extract_and_store.return_value = {
            "cost_usd": 0, "cost_measured_usd": 0, "calls_measured": 0, "calls_estimated": 0}
        with mock.patch.dict(sys.modules, {"extraction_engine": fake_engine, "anthropic": mock.MagicMock()}):
            import run_extraction as R
            with mock.patch.object(R, "_connect", return_value=(mock.MagicMock(), mock.MagicMock())), \
                 mock.patch.object(R, "_load_today_spend", return_value=0.0), \
                 mock.patch.object(R, "_record_spend"), \
                 mock.patch.object(sys, "argv", ["run_extraction", *rofar]):
                assert R.main() == 0
    return fake_engine


def test_a1_value_seeded_verdmetur_an_haiku():
    e = _keyra_main("--value-seeded", "--confirm", "--value-limit", "2000")
    e.fetch_listings_needing_extraction.assert_not_called()
    e.extract_and_store.assert_not_called()
    e.fetch_extracted_listings_to_value.assert_called_once()
    assert e.fetch_extracted_listings_to_value.call_args.kwargs["limit"] == 2000
    e.value_listings.assert_called_once()


def test_a2_gildran_forward_0_sleppir_verdmati():
    """Ástæða þess að keðjan sendir ekki --forward 0. Falli þetta má endurskoða athugasemdina."""
    e = _keyra_main("--forward", "0", "--confirm", "--value-limit", "2000")
    e.extract_and_store.assert_not_called()
    e.value_listings.assert_not_called()


def test_a3_samanburdur_forward_kallar_a_haiku():
    e = _keyra_main("--forward", "200", "--daily-cap-usd", "2.00", "--confirm", "--value-limit", "2000",
                    lykill_leyfdur=True)
    e.extract_and_store.assert_called_once()
    e.value_listings.assert_called_once()


def _keyra_run_extract(forward=None, value_limit=None):
    """Sker run_extract() og say() úr keðjunni og keyrir með python-staðgengli."""
    texti = KEDJA.read_bytes().decode("utf-8").replace("\r\n", "\n")
    fall = re.search(r"^run_extract\(\) \{.*?^\}\n", texti, re.S | re.M).group(0)
    gildi_f = re.search(r"^EXTRACT_FORWARD=(\d+)", texti, re.M).group(1) if forward is None else forward
    gildi_v = re.search(r"^EXTRACT_VALUE_LIMIT=(\d+)", texti, re.M).group(1) if value_limit is None else value_limit
    with tempfile.TemporaryDirectory() as t:
        t_posix = subprocess.run(["bash", "-c", f"cygpath -u '{t}'"], capture_output=True, text=True).stdout.strip()
        (Path(t) / "python").write_text('#!/bin/bash\necho "$@" > "$RAK"\necho "\'failed\': 0"\nexit 0\n', newline="\n")
        skrift = f"""
export PATH="{t_posix}:$PATH"; export RAK="{t_posix}/rak.txt"; chmod +x "{t_posix}/python"
EXTRACT_FORWARD={gildi_f}; EXTRACT_VALUE_LIMIT={gildi_v}; EXTRACT_DAILY_CAP_USD=2.00
DRY=0; TS=t; MODELOGS="{t_posix}"; APP="{t_posix}"; REPORT="{t_posix}/night.log"
say() {{ echo "$*" >> "$REPORT"; }}
{fall}
run_extract; echo "rc=$?"
"""
        (Path(t) / "s.sh").write_text(skrift, encoding="utf-8", newline="\n")
        r = subprocess.run(["bash", f"{t_posix}/s.sh"], capture_output=True, text=True, encoding="utf-8")
        assert "rc=0" in r.stdout, r.stdout + r.stderr
        return (Path(t) / "rak.txt").read_text().strip(), (Path(t) / "night.log").read_text(encoding="utf-8")


def test_b1_kedjan_eins_og_hun_er_a_greininni():
    rak, nott = _keyra_run_extract()
    assert "--value-seeded" in rak and "--forward" not in rak and "--daily-cap-usd" not in rak
    assert "--value-limit 2000" in rak
    assert "HAIKU SLÖKKT" in nott
    assert "sia1-k2" not in nott


def test_b2_bakkleid_ein_lina_endurheimtir_gamla_kallid():
    rak, nott = _keyra_run_extract(forward="200")
    assert "--forward 200 --daily-cap-usd 2.00 --confirm --value-limit 2000" in rak
    assert "--value-seeded" not in rak
    assert "HAIKU SLÖKKT" not in nott
    assert "sia1-k2" in nott


def test_b3_verdmatsrofinn_gildir_afram():
    rak, _ = _keyra_run_extract(value_limit="0")
    assert "--skip-valuation" in rak and "--value-limit" not in rak


if __name__ == "__main__":  # pytest er ekki í þessu umhverfi
    for nafn, f in sorted(globals().copy().items()):
        if nafn.startswith("test_"):
            f()
            print("PASS", nafn)
