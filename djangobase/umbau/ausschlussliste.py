# -*- coding: utf-8 -*-
u"""Die Ausschlussliste des Projekts — gesetzt in djangoBase, gespeichert im Projekt.

DIE ANSAGE (Edgar, 02.09.2026)
==============================
    „mach eine Exklusionsliste, die soll in djangoBase gesetzt werden können,
     aber im Oberprojekt gespeichert werden"

WARUM EINE DATEI IM OBERPROJEKT
===============================
Es gab bisher drei Orte für dieselbe Frage — und keiner davon konnte beides:

* ``skills/werkzeug.AUSGESCHLOSSEN`` steht in djangoBase und gilt damit in
  ALLEN sechs Projekten gleichzeitig. Was nur shortlongx ausschließen will,
  gehört nicht dorthin.
* ``DJANGOBASE["skills_ignorieren"]`` liegt richtig (im Projekt), ist aber
  ``settings.py`` — eine Seite schreibt keine Einstellungsdatei um.
* ``.cache/umbau/languageserver/konfig.json`` ist über die Seite schreibbar,
  liegt aber im Zwischenspeicher: nicht im Repo, weg beim ersten Aufräumen,
  auf keinem zweiten Rechner vorhanden.

Deshalb eine eigene Datei in der Projektwurzel, neben ``.gitignore``:
``pruefausschluss.txt``. Sie wird mit dem Projekt versioniert, ist im Diff
lesbar, verträgt Kommentare — und die Seite in djangoBase schreibt sie.

DAS FORMAT
==========
Ein Muster je Zeile, ``#`` beginnt einen Kommentar::

    # fremder Code
    sicherung            → wirkt als **/sicherung, in jeder Tiefe
    werkzeug/netz_*.py   → genau dort, Glob wie in .gitignore
    **/*.min.js          → Muster im pyright-Stil, wird durchgereicht

Zwei Leser mit verschiedenem Bedarf greifen darauf zu:

* :meth:`muster` — Glob-Muster für ``pyrightconfig.json`` und ``jsconfig.json``
  (Language Server). Ein nackter Name wird dort zu ``**/<name>``.
* :meth:`namen` — nur die nackten Verzeichnisnamen, für
  ``skills.Werkzeug.ausgeschlossen()``: Die Prüfwerkzeuge vergleichen
  Verzeichnisnamen, sie können mit Globs nichts anfangen. Ein Muster mit ``/``
  oder ``*`` fällt dort still heraus — das ist kein Fehler, sondern die Grenze
  des Verbrauchers, und die Seite sagt es dazu.

Django-frei; kein Verbraucher muss die Datei kennen (fehlt sie, ist die Liste
leer und alles bleibt, wie es war).
"""
import hashlib
from pathlib import Path

__all__ = ["Ausschlussliste"]

#: Zeichen, an denen ein Glob-Muster erkennbar ist.
GLOB = "*?["

KOPF = u"""# Ausschlussliste dieses Projekts — was KEIN Prüfwerkzeug ansehen soll.
#
# Ein Muster je Zeile, '#' ist ein Kommentar. Gepflegt wird die Datei über
# Hilfe → Werkzeug Language Server; sie gehört ins Repository.
#
#   sicherung            ein Name ohne Schrägstrich gilt in jeder Tiefe
#   werkzeug/netz_*.py   ein Pfad gilt ab der Projektwurzel
#   **/*.min.js          Glob-Muster werden durchgereicht
#
# Nackte Namen wirken zusätzlich in den Werkzeugen unter Hilfe → Skills;
# Muster mit Schrägstrich oder Stern gelten nur für den Language Server.
"""


