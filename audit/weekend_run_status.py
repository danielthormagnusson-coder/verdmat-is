"""
weekend_run_status.py — shared status-file writer for the Áfangi 0 weekend run.

Status file is the single observability surface during the multi-day run. Any
phase script can call StatusWriter.update() at any time; a background thread
polls and re-writes audit/weekend_run_status.md every UPDATE_INTERVAL_S
seconds.

The status file is human-readable Markdown so Danni can `cat` it from any
terminal at any time and see current state.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "audit"
STATUS_PATH = AUDIT_DIR / "weekend_run_status.md"
LOG_PATH = AUDIT_DIR / "weekend_run.log"

UPDATE_INTERVAL_S = 60.0  # write status every minute
RECENT_LOG_KEEP = 30  # keep last 30 log lines in status file


class StatusWriter:
    """Thread-safe shared status state. Background thread writes it periodically."""

    def __init__(self):
        self._lock = threading.Lock()
        self._fields = {
            "phase": "init",
            "subphase": "",
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "phase_started_at": None,
            "items_done": 0,
            "items_total": 0,
            "last_throughput_per_min": None,
            "halts": [],
            "errors_24h": [],
            "phase_state": {  # phase_name → "completed" | "in_progress" | "pending"
                "phase_1_storage_build": "pending",
                "phase_2_stage_a_augl_refresh": "pending",
                "phase_3_stage_b_image_bootstrap": "pending",
                "phase_4_commit_push": "pending",
            },
        }
        self._recent_log = deque(maxlen=RECENT_LOG_KEEP)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # --- public API ---

    def set_phase(self, name, state="in_progress"):
        with self._lock:
            self._fields["phase"] = name
            self._fields["phase_started_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._fields["items_done"] = 0
            self._fields["items_total"] = 0
            self._fields["phase_state"][name] = state
        self._write_now()

    def complete_phase(self, name):
        with self._lock:
            self._fields["phase_state"][name] = "completed"
        self._write_now()

    def set_subphase(self, sub):
        with self._lock:
            self._fields["subphase"] = sub
        self._write_now()

    def set_progress(self, done, total, throughput_per_min=None):
        with self._lock:
            self._fields["items_done"] = done
            self._fields["items_total"] = total
            if throughput_per_min is not None:
                self._fields["last_throughput_per_min"] = throughput_per_min

    def log(self, level, msg):
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        line = f"[{ts}] {level:5} {msg}"
        with self._lock:
            self._recent_log.append(line)
        try:
            AUDIT_DIR.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
        print(line, flush=True)

    def add_halt(self, reason):
        with self._lock:
            self._fields["halts"].append(
                f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}  {reason}"
            )
        self._write_now()

    def add_error(self, msg):
        with self._lock:
            self._fields["errors_24h"].append(
                f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}  {msg}"
            )

    # --- thread lifecycle ---

    def start(self):
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="StatusWriter", daemon=True
        )
        self._thread.start()
        self.log("INFO", "status writer thread started")

    def stop(self):
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=5)
        self._write_now()  # final write
        self.log("INFO", "status writer stopped")

    # --- internals ---

    def _run(self):
        while not self._stop_event.is_set():
            self._write_now()
            self._stop_event.wait(UPDATE_INTERVAL_S)

    def _write_now(self):
        try:
            with self._lock:
                content = self._render()
            AUDIT_DIR.mkdir(parents=True, exist_ok=True)
            tmp = STATUS_PATH.with_suffix(".md.tmp")
            tmp.write_text(content, encoding="utf-8")
            os.replace(tmp, STATUS_PATH)
        except OSError as e:
            print(f"[status_writer] write failed: {e}", flush=True)

    def _render(self):
        f = self._fields
        now = datetime.now(timezone.utc)
        started = datetime.fromisoformat(f["started_at"])
        total_elapsed = (now - started).total_seconds()
        phase_elapsed = None
        if f["phase_started_at"]:
            phase_started = datetime.fromisoformat(f["phase_started_at"])
            phase_elapsed = (now - phase_started).total_seconds()

        # ETA
        eta = "—"
        if f["items_total"] > 0 and f["items_done"] > 0 and phase_elapsed:
            rate = f["items_done"] / phase_elapsed  # items/sec
            remaining = (f["items_total"] - f["items_done"]) / rate if rate > 0 else 0
            eta_min = int(remaining / 60)
            eta = f"{eta_min} min ({eta_min // 60} h {eta_min % 60} min)"

        # Disk usage of D:\Gagnapakkar\images\
        try:
            usage = sum(
                f.stat().st_size
                for f in Path(r"D:\Gagnapakkar\images").rglob("*.jpg")
                if f.is_file()
            )
            disk_str = f"{usage / 1024 / 1024 / 1024:.2f} GB"
        except (OSError, FileNotFoundError):
            disk_str = "n/a"

        try:
            free_b = shutil.disk_usage("D:\\").free
            free_str = f"{free_b / 1024 / 1024 / 1024:.1f} GB free"
        except OSError:
            free_str = "n/a"

        lines = [
            "# Áfangi 0 — weekend run status",
            "",
            f"**Updated:** {now.isoformat(timespec='seconds')}  |  monitor with `cat audit/weekend_run_status.md`",
            f"**Run started:** {f['started_at']}  |  **total elapsed:** {self._fmt_duration(total_elapsed)}",
            "",
            "## Phase state",
            "",
        ]
        for ph_name, ph_state in f["phase_state"].items():
            marker = {"completed": "✓", "in_progress": "▶", "pending": "·"}[ph_state]
            lines.append(f"- {marker} **{ph_name}** — {ph_state}")
        lines += [
            "",
            "## Current activity",
            "",
            f"- **Phase:** {f['phase']}",
            f"- **Subphase:** {f['subphase'] or '—'}",
            f"- **Phase elapsed:** {self._fmt_duration(phase_elapsed) if phase_elapsed else '—'}",
            f"- **Items:** {f['items_done']:,} / {f['items_total']:,}"
            + (f" ({f['items_done']/f['items_total']*100:.1f}%)" if f["items_total"] else ""),
            f"- **Throughput:** {f['last_throughput_per_min']:.1f} items/min" if f["last_throughput_per_min"] else "- **Throughput:** —",
            f"- **ETA (current subphase):** {eta}",
            "",
            "## Disk",
            "",
            f"- `D:\\Gagnapakkar\\images\\` size: {disk_str}",
            f"- D:\\ free: {free_str}",
            "",
            "## Halts",
            "",
        ]
        if f["halts"]:
            for h in f["halts"][-10:]:
                lines.append(f"- {h}")
        else:
            lines.append("- (none)")
        lines += [
            "",
            "## Recent log (last 30 lines)",
            "",
            "```",
        ]
        lines += list(self._recent_log)
        lines += ["```", ""]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _fmt_duration(secs):
        if secs is None:
            return "—"
        m, s = divmod(int(secs), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        if d:
            return f"{d}d {h}h {m}m"
        if h:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"


# Singleton
_writer: StatusWriter | None = None


def get_writer() -> StatusWriter:
    global _writer
    if _writer is None:
        _writer = StatusWriter()
    return _writer
