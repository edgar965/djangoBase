"""ContextVar-basierte Job-Korrelation + getimestempelter stdout/stderr-Wrapper.

Generische Logging-Helfer, die in praktisch jedem Django-Backend nuetzlich
sind sobald lange Jobs (Analyse, Import, Cron) parallel laufen und man im
Log korrelieren will, welche Zeile zu welchem Job gehoert.

Benutzung (job_id-Korrelation):

    from djangobase.jobctx import with_job_id
    with with_job_id(rec_pk):
        logger.info("worker start")     # taucht im Log mit "[job=42] ..." auf

Benutzung (stdout/stderr-Timestamps):

    from djangobase.jobctx import install_stdout_timestamps
    install_stdout_timestamps()         # einmal beim Service-Start

Beides ist threadsicher.
"""
from __future__ import annotations

import contextvars
import logging
import re
import sys
import threading
import time
from contextlib import contextmanager


# ── Job-ID-ContextVar ────────────────────────────────────────────────────────

_job_id_var: contextvars.ContextVar = contextvars.ContextVar(
    "djangobase_job_id", default=None,
)


@contextmanager
def with_job_id(job_id):
    """Setzt den Job-ID-Kontext fuer alle Log-Calls im with-Block.

    Akzeptiert int (rec_pk) oder str (custom label). None setzt zurueck.
    Vererbt korrekt in untergeordnete Threads/Tasks die in diesem Kontext
    gestartet wurden (ContextVar-Semantik).
    """
    token = _job_id_var.set(job_id)
    try:
        yield
    finally:
        _job_id_var.reset(token)


def current_job_id():
    """Aktuelle Job-ID aus dem ContextVar (oder None)."""
    return _job_id_var.get()


class JobContextFilter(logging.Filter):
    """Haengt job_id + job_str an jeden LogRecord. Ohne Kontext leer.

    job_str ist eine fertig formatierte Variante '[job=N] ' (mit Trailing-
    Space) oder '' — bequem in Format-Strings einsetzbar, z.B.:

        "{asctime} [{levelname}] {name}: {job_str}{message}"
    """

    def filter(self, record: logging.LogRecord) -> bool:
        job_id = _job_id_var.get()
        record.job_id = job_id if job_id is not None else ""
        record.job_str = f"[job={job_id}] " if job_id is not None else ""
        return True


# ── Stdout/Stderr-Timestamp-Wrapper ──────────────────────────────────────────

# Erkennt unsere eigenen Logging-Zeilen ("2026-05-05 11:32:42 [INFO] ..."):
# wenn schon getimestempelt, NICHT doppelt prefixen.
_TS_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


class TimestampedStream:
    """Wrapper um sys.stdout/sys.stderr der pro-Zeile ein Datum vorhaengt
    wenn die Zeile noch keines hat.

    Buffert Teil-Schreibvorgaenge bis zum naechsten ``\\n`` — sonst kriegen
    z.B. tqdm-Progress-Bar-Updates jeweils einen eigenen Timestamp pro
    Carriage-Return-Tick (waere unleserlich).
    """

    def __init__(self, wrapped):
        self._wrapped = wrapped
        self._buffer = ""
        self._at_line_start = True
        # Lock fuer Multi-Thread-Schreiber (Waitress-Worker, Detector-Threads,
        # ...). Acquire kostet ~1 µs gegenueber dem eigentlichen Write.
        self._lock = threading.Lock()

    def write(self, s):
        if not s:
            return 0
        with self._lock:
            return self._write_locked(s)

    def _write_locked(self, s):
        s = self._buffer + s
        out = []
        i = 0
        n = len(s)
        line_start = self._at_line_start
        broke_early = False
        while i < n:
            j_n = s.find("\n", i)
            j_r = s.find("\r", i)
            j = min(x for x in (j_n, j_r) if x != -1) if (j_n != -1 or j_r != -1) else -1
            if j == -1:
                self._buffer = s[i:]
                self._at_line_start = line_start
                broke_early = True
                break
            chunk = s[i:j + 1]
            if line_start and chunk.strip() and not _TS_PREFIX_RE.match(chunk):
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                out.append(f"{ts} {chunk}")
            else:
                out.append(chunk)
            line_start = True
            i = j + 1
        if not broke_early:
            self._buffer = ""
            self._at_line_start = line_start
        if out:
            self._wrapped.write("".join(out))
        return len(s)

    def flush(self):
        with self._lock:
            if self._buffer:
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                if not _TS_PREFIX_RE.match(self._buffer):
                    self._wrapped.write(f"{ts} {self._buffer}")
                else:
                    self._wrapped.write(self._buffer)
                self._buffer = ""
            self._wrapped.flush()

    def __getattr__(self, name):
        return getattr(self._wrapped, name)


_INSTALLED = False
_INSTALL_LOCK = threading.Lock()


def install_stdout_timestamps():
    """Wickelt sys.stdout/sys.stderr in TimestampedStream ein. Idempotent
    und thread-safe (Modul-Level-Lock guarded)."""
    global _INSTALLED
    with _INSTALL_LOCK:
        if _INSTALLED:
            return
        if not isinstance(sys.stdout, TimestampedStream):
            sys.stdout = TimestampedStream(sys.stdout)
        if not isinstance(sys.stderr, TimestampedStream):
            sys.stderr = TimestampedStream(sys.stderr)
        _INSTALLED = True
