# -*- coding: utf-8 -*-
u"""Der Werkzeugkatalog als Testfall - damit niemand nachbaut, was es gibt.

WARUM ES DIESEN TEST GIBT (25.08.2026)
======================================
Ein Durchgang durch die Skills-Befunde im Projekt assistant meldete 174
tote Importe. Statt nachzusehen, WAS DER WERKZEUGKASTEN DAFUER SCHON
HAT, entstanden zwei neue Dateien im Projekt: ein Pruefer und ein
Entferner, zusammen rund 300 Zeilen - beide mit denselben vier
Sicherungen, die ``skills/fix_importe.ImportFixer`` seit dem 17.08.2026
mitbringt. Der vorhandene Fixer war dabei GRUENDLICHER: Nach dem
Nachbau fand er noch fuenfundvierzig weitere Stellen.

Der Katalog stand die ganze Zeit unter Hilfe -> Skills. Er wurde nur
nicht gelesen. Ein Verzeichnis, das man aufschlagen KANN, wird nicht
aufgeschlagen - ein Test, der bei jedem Lauf durchlaeuft, schon.

WAS DER TEST TUT
================
1. Er DRUCKT den vollstaendigen Katalog: jedes Werkzeug, jeder Fixer,
   mit Kennung und Zweck. Das steht damit in jedem Testbericht, den
   jemand liest - ohne dass er danach suchen muesste.
2. Er MELDET NACHBAUTEN: eine Projektdatei, deren Name auf die Kennung
   eines vorhandenen Werkzeugs passt, ist mit grosser Wahrscheinlichkeit
   genau das - eine zweite Fassung von etwas, das es gibt.

Punkt 2 schlaegt fehl statt nur zu warnen. Das ist Absicht: Eine
Warnung haette denselben Weg genommen wie der Katalog selbst.

WENN DER NACHBAU BEABSICHTIGT IST
=================================
Es gibt gute Gruende fuer eine eigene Fassung - etwa, wenn das
Projektwerkzeug etwas kann, das dem allgemeinen fehlt. Dann gehoert der
Dateiname in die Ausnahmeliste, und zwar MIT Begruendung::

    DJANGOBASE["werkzeugkatalog"] = {
        "eigene": {
            "tote_importe_teilweise.py":
                "entfernt EINZELNE Namen aus einer Sammelzeile — "
                "ImportFixer nimmt nur ganze Anweisungen",
        },
    }

Ein Eintrag ohne Begruendung zaehlt nicht: sonst wird die Liste zu dem
Schalter, mit dem man den Test abstellt.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

__all__ = ["GrundtestWerkzeugkatalog", "katalog", "nachbauten"]

#: Verzeichnisse, in denen ein Projekt seine eigenen Werkzeuge ablegt.
WERKZEUGORTE = ("werkzeug", "werkzeuge", "tools", "scripts", "skripte")

#: Ordner unter den Werkzeugorten, die NICHT geprueft werden.
#: ``sicherung`` sind eingefrorene Kopien, ``befunde`` sind Ausgaben,
#: und ``aufteilen``/``gegenprobe`` sind Vergleichslaeufe gegen alten
#: Quelltext - alles keine Nachbauten.
NICHT_PRUEFEN = ("sicherung", "backup", "befunde", "aufteilen", "sabotage",
                 "__pycache__", "gegenprobe")


def katalog():
    u"""``[(Kennung, Titel, Zweck, Bauform), …]`` - alles, was es gibt."""
    from djangobase import skills

    raus = []
    for werkzeug in skills.werkzeuge():
        raus.append((werkzeug.slug, werkzeug.titel,
                     getattr(werkzeug, "zweck", ""), "Werkzeug"))
    for fixer in _fixer():
        raus.append((fixer.slug, fixer.titel,
                     getattr(fixer, "tut", ""), "Fixer"))
    return sorted(raus)


def _fixer():
    from djangobase import skills

    for name in ("fixer_alle", "fixers", "FIXER", "alle_fixer"):
        holen = getattr(skills, name, None)
        if callable(holen):
            return list(holen())
        if isinstance(holen, (list, tuple)):
            return list(holen)
    # Kein Sammel-Einstieg: die Klassen aus dem Paket zusammensuchen.
    from djangobase.skills.fixer import Fixer

    gefunden = []
    for wert in vars(skills).values():
        if (isinstance(wert, type) and issubclass(wert, Fixer)
                and wert is not Fixer and getattr(wert, "slug", None)):
            gefunden.append(wert)
    return gefunden


def _wortformen(kennung):
    u"""``tote-importe`` -> ``{tote_importe, toteimporte, tote-importe}``."""
    kern = kennung.strip().lower()
    return {kern, kern.replace("-", "_"), kern.replace("-", "")}


def nachbauten(wurzel=None):
    u"""``[(Datei, Kennung, Titel), …]`` - Projektdateien wie ein Werkzeug."""
    wurzel = Path(wurzel or getattr(settings, "BASE_DIR", "."))
    erlaubt = _ausnahmen()
    bekannt = [(k, t) for k, t, _z, _b in katalog()]

    gefunden = []
    for ort in WERKZEUGORTE:
        ordner = wurzel / ort
        if not ordner.is_dir():
            continue
        for datei in ordner.rglob("*.py"):
            wie = datei.relative_to(wurzel).as_posix()
            if any(teil in wie for teil in NICHT_PRUEFEN):
                continue
            if datei.name in erlaubt:
                continue
            stamm = re.sub(r"\.py$", "", datei.name).lower()
            for kennung, titel in bekannt:
                if any(form and form in stamm for form in _wortformen(kennung)):
                    gefunden.append((wie, kennung, titel))
                    break
    return gefunden


def _ausnahmen():
    u"""Dateinamen mit Begruendung - ohne Begruendung zaehlen sie nicht."""
    cfg = (getattr(settings, "DJANGOBASE", {}) or {}).get("werkzeugkatalog") or {}
    eigen = cfg.get("eigene") or {}
    return {name for name, grund in eigen.items() if str(grund).strip()}


class GrundtestWerkzeugkatalog(SimpleTestCase):
    u"""Steht der Katalog im Bericht - und baut das Projekt nichts nach?"""

    def test_katalog_steht_im_bericht(self):
        u"""Druckt jedes Werkzeug. Kein Urteil - nur Sichtbarkeit."""
        alles = katalog()
        self.assertTrue(alles, "Der Werkzeugkasten ist leer - das kann nicht "
                               "stimmen; laeuft djangobase.skills?")
        zeilen = ["", "=" * 78,
                  "WERKZEUGKASTEN (Hilfe -> Skills): %d Eintraege" % len(alles),
                  "Bevor du ein eigenes Pruefwerkzeug baust: steht es hier "
                  "schon?", "=" * 78]
        for kennung, titel, zweck, bauform in alles:
            zeilen.append("%-9s %-26s %s" % (bauform, kennung, titel))
            if zweck:
                zeilen.append("%-9s %-26s %.72s" % ("", "", zweck))
        print("\n".join(zeilen))

    def test_projekt_baut_nichts_nach(self):
        u"""Eine Projektdatei, die heisst wie ein Werkzeug, IST meist eins."""
        doppelt = nachbauten()
        if not doppelt:
            return
        meldung = ["%d Projektdatei(en) tragen den Namen eines vorhandenen "
                   "Werkzeugs:" % len(doppelt), ""]
        for wie, kennung, titel in doppelt:
            meldung.append("   %s" % wie)
            meldung.append("      -> es gibt bereits: %s (%s)"
                           % (kennung, titel))
        meldung += [
            "",
            "Pruefe, ob das vorhandene Werkzeug reicht - meist tut es das,",
            "und es bringt Sicherung und Netz schon mit. Ist die eigene",
            "Fassung noetig, trage sie MIT BEGRUENDUNG ein:",
            "",
            '    DJANGOBASE["werkzeugkatalog"] = {"eigene": {',
            '        "<dateiname>.py": "<warum das vorhandene nicht reicht>",',
            "    }}",
        ]
        self.fail("\n".join(meldung))
