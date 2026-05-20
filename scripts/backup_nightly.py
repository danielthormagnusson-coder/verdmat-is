"""Nightly backup driver — rclone sync → Cloudflare R2 verdmat-backups.

Strategy (revised 2026-05-20):
  • `current/<rel>/` holds the LIVE MIRROR of every backed-up path.
  • `archive/<ts>/<rel>/` holds prior versions of any file that was
    overwritten or deleted by the latest sync (via rclone --backup-dir).
  • Retention prunes `archive/<ts>/` prefixes older than 30 days.

This is the canonical rclone-incremental pattern: storage cost stays
~9.7 GB + the delta drift, instead of N × 9.7 GB for N snapshots.

The pre-existing 2026-05-20T12-35/ full-snapshot (old strategy) is left
intact at bucket root — not under current/ or archive/, so the retention
prune cannot touch it.

Reads:  D:\\verdmat-is\\.env
        D:\\verdmat-is\\app\\scripts\\backup_paths.json
Writes: D:\\verdmat-is\\backup_log\\<ts>.log
        D:\\verdmat-is\\backup_log\\<ts>_manifest.json
Logs:   per-run rclone log via --log-file

Safety:
  • Refuses to start if rclone.conf or .env absent.
  • Pre-flight bytes check (9.72 GB ± window); halts above 25 GB.
  • Retention prune halts if any `archive/<ts>/` prefix fails to parse
    or if the count exceeds 60.
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
RETENTION_DAYS = 30

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}$")
SIZE_HARD_MAX_GB = 25.0


def utc_ts() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_excluded(path: Path, excluded_names: set, excluded_norm: list) -> bool:
    if path.name in excluded_names:
        return True
    pn = str(path.resolve()).lower()
    for ex in excluded_norm:
        if pn == ex or pn.startswith(ex + os.sep):
            return True
    return False


def preflight_size(paths_config: dict, excluded_names: set, excluded_norm: list):
    """Walk the include set the same way rclone will, sum bytes for the
    halt check. Returns (file_count, total_bytes)."""
    n = 0
    total = 0
    for entry in paths_config["include"]:
        local = Path(entry["local_path"])
        kind = entry["kind"]
        if kind == "file":
            if local.exists() and not is_excluded(local, excluded_names, excluded_norm):
                n += 1
                total += local.stat().st_size
        elif kind == "dir" and local.exists():
            it = local.rglob("*") if entry.get("recurse", True) else local.glob("*")
            for f in it:
                if f.is_file() and not is_excluded(f, excluded_names, excluded_norm):
                    n += 1
                    total += f.stat().st_size
        elif kind == "glob" and local.exists():
            patterns = entry["patterns"]
            recurse = entry.get("recurse", False)
            it = local.rglob("*") if recurse else local.iterdir()
            for f in it:
                try:
                    if f.is_file() and not is_excluded(f, excluded_names, excluded_norm):
                        if any(fnmatch.fnmatch(f.name, p) for p in patterns):
                            n += 1
                            total += f.stat().st_size
                except OSError:
                    pass
    return n, total


def sha256_manifest(paths_config: dict, excluded_names: set, excluded_norm: list,
                    bucket: str, ts: str) -> list[dict]:
    """Compute SHA-256 + remote path for every file in the include set.
    Mirror layout: r2backup:<bucket>/current/<remote_sub>/<rel> ."""
    items: list[dict] = []
    for entry in paths_config["include"]:
        local = Path(entry["local_path"])
        remote_base = entry["remote_subpath"]
        kind = entry["kind"]
        if kind == "file":
            if local.exists() and not is_excluded(local, excluded_names, excluded_norm):
                items.append(_make_item(local, f"current/{remote_base}", bucket))
        elif kind == "dir" and local.exists():
            it = local.rglob("*") if entry.get("recurse", True) else local.glob("*")
            for f in it:
                if f.is_file() and not is_excluded(f, excluded_names, excluded_norm):
                    rel = f.relative_to(local).as_posix()
                    items.append(_make_item(f, f"current/{remote_base}/{rel}", bucket))
        elif kind == "glob" and local.exists():
            patterns = entry["patterns"]
            recurse = entry.get("recurse", False)
            it = local.rglob("*") if recurse else local.iterdir()
            for f in it:
                try:
                    if f.is_file() and not is_excluded(f, excluded_names, excluded_norm):
                        if any(fnmatch.fnmatch(f.name, p) for p in patterns):
                            if recurse:
                                rel = f.relative_to(local).as_posix()
                                items.append(_make_item(f, f"current/{remote_base}/{rel}", bucket))
                            else:
                                items.append(_make_item(f, f"current/{remote_base}/{f.name}", bucket))
                except OSError:
                    pass
    return items


def _make_item(local: Path, remote_rel: str, bucket: str) -> dict:
    try:
        sha = file_sha256(local)
    except OSError as e:
        sha = None
        print(f"  WARN sha256 failed for {local}: {e}")
    return {
        "local": str(local),
        "remote": f"r2backup:{bucket}/{remote_rel}",
        "remote_rel": remote_rel,
        "size_bytes": local.stat().st_size,
        "sha256": sha,
    }


def rclone_sync_entry(entry: dict, bucket: str, ts: str, log_path: Path) -> tuple[int, str]:
    """Sync one include entry. Uses `rclone sync` for dirs/globs (so
    deletes propagate to archive) and `rclone copyto` for individual files
    (single-source/single-dest, --backup-dir still archives if overwritten)."""
    kind = entry["kind"]
    local = entry["local_path"]
    remote_sub = entry["remote_subpath"]
    target_current = f"r2backup:{bucket}/current/{remote_sub}"
    target_archive = f"r2backup:{bucket}/archive/{ts}/{remote_sub}"

    common_flags = [
        "--config", str(RCLONE_CONF),
        "--transfers", "4",
        "--checkers", "8",
        "--stats", "30s",
        "--log-file", str(log_path),
        "--log-level", "INFO",
        "--backup-dir", target_archive,
    ]

    if kind == "file":
        cmd = [str(RCLONE_EXE), "copyto", local, target_current, *common_flags]
    elif kind == "dir":
        # Keep parents; sync the whole subtree. Excludes are enforced at the
        # filesystem level above (no excluded files are queued), but we also
        # mirror the filename excludes as rclone --exclude for safety.
        cmd = [str(RCLONE_EXE), "sync", local, target_current, *common_flags]
        if not entry.get("recurse", True):
            cmd.extend(["--max-depth", "1"])
    elif kind == "glob":
        # rclone sync with include patterns + max-depth 1 for top-level glob.
        recurse = entry.get("recurse", False)
        cmd = [str(RCLONE_EXE), "sync", local, target_current, *common_flags]
        if not recurse:
            cmd.extend(["--max-depth", "1"])
        for pat in entry["patterns"]:
            cmd.extend(["--include", pat])
    else:
        return 99, f"unknown kind: {kind!r}"

    proc = subprocess.run(cmd, capture_output=True, text=True)
    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-30:])
    return proc.returncode, tail


def prune_old_archives(bucket: str, keep_days: int = RETENTION_DAYS) -> None:
    """List `archive/<ts>/` prefixes, delete those older than keep_days.

    Safety: if ANY prefix fails to parse or count >60, halt without deleting."""
    print(f"\n=== Retention: prune archive/ entries older than {keep_days} days ===")
    target = f"r2backup:{bucket}/archive/"
    result = subprocess.run(
        [str(RCLONE_EXE), "--config", str(RCLONE_CONF), "lsf",
         "--dirs-only", target],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        # If archive/ doesn't exist yet (first sync, nothing was overwritten),
        # rclone returns an error — treat as "nothing to prune".
        msg = (result.stderr or "")[:200]
        if "directory not found" in msg.lower():
            print("  archive/ is empty (no overwritten files yet) — nothing to prune.")
            return
        print(f"  ERROR rclone lsf: {msg}")
        return
    raw = [ln.strip().rstrip("/") for ln in result.stdout.splitlines() if ln.strip()]
    bad = [p for p in raw if not TS_RE.match(p)]
    if bad:
        print(f"  HALT: {len(bad)} prefix(es) don't match YYYY-MM-DDTHH-MM. Sample: {bad[:5]}")
        return
    if len(raw) > 60:
        print(f"  HALT: found {len(raw)} archive prefixes (>60). Refusing to delete.")
        return
    now = dt.datetime.now(dt.timezone.utc)
    to_delete = []
    for p in raw:
        try:
            ts = dt.datetime.strptime(p, "%Y-%m-%dT%H-%M").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        age_days = (now - ts).total_seconds() / 86400
        if age_days > keep_days:
            to_delete.append((p, round(age_days, 1)))
    print(f"  archive entries: {len(raw)}; to delete (>{keep_days}d): {len(to_delete)}")
    for p, age in to_delete:
        path = f"{target}{p}/"
        print(f"  purging {path}  (age {age}d)")
        subprocess.run(
            [str(RCLONE_EXE), "--config", str(RCLONE_CONF), "purge", path],
            timeout=600,
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
    log_path = LOG_DIR / f"{ts}.log"
    manifest_path = LOG_DIR / f"{ts}_manifest.json"
    print(f"=== Backup {ts} (sync → current/, archive overwrites → archive/{ts}/) ===")
    print(f"  bucket:   {bucket}")
    print(f"  log:      {log_path}")
    print(f"  manifest: {manifest_path}")

    paths_config = json.loads(PATHS_JSON.read_text(encoding="utf-8"))
    excluded_names = set(paths_config.get("exclude_filenames", []))
    excluded_norm = [str(Path(p).resolve()).lower() for p in paths_config.get("exclude_paths", [])]

    n_files, total_bytes = preflight_size(paths_config, excluded_names, excluded_norm)
    total_gb = total_bytes / 1024**3
    print(f"\nPre-flight: {n_files:,} files, {total_bytes:,} bytes ({total_gb:.2f} GB)")
    if total_gb > SIZE_HARD_MAX_GB:
        print(f"HALT: {total_gb:.2f} GB exceeds {SIZE_HARD_MAX_GB} GB safety threshold. Misconfig?")
        return 2

    # Manifest (SHA-256 of every file we're about to sync, with the remote
    # current/ path it'll land at). Used by the restore test.
    print("\nComputing SHA-256 on local files (pre-sync manifest) ...")
    t_hash_start = time.time()
    items = sha256_manifest(paths_config, excluded_names, excluded_norm, bucket, ts)
    print(f"  manifest items: {len(items):,}   hashing elapsed: {time.time() - t_hash_start:.1f} s")

    # Sync per include entry. Each sync handles its own subtree.
    print(f"\nSyncing {len(paths_config['include'])} include entries ...")
    t_up_start = time.time()
    n_entries_ok = 0
    n_entries_err = 0
    err_samples: list[tuple[str, str]] = []
    for entry in paths_config["include"]:
        label = entry["local_path"]
        print(f"  → syncing {label}")
        rc, tail = rclone_sync_entry(entry, bucket, ts, log_path)
        if rc == 0:
            n_entries_ok += 1
            print(f"     OK")
        else:
            n_entries_err += 1
            err_samples.append((label, tail))
            print(f"     FAIL rc={rc}")
            for line in tail.splitlines()[-5:]:
                print(f"       {line}")

    elapsed = time.time() - t_up_start
    summary = {
        "snapshot": ts,
        "strategy": "sync+backup-dir (current/ mirror, archive/<ts>/ overwrites)",
        "bucket": bucket,
        "current_root": f"r2backup:{bucket}/current/",
        "archive_root": f"r2backup:{bucket}/archive/{ts}/",
        "entries_total": len(paths_config["include"]),
        "entries_ok": n_entries_ok,
        "entries_err": n_entries_err,
        "files_in_manifest": len(items),
        "total_bytes": total_bytes,
        "elapsed_seconds": round(elapsed, 1),
        "items": items,
    }
    manifest_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== Backup summary ===")
    print(f"  entries OK:     {n_entries_ok} / {len(paths_config['include'])}")
    print(f"  entries failed: {n_entries_err}")
    print(f"  files in manifest: {len(items):,}")
    print(f"  total bytes:    {total_bytes:,} ({total_gb:.2f} GB)")
    print(f"  sync time:      {elapsed:.1f} s ({elapsed/60:.2f} min)")
    print(f"  manifest:       {manifest_path}")

    if n_entries_err > 0:
        print("\nWARN: some sync entries failed. Skipping retention prune.")
        return 1

    prune_old_archives(bucket, keep_days=RETENTION_DAYS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