class Ausschlussliste:
    u"""Die Datei ``pruefausschluss.txt`` in der Projektwurzel — lesen, prüfen, schreiben."""

    DATEI = "pruefausschluss.txt"
    #: Deckel gegen ein versehentlich eingefügtes Protokoll im Textfeld.
    HOECHSTENS = 500

    #: ``pfad -> (mtime, groesse, text)``. ``ausgeschlossen()`` fragt je
    #: Prüfwerkzeug und Datei nach; ohne Merker wäre das ein Dateizugriff je
    #: Aufruf.
    _gelesen = {}

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel)

    # ── Ort ──────────────────────────────────────────────────────────────
    def pfad(self):
        return self.wurzel / self.DATEI

    def vorhanden(self):
        return self.pfad().is_file()

    # ── lesen ────────────────────────────────────────────────────────────
    def text(self):
        u"""Der rohe Inhalt — für das Textfeld. Fehlt die Datei: die Vorlage."""
        roh = self._roh()
        return roh if roh is not None else KOPF

    def _roh(self):
        pfad = self.pfad()
        try:
            stat = pfad.stat()
        except OSError:
            return None
        merker = self._gelesen.get(str(pfad))
        if merker and merker[0] == stat.st_mtime and merker[1] == stat.st_size:
            return merker[2]
        try:
            inhalt = pfad.read_text(encoding="utf-8")
        except OSError:
            return None
        self._gelesen[str(pfad)] = (stat.st_mtime, stat.st_size, inhalt)
        return inhalt

    def eintraege(self):
        u"""``[(nummer, roh, muster, grund)]`` — Kommentare und Leerzeilen fehlen.

        ``muster`` ist ``None``, wenn die Zeile verworfen wurde; ``grund`` sagt
        dann, warum. Verworfen wird nichts stillschweigend: Die Zeile bleibt in
        der Datei stehen, die Seite zeigt den Grund daneben."""
        raus = []
        for nr, zeile in enumerate((self._roh() or "").splitlines(), start=1):
            roh = zeile.strip()
            if not roh or roh.startswith("#"):
                continue
            muster, grund = self._deuten(roh)
            raus.append((nr, roh, muster, grund))
        return raus

    def muster(self):
        u"""Glob-Muster für pyright und tsc — nackte Namen als ``**/<name>``."""
        raus = []
        for _nr, _roh, muster, _grund in self.eintraege():
            if muster and muster not in raus:
                raus.append(muster)
        return raus

    def namen(self):
        u"""Nur die nackten Verzeichnis-/Dateinamen — für die Skills-Werkzeuge."""
        raus = []
        for _nr, roh, muster, _grund in self.eintraege():
            if muster and "/" not in roh and not any(z in roh for z in GLOB):
                raus.append(roh)
        return raus

    def fehler(self):
        return [(nr, roh, grund) for nr, roh, muster, grund in self.eintraege()
                if muster is None]

    def abdruck(self):
        u"""Über den Ablage-Schlüssel: andere Liste, anderes Ergebnis."""
        roh = u"\n".join(self.muster())
        return hashlib.md5(roh.encode("utf-8")).hexdigest()[:10]

    # ── schreiben ────────────────────────────────────────────────────────
    def speichern(self, text):
        u"""Schreibt den Text unverändert (nur Zeilenenden vereinheitlicht).

        Zurück kommt ``(anzahl_muster, fehler)``. Bewusst wird nichts
        weggeputzt: Wer eine Zeile schreibt, die nicht trägt, soll sie
        wiederfinden und den Grund daneben lesen — eine Liste, die beim
        Speichern heimlich schrumpft, ist schlimmer als eine mit einem Hinweis."""
        zeilen = [z.rstrip() for z in (text or "").replace("\r\n", "\n")
                  .replace("\r", "\n").split("\n")]
        if len(zeilen) > self.HOECHSTENS:
            zeilen = zeilen[:self.HOECHSTENS]
        while zeilen and not zeilen[-1]:
            zeilen.pop()
        pfad = self.pfad()
        inhalt = u"\n".join(zeilen) + (u"\n" if zeilen else u"")
        # newline="" : LF auch unter Windows, damit die Datei im Repo auf
        # jedem Rechner gleich aussieht.
        with open(str(pfad), "w", encoding="utf-8", newline="") as datei:
            datei.write(inhalt)
        self._gelesen.pop(str(pfad), None)
        return len(self.muster()), self.fehler()

    # ── deuten ───────────────────────────────────────────────────────────
    @staticmethod
    def _deuten(roh):
        u"""``(muster, grund)`` — eine Zeile als Glob-Muster, oder der Grund dagegen."""
        wert = roh.replace("\\", "/").strip()
        while wert.startswith("./"):
            wert = wert[2:]
        wert = wert.rstrip("/")
        if not wert:
            return None, u"leer"
        if wert.startswith("/") or (len(wert) > 1 and wert[1] == ":"):
            return None, u"absoluter Pfad — Muster gelten ab der Projektwurzel"
        if ".." in wert.split("/"):
            return None, u"„..“ führt aus dem Projekt heraus"
        if "/" not in wert and not any(z in wert for z in GLOB):
            return "**/" + wert, ""
        return wert, ""
