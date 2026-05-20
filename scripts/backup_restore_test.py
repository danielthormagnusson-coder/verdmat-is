"""Restore-test — sample 5 files from current/ mirror, verify SHA-256.

Strategy (post-2026-05-20 sync conversion):
  • The live mirror lives at r2backup:<bucket>/current/<rel>/...
  • Restore-test reads the latest local manifest, picks 5 entries (seed=42),
    downloads each into D:\\restore_test\\, and compares:
       (a) restored-file SHA-256 vs manifest-recorded SHA-256
       (b) restored-file SHA-256 vs CURRENT local-file SHA-256 (round-trip)

The second check is what the new pattern enables — it confirms current/
mirrors the local truth at this exact moment, not just what was on disk
at backup time. Useful for detecting drift between local + remote.

Exits 0 on all-pass, non-zero on any mismatch. Always cleans D:\\restore_test\\.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

RCLONE_EXE = Path(r"D:\verdmat-is\tools\rclone\rclone.exe")
RCLONE_CONF = Path(r"D:\verdmat-is\tools\rclone\rclone.conf")
LOG_DIR = Path(r"D:\verdmat-is\backup_log")
RESTORE_DIR = Path(r"D:\restore_test")
SAMPLE_SIZE = 5
SEED = 42


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def latest_manifest() -> Path:
    candidates = sorted(LOG_DIR.glob("*_manifest.json"))
    if not candidates:
        raise FileNotFoundError(f"no manifest files in {LOG_DIR}")
    return candidates[-1]


def main() -> int:
    if not RCLONE_EXE.exists() or not RCLONE_CONF.exists():
        print("ERROR: rclone binary or config missing.")
        return 2

    try:
        manifest_path = latest_manifest()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 2
    print(f"Using manifest: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    strategy = data.get("strategy", "<unknown>")
    print(f"Manifest strategy: {strategy}")
    items = [it for it in data["items"] if it.get("sha256")]
    if len(items) < SAMPLE_SIZE:
        print(f"ERROR: manifest has only {len(items)} items with sha256, need {SAMPLE_SIZE}")
        return 2

    rng = random.Random(SEED)
    sample = rng.sample(items, SAMPLE_SIZE)
    RESTORE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Sampling {SAMPLE_SIZE} files (seed={SEED}); restoring to {RESTORE_DIR}\n")

    exit_code = 0
    try:
        for i, item in enumerate(sample, 1):
            remote = item["remote"]
            local_orig = Path(item["local"])
            manifest_sha = item["sha256"]
            size = item["size_bytes"]
            restore_name = f"{i:02d}_" + local_orig.name
            restore_path = RESTORE_DIR / restore_name

            print(f"[{i}/{SAMPLE_SIZE}] {remote}")
            print(f"  → {restore_path}  ({size:,} bytes expected from manifest)")

            r = subprocess.run(
                [str(RCLONE_EXE), "--config", str(RCLONE_CONF),
                 "copyto", remote, str(restore_path)],
                capture_output=True, text=True, timeout=600,
            )
            if r.returncode != 0:
                print(f"  FAIL rclone exit {r.returncode}")
                print(f"  stderr: {r.stderr[-400:]}")
                exit_code = 1
                continue
            if not restore_path.exists():
                print("  FAIL: file did not arrive on disk")
                exit_code = 1
                continue

            restored_sha = file_sha256(restore_path)
            restored_size = restore_path.stat().st_size

            # Check 1: restored matches manifest record
            manifest_match = restored_sha == manifest_sha and restored_size == size
            print(f"  manifest sha256: {manifest_sha}")
            print(f"  restored sha256: {restored_sha}  [{'OK' if manifest_match else 'MISMATCH'}]")
            print(f"  restored size:   {restored_size:,} bytes")

            # Check 2: restored matches CURRENT local file (round-trip)
            # Only meaningful if local file still exists at the same path.
            local_match = None
            if local_orig.exists():
                local_now_sha = file_sha256(local_orig)
                local_match = local_now_sha == restored_sha
                print(f"  local-now sha256: {local_now_sha}  [{'MATCH' if local_match else 'DIFFERS'}]")
            else:
                print(f"  local file no longer present at {local_orig} (skip drift check)")

            if not manifest_match:
                exit_code = 1
                print("  ! FAIL — restored file differs from manifest record")
            # local-match=False is INFORMATIONAL — file changed since backup,
            # not a backup integrity failure.

        if exit_code == 0:
            print(f"\nRESTORE TEST PASSED: {SAMPLE_SIZE}/{SAMPLE_SIZE} manifest SHA-256 match")
        else:
            print(f"\nRESTORE TEST FAILED: see mismatches above")
    finally:
        if RESTORE_DIR.exists():
            shutil.rmtree(RESTORE_DIR, ignore_errors=True)
            print(f"Cleaned up {RESTORE_DIR}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
