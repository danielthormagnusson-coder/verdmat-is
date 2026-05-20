"""Restore-test — sample 5 files from latest snapshot, download, SHA-256 compare.

Reads the most recent manifest in D:\\verdmat-is\\backup_log\\, picks 5 entries
using random seed=42, downloads each to D:\\restore_test\\, computes SHA-256
on the restored file, and asserts it matches the manifest entry.

Exits 0 on all-pass, non-zero on any mismatch. Always cleans up D:\\restore_test\\
on exit (success OR failure).
"""
from __future__ import annotations

import hashlib
import json
import os
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
            local_orig = item["local"]
            expected_sha = item["sha256"]
            size = item["size_bytes"]
            restore_name = f"{i:02d}_" + Path(local_orig).name
            restore_path = RESTORE_DIR / restore_name

            print(f"[{i}/{SAMPLE_SIZE}] {remote}")
            print(f"  → {restore_path}  ({size:,} bytes expected)")

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

            actual_sha = file_sha256(restore_path)
            actual_size = restore_path.stat().st_size
            match = actual_sha == expected_sha and actual_size == size
            status = "OK" if match else "MISMATCH"
            print(f"  expected sha256: {expected_sha}")
            print(f"  actual   sha256: {actual_sha}  [{status}]")
            print(f"  actual size:     {actual_size:,} bytes")
            if not match:
                exit_code = 1
                print("  ! FAIL — checksum or size differs from manifest")

        if exit_code == 0:
            print(f"\nRESTORE TEST PASSED: {SAMPLE_SIZE}/{SAMPLE_SIZE} checksums match")
        else:
            print(f"\nRESTORE TEST FAILED: see mismatches above")
    finally:
        # Cleanup regardless of pass/fail
        if RESTORE_DIR.exists():
            shutil.rmtree(RESTORE_DIR, ignore_errors=True)
            print(f"Cleaned up {RESTORE_DIR}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
