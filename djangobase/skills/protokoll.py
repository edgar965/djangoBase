# -*- coding: utf-8 -*-
u"""Protokoll - geht ein Fehler ins Log oder ins Nichts?

    Kriterium 16: Logging sauber - console.log vermeiden, Server-Logging und den
    rotierenden Logger von djangoBase nutzen, klare Ausnahmen im UI und im
    Server-Exception-Log, wichtige Aktionen mit Zeitstempel vermerken.

WARUM DAS EIN EIGENES WERKZEUG BRAUCHT
======================================
Ein ``console.log`` ist nach dem Neuladen der Seite weg, und niemand sieht es je
- ein Fehler, der nur dort landet, ist nicht passiert. Dasselbe gilt fuer den
Server: ``except Exception: pass`` macht aus einem Absturz eine leere Seite, und
die Ursache steht nirgends.

Gesucht wird deshalb nach dem, was ein Ereignis VERSCHWINDEN laesst:

    1. ``console.*`` in eigenen Browser-Modulen (Fremd-/min-Dateien ausgenommen)
    2. ``print()`` statt Logger - ausser in Skripten und Management-Commands,
       wo die Ausgabe der Zweck ist
    3. Ausnahmen, die stillschweigend verschluckt werden (``pass``, blosses
       ``continue``/``return`` ohne Log)
    4. Ausnahmen, die etwas tun, aber nichts protokollieren
    5. Die Grundeinstellung selbst: rotierender Handler und Zeitstempel im Format

DER ZEITSTEMPEL WIRD NICHT JE AUFRUF GEPRUEFT
=============================================
„Wichtige Aktionen mit Zeitstempel" ist keine Eigenschaft des Aufrufs, sondern
des FORMATS: ``dblog.config`` schreibt ``{asctime} [{levelname}] {name}: …``.
Jeder ``logger.info(...)`` traegt ihn damit von selbst. Geprueft wird also die
Einstellung - alles andere waere Beschaeftigung ohne Aussage.
"""
import ast
import re

from .werkzeug import Ergebnis
from .basis import EigenesWerkzeug

__all__ = ["Protokoll"]


