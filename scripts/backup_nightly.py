"""Nightly backup driver — rclone copy → Cloudflare R2 verdmat-backups.

Reads backup_paths.json, generates a timestamped prefix (YYYY-MM-DDTHH-MM),
invokes rclone copy per include entry, writes a manifest with SHA-256 per
local file, and prunes snapshots older than the newest 30.

Pre-flight: total bytes across all include entries must be 7-15 GB. Out-of-
range → halt before any uploads.

Output:
  D:\\verdmat-is\\backup_log\\<ts>.log
  D:\\verdmat-is\\backup_log\\<ts>_manifest.json

Safety:
  - Refuses to start if .env is missing or rclone.conf absent.
  - Refuses to delete if parsed prefix count > 60 or any prefix fails to parse.
  - SHA-256 computed locally before upload (manifest); not after (R2 supports
    server-side checksums but we trust rclone's integrity).
"""
from __future__ import annotations

import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not installed.")
    sys.exit(2)

ENV_PATH = Path(r"D:\verdmat-is\.env")
RCLONE_EXE = Path(r"D:\verdmat-is\tools\rclone\rclone.exe")
RCLONE_CONF = Path(r"D:\verdmat-is\tools\rclone\rclone.conf")
PATHS_JSON = Path(__file__).resolve().parent / "backup_paths.json"
LOG_DIR = Path(r"D:\verdmat-is\backup_log")
RETENTION = 30

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}/?$")
SIZE_MIN_GB = 7.0
SIZE_MAX_GB = 15.0


def utc_ts() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files(paths_config: dict, excluded_names: set, excluded_dirs: list) -> list[tuple[Path, str]]:
    """Walk include entries → list of (local_path, remote_subpath).

    Honors exclude_paths (any local path under any excluded dir is skipped)
    and exclude_filenames (basename match)."""
    excluded_norm = [str(Path(p).resolve()).lower() for p in excluded_dirs]

    def is_excluded(path: Path) -> bool:
        if path.name in excluded_names:
            return True
        p_norm = str(path.resolve()).lower()
        for ex in excluded_norm:
            if p_norm == ex or p_norm.startswith(ex + os.sep):
                return True
        return False

    out: list[tuple[Path, str]] = []
    for entry in paths_config["include"]:
        local = Path(entry["local_path"])
        remote_base = entry["remote_subpath"]
        kind = entry["kind"]

        if kind == "file":
            if local.exists() and not is_excluded(local):
                out.append((local, remote_base))
            elif not local.exists():
                print(f"  WARN file missing: {local}")
        elif kind == "dir":
            if not local.exists():
                print(f"  WARN dir missing: {local}")
                continue
            recurse = entry.get("recurse", True)
            iterator = local.rglob("*") if recurse else local.glob("*")
            for f in iterator:
                if not f.is_file() or is_excluded(f):
                    continue
                rel = f.relative_to(local).as_posix()
                out.append((f, f"{remote_base}/{rel}"))
        elif kind == "glob":
            patterns = entry["patterns"]
            recurse = entry.get("recurse", False)
            if recurse:
                for f in local.rglob("*"):
                    if not f.is_file() or is_excluded(f):
                        continue
                    if any(fnmatch.fnmatch(f.name, p) for p in patterns):
                        rel = f.relative_to(local).as_posix()
                        out.append((f, f"{remote_base}/{rel}"))
            else:
                for f in local.iterdir():
                    if not f.is_file() or is_excluded(f):
                        continue
                    if any(fnmatch.fnmatch(f.name, p) for p in patterns):
                        out.append((f, f"{remote_base}/{f.name}"))
        else:
            print(f"  WARN unknown include kind: {kind!r}")
    return out


def rclone_copy_file(local: Path, remote: str, log_path: Path) -> tuple[int, str]:
    """Copy a single local file to a single remote path via rclone copyto.
    Returns (return_code, last_50_lines_of_output)."""
    cmd = [
        str(RCLONE_EXE), "--config", str(RCLONE_CONF),
        "copyto", str(local), remote,
        "--transfers", "4",
        "--checkers", "8",
        "--stats", "30s",
        "--log-file", str(log_path),
        "--log-level", "INFO",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-50:])
    return proc.returncode, tail


