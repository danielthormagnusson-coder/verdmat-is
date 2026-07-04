"""halt_reason lifecycle round-trip (DELTA_TIMEOUT_DIAG_2026-07-04 root-fix).

Two invariants the nightly chain gate depends on:
  (a) KillSwitch (3 consecutive timeouts) SETS halt_reason in the persisted state.
  (b) A clean _delta close CLEARS halt_reason — a stale flag from an earlier night
      must not survive a run that logs "delta done" (the 06-30 -> 07-01/02/03 bug).

No network, no real DBs: fake session objects, in-memory sqlite (schema stubs so
verify_schema passes), state round-tripped through a temp file via save/load_state.

Run:  python -m unittest tests.test_fetch_mbl_halt_reason   (from repo root)
"""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from fetch_mbl import (  # noqa: E402
    KillSwitch, MblFetcher, default_state, load_state, save_state,
)


class _EmptyPageSession:
    """Every POST returns HTTP 200 with zero rows -> _delta breaks cleanly on page 1."""
    class _Resp:
        status_code = 200
        content = json.dumps({"data": {"fs_fasteign": []}}).encode()
        headers = {"content-type": "application/json"}

    def post(self, *a, **kw):
        return self._Resp()


class _TimeoutSession:
    """Every POST times out -> kill-switch after MAX_CONSEC_TIMEOUT attempts."""
    def post(self, *a, **kw):
        raise requests.ConnectTimeout("simulated timeout")


def _stub_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE raw_blobs(content_hash)")
    conn.execute("CREATE TABLE raw_fetches(id)")
    return conn


class HaltReasonRoundTrip(unittest.TestCase):
    def setUp(self):
        fd, self.state_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self.addCleanup(os.unlink, self.state_path)

    def _fetcher(self, session, state):
        f = MblFetcher(session, _stub_conn(), state, self.state_path,
                       mode="delta-sale", min_spacing=60, log=lambda *a: None)
        f._sleep = lambda s: None
        return f

    def test_killswitch_sets_halt_reason(self):
        state = default_state()
        f = self._fetcher(_TimeoutSession(), state)
        with self.assertRaises(KillSwitch):
            f.run()
        persisted = load_state(self.state_path)
        self.assertEqual(persisted["delta_sale"]["halt_reason"], "3 consecutive timeouts")
        self.assertIsNotNone(persisted["delta_sale"]["last_run_at"])

    def test_clean_run_clears_stale_halt_reason(self):
        state = default_state()
        state["delta_sale"]["halt_reason"] = "3 consecutive timeouts"   # stale, from a prior night
        state["delta_sale"]["last_br_dags_seen"] = "2026-06-29T00:14:00+00:00"
        save_state(self.state_path, state)
        f = self._fetcher(_EmptyPageSession(), load_state(self.state_path))
        f.run()
        persisted = load_state(self.state_path)
        self.assertIsNone(persisted["delta_sale"]["halt_reason"])
        # high-water untouched by an empty delta
        self.assertEqual(persisted["delta_sale"]["last_br_dags_seen"],
                         "2026-06-29T00:14:00+00:00")


if __name__ == "__main__":
    unittest.main()