class Protokoll(EigenesWerkzeug):
    slug = "protokoll"
    titel = "Logging: Fehler ins Log statt ins Nichts"
    zweck = ("console.* in eigenen Modulen, print() statt Logger, verschluckte "
             "Ausnahmen — und ob die Logging-Grundeinstellung rotiert und einen "
             "Zeitstempel schreibt.")
    befund = ("Ein Fehler, der nur in der Browser-Konsole steht, ist nach dem "
              "Neuladen weg. Ein `except: pass` macht daraus eine leere Seite "
              "ohne jede Spur.")
    abhilfe = ("Im Browser eine sichtbare Meldung plus Server-Meldung; im Server "
               "`logger.exception(...)`. Grundeinstellung über "
               "`dblog.config(BASE_DIR/'logs')`.")
    dauer = "3–10 s"
    kriterium = 16

    #: Nur diese Konsolen-Aufrufe sind Fundstellen. ``console.error`` bleibt
    #: erlaubt: eine Fehlermeldung im Browser ist richtig - sie darf nur nicht
    #: die EINZIGE Spur sein.
    KONSOLE = re.compile(r"\bconsole\.(log|info|debug|warn|table|dir)\s*\(")
    #: Dateien, die niemand von Hand geschrieben hat.
    FREMD = (".min.js", "htmx", "bootstrap", "jquery", "chart", "vendor")
    #: Dort ist Ausgabe der Zweck, kein Protokoll-Ersatz.
    AUSGABE_ERLAUBT = ("/management/commands/", "/werkzeug/", "/scripts/",
                       "/tools/", "/tests", "conftest.py", "manage.py")
    LOGGER_RUF = re.compile(r"\b(logger|log|logging|self\.log)\b\s*\.\s*"
                            r"(debug|info|warning|warn|error|exception|critical)")
    #: Vermerk am Code fuer einen Block, der bewusst stumm bleibt. Die
    #: Begruendung MUSS dahinterstehen — „# stumm gewollt:" allein zaehlt nicht,
    #: sonst wird der Vermerk zum Schalter, mit dem man jeden Befund abschaltet.
    STUMM_GEWOLLT = re.compile(r"#\s*stumm gewollt:\s*\S+")

    def laufen(self):
        zeilen = []
        zeilen += self._konsole()
        zeilen += self._python()
        zeilen += self._einstellung()
        rang = {"Einstellung": 0, "Ausnahme verschluckt": 1,
                "Ausnahme ohne Log": 2, "print statt Logger": 3, "console.*": 4}
        zeilen.sort(key=lambda z: (rang.get(z["art"], 9), z["datei"]))
        offen = [z for z in zeilen if z["art"] != "console.*"]
        return Ergebnis(
            ["art", "datei", "zeile", "fundstelle", "hinweis"], zeilen,
            "%d Stellen — davon %d serverseitig (die teureren)"
            % (len(zeilen), len(offen)),
            "console.* ist im Browser nicht immer falsch — es darf nur nicht die "
            "einzige Spur eines Fehlers sein. Serverseitig gilt: eine "
            "verschluckte Ausnahme kostet später Stunden.")

    # ------------------------------------------------------------------ Browser

    def _konsole(self):
        aus = []
        for pfad in self.dateien(".js"):
            name = pfad.name.lower()
            if any(t in name for t in self.FREMD) or any(
                    t in pfad.as_posix().lower() for t in self.FREMD):
                continue
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for nr, zeile in enumerate(text.split("\n"), 1):
                nackt = zeile.strip()
                if nackt.startswith(("//", "*", "/*")):
                    continue
                m = self.KONSOLE.search(zeile)
                if m:
                    aus.append({"art": "console.*", "datei": pfad.name, "zeile": nr,
                                "fundstelle": "console.%s(…)" % m.group(1),
                                "hinweis": "im Browser flüchtig — Fehler zusätzlich "
                                           "an den Server melden"})
        return aus

    # ------------------------------------------------------------------ Server

    def _python(self):
        aus = []
        for d in self.dateien():
            if d.baum is None:
                continue
            weich = any(t in "/" + d.name for t in self.AUSGABE_ERLAUBT)
            hat_logger = bool(self.LOGGER_RUF.search(d.text))
            for k in d.knoten(ast.ExceptHandler):
                aus += self._ausnahme(d, k)
            if weich:
                continue
            for k in d.knoten(ast.Call):
                if getattr(k.func, "id", "") == "print":
                    aus.append({"art": "print statt Logger", "datei": d.name,
                                "zeile": k.lineno, "fundstelle": "print(…)",
                                "hinweis": "Logger nutzen — print landet in keiner "
                                           "Datei" + ("" if hat_logger
                                                      else "; Modul hat noch keinen Logger")})
        return aus

    def _ausnahme(self, d, k):
        """Ein except-Block ohne Protokoll - verschluckt oder nur stumm."""
        rumpf = [x for x in k.body
                 if not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant))]
        alle = d.text.split("\n")
        quelle = "\n".join(alle[k.lineno - 1:getattr(k, "end_lineno", k.lineno)])
        # Der Vermerk steht ueblicherweise UEBER dem ``except`` — dort, wo man
        # ihn beim Lesen braucht. Der erste Wurf las erst ab der except-Zeile
        # und fand ihn deshalb nie (17.08.2026). Mitgelesen wird nur der
        # unmittelbar davor stehende, zusammenhaengende Kommentarblock: So kann
        # ein Vermerk nicht auf einen fremden Block abfaerben.
        i = k.lineno - 2
        davor = []
        while i >= 0 and alle[i].strip().startswith("#"):
            davor.insert(0, alle[i])
            i -= 1
        quelle = "\n".join(davor) + "\n" + quelle
        if self.LOGGER_RUF.search(quelle):
            return []
        # Ein `raise` reicht ebenfalls: die Ausnahme geht weiter nach oben und
        # landet dort im Log - sie verschwindet nicht.
        if any(isinstance(x, ast.Raise) for x in ast.walk(k)):
            return []
        # Vermerk im Code: Es gibt Blöcke, die stumm bleiben MÜSSEN — im
        # Protokoll-Middleware selbst (ein Log dort ruft sich im Zweifel
        # rekursiv auf) oder wenn ein Prozess zwischen zwei Zeilen verschwindet.
        # Der Vermerk steht am Code und ist damit nachprüfbar; eine Ausnahmeliste
        # im Werkzeug wäre es nicht (siehe skills2, gleiche Bauform).
        if self.STUMM_GEWOLLT.search(quelle):
            return []
        stumm = all(isinstance(x, (ast.Pass, ast.Continue, ast.Break)) or
                    (isinstance(x, ast.Return) and x.value is None) for x in rumpf)
        art = "Ausnahme verschluckt" if stumm else "Ausnahme ohne Log"
        return [{"art": art, "datei": d.name, "zeile": k.lineno,
                 "fundstelle": "except %s" % self._typname(k.type),
                 "hinweis": ("nichts bleibt übrig — logger.exception(…) setzen"
                             if stumm else
                             "behandelt, aber nicht protokolliert")}]

    @staticmethod
    def _typname(knoten):
        """„except:", „except ValueError", „except (A, B)".

        Der erste Wurf schrieb ``except None`` fuer das nackte ``except:`` —
        richtig gezaehlt, aber unlesbar gemeldet."""
        if knoten is None:
            return ":"                       # nacktes except - faengt auch KeyboardInterrupt
        if isinstance(knoten, ast.Name):
            return knoten.id
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        if isinstance(knoten, ast.Tuple):
            return "(%s)" % ", ".join(getattr(e, "id", None) or getattr(e, "attr", "?")
                                      for e in knoten.elts)
        return "?"

    # ----------------------------------------------------------- Grundeinstellung

    def _einstellung(self):
        """Rotiert das Log, und steht ein Zeitstempel im Format?"""
        from django.conf import settings
        cfg = getattr(settings, "LOGGING", None)
        if not cfg:
            return [{"art": "Einstellung", "datei": "settings.py", "zeile": 0,
                     "fundstelle": "LOGGING fehlt",
                     "hinweis": "dblog.config(BASE_DIR/'logs') setzen — sonst gibt "
                                "es keine Log-Datei"}]
        aus = []
        handler = (cfg.get("handlers") or {}).values()
        if not any("Rotating" in str(h.get("class", "")) for h in handler):
            aus.append({"art": "Einstellung", "datei": "settings.py", "zeile": 0,
                        "fundstelle": "kein rotierender Handler",
                        "hinweis": "djangoBase liefert ihn über dblog.config — "
                                   "sonst wächst die Datei unbegrenzt"})
        formate = " ".join(str(f.get("format", ""))
                           for f in (cfg.get("formatters") or {}).values())
        if formate and "asctime" not in formate:
            aus.append({"art": "Einstellung", "datei": "settings.py", "zeile": 0,
                        "fundstelle": "kein Zeitstempel im Format",
                        "hinweis": "ohne {asctime} ist keine Aktion zeitlich "
                                   "einzuordnen"})
        if not any("error" in str(h.get("filename", "")).lower() for h in handler):
            aus.append({"art": "Einstellung", "datei": "settings.py", "zeile": 0,
                        "fundstelle": "keine eigene Fehlerdatei",
                        "hinweis": "dblog.config schreibt error.log zusätzlich — "
                                   "Ausnahmen gehen sonst im Alltag unter"})
        return aus