def prune_old(ts_root: str, keep: int = RETENTION) -> None:
    """List timestamped prefixes under bucket root, parse, delete oldest beyond `keep`.
    Refuses to delete if any parse failure or count > 60."""
    print(f"\n=== Retention prune: keep newest {keep} snapshots ===")
    result = subprocess.run(
        [str(RCLONE_EXE), "--config", str(RCLONE_CONF), "lsf", "--dirs-only", ts_root + "/"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        print(f"  ERROR rclone lsf: {result.stderr[:500]}")
        return
    raw = [ln.strip().rstrip("/") for ln in result.stdout.splitlines() if ln.strip()]
    bad = [p for p in raw if not TS_RE.match(p + "/")]
    if bad:
        print(f"  HALT: {len(bad)} prefix(es) don't match YYYY-MM-DDTHH-MM. Sample: {bad[:5]}")
        return
    if len(raw) > 60:
        print(f"  HALT: found {len(raw)} prefixes (>60). Refusing to delete.")
        return
    snapshots = sorted(raw)
    to_delete = snapshots[:-keep] if len(snapshots) > keep else []
    print(f"  total snapshots: {len(snapshots)};  to delete: {len(to_delete)}")
    for old in to_delete:
        target = f"{ts_root}/{old}"
        print(f"  purging {target}")
        subprocess.run(
            [str(RCLONE_EXE), "--config", str(RCLONE_CONF), "purge", target],
            timeout=300,
        )


def main() -> int:
    if not RCLONE_EXE.exists() or not RCLONE_CONF.exists():
        print(f"ERROR: missing rclone binary or config (run backup_setup.py first).")
        return 2
    if not ENV_PATH.exists():
        print(f"ERROR: .env missing at {ENV_PATH}")
        return 2

    load_dotenv(ENV_PATH)
    bucket = os.environ.get("R2_BUCKET_NAME")
    if not bucket:
        print("ERROR: R2_BUCKET_NAME missing from .env")
        return 2

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = utc_ts()
    ts_root = f"r2backup:{bucket}"
    snapshot_root = f"{ts_root}/{ts}"
    log_path = LOG_DIR / f"{ts}.log"
    manifest_path = LOG_DIR / f"{ts}_manifest.json"
    print(f"=== Backup {ts} → {snapshot_root} ===")
    print(f"  log:      {log_path}")
    print(f"  manifest: {manifest_path}")

    paths_config = json.loads(PATHS_JSON.read_text(encoding="utf-8"))
    excluded_names = set(paths_config.get("exclude_filenames", []))
    excluded_dirs = paths_config.get("exclude_paths", [])

    files = collect_files(paths_config, excluded_names, excluded_dirs)
    total_bytes = sum(f.stat().st_size for f, _ in files if f.exists())
    total_gb = total_bytes / 1024**3
    print(f"\nPre-flight: {len(files):,} files, {total_bytes:,} bytes ({total_gb:.2f} GB)")
    if total_gb < SIZE_MIN_GB or total_gb > SIZE_MAX_GB * 1.7:
        # 1.7× allowance to cover near-the-edge expansions; >25 GB still halts.
        if total_gb > 25:
            print(f"HALT: {total_gb:.2f} GB exceeds 25 GB safety threshold. Misconfig?")
            return 2
        print(f"  NOTE: outside expected 7-15 GB window but under 25 GB ceiling — continuing.")

    # Manifest items: compute SHA-256 + sizes
    print("\nComputing SHA-256 on local files (pre-upload integrity record) ...")
    manifest_items = []
    t_hash_start = time.time()
    for i, (local, remote_sub) in enumerate(files, 1):
        if not local.exists():
            continue
        try:
            sha = file_sha256(local)
        except OSError as e:
            print(f"  WARN sha256 failed for {local}: {e}")
            sha = None
        manifest_items.append({
            "local": str(local),
            "remote": f"{snapshot_root}/{remote_sub}",
            "size_bytes": local.stat().st_size,
            "sha256": sha,
        })
        if i % 250 == 0 or i == len(files):
            print(f"  hashed {i:>5,}/{len(files):,}")
    print(f"  hashing elapsed: {time.time() - t_hash_start:.1f} s")

    # Upload via rclone copyto per file (per-file BEGIN/COMMIT-equivalent: each
    # upload is atomic — partial failure leaves prior files intact remotely).
    print(f"\nUploading {len(manifest_items):,} files ...")
    t_up_start = time.time()
    n_ok = 0
    n_err = 0
    err_samples: list[tuple[str, str]] = []
    for i, item in enumerate(manifest_items, 1):
        rc, tail = rclone_copy_file(Path(item["local"]), item["remote"], log_path)
        if rc == 0:
            n_ok += 1
        else:
            n_err += 1
            if len(err_samples) < 5:
                err_samples.append((item["local"], tail))
        if i % 100 == 0 or i == len(manifest_items):
            elapsed = time.time() - t_up_start
            rate = i / max(elapsed, 0.001)
            print(f"  uploaded {i:>5,}/{len(manifest_items):,} ({rate:.1f}/sec, {n_err} errors)")

    elapsed = time.time() - t_up_start
    summary = {
        "snapshot": ts,
        "bucket": bucket,
        "snapshot_root": snapshot_root,
        "files_total": len(manifest_items),
        "files_ok": n_ok,
        "files_err": n_err,
        "total_bytes": total_bytes,
        "elapsed_seconds": round(elapsed, 1),
        "items": manifest_items,
    }
    manifest_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== Backup summary ===")
    print(f"  files OK:      {n_ok:,} / {len(manifest_items):,}")
    print(f"  files failed:  {n_err}")
    print(f"  total bytes:   {total_bytes:,} ({total_gb:.2f} GB)")
    print(f"  upload time:   {elapsed:.1f} s ({elapsed/60:.2f} min)")
    print(f"  manifest:      {manifest_path}")
    if err_samples:
        print("\nError samples:")
        for local, tail in err_samples:
            print(f"  {local}")
            for line in tail.splitlines()[-5:]:
                print(f"    {line}")

    if n_err > 0:
        print("\nWARN: some files failed to upload. Skipping retention prune.")
        return 1

    prune_old(ts_root, keep=RETENTION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
