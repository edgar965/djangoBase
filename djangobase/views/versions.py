"""Hilfe -> Versionen: Changelog aus GitHub/Git + Umgebung/Pakete.

Repo-Liste, App-Version, Paket-Liste, optionaler Commit-Text-Transform
und Commits-pro-Page kommen aus settings.DJANGOBASE.

Pro Commit wird zusätzlich ermittelt:
  - is_release / version_label  (Subject matched Release-Marker?)
  - effective_version           (Newest-First-Scan: in welchem Release ist
                                  der Commit gelandet — oder "vX.Y+1-dev"
                                  für noch ungebumpte Commits)
  - is_unreleased               (Commit ist neuer als letztes Release)
  - is_current                  (entspricht der laufenden App-Version)

Außerdem werden Git-Tags geholt + ein "local_in_remote"-Flag berechnet,
das zeigt, ob HEAD bereits gepushed ist. Beides ist optional sichtbar
im Template.
"""
import html
import importlib
import json
import logging
import platform
import re
import subprocess
import threading
import time
from pathlib import Path

import django
from django.shortcuts import render
from django.views import View

from ..conf import conf
from ..gitabfrage import Gitabfrage
from ..mixins import ZugriffMixin

logger = logging.getLogger(__name__)

_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_GH_TTL_S = 300.0
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_TRANSFORM_CACHE: dict = {}


class _Einmalig:
    """Merkt sich, welche Schlüssel gerade bearbeitet werden.

    `add_if_absent` gibt True zurück, wenn der Aufrufer der erste ist —
    prüfen und eintragen unter EINER Sperre, sonst starten zwei Anfragen zwei
    Erneuerungsfaeden für denselben Schlüssel."""

    def __init__(self):
        self._lock = threading.Lock()
        self._menge = set()

    def add_if_absent(self, key) -> bool:
        with self._lock:
            if key in self._menge:
                return False
            self._menge.add(key)
            return True

    def discard(self, key) -> None:
        with self._lock:
            self._menge.discard(key)


class _TTLCache:
    """Mini-TTL-Cache mit RLock + per-Key-Lock gegen Thundering Herd.

    Ohne Lock spawnen zwei parallele Page-Renders auf Cache-Miss doppelt so
    viele `gh`-Subprocesses (pro Repo einen je Render). Unter ASGI/Daphne mit
    echter Nebenlaeufigkeit ist das real. Der per-Key-Lock hält den zweiten
    Caller zurück, bis der erste denselben Key gefuellt hat.
    """

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = float(ttl_seconds)
        self._data: dict = {}
        # _data und _key_locks werden beide unter _meta_lock geschuetzt.
        self._meta_lock = threading.RLock()
        self._key_locks: dict = {}
        # Welche Schluessel gerade im Hintergrund erneuert werden — damit nicht
        # jede Anfrage einen eigenen Faden dafuer startet.
        self._laeuft = _Einmalig()

    def get_or_compute(self, key, producer):
        now = time.time()
        # Fast-path: lock-free read. dict.get ist GIL-atomar; ein falsch-stale
        # Treffer waere harmlos, da wir gleich nochmal unter Lock pruefen.
        hit = self._data.get(key)
        if hit and (now - hit[0]) < self._ttl:
            return hit[1]
        with self._meta_lock:
            key_lock = self._key_locks.setdefault(key, threading.Lock())
        # ALTEN WERT AUSLIEFERN UND IM HINTERGRUND ERNEUERN (Review 13.08.2026,
        # gemessen): Die Versionen-Seite brauchte bei kaltem bzw. abgelaufenem
        # Cache 4,9 s, warm 0,7 s — vier Repos mal zwei `gh api`-Aufrufe, jeder
        # mit bis zu 10 s Zeitgrenze, alle IN der Anfrage. Wer nach Ablauf der
        # Haltbarkeit zuerst kommt, zahlt das jedes Mal.
        # Ist schon ein Wert da, ist er hoechstens ein TTL alt — fuer eine
        # Commit-Liste ist das genau richtig. Nur der ALLERERSTE Abruf rechnet
        # noch in der Anfrage, denn vorher gibt es nichts zu zeigen. Dasselbe
        # Muster wie djangobase.hintergrund_cache, hier ohne Umbau der API.
        if hit is not None:
            if self._laeuft.add_if_absent(key):
                threading.Thread(
                    target=self._erneuern, args=(key, producer, key_lock),
                    name="ttlcache-%s" % str(key)[:40], daemon=True).start()
            return hit[1]

        with key_lock:
            # Double-check: anderer Thread hat zwischenzeitlich gefuellt.
            now = time.time()
            hit = self._data.get(key)
            if hit and (now - hit[0]) < self._ttl:
                return hit[1]
            value = producer()
            self._data[key] = (now, value)
            return value

    def _erneuern(self, key, producer, key_lock):
        """Im Hintergrund neu berechnen. Fehler bleiben still: Der alte Wert
        steht weiter, und genau dafür ist dieser Weg da."""
        try:
            with key_lock:
                wert = producer()
                self._data[key] = (time.time(), wert)
        except Exception:                                        # noqa: BLE001
            logger.warning("Versionen: Hintergrund-Erneuerung von %r fehlgeschlagen",
                           key, exc_info=True)
        finally:
            self._laeuft.discard(key)

    def clear(self) -> None:
        with self._meta_lock:
            self._data.clear()


