"""Hilfe -> Logs: Log-Viewer (Tabs: Exceptions + Alle), 3-Spalten-Tabelle.
Portiert aus dem Assistant; Log-Quellen + Verzeichnis kommen aus
settings.DJANGOBASE."""
from __future__ import annotations

import os
import re
from pathlib import Path

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.module_loading import import_string
from django.views import View

from ..conf import conf
from ..log_classifier import LogClassifier
from ..mixins import ZugriffMixin

_PROGRESS_RE = re.compile(r"\[#+-+\]\s+\d+/\d+")
_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:[,\.]\d+)?)\s*(.*)$")
_DEFAULT_SOURCE = "all"


def _tail_lines(path: Path | None, max_lines: int) -> list[str]:
    if not path:
        return []
    files: list[Path] = []
    if path.exists():
        files.append(path)
    for i in range(1, 11):
        rot = path.with_suffix(path.suffix + f".{i}")
        if rot.exists():
            files.insert(0, rot)
    if not files:
        return []
    collected: list[str] = []
    block = 65536
    for f_path in reversed(files):
        try:
            size = os.path.getsize(f_path)
        except OSError:
            continue
        data = b""
        try:
            with open(f_path, "rb") as f:
                pos = size
                while pos > 0 and data.count(b"\n") <= max_lines:
                    read = min(block, pos)
                    pos -= read
                    f.seek(pos)
                    data = f.read(read) + data
        except OSError:
            continue
        collected = data.decode("utf-8", errors="replace").splitlines() + collected
        if len(collected) >= max_lines:
            break
    return collected[-max_lines:]


def _line_class(content: str) -> str:
    # Request/Response-Marker (Assistant-Projekt) sind keine Severity, sondern
    # Kategorien und behalten ihre eigene Farbe -> zuerst pruefen.
    if "[REQ ]" in content:
        return "lg-req"
    if "[RESP]" in content:
        return "lg-resp"
    # Severity vom zentralen LogClassifier: erkennt benannte/Custom-Exceptions
    # (ValueError:, GarmentFitError:) und Traceback-Frames auch ohne
    # [ERROR]-Prefix. 'info' -> leere Klasse (Default-Farbe wie zuvor).
    sev = LogClassifier.severity(content)
    return "" if sev == "info" else "lg-" + sev


def _parse_blocks(lines: list[str], src_key: str) -> list[dict]:
    out: list[dict] = []
    cur: dict | None = None
    for ln in lines:
        if _PROGRESS_RE.search(ln):
            continue
        m = _TS_RE.match(ln)
        if m:
            if cur is not None:
                cur["cls"] = _line_class(cur["content"])
                out.append(cur)
            cur = {"ts": m.group(1).replace(",", "."), "src": src_key,
                   "content": m.group(2), "has_ts": True}
        else:
            if cur is None:
                cur = {"ts": "", "src": src_key, "content": ln, "has_ts": False}
            else:
                cur["content"] += "\n" + ln
    if cur is not None:
        cur["cls"] = _line_class(cur["content"])
        out.append(cur)
    return out


def _collect_all(log_dir: Path, sources: list, max_per_source: int,
                  noisy: set[str] | None = None) -> list[dict]:
    """Tailt alle Quellen und sortiert chronologisch absteigend.
    `noisy` (DJANGOBASE['log_noisy_sources']): Source-Keys, die in der
    'all'-Sicht uebersprungen werden — fuer extrem schreibwuetige Worker
    (z.B. PST-Import) deren Rauschen kein Progress-Bar-Filter abfaengt.
    """
    skip = noisy or set()
    blocks: list[dict] = []
    for key, _label, out_name, err_name in sources:
        if key == "all" or key in skip:
            continue
        for fname in (out_name, err_name):
            if not fname:
                continue
            blocks.extend(_parse_blocks(_tail_lines(log_dir / fname, max_per_source), key))
    blocks.sort(key=lambda b: b["ts"] or "", reverse=True)
    return blocks


def _collect_exceptions(log_dir, sources, max_per_source, noisy=None) -> list[dict]:
    blocks = _collect_all(log_dir, sources, max_per_source, noisy=noisy)
    return [b for b in blocks if b["cls"] in ("lg-critical", "lg-err", "lg-trace")
            or LogClassifier.is_exception_line(b["content"])]


def _resolve_log_config(request, c) -> tuple[Path, list]:
    """Liefert (log_verzeichnis, log_sources) — optional projektspezifisch.

    Wenn DJANGOBASE['log_source_provider'] gesetzt ist (dotted path oder
    Callable), bestimmt es die Quellen pro Request (z.B. pro Station /
    datums-suffigierte Dateinamen). Rueckgabe entweder eine Liste `sources`
    (Verzeichnis bleibt DJANGOBASE['log_verzeichnis']) oder ein Tupel
    `(verzeichnis, sources)`. Absolute Dateinamen in `sources` gewinnen
    gegenueber `verzeichnis` (Path('/a') / '/abs' -> '/abs').
    """
    log_dir = c["log_verzeichnis"]
    sources = c["log_sources"]
    provider = c.get("log_source_provider")
    if provider:
        fn = import_string(provider) if isinstance(provider, str) else provider
        result = fn(request)
        if isinstance(result, tuple):
            d, sources = result
            if d:
                log_dir = d
        else:
            sources = result
    return Path(str(log_dir)), list(sources)


