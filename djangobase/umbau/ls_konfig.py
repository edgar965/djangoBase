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

#: (TS-Nummer, stumm in der Vorgabe, was sie meldet).
#:
#: WARUM ZWEI DAVON IN DER VORGABE STUMM SIND (02.09.2026, gemessen)
#: ================================================================
#: Der erste Lauf über shortlongx meldete 7.593 Befunde bei einem laufenden
#: Programm. 2.925 davon — 38 % — waren ``TS2339``/``TS2551``:
#: ``Property 'value' does not exist on type 'HTMLElement'``. In JavaScript
#: ist ``document.getElementById(x).value`` richtig; TypeScript kennt nur den
#: Rückgabetyp ``HTMLElement`` und will ``HTMLInputElement``. Das ist keine
#: Aussage über den Code, sondern über fehlende Typangaben — und in einem
#: Projekt ohne ``.d.ts`` sind es Tausende.
#:
#: Die anderen bleiben an: Ein unbekannter Name (``TS2304``) oder ein Aufruf
#: mit zwei Argumenten an eine Funktion, die eins nimmt (``TS2554``), ist auch
#: ohne Typen ein Befund.
JS_REGELN = (
    ("TS2339", True, u"Eigenschaft gibt es an diesem Typ nicht (.value an HTMLElement)"),
    ("TS2551", True, u"Eigenschaft fast so geschrieben wie eine vorhandene"),
    ("TS2304", False, u"Name nirgends gefunden"),
    ("TS2307", False, u"Modul nicht gefunden"),
    ("TS2554", False, u"Aufruf mit falscher Argumentzahl"),
    ("TS2345", False, u"Argument vom falschen Typ"),
)

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
              "stufe", "deckel", "stubs", "zeitlimit", "javascript", "js_stumm",
              "rahmen_stumm")

    #: Nur diese Felder bestimmen, WAS gerechnet wird. ``stufe``, ``deckel``,
    #: ``js_stumm`` und ``rahmen_stumm`` bestimmen nur, was von einem fertigen
    #: Ergebnis zu sehen ist — stünden sie im Abdruck, kostete jedes Umschalten
    #: eines Filters einen neuen Lauf (70 s auf shortlongx).
    LAUFFELDER = ("werkzeug", "modus", "pfade", "ausschluss", "python", "regeln",
                  "stubs", "javascript")

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
        # DIE PROJEKTEIGENE LISTE (02.09.2026) steht bewusst NICHT in FELDER:
        # Sie gehört nicht in diese Datei, sondern in ``pruefausschluss.txt``
        # der Projektwurzel (``umbau/ausschlussliste.py``). Hier ist sie nur
        # zur Laufzeit dabei — damit sie in die Muster und in den Abdruck geht.
        self.zusatz = [str(m) for m in (werte.get("zusatz") or [])]

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
            "js_stumm": [r for r, stumm, _t in JS_REGELN if stumm],
            # IN DER VORGABE AN (02.09.2026, gemessen an shortlongx): Ein
            # Projekt, das Namen ueber ein Sammelmodul weiterreicht
            # (``__all__`` aus ``globals()``), bekommt vom Typpruefer JEDEN
            # durchgereichten Namen als „nicht definiert" gemeldet — 514
            # Meldungen, davon 486 ueber Namen, die es nachweislich gibt.
            # Wer keine solchen Module hat, merkt von dem Haken nichts:
            # ``umbau/rahmenmodule.py`` erkennt sie am Quelltext.
            "rahmen_stumm": True,
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
        u"""Was in die ``konfig.json`` gehört — OHNE ``zusatz``.

        ``zusatz`` steht mit Absicht nicht darin: Die Ausschlussliste
        gehört ins Projekt (``pruefausschluss.txt``), nicht in den
        Zwischenspeicher dieses Rechners.

        Wer den GANZEN Zustand braucht — etwa um eine Konfiguration
        weiterzureichen oder abzuwandeln —, nimmt :meth:`alle_werte`.
        Diese Methode hier ist der Dateiinhalt, nicht das Objekt.
        """
        return {feld: getattr(self, feld) for feld in self.FELDER}

    def alle_werte(self):
        u"""Der vollständige Zustand — ``LsKonfig(k.alle_werte())`` ist ``k``.

        DIE FALLE, DIE DAS HIER SCHLIESST (02.09.2026)
        ==============================================
        ``__init__`` NIMMT ``zusatz`` an, ``als_dict()`` gibt es nicht
        heraus. Eine Rundreise über ``LsKonfig(k.als_dict())`` verlor die
        Ausschlussliste des Projekts also still — kein Fehler, keine
        Warnung, nur ein plötzlich viel grösserer Lauf.

        Gemessen an CamTrack, derselbe Zustand zweimal gefahren:

            mit ``alle_werte()``   719 Dateien,  762 Befunde
            mit ``als_dict()``     762 Dateien, 1769 Befunde

        Der ganze Datenordner war wieder dabei. Wer die Zahlen nicht
        nebeneinander legt, hält das für einen echten Anstieg.
        """
        werte = self.als_dict()
        werte["zusatz"] = list(self.zusatz)
        return werte

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
        # `alle_werte()` statt `als_dict()` + Zeile fuer `zusatz`: Es gab
        # hier zwei Stellen mit demselben Wissen, und nur EINE war richtig.
        # Kommt ein weiteres Feld dazu, das nicht in die Datei gehoert,
        # nimmt es diesen Weg von allein mit.
        werte = alt.alle_werte()
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
        werte["js_stumm"] = [r for r, _s, _t in JS_REGELN if r in holen("js_stumm")]
        werte["rahmen_stumm"] = bool(holen("rahmen_stumm"))
        werte["deckel"] = _zahl(daten.get("deckel"), alt.deckel, 10, 5000)
        werte["zeitlimit"] = _zahl(daten.get("zeitlimit"), alt.zeitlimit, 10, 3600)
        if daten.get("python"):
            werte["python"] = str(daten.get("python")).strip()
        return cls(werte)

    # ── Abdruck ──────────────────────────────────────────────────────────
    def abdruck(self):
        werte = {feld: getattr(self, feld) for feld in self.LAUFFELDER}
        if self.zusatz:            # leere Liste = wie bisher, altes Ergebnis bleibt auffindbar
            werte["zusatz"] = list(self.zusatz)
        roh = json.dumps(werte, sort_keys=True, ensure_ascii=False)
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
        u"""Die Haken dieser Seite plus die Liste des Projekts — ohne Dubletten."""
        raus = []
        for schluessel, muster, _v, _l in AUSSCHLUESSE:
            if self.ausschluss.get(schluessel):
                raus.extend(muster)
        for muster in self.zusatz:
            if muster not in raus:
                raus.append(muster)
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
            # JEDER HAUPTAST IST EINE IMPORT-WURZEL (02.09.2026): Skripte in
            # ``werkzeug/`` laufen aus ihrem Ordner heraus und importieren die
            # Nachbarn flach (``import zahl``). Python legt das Skriptverzeichnis
            # in ``sys.path``, pyright nicht — das allein waren 370 Meldungen
            # „Import, den es nicht gibt" über Module, die alle vorhanden sind.
            "extraPaths": ([str(wurzel)] + [str(wurzel / p) for p in self.pfade]
                           + [str(p) for p in extra]),
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


__all__ = ["LsKonfig", "REGELN", "STUFEN", "AUSSCHLUESSE", "JS_REGELN"]
