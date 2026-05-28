"""shakedown_orchestrator.py — THROWAWAY self-test for the orchestrator's
subprocess handling + crash-finalize path. Not part of the monthly cycle.

Covers the failure modes that bit run_monthly on first real execution:
  - happy   : emits Icelandic + box-drawing chars, exit 0, "Done." on stdout
  - halt    : emits an error on stdout, exit 2 (clean halt)
  - crash   : emits an error on stdout, exit 1 (like rebuild preflight bail)
  - explode : raises an unhandled exception in the CHILD (non-zero exit)

The script operates in two roles:
  (1) child mode  : `python shakedown_orchestrator.py --child <mode>`
                    produces the synthetic output for one mode.
  (2) driver mode : `python shakedown_orchestrator.py`
                    runs each mode through subprocess_with_shape_safety and
                    asserts: stdout/stderr capture works (Icelandic survives
                    decode), exit-status maps correctly, no crash.

It also exercises the crash-finalize path directly against Supabase using a
'shakedown' run_type (writes pipeline_runs/pipeline_steps rows, then verifies
no dangling row remains). These rows are tagged run_type='shakedown' and are
deleted at the end so the audit tables stay clean.

NO monthly-cycle scripts are invoked. NO Supabase data-layer writes
(properties/predictions/etc.). Only pipeline_runs/pipeline_steps with
run_type='shakedown', created and then removed.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# NB: the 'cp1252_writer' child mode must NOT reconfigure stdout — it deliberately
# relies on the inherited default encoding (driven by PYTHONIOENCODING from the
# parent's env) to reproduce bug #5. Skip the top-of-file reconfigure for it so
# the test is faithful; all other modes + driver keep utf-8 stdout.
_is_cp1252_child = (
    len(sys.argv) >= 3 and sys.argv[1] == "--child" and sys.argv[2] == "cp1252_writer"
)
if not _is_cp1252_child:
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
sys.path.insert(0, str(Path(__file__).parent))

from migration_helpers import open_connection, subprocess_with_shape_safety  # noqa: E402

ICELANDIC = "á í ð þ ö Ð Þ Æ — box: │ ─ ┌ ┐ └ ┘"
SELF = str(Path(__file__).resolve())


# ----------------------------------------------------------------------
# CHILD MODE — produce synthetic output for one mode
# ----------------------------------------------------------------------
def child(mode: str) -> int:
    if mode == "happy":
        print("STAGE 1: building ...")
        print(f"  {ICELANDIC}")
        print("  ┌──────────────┐")
        print("  │  Reykjavík   │")
        print("  └──────────────┘")
        print("Done.")
        return 0
    if mode == "halt":
        print("STAGE 1: preflight check")
        print(f"  [HALT] drift exceeded threshold — {ICELANDIC}")
        return 2
    if mode == "crash":
        print("STAGE 1: preflight check")
        print(f"  [ERROR] missing input file — {ICELANDIC}")
        return 1
    if mode == "explode":
        print("STAGE 1: starting ...")
        raise RuntimeError(f"synthetic unhandled exception — {ICELANDIC}")
    if mode == "cp1252_writer":
        # Faithful repro of bug #5: a child that does NOT reconfigure its own
        # stdout (the top-of-file reconfigure was skipped for this mode) and
        # prints → / Icelandic / box-drawing. Without PYTHONIOENCODING=utf-8 in
        # the env, the child's stdout defaults to cp1252 and `print("→")` raises
        # UnicodeEncodeError. With the (A) env fix, stdout is utf-8 → clean.
        print("STAGE 4: Validating ...")
        print(f"  repeat_sale_index.csv: 2,673 → 2,681 rows (+0.3%)  {ICELANDIC}")
        print("Done.")
        return 0
    print(f"unknown child mode: {mode}", file=sys.stderr)
    return 99


# ----------------------------------------------------------------------
# DRIVER MODE — run each mode through the helper + assert
# ----------------------------------------------------------------------
def run_mode(mode: str) -> dict:
    cmd = [sys.executable, SELF, "--child", mode]
    exit_code, rowcount_after, msg = subprocess_with_shape_safety(
        cmd, timeout=30
    )
    return {"mode": mode, "exit_code": exit_code, "rowcount_after": rowcount_after, "msg": msg}


def assert_(cond: bool, label: str, results: list):
    mark = "PASS" if cond else "FAIL"
    results.append((label, cond))
    print(f"    [{mark}] {label}")


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--child":
        return child(sys.argv[2])

    print("=" * 70)
    print("SHAKEDOWN — subprocess_with_shape_safety + crash-finalize")
    print("=" * 70)
    results: list[tuple[str, bool]] = []

    # ----- A) subprocess capture + exit-status mapping per mode -----
    print("\n[A] subprocess handling per mode:")

    print("\n  happy (exit 0, Icelandic + box-drawing on stdout):")
    r = run_mode("happy")
    print(f"    -> exit_code={r['exit_code']}, msg={r['msg']!r}")
    assert_(r["exit_code"] == 0, "happy maps to exit 0", results)
    # Icelandic survives decode → no crash, msg is a clean 'subprocess ok (...)'
    assert_("subprocess ok" in r["msg"], "happy stdout decoded cleanly (no UnicodeDecodeError)", results)

    print("\n  halt (exit 2, error on stdout):")
    r = run_mode("halt")
    print(f"    -> exit_code={r['exit_code']}, msg(head)={r['msg'][:80]!r}")
    assert_(r["exit_code"] == 2, "halt maps to exit 2", results)
    assert_("HALT" in r["msg"] or "stdout-tail" in r["msg"], "halt stdout surfaced in msg", results)
    assert_("Ã" not in r["msg"], "halt Icelandic not mojibake (utf-8 decode)", results)

    print("\n  crash (exit 1, error on stdout — like rebuild preflight bail):")
    r = run_mode("crash")
    print(f"    -> exit_code={r['exit_code']}, msg(head)={r['msg'][:80]!r}")
    assert_(r["exit_code"] == 1, "crash maps to exit 1", results)
    assert_("ERROR" in r["msg"] or "stdout-tail" in r["msg"], "crash stdout surfaced in msg (the bug-1 regression test)", results)

    print("\n  explode (unhandled exception in child → non-zero exit):")
    r = run_mode("explode")
    print(f"    -> exit_code={r['exit_code']}, msg(head)={r['msg'][:120]!r}")
    assert_(r["exit_code"] != 0, "explode maps to non-zero exit", results)
    # Python prints the traceback to stderr; confirm stderr captured (not None)
    assert_("RuntimeError" in r["msg"] or "Traceback" in r["msg"] or "stderr" in r["msg"],
            "explode child traceback captured (stderr non-None)", results)

    print("\n  cp1252_writer (child WITHOUT stdout reconfigure, prints → — bug #5 repro):")
    r = run_mode("cp1252_writer")
    print(f"    -> exit_code={r['exit_code']}, msg={r['msg']!r}")
    # With the (A) env fix, PYTHONIOENCODING=utf-8 forces the child's stdout to
    # utf-8 even though it never reconfigures → the → prints fine and exit is 0.
    assert_(r["exit_code"] == 0, "cp1252_writer exit 0 (env fix forces child stdout utf-8)", results)
    assert_("subprocess ok" in r["msg"], "cp1252_writer no child-side UnicodeEncodeError", results)

    # Negative control: prove the env fix is load-bearing. Run the SAME child
    # through a raw subprocess.run WITHOUT PYTHONIOENCODING → child stdout
    # defaults to cp1252 → printing → raises UnicodeEncodeError → non-zero exit.
    print("\n  cp1252_writer NEGATIVE CONTROL (no PYTHONIOENCODING → expect child crash):")
    env_no_pio = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
    nc = subprocess.run(
        [sys.executable, SELF, "--child", "cp1252_writer"],
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=30, env=env_no_pio,
    )
    print(f"    -> exit_code={nc.returncode}; stderr(head)={(nc.stderr or '')[:90]!r}")
    assert_(nc.returncode != 0, "negative control crashes without PYTHONIOENCODING (env fix is load-bearing)", results)
    assert_("UnicodeEncodeError" in (nc.stderr or "") or "charmap" in (nc.stderr or ""),
            "negative control fails with cp1252 encode error (confirms bug #5 mechanism)", results)

    # ----- B) crash-finalize path against Supabase (shakedown rows) -----
    print("\n[B] crash-finalize path (pipeline_runs/steps, run_type='shakedown'):")
    conn = open_connection()
    run_id = None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.pipeline_runs (run_type, started_at) "
                "VALUES ('shakedown', now()) RETURNING id"
            )
            run_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO public.pipeline_steps (run_id, step_name, step_order, started_at) "
                "VALUES (%s, 'synthetic_inflight', 1, now()) RETURNING id",
                (run_id,),
            )
            step_id = cur.fetchone()[0]
        conn.commit()
        print(f"    created shakedown run_id={run_id}, in-flight step_id={step_id}")

        # Simulate crash-finalize (mirrors run_monthly except-block logic)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.pipeline_steps SET ended_at=now(), exit_code=-1, "
                "notes='crashed: synthetic' WHERE id=%s", (step_id,)
            )
            cur.execute(
                "UPDATE public.pipeline_runs SET ended_at=now(), exit_status='crashed' "
                "WHERE id=%s", (run_id,)
            )
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT exit_status, ended_at IS NOT NULL FROM public.pipeline_runs WHERE id=%s", (run_id,))
            rstat, rended = cur.fetchone()
            cur.execute("SELECT exit_code, ended_at IS NOT NULL FROM public.pipeline_steps WHERE id=%s", (step_id,))
            sexit, sended = cur.fetchone()
        print(f"    post-finalize: run exit_status={rstat!r} ended={rended}; step exit_code={sexit} ended={sended}")
        assert_(rstat == "crashed" and rended, "crash-finalize sets run exit_status='crashed' + ended_at", results)
        assert_(sexit == -1 and sended, "crash-finalize sets in-flight step exit_code=-1 + ended_at (no dangling)", results)

    finally:
        # Clean up shakedown rows so audit tables stay pristine.
        if run_id is not None:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM public.pipeline_steps WHERE run_id=%s", (run_id,))
                cur.execute("DELETE FROM public.pipeline_runs WHERE id=%s", (run_id,))
            conn.commit()
            print(f"    cleaned up shakedown run_id={run_id} (rows deleted)")
        conn.close()

    # ----- Verdict -----
    print("\n" + "=" * 70)
    n_pass = sum(1 for _, ok in results if ok)
    n_total = len(results)
    print(f"SHAKEDOWN: {n_pass}/{n_total} assertions passed")
    for label, ok in results:
        if not ok:
            print(f"  FAILED: {label}")
    print("=" * 70)
    return 0 if n_pass == n_total else 1


if __name__ == "__main__":
    sys.exit(main())