_GH_CACHE = _TTLCache(_GH_TTL_S)


def _md_inline(text: str) -> str:
    out = html.escape(text)
    out = _RE_INLINE_CODE.sub(r"<code>\1</code>", out)
    out = _RE_BOLD.sub(r"<strong>\1</strong>", out)
    return out


def _render_body_html(body: str) -> str:
    if not body:
        return ""
    out: list[str] = []
    depth = 0
    para: list[str] = []
    bullet_re = re.compile(r"^(\s*)[-*]\s+(.+)$")

    def flush():
        if para:
            t = " ".join(para).strip()
            if t:
                out.append(f"<p>{_md_inline(t)}</p>")
            para.clear()

    def close(to):
        nonlocal depth
        while depth > to:
            out.append("</ul>")
            depth -= 1

    def opn(to):
        nonlocal depth
        while depth < to:
            out.append("<ul>")
            depth += 1

    for raw in body.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        m = bullet_re.match(line)
        if m:
            flush()
            indent = len(m.group(1).replace("\t", "    "))
            text = m.group(2).rstrip()
            d = 1 if indent < 2 else 2
            opn(d) if d > depth else (close(d) if d < depth else None)
            cp = text.find(":")
            if 0 < cp < 60 and " " not in text[:cp]:
                rendered = f"<strong>{html.escape(text[:cp])}</strong>{_md_inline(text[cp:])}"
            else:
                rendered = _md_inline(text)
            out.append(f"<li>{rendered}</li>")
        elif line.strip().endswith(":") and len(line.strip()) < 60:
            close(0)
            flush()
            out.append(f"<h3>{_md_inline(line.strip())}</h3>")
        else:
            para.append(line.strip())
    flush()
    close(0)
    return "\n".join(out)


def _resolve_transform(dotted: str | None):
    """DJANGOBASE['commit_text_transform']="search.utils.umlauts.restore_umlauts"
    lädt einmalig und cached. Bei None oder Import-Fehler: identity."""
    if not dotted:
        return lambda s: s
    if dotted in _TRANSFORM_CACHE:
        return _TRANSFORM_CACHE[dotted]
    try:
        mod, name = dotted.rsplit(".", 1)
        fn = getattr(importlib.import_module(mod), name)
        _TRANSFORM_CACHE[dotted] = fn
        return fn
    except (ImportError, AttributeError, ValueError):
        _TRANSFORM_CACHE[dotted] = lambda s: s
        return _TRANSFORM_CACHE[dotted]


def _gh(args, timeout=10):
    try:
        r = subprocess.run(["gh", "api", *args], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace",
                           creationflags=_NO_WINDOW)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)


