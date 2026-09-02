# -*- coding: utf-8 -*-
u"""Die Einstellungen des Language-Server-Laufs — gespeichert, prüfbar, abdruckbar.

ANLASS (Edgar, 02.09.2026)
==========================
    „mach eine neue Seite Hilfe – Werkzeug Language Server … das konfigurierbar
     auf Knopfdruck macht … mache beide (basedpyright und pyright), die man
     umschalten kann"

Alles, was der Nutzer auf der Seite einstellt, steht hier als EIN Objekt:
Werkzeug, Prüfmodus, Pfade, Ausschlüsse, Regeln, Anzeigestufe, Deckel,
Zeitlimit. Daraus entsteht die ``pyrightconfig.json`` für den Lauf und die
Einstellungs-Antwort für die LSP-Sitzung — beide aus derselben Quelle, damit
Stapellauf und Sitzung nie verschiedene Dinge prüfen.

Der ``abdruck`` geht in den Ablage-Schlüssel: Ein Ergebnis mit anderen
Einstellungen ist ein anderes Ergebnis (dieselbe Lehre wie
``artefakte-benennen``).

Django-frei. Gespeichert wird als JSON unter dem Ablage-Ordner, nicht im
System-Temp.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

#: (Regel, Vorgabe-Stufe, was sie findet). Die Vorgabe: harte Fehler an,
#: Django-Rauschen aus — ``objects`` am Model und ``import *`` kennt der
#: Server nicht, und jeder Treffer davon wäre ein Fehlalarm.
REGELN = (
    ("reportUndefinedVariable", "error", u"Name, den es nirgends gibt"),
    ("reportCallIssue", "error", u"Aufruf passt nicht zur Signatur"),
    ("reportArgumentType", "error", u"Argument vom falschen Typ"),
    # NICHT ``reportPossiblyUnbound`` wie in der Doku - beide Werkzeuge melden
    # das als „unrecognized setting" (02.09.2026 gemessen); der Schluessel
    # heisst ``reportPossiblyUnboundVariable``.
    ("reportPossiblyUnboundVariable", "error", u"Variable nur auf einem Zweig gesetzt"),
    ("reportMissingImports", "error", u"Import, den es nicht gibt"),
    ("reportUnusedImport", "warning", u"Import ohne Verwendung"),
    ("reportUnusedVariable", "warning", u"Variable ohne Verwendung"),
    ("reportOptionalMemberAccess", "warning", u"Zugriff auf etwas, das None sein kann"),
    ("reportIndexIssue", "warning", u"Index oder Schlüssel passt nicht"),
    ("reportRedeclaration", "warning", u"Name in derselben Datei zweimal definiert"),
    ("reportAttributeAccessIssue", "none",
     u"Attribut, das der Server nicht kennt (Django-Manager, import *)"),
    ("reportSelfClsParameterName", "none", u"self/cls-Namensregel"),
)

STUFEN = ("error", "warning", "information", "none")

#: (Schlüssel, Muster, Vorgabe, Beschriftung). Muster im pyright-Stil,
#: ``**/`` findet sie in jeder Tiefe.
AUSSCHLUESSE = (
    ("venv", ("**/pythonVENV", "**/venv", "**/.venv", "**/env"), True,
     u"virtuelle Umgebungen"),
    ("migrations", ("**/migrations",), True, u"Django-Migrationen"),
    ("cache", ("**/.cache", "**/__pycache__", "**/node_modules"), True,
     u"Zwischenspeicher und node_modules"),
    ("sicherung", ("**/sicherung", "**/backup_*"), True,
     u"Sicherungskopien alter Fassungen"),
    ("tests", ("**/tests", "**/tests_app"), False, u"Tests"),
)


class LsKonfig:
    u"""Die Einstellungen eines Laufs — Vorgaben, Formular, Datei, Abdruck."""

    WERKZEUGE = ("auto", "basedpyright", "pyright")
    MODI = ("off", "basic", "standard", "strict")
    FELDER = ("werkzeug", "modus", "pfade", "ausschluss", "python", "regeln",
              "stufe", "deckel", "stubs", "zeitlimit", "javascript")

    def __init__(self, werte=None):
        vorgaben = self.vorgaben()
        werte = dict(werte or {})
        for feld in self.FELDER:
            setattr(self, feld, werte.get(feld, vorgaben[feld]))
        # Nachgetragene Regeln und Ausschlüsse bekommen ihre Vorgabe, sonst
        # fehlte nach einem Update jede neue Regel still.
        regeln = dict(vorgaben["regeln"])
        regeln.update({k: v for k, v in (self.regeln or {}).items() if v in STUFEN})
        self.regeln = regeln
        ausschluss = dict(vorgaben["ausschluss"])
        ausschluss.update({k: bool(v) for k, v in (self.ausschluss or {}).items()})
        self.ausschluss = ausschluss
        self.pfade = [str(p) for p in (self.pfade or [])]

    @classmethod
    def vorgaben(cls):
        return {
            "werkzeug": "auto",
            "modus": "basic",
            "pfade": [],
            "ausschluss": {k: v for k, _m, v, _l in AUSSCHLUESSE},
            "python": sys.executable,
            "regeln": {r: s for r, s, _t in REGELN},
            "stufe": "warning",
            "deckel": 500,
            "stubs": True,
            "zeitlimit": 300,
            # JavaScript im selben Lauf ueber tsc --checkJs (ls_javascript.py).
            "javascript": True,
        }

    # ── Datei ────────────────────────────────────────────────────────────
    @classmethod
    def laden(cls, pfad):
        try:
            return cls(json.loads(Path(pfad).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return cls()

    def speichern(self, pfad):
        pfad = Path(pfad)
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps(self.als_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8")

    def als_dict(self):
        return {feld: getattr(self, feld) for feld in self.FELDER}

    # ── Formular ─────────────────────────────────────────────────────────
    @classmethod
    def aus_formular(cls, daten, alt=None):
        u"""Werte aus einem POST — Listen über ``getlist``, Häkchen als Name.

        ``alt`` ist die bisherige Konfiguration; sie gilt für alles, was das
        Formular nicht mitschickt (Python-Pfad, Zeitlimit)."""
        alt = alt or cls()
        holen = daten.getlist if hasattr(daten, "getlist") else (
            lambda k: daten.get(k) if isinstance(daten.get(k), list) else
            ([daten[k]] if k in daten else []))
        werte = alt.als_dict()
        werte["werkzeug"] = _wahl(daten.get("werkzeug"), cls.WERKZEUGE, alt.werkzeug)
        werte["modus"] = _wahl(daten.get("modus"), cls.MODI, alt.modus)
        werte["stufe"] = _wahl(daten.get("stufe"), STUFEN[:3], alt.stufe)
        werte["pfade"] = [p for p in holen("pfade") if p]
        werte["ausschluss"] = {k: (k in holen("ausschluss"))
                               for k, _m, _v, _l in AUSSCHLUESSE}
        werte["regeln"] = {r: _wahl(daten.get("regel_" + r), STUFEN, s)
                           for r, s, _t in REGELN}
        werte["stubs"] = bool(holen("stubs"))
        werte["javascript"] = bool(holen("javascript"))
        werte["deckel"] = _zahl(daten.get("deckel"), alt.deckel, 10, 5000)
        werte["zeitlimit"] = _zahl(daten.get("zeitlimit"), alt.zeitlimit, 10, 3600)
        if daten.get("python"):
            werte["python"] = str(daten.get("python")).strip()
        return cls(werte)

    # ── Abdruck ──────────────────────────────────────────────────────────
    def abdruck(self):
        roh = json.dumps(self.als_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.md5(roh.encode("utf-8")).hexdigest()[:10]

    # ── für den Lauf ─────────────────────────────────────────────────────
    def venv(self):
        u"""``(venvPath, venv)`` aus dem Interpreter — oder ``(None, None)``.

        Windows: ``…/pythonVENV/Scripts/python.exe``; sonst ``…/venv/bin/python``.
        Ohne diese Angabe löst der Server die installierten Pakete nicht auf und
        meldet jeden Import als fehlend."""
        p = Path(self.python or sys.executable)
        if p.parent.name.lower() in ("scripts", "bin"):
            venv = p.parent.parent
            return str(venv.parent), venv.name
        return None, None

    def ausschluss_muster(self):
        raus = []
        for schluessel, muster, _v, _l in AUSSCHLUESSE:
            if self.ausschluss.get(schluessel):
                raus.extend(muster)
        return raus

    def als_pyrightconfig(self, wurzel, extra=(), ablage=None):
        u"""Die ``pyrightconfig.json`` für ``-p``.

        ``include``-Pfade müssen RELATIV zum Verzeichnis der Datei stehen —
        pyright verwirft absolute („Ignoring path … because it is not
        relative", 02.09.2026 gemessen: 0 Dateien geprüft), basedpyright nimmt
        beide. Deshalb ``ablage`` (das Verzeichnis der Datei) hier hinein und
        ``relpath``; liegt das Projekt auf einem anderen Laufwerk, bleibt nur
        der absolute Pfad, und dann prüft nur basedpyright."""
        wurzel = Path(wurzel)
        ziele = [wurzel / p for p in self.pfade] or [wurzel]
        include = [self._relativ(z, ablage) for z in ziele]
        # AUCH DIE AUSSCHLUESSE RELATIV ZUR DATEI (02.09.2026): ``**/sicherung``
        # gilt ab dem Verzeichnis der Konfiguration - und das liegt im
        # Ablage-Ordner, nicht ueber dem Projekt. Ohne Praefix traf kein
        # Muster: werkzeug/ mit 1095 statt 491 Dateien, 80 statt 39 s, und
        # beim ersten Lauf die ganze virtuelle Umgebung (8 Minuten, abgebrochen).
        vorsatz = self._relativ(wurzel, ablage) if ablage else ""
        exclude = [(vorsatz + "/" + m) if vorsatz else m for m in self.ausschluss_muster()]
        cfg = {
            "include": include,
            "exclude": exclude,
            "typeCheckingMode": self.modus,
            "extraPaths": [str(wurzel)] + [str(p) for p in extra],
            "useLibraryCodeForTypes": True,
        }
        venv_pfad, venv = self.venv()
        if venv:
            cfg["venvPath"], cfg["venv"] = venv_pfad, venv
        cfg.update(self.regeln)
        return cfg

    def als_lsp_einstellungen(self, wurzel, extra=()):
        u"""Antwort auf ``workspace/configuration`` — je Abschnitt ein dict."""
        cfg = self.als_pyrightconfig(wurzel, extra)
        analyse = {
            "typeCheckingMode": self.modus,
            "extraPaths": cfg["extraPaths"],
            "exclude": cfg["exclude"],
            "useLibraryCodeForTypes": True,
            "diagnosticSeverityOverrides": dict(self.regeln),
            "autoSearchPaths": True,
        }
        python = {"analysis": analyse}
        if cfg.get("venv"):
            python["venvPath"], python["venv"] = cfg["venvPath"], cfg["venv"]
        python["pythonPath"] = self.python
        return {"python": python, "python.analysis": analyse,
                "pyright": {"disableOrganizeImports": True},
                "basedpyright": {"disableOrganizeImports": True}}


    @staticmethod
    def _relativ(pfad, ablage):
        if not ablage:
            return str(pfad)
        try:
            # Schrägstriche: pyright liest include als Muster, und ein
            # Backslash ist darin ein Fluchtzeichen, kein Trenner.
            return os.path.relpath(str(pfad), str(ablage)).replace("\\", "/")
        except ValueError:                                 # anderes Laufwerk
            return str(pfad).replace("\\", "/")


def _wahl(wert, erlaubt, sonst):
    return wert if wert in erlaubt else sonst


def _zahl(wert, sonst, lo, hi):
    try:
        return max(lo, min(hi, int(wert)))
    except (TypeError, ValueError):
        return sonst


__all__ = ["LsKonfig", "REGELN", "STUFEN", "AUSSCHLUESSE"]
