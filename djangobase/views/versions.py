"""Hilfe -> Versionen: Changelog aus GitHub/Git + Umgebung/Pakete.

Repo-Liste, App-Version, Paket-Liste, optionaler Commit-Text-Transform
und Commits-pro-Page kommen aus settings.DJANGOBASE.

Pro Commit wird zusaetzlich ermittelt:
  - is_release / version_label  (Subject matched Release-Marker?)
  - effective_version           (Newest-First-Scan: in welchem Release ist
                                  der Commit gelandet — oder "vX.Y+1-dev"
                                  fuer noch ungebumpte Commits)
  - is_unreleased               (Commit ist neuer als letztes Release)
  - is_current                  (entspricht der laufenden App-Version)

Ausserdem werden Git-Tags geholt + ein "local_in_remote"-Flag berechnet,
das zeigt, ob HEAD bereits gepushed ist. Beides ist optional sichtbar
im Template.
"""
import html
import importlib
import json
import platform
import re
import subprocess
import time
from pathlib import Path

import django
from django.shortcuts import render
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin

_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_GH_CACHE: dict = {}
_GH_TTL_S = 300.0
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_TRANSFORM_CACHE: dict = {}


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
    laedt einmalig und cached. Bei None oder Import-Fehler: identity."""
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
    key = f"commits:{repo}:{per_page}"
    hit = _GH_CACHE.get(key)
    if hit and (time.time() - hit[0]) < _GH_TTL_S:
        return hit[1]
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
    _GH_CACHE[key] = (time.time(), result)
    return result


def _gh_list_tags(repo: str) -> list[dict]:
    """Git-Tags des Repos — Release-Marker."""
    key = f"tags:{repo}"
    hit = _GH_CACHE.get(key)
    if hit and (time.time() - hit[0]) < _GH_TTL_S:
        return hit[1]
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
    _GH_CACHE[key] = (time.time(), result)
    return result


def _git(repo_path, *args, timeout=5):
    try:
        r = subprocess.run(["git", "-C", str(repo_path), *args], capture_output=True,
                           text=True, timeout=timeout, encoding="utf-8", errors="replace",
                           creationflags=_NO_WINDOW)
        if r.returncode == 0:
            return r.stdout
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def _git_log_local(repo_path, n=40, transform=None):
    """Fallback ohne gh: lokales git log als Changelog."""
    out = _git(repo_path, "log", f"-{n}", "--pretty=format:%h\x1f%an\x1f%ad\x1f%s", "--date=short")
    tr = transform or (lambda s: s)
    res = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            sha, an, ad, subj = parts
            m = re.match(r"^(?:v|Version\s+)(\d+\.\d+(?:\.\d+)?)", subj, re.I)
            subj_t = tr(subj)
            res.append({"sha": sha, "sha_full": sha, "subject": subj_t[:240],
                        "version_label": ("v" + m.group(1)) if m else None,
                        "title": subj_t[:240], "body": "", "body_html": "",
                        "author": an, "date": ad,
                        "url": "", "is_release": m is not None})
    return res


def _next_dev_label(current_version: str) -> str:
    """Fuer Commits NEUER als das letzte Release: naechste Minor-Version
    mit '-dev'-Suffix. '0.46' -> 'v0.47-dev'."""
    norm = (current_version or "").lstrip("v").strip()
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", norm)
    if not m:
        return "next-dev"
    major, minor = int(m.group(1)), int(m.group(2))
    return f"v{major}.{minor + 1}-dev"


def _annotate_chronological(commits: list, current_version: str) -> list[dict]:
    """Newest-First-Scan: jedem Commit eine effective_version zuordnen
    (welches Release enthaelt diesen Commit?). Commits ueber dem letzten
    Release sind unreleased-dev.

    Markiert is_current fuer den Commit, der genau current_version traegt.
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


class VersionsView(ZugriffMixin, View):
    def get(self, request):
        if request.GET.get("refresh") == "1":
            _GH_CACHE.clear()
        c = conf()
        base_dir = c["log_verzeichnis"]  # = BASE_DIR-Default
        current_version = c["version"]
        per_page = int(c.get("version_commits_per_page") or 100)
        transform = _resolve_transform(c.get("commit_text_transform"))
        repos = []
        for display, gh_repo, local_dir in c["repos"]:
            local_path = (Path(base_dir) / local_dir).resolve()
            head = _git(local_path, "rev-parse", "--short=7", "HEAD").strip() if local_path.exists() else ""
            dirty = len([l for l in _git(local_path, "status", "--porcelain").splitlines() if l.strip()])
            commits = _gh_list_commits(gh_repo, per_page=per_page, transform=transform) if gh_repo else []
            if not commits and local_path.exists():
                commits = _git_log_local(local_path, transform=transform)
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
            "pakete": _pakete(c["version_pakete"]),
        })
