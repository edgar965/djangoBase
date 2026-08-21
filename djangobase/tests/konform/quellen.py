# -*- coding: utf-8 -*-
u"""Welche Dateien eine Konformitätsprüfung überhaupt ansehen darf.

DER VORFALL, DER DAS NÖTIG MACHTE (assistant, 21.08.2026)
========================================================
Der erste Lauf der Konformitätsprüfungen im Projekt ``assistant`` meldete:

    111 Einbindungen ohne ?v=-Kennung          alle 111 aus ``var/verkauf/``
    60 Vorlagen mit eigenem <html>             56 davon aus ``var/``
    28 selbstgebaute Tabellen ohne Sortierung  23 davon aus Datenordnern

Der Reihe nach waren das: das Chrome-Profil eines Verkaufs-Werkzeugs (Erweiterungen
bringen ihr eigenes HTML mit), ein eingelagertes Fremd-UI (``vendor/ace-step``) und
der Quarantäne-Ordner der Virensuche — JavaScript-Dateien, die die Anwendung
*untersucht*, nicht ausführt.

Von 199 Befunden waren **6 echt**. Nach der Regel „Eigene Prüfwerkzeuge erzeugen
Fehlalarme" (`~/.claude/rules/analysewerkzeuge.md`) ist das die teuerste Sorte
Prüfung: Sie deckt die echten Befunde zu, und wer ihr folgt, ändert fremden Code.

WAS AUSSEN BLEIBT
=================
1. ``TABU`` — Ordner, die nie Projektcode enthalten (Umgebungen, Caches, ``.git``).
2. Das djangoBase-Paket selbst — es prüft sich nicht mit den Regeln der Konsumenten.
3. ``MEDIA_ROOT`` — Django sagt selbst, dass dort Nutzerdaten liegen, kein Code.
4. ``DJANGOBASE_KONFORM_AUS`` — Teilstrings von Pfaden, die das Projekt ausnimmt.
   Eine Entscheidung, die man in ``settings.py`` sieht, statt einer Regel, die
   niemand einhält.

NEBENBEI: LAUFZEIT
==================
``Path.rglob`` steigt in JEDEN Ordner ab und filtert erst danach — im assistant
sind das 84.442 Dateien allein im Mail-Archiv, je Suchmuster und je Testmethode
erneut. Hier wird stattdessen mit ``os.walk`` gelaufen und der Ast **vor** dem
Abstieg abgeschnitten; das Ergebnis liegt danach im Zwischenspeicher. Der Lauf
der Konformitätsprüfungen fiel dadurch von 81 s auf wenige Sekunden.
"""
import os
from functools import lru_cache
from pathlib import Path

from django.conf import settings

__all__ = ["TABU", "dateien", "wurzel", "ausnahmen"]

#: Ordner, in denen nie Projektcode steht.
TABU = {"node_modules", "__pycache__", "venv", ".venv", "pythonVENV", ".git",
        "site-packages", "migrations", ".mypy_cache", ".pytest_cache", ".tox"}

#: Wurzel des djangoBase-Pakets — Konsumenten-Regeln gelten nicht für es selbst.
PAKET = Path(__file__).resolve().parents[2]


def wurzel():
    return Path(getattr(settings, "BASE_DIR", ".")).resolve()


def ausnahmen():
    u"""Die Pfad-Teilstrings aus ``DJANGOBASE_KONFORM_AUS`` (mit ``/``)."""
    roh = getattr(settings, "DJANGOBASE_KONFORM_AUS", ()) or ()
    return tuple(str(t).replace("\\", "/").strip("/") for t in roh if str(t).strip())


def _media():
    u"""``MEDIA_ROOT``, falls er im Projekt liegt — dort stehen Nutzerdaten."""
    roh = getattr(settings, "MEDIA_ROOT", "") or ""
    if not roh:
        return None
    try:
        return Path(str(roh)).resolve()
    except OSError:                                    # pragma: no cover
        return None


def ausgenommen(pfad, aus=None):
    u"""Liegt der Pfad in einem Bereich, den das Projekt ausnimmt?"""
    text = str(pfad).replace("\\", "/")
    for teil in (aus if aus is not None else ausnahmen()):
        if teil and teil in text:
            return True
    return False


@lru_cache(maxsize=64)
def _gesammelt(endungen, basis, aus, media):
    u"""Der eigentliche Lauf — einmal je Kombination, danach aus dem Speicher."""
    treffer = []
    basis_p = Path(basis)
    for ordner, unter, namen in os.walk(basis_p):
        p_ordner = Path(ordner)
        # VOR dem Abstieg abschneiden: Was hier herausfliegt, wird nie betreten.
        unter[:] = [u for u in unter
                    if u not in TABU
                    and not ausgenommen((p_ordner / u).as_posix() + "/", aus)
                    and not (media and (p_ordner / u).resolve() == Path(media))
                    and (p_ordner / u).resolve() != PAKET]
        for name in namen:
            if not name.lower().endswith(endungen):
                continue
            pfad = p_ordner / name
            if ausgenommen(pfad, aus):
                continue
            treffer.append(pfad)
    return tuple(sorted(treffer))


def dateien(*endungen):
    u"""Alle Projektdateien mit diesen Endungen (``".js"``, ``".html"`` …).

    Reihenfolge ist stabil (sortiert), damit Fehlermeldungen zwischen zwei
    Läufen dieselben Beispiele nennen."""
    endungen = tuple(e.lower() if e.startswith(".") else "." + e.lower()
                     for e in endungen)
    media = _media()
    return _gesammelt(endungen, str(wurzel()), ausnahmen(),
                      str(media) if media else "")


def text_von(pfad):
    u"""Dateiinhalt oder ``None`` — eine unlesbare Datei bricht keine Prüfung ab."""
    try:
        return Path(pfad).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
