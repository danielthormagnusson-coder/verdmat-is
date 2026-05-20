"""Backup setup — generate rclone.conf for Cloudflare R2 from .env credentials,
then run a non-destructive bucket-listing test.

Reads:  D:\\verdmat-is\\.env  (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID,
        R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_ENDPOINT_URL)
Writes: D:\\verdmat-is\\tools\\rclone\\rclone.conf  (NOT committed to git)

Run:    python scripts/backup_setup.py
Exit 0: bucket listing returned at least the configured bucket name
Exit 2: missing .env, missing keys, or rclone binary not found
Exit 3: rclone listing failed (bad credentials or network)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not installed. Run: pip install --user python-dotenv")
    sys.exit(2)

ENV_PATH = Path(r"D:\verdmat-is\.env")
RCLONE_EXE = Path(r"D:\verdmat-is\tools\rclone\rclone.exe")
RCLONE_CONF = Path(r"D:\verdmat-is\tools\rclone\rclone.conf")
REQUIRED_KEYS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
    "R2_ENDPOINT_URL",
)

CONF_TEMPLATE = """\
[r2backup]
type = s3
provider = Cloudflare
access_key_id = {access_key_id}
secret_access_key = {secret_access_key}
endpoint = {endpoint}
acl = private
no_check_bucket = true
"""


def main() -> int:
    if not RCLONE_EXE.exists():
        print(f"ERROR: rclone.exe not found at {RCLONE_EXE}")
        print("Re-run Step 1A install (rclone download → tools/rclone/).")
        return 2

    if not ENV_PATH.exists():
        print(f"ERROR: .env not found at {ENV_PATH}")
        print("Create it with the 5 required keys before running this script.")
        return 2

    load_dotenv(ENV_PATH)
    missing = [k for k in REQUIRED_KEYS if not os.environ.get(k)]
    if missing:
        print(f"ERROR: missing keys in {ENV_PATH}: {missing}")
        return 2

    # Generate rclone.conf
    RCLONE_CONF.parent.mkdir(parents=True, exist_ok=True)
    RCLONE_CONF.write_text(
        CONF_TEMPLATE.format(
            access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            endpoint=os.environ["R2_ENDPOINT_URL"],
        ),
        encoding="utf-8",
    )
    print(f"Wrote rclone.conf to {RCLONE_CONF} ({RCLONE_CONF.stat().st_size} bytes)")
    print("  NOTE: this file contains secrets — do NOT commit it (rclone.conf in .gitignore).")

    # Sanity test: list contents of the bucket. R2 scoped tokens cannot run
    # `ListBuckets` (account-level operation) so we do a bucket-scoped probe
    # instead. An empty bucket returns 0 lines, exit code 0 — still success.
    bucket = os.environ["R2_BUCKET_NAME"]
    target = f"r2backup:{bucket}/"
    print(f"\nTesting bucket access via `rclone lsjson --max-depth 1 {target}` ...")
    try:
        result = subprocess.run(
            [str(RCLONE_EXE), "--config", str(RCLONE_CONF), "lsjson",
             "--max-depth", "1", target],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("ERROR: rclone lsjson timed out (network or endpoint config issue).")
        return 3

    if result.returncode != 0:
        print(f"ERROR: rclone returned {result.returncode}")
        print(f"stderr: {result.stderr[:1000]}")
        return 3

    # lsjson emits [] for empty buckets — that's still success.
    import json as _json
    try:
        entries = _json.loads(result.stdout) if result.stdout.strip() else []
    except _json.JSONDecodeError:
        print(f"ERROR: rclone returned non-JSON output:\n{result.stdout[:500]}")
        return 3

    print(f"OK: bucket '{bucket}' is reachable. Top-level entries: {len(entries)}")
    if entries:
        print("  (existing entries — backup snapshots, etc.):")
        for e in entries[:10]:
            print(f"    {e.get('Path', e)}")
        if len(entries) > 10:
            print(f"    ... +{len(entries) - 10} more")
    else:
        print("  (bucket is empty — first backup will populate it)")
    print("\nStep 1B halt point cleared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