def _gh_list_commits(repo, per_page=100, transform=None):
    return _GH_CACHE.get_or_compute(
        f"commits:{repo}:{per_page}",
        lambda: _fetch_commits(repo, per_page, transform),
    )


def _fetch_commits(repo, per_page, transform):
    rc, out, _err = _gh([f"repos/{repo}/commits?per_page={per_page}"])
    if rc != 0:
        return []
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError:
        return []
    tr = transform or (lambda s: s)
    result = []
    for c in data:
        commit = c.get("commit", {}) or {}
        author = commit.get("author", {}) or {}
        full = (commit.get("message") or "").strip()
        subject, body = (full.split("\n\n", 1) + [""])[:2] if "\n\n" in full else (full, "")
        body = "\n".join(l for l in body.splitlines()
                         if not l.startswith(("Co-Authored-By:", "Co-authored-by:", "Signed-off-by:"))).strip()
        subj = subject.strip()
        label, title = None, subj
        # Erste Form: "v0.46: Foo" / "Version 0.46 — Foo"
        m = re.match(r"^(?:v|Version\s+)(\d+\.\d+(?:\.\d+)?)\s*[:—\-]\s*(.+)$", subj, re.I)
        if m:
            label, title = "v" + m.group(1), m.group(2).strip()
        else:
            # Zweite Form: nackt "Version 0.46"
            m2 = re.match(r"^(?:v|Version\s+)(\d+\.\d+(?:\.\d+)?)\s*$", subj, re.I)
            if m2:
                label = "v" + m2.group(1)
            else:
                # Dritte Form: Release-Marker IRGENDWO im Subject
                m3 = re.search(r"(?:^|[\s\(\[\+,—\-])(?:v|Version\s+)(\d+\.\d+(?:\.\d+)?)\b", subj, re.I)
                if m3:
                    label = "v" + m3.group(1)
        sha_full = c.get("sha") or ""
        subj_t = tr(subj)
        title_t = tr(title)
        body_t = tr(body)
        result.append({
            "sha": sha_full[:7], "sha_full": sha_full,
            "subject": subj_t[:240], "version_label": label,
            "title": title_t[:240], "body": body_t,
            "body_html": _render_body_html(body_t),
            "author": author.get("name") or "?",
            "date": (author.get("date") or "")[:10],
            "url": c.get("html_url") or "",
            "is_release": label is not None,
        })
    return result


def _gh_list_tags(repo: str) -> list[dict]:
    """Git-Tags des Repos — Release-Marker."""
    return _GH_CACHE.get_or_compute(f"tags:{repo}", lambda: _fetch_tags(repo))


def _fetch_tags(repo):
    rc, out, _err = _gh([f"repos/{repo}/tags?per_page=30"])
    if rc != 0:
        return []
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError:
        return []
    result = [{
        "name": t.get("name", ""),
        "sha": (t.get("commit", {}).get("sha") or "")[:7],
    } for t in data]
    return result


def _git(repo_path, *args, timeout=5):
    u"""`git` im Repo aufrufen — über :class:`Gitabfrage`, also mit Cache.

    GEMESSEN (17.08.2026): Diese Funktion war der ganze Aufwand der Seite —
    650 von 690 ms warm, bei 0 SQL-Abfragen. Zwölf Aufrufe (vier Repos mal
    `remote get-url` / `rev-parse` / `status --porcelain`), jeder rund 50 ms,
    weil das STARTEN eines Prozesses unter Windows so viel kostet. Die
    Begründung für den Cache und seine Haltbarkeit steht in
    ``djangobase/gitabfrage.py``.
    """
    return Gitabfrage.lauf(repo_path, *args, timeout=timeout)


# Matcht den GitHub-Slug 'owner/repo' aus SSH- und HTTPS-Remotes:
#   git@github.com:owner/repo.git
#   https://github.com/owner/repo(.git)
_REMOTE_SLUG_RE = re.compile(r"github\.com[:/]+([^/\s]+/[^/\s]+?)(?:\.git)?/?$")