def _stat(p: Path | None) -> dict | None:
    if not p or not p.exists():
        return None
    try:
        st = p.stat()
        return {"path": str(p), "size_kb": round(st.st_size / 1024, 1), "mtime": st.st_mtime}
    except OSError:
        return None


def _truncate_source(log_dir: Path, sources: list, key: str):
    """Best-effort Truncate aller Dateien einer Source (bei 'all' alle Quellen).

    Auf Windows kann eine Datei, die ein RotatingFileHandler offen haelt,
    zwar per open('w') getruncatet werden, aber der Append-Pointer des
    Handlers steht noch beim alten Offset -> Null-Byte-Padding. Best-effort
    reicht fuer die Log-Seite; PermissionError wird sauber gemeldet.
    """
    cleared, locked, failed = 0, [], []
    targets = sources if key == _DEFAULT_SOURCE else [s for s in sources if s[0] == key]
    seen: set[str] = set()
    for _key, _label, out_name, err_name in targets:
        for fname in (out_name, err_name):
            if not fname or fname in seen:
                continue
            seen.add(fname)
            path = log_dir / fname
            if not path.exists():
                continue
            try:
                with open(path, "w", encoding="utf-8"):
                    pass
                cleared += 1
            except PermissionError:
                locked.append(fname)
            except OSError as exc:
                failed.append(f"{fname}: {exc}")
    return cleared, locked, failed


class LogsClearView(ZugriffMixin, View):
    """Hilfe -> Logs: leert (truncatet) die Dateien der gewaehlten Quelle.
    POST-only; nach dem Leeren Redirect zurueck auf die Logs-Seite."""

    def post(self, request):
        c = conf()
        log_dir, sources = _resolve_log_config(request, c)
        key = (request.POST.get("source") or _DEFAULT_SOURCE).strip()
        valid = {s[0] for s in sources} | {_DEFAULT_SOURCE}
        if key not in valid:
            messages.error(request, f"Unbekannte Log-Quelle: {key}")
            return redirect("djangobase:logs")
        cleared, locked, failed = _truncate_source(log_dir, sources, key)
        parts = []
        if cleared:
            parts.append(f"{cleared} Datei(en) geleert")
        if locked:
            parts.append(f"{len(locked)} gesperrt: {', '.join(locked)}")
        if failed:
            parts.append(f"{len(failed)} Fehler: {'; '.join(failed)}")
        summary = "; ".join(parts) if parts else "nichts zu leeren"
        (messages.warning if (locked or failed) else messages.success)(request, summary)
        return redirect(f"{reverse('djangobase:logs')}?source={key}")


class LogsView(ZugriffMixin, View):
    """Hilfe -> Logs: Tabbed Log-Viewer (Exceptions + alle)."""

    def get(self, request):
        c = conf()
        log_dir, log_sources = _resolve_log_config(request, c)

        source_key = request.GET.get("source") or _DEFAULT_SOURCE
        try:
            max_lines = int(request.GET.get("lines") or 500)
        except ValueError:
            max_lines = 500
        max_lines = max(50, min(5000, max_lines))

        sources_map = {s[0]: s for s in log_sources}
        if source_key not in sources_map:
            source_key = _DEFAULT_SOURCE if _DEFAULT_SOURCE in sources_map else (log_sources[0][0] if log_sources else "all")
        _key, label, out_name, err_name = sources_map.get(source_key, (source_key, source_key, None, None))

        noisy = set(c.get("log_noisy_sources") or [])
        if source_key == "all":
            all_records = _collect_all(log_dir, log_sources, max_lines, noisy=noisy)[:max_lines]
            exception_records = _collect_exceptions(log_dir, log_sources, max(max_lines, 2000), noisy=noisy)
            out_stat = err_stat = None
        else:
            out_path = log_dir / out_name if out_name else None
            err_path = log_dir / err_name if err_name else None
            all_records = list(reversed(_parse_blocks(_tail_lines(out_path, max_lines), source_key)))
            exception_records = _parse_blocks(_tail_lines(err_path, max_lines), source_key)
            extra = [r for r in all_records if r["cls"] in ("lg-critical", "lg-err", "lg-trace")]
            seen = {(r["ts"], r["content"][:80]) for r in exception_records}
            for r in extra:
                if (r["ts"], r["content"][:80]) not in seen:
                    exception_records.append(r)
            exception_records.sort(key=lambda r: r["ts"] or "", reverse=True)
            out_stat, err_stat = _stat(out_path), _stat(err_path)

        return render(request, "djangobase/hilfe/logs.html", {
            "aktiv": "logs",
            "source_key": source_key,
            "source_label": label,
            "sources": [{"key": k, "label": lab} for k, lab, _o, _e in log_sources],
            "max_lines": max_lines,
            "all_records": all_records,
            "exception_records": exception_records,
            "all_count": len(all_records),
            "exception_count": len(exception_records),
            "out_stat": out_stat,
            "err_stat": err_stat,
        })