def _gh_repo_from_remote(repo_path):
    """Leitet 'owner/repo' aus dem origin-Remote des lokalen Repos ab — so muss
    KEIN abhaengiges Projekt seinen GitHub-Slug in der Config (oder gar in
    djangoBase) hardcoden; Git kennt das Remote bereits. Leerstring wenn kein
    GitHub-Remote gefunden wird (z.B. nur lokales Repo)."""
    m = _REMOTE_SLUG_RE.search(_git(repo_path, "remote", "get-url", "origin").strip())
    return m.group(1) if m else ""


def _git_log_local(repo_path, n=100, transform=None, gh_repo=""):
    """Fallback ohne gh: lokales git log als Changelog — inkl. Commit-BODY,
    damit ausfuehrliche Release-Beschreibungen (Bullet-Listen im Commit)
    genauso erscheinen wie über die GitHub-API."""
    out = _git(repo_path, "log", f"-{n}",
               "--pretty=format:%H\x1f%an\x1f%ad\x1f%B\x1e", "--date=short")
    tr = transform or (lambda s: s)
    res = []
    for rec in out.split("\x1e"):
        rec = rec.strip("\n\r ")
        if not rec:
            continue
        parts = rec.split("\x1f")
        if len(parts) != 4:
            continue
        sha_full, an, ad, full = parts
        full = full.strip()
        subject, body = (full.split("\n\n", 1) + [""])[:2] if "\n\n" in full else (full, "")
        body = "\n".join(l for l in body.splitlines()
                         if not l.startswith(("Co-Authored-By:", "Co-authored-by:", "Signed-off-by:"))).strip()
        subj = subject.strip().splitlines()[0] if subject.strip() else ""
        label, title = None, subj
        # gleiche Release-Erkennung wie im gh-Pfad
        m = re.match(r"^(?:v|Version\s+)(\d+\.\d+(?:\.\d+)?)\s*[:—\-]\s*(.+)$", subj, re.I)
        if m:
            label, title = "v" + m.group(1), m.group(2).strip()
        else:
            m2 = re.match(r"^(?:v|Version\s+)(\d+\.\d+(?:\.\d+)?)\s*$", subj, re.I)
            if m2:
                label = "v" + m2.group(1)
            else:
                m3 = re.search(r"(?:^|[\s\(\[\+,—\-])(?:v|Version\s+)(\d+\.\d+(?:\.\d+)?)\b", subj, re.I)
                if m3:
                    label = "v" + m3.group(1)
        subj_t = tr(subj)
        title_t = tr(title)
        body_t = tr(body)
        res.append({"sha": sha_full[:7], "sha_full": sha_full,
                    "subject": subj_t[:240], "version_label": label,
                    "title": title_t[:240], "body": body_t,
                    "body_html": _render_body_html(body_t),
                    "author": an, "date": ad,
                    "url": f"https://github.com/{gh_repo}/commit/{sha_full}" if gh_repo else "",
                    "is_release": label is not None})
    return res


def _next_dev_label(current_version: str) -> str:
    """Für Commits NEUER als das letzte Release: nächste Minor-Version
    mit '-dev'-Suffix. '0.46' -> 'v0.47-dev'."""
    norm = (current_version or "").lstrip("v").strip()
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", norm)
    if not m:
        return "next-dev"
    major, minor = int(m.group(1)), int(m.group(2))
    return f"v{major}.{minor + 1}-dev"


def _annotate_chronological(commits: list, current_version: str) -> list[dict]:
    """Newest-First-Scan: jedem Commit eine effective_version zuordnen
    (welches Release enthält diesen Commit?). Commits über dem letzten
    Release sind unreleased-dev.

    Markiert is_current für den Commit, der genau current_version trägt.
    """
    norm_current = (current_version or "").lstrip("v").strip()
    out = []
    latest_seen: str | None = None
    dev_label = _next_dev_label(current_version)
    for c in commits:
        label = c.get("version_label")
        if label:
            latest_seen = label
        if latest_seen is None:
            effective = dev_label
            is_unreleased = True
        else:
            effective = latest_seen
            is_unreleased = False
        out.append({
            **c,
            "effective_version": effective,
            "is_unreleased": is_unreleased,
            "is_current": bool(label and label.lstrip("v") == norm_current),
        })
    return out


def _pakete(namen):
    from importlib.metadata import PackageNotFoundError, version
    out = [("Python", platform.python_version()), ("Django", django.get_version())]
    for n in namen:
        if n.lower() == "django":
            continue
        try:
            out.append((n, version(n)))
        except PackageNotFoundError:
            out.append((n, "—"))
    return out


def _manual_entries(raw_list, current_version):
    """Normiert DJANGOBASE['manual_versions'] auf das gleiche Schema wie
    GitHub-Commits, damit das Template einen Eintragstyp rendern kann.

    Eingabe-Items:
        {"version": "v0.83", "date": "2026-06-08", "title": "...",
         "body_html": "..." }
        {"version": "0.82", "date": "...", "title": "...",
         "body_md": "- a\n- b" }
    """
    norm_current = (current_version or "").lstrip("v").strip()
    out = []
    for item in raw_list or []:
        version = (item.get("version") or "").strip()
        if not version:
            continue
        label = version if version.startswith("v") else f"v{version}"
        norm = label.lstrip("v")
        body_html = item.get("body_html") or ""
        body_md = item.get("body_md") or ""
        if not body_html and body_md:
            body_html = _render_body_html(body_md)
        out.append({
            "sha": "manual", "sha_full": "",
            "subject": item.get("title", ""),
            "title": item.get("title", ""),
            "version_label": label,
            "effective_version": label,
            "body": body_md, "body_html": body_html,
            "author": item.get("author", ""),
            "date": item.get("date", ""),
            "url": item.get("url", ""),
            "is_release": True,
            "is_unreleased": False,
            "is_current": norm == norm_current,
            "is_manual": True,
        })
    return out


class VersionsView(ZugriffMixin, View):
    def get(self, request):
        if request.GET.get("refresh") == "1":
            _GH_CACHE.clear()
        c = conf()
        base_dir = c["log_verzeichnis"]  # = BASE_DIR-Default
        current_version = c["version"]
        per_page = int(c.get("version_commits_per_page") or 100)
        transform = _resolve_transform(c.get("commit_text_transform"))
        manual = _manual_entries(c.get("manual_versions") or [], current_version)
        repos = []
        for display, gh_repo, local_dir in c["repos"]:
            local_path = (Path(base_dir) / local_dir).resolve()
            # Leerer Slug in der Config -> aus dem lokalen origin-Remote ableiten,
            # damit kein Projekt seinen 'owner/repo' irgendwo hardcoden muss.
            if not gh_repo and local_path.exists():
                gh_repo = _gh_repo_from_remote(local_path)
            head = _git(local_path, "rev-parse", "--short=7", "HEAD").strip() if local_path.exists() else ""
            dirty = len([l for l in _git(local_path, "status", "--porcelain").splitlines() if l.strip()])
            commits = _gh_list_commits(gh_repo, per_page=per_page, transform=transform) if gh_repo else []
            if not commits and local_path.exists():
                commits = _git_log_local(local_path, transform=transform, gh_repo=gh_repo)
            tags = _gh_list_tags(gh_repo) if gh_repo else []
            local_in_remote = bool(head and any(c_["sha"] == head for c_ in commits))
            annotated = _annotate_chronological(commits, current_version)
            repos.append({
                "name": display, "gh_repo": gh_repo,
                "gh_url": f"https://github.com/{gh_repo}" if gh_repo else "",
                "local_path": str(local_path),
                "local_exists": local_path.exists(),
                "head_sha": head, "uncommitted": dirty,
                "local_in_remote": local_in_remote,
                "commits": annotated, "tags": tags,
            })
        return render(request, "djangobase/hilfe/versions.html", {
            "aktiv": "versions",
            "current_version": current_version,
            "repos": repos,
            "manual_versions": manual,
            "pakete": _pakete(c["version_pakete"]),
        })
