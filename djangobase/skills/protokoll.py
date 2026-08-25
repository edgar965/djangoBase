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
from .anlassfall import Anlassfall
from .basis import EigenesWerkzeug
from .frontendquellen import Frontendquellen

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
    #: Ein Protokollaufruf im Block. Zwei Schreibweisen sind am 17.08.2026
    #: dazugekommen, weil der Logger in 3DTools beides Mal woanders herkam:
    #:
    #: * ``logging.getLogger('core').exception(…)`` (`bvhtext.py:111`) — kein
    #:   Modulname davor, der Aufruf haengt direkt an der Fabrik. Nach
    #:   ``logging.`` folgt ``getLogger``, nicht eine Stufe.
    #: * ``pipeline_logger.debug(…)`` (`pipelines/werkzeuge.py`) — ein ZWEITER
    #:   Logger im Modul, fuer die Pipeline-Zeilen. ``\blogger`` greift dort
    #:   nicht: Der Unterstrich ist ein Wortzeichen, also gibt es vor „logger"
    #:   keine Wortgrenze. Beide Stellen protokollierten und wurden gemeldet.
    #:
    #: ``(\w*_)?`` verlangt den Unterstrich, damit nicht jedes Wort auf „log"
    #: mitzaehlt: ``dialog.error(…)`` oder ``katalog.info(…)`` bleiben aussen.
    #:
    #: ``\w*`` statt ``\w+`` seit dem 17.08.2026: Mit ``\w+_`` braucht es
    #: mindestens ein Zeichen VOR dem Unterstrich, und damit fiel der haeufigste
    #: Fall durch — ``_log = logging.getLogger('mail')``. Drei Module
    #: (``mail/ai/DailyScan.py``, ``MailKiAnalyzer.py``, ``dav/CardDavImporter.py``)
    #: fuehren ihren Logger so; ihre ordentlich protokollierten Bloecke galten
    #: als stumm. Aufgefallen ist es, weil ``fix-ausnahme`` dort einen Log-Aufruf
    #: setzte und die eigene Gegenprobe danach weiter „stumm" meldete.
    #: ``self\._?log`` deckt dieselbe Schreibweise als Attribut ab.
    LOGGER_RUF = re.compile(
        r"(?:(?<![\w.])(?:\w*_)?(?:logger|logging|log)(?:_\w+)?"
        r"|self\._?log(?:ger)?|getLogger\([^)]*\))"
        r"\s*\.\s*"
        r"(?:debug|info|warning|warn|error|exception|critical)")
    #: Die Methodennamen eines Loggers. Als Menge fuer den Syntaxbaum -
    #: ``LOGGER_RUF`` daneben arbeitet auf dem Text und wird dort
    #: gebraucht, wo kein Baum vorliegt.
    LOGSTUFEN = frozenset(("debug", "info", "warning", "warn", "error",
                           "exception", "critical"))
    #: Vermerk am Code fuer einen Block, der bewusst stumm bleibt. Die
    #: Begruendung MUSS dahinterstehen — „# stumm gewollt:" allein zaehlt nicht,
    #: sonst wird der Vermerk zum Schalter, mit dem man jeden Befund abschaltet.
    STUMM_GEWOLLT = re.compile(r"#\s*stumm gewollt:\s*\S+")
    #: Django-Messages: der Grund landet sichtbar beim Nutzer, nicht im Nichts.
    MELDUNG_AN_NUTZER = re.compile(r"messages\.(error|warning)\s*\(")

    #: Der echte Fall steht oben, darunter die DREI Ausnahmen, die dieses
    #: Werkzeug am 17.08.2026 gelernt hat. `hoechstens=1` haelt sie fest: Jede
    #: davon hat Fehlalarme in dreistelliger Zahl erzeugt, und wer sie beim
    #: naechsten Umbau verliert, sieht nur „mehr Befunde" und haelt das fuer
    #: Gruendlichkeit.
    anlassfall = Anlassfall(
        {"ansichten.py": '''# -*- coding: utf-8 -*-
import json
import logging

from django.http import JsonResponse


def netz_speichern(request):
    """Der echte Fall: antwortet 500 und wirft die Stapelspur weg."""
    try:
        return JsonResponse({"ok": rechnen(request)})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def netz_lesen(request):
    """Ausnahme 1: Ein 4xx IST die Meldung - der Aufrufer ist die Ursache."""
    try:
        daten = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "kein JSON"}, status=400)
    return JsonResponse({"ok": True, "n": len(daten)})


def datei_schreiben(pfad, text):
    """Ausnahme 2: protokolliert - nur nicht ueber eine Modulvariable."""
    try:
        pfad.write_text(text, encoding="utf-8")
    except OSError:
        logging.getLogger("core").exception("schreiben fehlgeschlagen: %s", pfad)
        return False
    return True


def bildrate(video):
    """Ausnahme 2b: protokolliert ueber den ZWEITEN Logger des Moduls."""
    try:
        return messen(video)
    except Exception:                                         # noqa: BLE001
        pipeline_logger.debug("Bildrate nicht lesbar: %s", video, exc_info=True)
        return 30.0


def aufraeumen(pfade):
    """Ausnahme 3: Vermerk am Code, mit Begruendung."""
    for p in pfade:
        try:
            p.unlink()
        # stumm gewollt: Wer gerade verschwunden ist, ist aufgeraeumt.
        except OSError:
            continue


def kleid_holen(request, name):
    """Ausnahme 4: Die Fehlerklasse bringt Text UND Code selbst mit."""
    try:
        return JsonResponse({"kleid": laden(name)})
    except KleiderFehler as e:
        return JsonResponse({"error": e.text}, status=e.kennzahl)
''',
         "tests/pruefung.py": '''# -*- coding: utf-8 -*-
"""Ausnahme 5: In einem Test IST der Fehlertext das Ergebnis."""


def fahren(fall):
    try:
        fall.laufen()
    except Exception as e:                                    # noqa: BLE001
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    return {"ok": True}


def schlucken(fall):
    """Der Gegenfall: hier verschwindet ein Fehlschlag wirklich.

    Steht mit im Anlassfall, damit die Testdatei-Ausnahme nicht zur Freikarte
    wird — dieser Block MUSS gemeldet werden. Deshalb `mindestens=2`.
    """
    try:
        fall.laufen()
    except Exception:                                         # noqa: BLE001
        pass
'''},
        mindestens=2, hoechstens=2,
        # Die LOGGING-Pruefung liest die Einstellungen des Projekts und kennt
        # kein Verzeichnis — im Probelauf zaehlt sie nicht mit.
        ohne_arten=("Einstellung",),
        erwartet_in="antwortet mit 500",
        warum=("3DTools, 17.08.2026: 16 Ansichten antworteten mit 500 und "
               "protokollierten nichts — die Ursache war mit der Antwort weg. "
               "Im selben Lauf entpuppten sich 53 der 149 Befunde als "
               "4xx-Antworten, 14 als Testberichte, vier als Fehlerklasse mit "
               "eigenem Code und einer als `logging.getLogger(…).exception(…)`."))

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
        # `Frontendquellen` statt `dateien(".js")`: Es haelt die Ausschlussliste
        # aller JS-Werkzeuge an einer Stelle UND erkennt erzeugten Code an der
        # Zeilenlaenge. Vorher meldete diese Pruefung in 3DTools 40 Stellen aus
        # zwei Vite-Buendeln (`theatre-app.js`, `studio-app.js`) — Code, den
        # niemand geschrieben hat, und dessen Quelle daneben nochmal
        # (17.08.2026).
        aus = []
        for pfad, kurz in self.frontendquellen().paare(".js"):
            name = pfad.name.lower()
            if any(t in name for t in self.FREMD) or any(
                    t in pfad.as_posix().lower() for t in self.FREMD):
                continue
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            zeilen = text.split("\n")
            # Dieselbe Frage wie in `jsregeln.LauteAusgabe`, deshalb derselbe
            # Massstab: Protokollklassen, Test-/Debug-Laeufer und ein
            # `dauerhaft gewollt` im Dateikopf. Ohne das zaehlte diese Pruefung
            # 24 Stellen aus einem Playwright-Laeufer mit, dessen Ausgabe das
            # Ergebnis IST (17.08.2026).
            if Frontendquellen.ausgabe_gewollt(kurz, zeilen):
                continue
            for nr, zeile in enumerate(zeilen, 1):
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
            weich = (any(t in "/" + d.name for t in self.AUSGABE_ERLAUBT)
                     or self._ist_skript(d.baum))
            hat_logger = bool(self.LOGGER_RUF.search(d.text))
            for k in d.knoten(ast.ExceptHandler):
                aus += self._ausnahme(d, k)
            if weich:
                continue
            for k in d.knoten(ast.Call):
                if getattr(k.func, "id", "") != "print":
                    continue
                # DANEBEN STEHT SCHON EIN LOG-AUFRUF (17.08.2026)
                # ===============================================
                # Zwei Fundstellen im Projekt assistant lauteten:
                #     def _log(self, msg):
                #         logger.info(msg)
                #         if self.progress_cb is None:
                #             print(msg, flush=True)
                # Dieselbe Zeile geht ins Log UND auf die Konsole - das ist kein
                # „print statt Logger", sondern ein Fortschrittsbalken fuer den
                # Aufruf von Hand. Gemeldet wird nur, was NEBEN dem print keinen
                # Log-Aufruf in derselben Funktion hat.
                if self._funktion_loggt(d, k):
                    continue
                aus.append({"art": "print statt Logger", "datei": d.name,
                            "zeile": k.lineno, "fundstelle": "print(…)",
                            "hinweis": "Logger nutzen — print landet in keiner "
                                       "Datei" + ("" if hat_logger
                                                  else "; Modul hat noch keinen Logger")})
        return aus

    @classmethod
    def _funktion_loggt(cls, d, aufruf):
        u"""Steht in derselben Funktion auch ein Logger-Aufruf?

        Gesucht wird die INNERSTE Funktion, die den ``print`` umschliesst, und
        darin nach ``LOGGER_RUF``. Ohne die Eingrenzung auf die Funktion wuerde
        jedes Modul mit irgendeinem Logger jeden ``print`` freigeben.
        """
        zeilen = d.text.split("\n")
        beste = None
        for k in ast.walk(d.baum):
            if not isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            ende = getattr(k, "end_lineno", k.lineno)
            if k.lineno <= aufruf.lineno <= ende:
                if beste is None or k.lineno > beste.lineno:
                    beste = k
        if beste is None:
            return False
        rumpf = "\n".join(zeilen[beste.lineno - 1:
                                 getattr(beste, "end_lineno", beste.lineno)])
        return bool(cls.LOGGER_RUF.search(rumpf))

    @staticmethod
    def _ist_skript(baum):
        u"""Wird diese Datei AUSGEFUEHRT statt importiert? Dann ist Ausgabe Zweck.

        AM CODE erkannt, nicht am Ordner — dieselbe Lehre wie bei den toten
        Modulen („eine Ordnerliste raet und liegt beim naechsten Verzeichnis
        daneben"). Zwei Kennzeichen:

        * ``if __name__ == "__main__":`` auf Modulebene, oder
        * Anweisungen auf Modulebene, die etwas TUN — eine Schleife, ein ``with``,
          ein Aufruf. Import, Konstante, ``def`` und ``class`` zaehlen nicht.

        Der belegte Fall (3DTools, 17.08.2026): ``restart_server.py`` hat keine
        einzige Funktion; die Schleife ueber die Prozesse steht auf Modulebene und
        die drei ``print`` sind ihre Ausgabe. Als „print statt Logger" gemeldet
        waren das drei Fehlalarme von drei.
        """
        for k in baum.body:
            if isinstance(k, ast.If):
                for x in ast.walk(k.test):
                    if isinstance(x, ast.Name) and x.id == "__name__":
                        return True
            if isinstance(k, (ast.For, ast.While, ast.With, ast.AsyncWith,
                              ast.Try)):
                return True
            if isinstance(k, ast.Expr) and isinstance(k.value, ast.Call):
                return True
        return False

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
        # DEM CLIENT GEMELDET ist gemeldet (17.08.2026). Ein Block, der mit
        # einem 4xx antwortet, hat die Ursache benannt — an die Stelle, die sie
        # angeht: `except JSONDecodeError: return JsonResponse({'error':
        # 'Invalid JSON'}, status=400)`. Ein Log daraus ist von aussen beliebig
        # oft ausloesbar und sagt nichts, was der Aufrufer nicht schon weiss.
        #
        # Gemessen in 3DTools: 149 Befunde, davon 53 mit 4xx. Bei einem 5xx
        # bleibt es ein Befund — dort ist die Ursache SERVERSEITIG und mit der
        # Antwort für immer weg (16 Faelle).
        status = self._fehlerstatus(k)
        if status is not None and 400 <= status < 500:
            return []
        if self._eigener_code(k) or self._testbericht(d, k):
            return []
        if self._ueber_helfer(d, k):
            return []
        # DEM NUTZER GEMELDET ist auch gemeldet (17.08.2026). Django-Messages
        # zeigen den Grund auf der naechsten Seite an:
        #   except Exception as exc:
        #       messages.error(request, f'Import fehlgeschlagen: {exc}')
        # Das ist keine verschluckte Ausnahme, sondern der Weg, auf dem der
        # Nutzer sie zu sehen bekommt. Aufgefallen an `steuer_web/views/api.py`,
        # das `fix-ausnahme` deshalb nicht ruhigstellen konnte.
        if self.MELDUNG_AN_NUTZER.search(quelle):
            return []
        stumm = all(isinstance(x, (ast.Pass, ast.Continue, ast.Break)) or
                    (isinstance(x, ast.Return) and x.value is None) for x in rumpf)
        art = "Ausnahme verschluckt" if stumm else "Ausnahme ohne Log"
        hinweis = ("nichts bleibt übrig — logger.exception(…) setzen" if stumm
                   else "behandelt, aber nicht protokolliert")
        if status is not None and status >= 500:
            hinweis = ("antwortet mit %d, protokolliert aber nichts — die "
                       "Ursache ist danach weg" % status)
        return [{"art": art, "datei": d.name, "zeile": k.lineno,
                 "fundstelle": "except %s" % self._typname(k.type),
                 "hinweis": hinweis}]

    @classmethod
    def _ueber_helfer(cls, d, knoten):
        """``return self._fehler("…")`` — die 4xx-Antwort steht eine Ebene tiefer.

        ``_fehlerstatus`` sucht den Statuscode IM Block. Das trifft die
        direkte Schreibweise::

            except ValueError:
                return JsonResponse({"error": "…"}, status=400)

        und nicht die haeufigere, sobald eine Datei mehr als zwei
        Fehlerantworten hat — dann wandert der Aufbau in eine kleine
        Hilfsmethode::

            def _fehler(self, text, code=400):
                return JsonResponse({"ok": False, "error": text}, status=code)
            ...
            except ValueError:
                return self._fehler("mail_id ist keine Zahl")

        Beides sagt dem Nutzer dasselbe. Trotzdem galt nur das erste als
        behandelt: im Projekt assistant standen am 25.08.2026 SIEBZEHN
        Befunde "behandelt, aber nicht protokolliert", und NACH DER
        EINZELPRUEFUNG WAR KEIN EINZIGER ECHT — dreizehn davon riefen so
        einen Helfer, drei reichten die Ausnahme an eine Methode weiter,
        einer wich auf einen zweiten Weg aus.

        Das ist kein neues Zugestaendnis, sondern dieselbe Regel wie
        oben, nur eine Ebene tiefer aufgeloest: Der Helfer muss IM
        SELBEN MODUL stehen und dort nachweislich eine 4xx-Antwort
        bauen. Ein Name allein genuegt nicht - sonst wuerde jede Methode
        mit "fehler" im Namen den Block stillstellen.
        """
        aufrufe = [x for x in ast.walk(knoten) if isinstance(x, ast.Call)]
        if not aufrufe:
            return False
        fest, durchgereicht, protokollierend = cls._helfer(d)
        for ruf in aufrufe:
            name = (ruf.func.attr if isinstance(ruf.func, ast.Attribute)
                    else getattr(ruf.func, "id", ""))
            if name in fest:
                return True
            # Helfer, der den Code DURCHREICHT: dann steht die Zahl beim
            # Aufruf - `self._fehler("Mail nicht gefunden", 404)`.
            if name in durchgereicht and cls._ruft_mit_4xx(ruf,
                                                          durchgereicht[name]):
                return True
            # Die gefangene Ausnahme wird an eine Methode gegeben, die
            # protokolliert. Sie ist damit nicht verschwunden - sie wird
            # nur woanders behandelt.
            if name in protokollierend and cls._gibt_ausnahme_mit(ruf, knoten):
                return True
        return False

    @staticmethod
    def _ruft_mit_4xx(ruf, vorgabe):
        """Steht beim Aufruf ein 4xx - als Wert oder als Vorgabe des Helfers?"""
        for wert in list(ruf.args) + [s.value for s in ruf.keywords]:
            if isinstance(wert, ast.Constant) and isinstance(wert.value, int):
                if 400 <= wert.value < 500:
                    return True
                if wert.value >= 500:
                    return False
        return vorgabe is not None and 400 <= vorgabe < 500

    @staticmethod
    def _gibt_ausnahme_mit(ruf, knoten):
        """Wandert die gefangene Ausnahme als Argument in den Aufruf?"""
        if not knoten.name:
            return False
        for wert in list(ruf.args) + [s.value for s in ruf.keywords]:
            for teil in ast.walk(wert):
                if isinstance(teil, ast.Name) and teil.id == knoten.name:
                    return True
        return False

    @classmethod
    def _helfer(cls, d):
        """Die Hilfsmethoden dieses Moduls, in drei Gruppen.

        ``(fest, durchgereicht, protokollierend)``:

        * **fest** - baut eine Antwort mit fest verdrahtetem 4xx.
        * **durchgereicht** - Name -> Vorgabewert des Status-Parameters
          (oder ``None``). Der eigentliche Code steht beim Aufruf.
        * **protokollierend** - schreibt selbst ins Log. Wer die
          gefangene Ausnahme dorthin gibt, hat sie nicht verschluckt.

        Je Datei einmal ermittelt und gemerkt - ``_ausnahme`` fragt sonst
        fuer jeden except-Block erneut den ganzen Syntaxbaum ab.
        """
        gemerkt = getattr(d, "_protokoll_helfer", None)
        if gemerkt is not None:
            return gemerkt
        fest, durchgereicht, protokollierend = set(), {}, set()
        try:
            baum = d.baum
        except Exception:
            baum = None
        if baum is not None:
            for x in ast.walk(baum):
                if not isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                status = cls._fehlerstatus(x)
                if status is not None and 400 <= status < 500:
                    fest.add(x.name)
                elif cls._status_durchgereicht(x):
                    durchgereicht[x.name] = cls._vorgabe_status(x)
                if cls._protokolliert(x):
                    protokollierend.add(x.name)
        ergebnis = (fest, durchgereicht, protokollierend)
        try:
            d._protokoll_helfer = ergebnis
        except Exception:
            # stumm gewollt: Der Merkzettel ist Beschleunigung, kein
            # Ergebnis. Laesst die Quelldatei kein Attribut zu, wird
            # eben jedes Mal neu gerechnet.
            pass
        return ergebnis

    @staticmethod
    def _status_durchgereicht(fn):
        """``status=status`` - der Code kommt von aussen, nicht aus dem Code."""
        namen = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
        for x in ast.walk(fn):
            if not isinstance(x, ast.Call):
                continue
            for s in x.keywords:
                if s.arg == "status" and isinstance(s.value, ast.Name):
                    if s.value.id in namen:
                        return True
        return False

    @staticmethod
    def _vorgabe_status(fn):
        """Vorgabewert des ``status``-Parameters - oder ``None``."""
        stellen = fn.args.args + fn.args.kwonlyargs
        vorgaben = ([None] * (len(fn.args.args) - len(fn.args.defaults))
                    + list(fn.args.defaults)
                    + list(fn.args.kw_defaults))
        for arg, vorgabe in zip(stellen, vorgaben):
            if arg.arg not in ("status", "code"):
                continue
            if isinstance(vorgabe, ast.Constant) and isinstance(vorgabe.value, int):
                return vorgabe.value
        return None

    @classmethod
    def _protokolliert(cls, fn):
        """Schreibt diese Funktion selbst ins Log?"""
        for x in ast.walk(fn):
            if not isinstance(x, ast.Call) or not isinstance(x.func, ast.Attribute):
                continue
            if x.func.attr not in cls.LOGSTUFEN:
                continue
            wurzel = x.func.value
            name = (getattr(wurzel, "id", "") or getattr(wurzel, "attr", ""))
            if "log" in name.lower():
                return True
        return False


    @staticmethod
    def _eigener_code(knoten):
        """``status=e.kennzahl`` — die Fehlerklasse bringt ihren Code selbst mit.

        Das Hausmuster dahinter ist eine eigene Fehlerklasse mit Text UND Code
        (``DienstFehler``, ``KleiderFehler``, ``BvhFehler``: ``VORGABE = 400``).
        Der Block daneben ist genau der Fall, den ``_fehlerstatus`` schon
        durchlaesst — nur steht die Zahl in der Ausnahme statt in der Zeile:

            except KleiderFehler as e:
                return JsonResponse({"error": e.text}, status=e.kennzahl)

        Vier solche Ansichten waren in 3DTools als „behandelt, aber nicht
        protokolliert" gemeldet (17.08.2026), obwohl sie die vollstaendige
        Meldung an den Aufrufer geben. Bedingung ist deshalb doppelt: Der Code
        muss von der GEFANGENEN Ausnahme kommen, und die darf nicht
        ``Exception`` sein — bei einem unerwarteten Fehler ist die Ursache
        serverseitig und ein Log unverzichtbar.
        """
        if knoten.name is None or knoten.type is None:
            return False
        if Protokoll._typname(knoten.type) in ("Exception", "BaseException", ":"):
            return False
        for k in ast.walk(knoten):
            if not isinstance(k, ast.Call):
                continue
            for s in k.keywords:
                if s.arg != "status" or not isinstance(s.value, ast.Attribute):
                    continue
                if getattr(s.value.value, "id", None) == knoten.name:
                    return True
        return False

    def _testbericht(self, d, knoten):
        """In einer Testdatei IST der Fehlertext das Ergebnis.

        ``AUSGABE_ERLAUBT`` galt bisher nur fuer ``print`` — bei den Ausnahmen
        hat das 14 Stellen der Testsuite von 3DTools gemeldet (17.08.2026). Dort
        gehoert der Fehler in den Bericht, nicht ins Log:

            except Exception as e:
                return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}

        Ein Log daneben schriebe jeden roten Test doppelt und niemand liest es;
        der Bericht steht in der Oberflaeche.

        Die Bedingung ist nicht „liegt unter tests/" allein: Der Fehler muss
        WEITERGEGEBEN werden — sein Name kommt im Rumpf vor, oder es steht eine
        Zusicherung darin (``self.assertNotIn(…, str(e))``). Ein ``except: pass``
        in einem Test bleibt ein Befund, denn das verschluckt einen Fehlschlag.
        """
        if not any(t in "/" + d.name for t in self.AUSGABE_ERLAUBT):
            return False
        for k in ast.walk(knoten):
            if (knoten.name and isinstance(k, ast.Name)
                    and k.id == knoten.name):
                return True
            if (isinstance(k, ast.Call) and isinstance(k.func, ast.Attribute)
                    and k.func.attr.startswith("assert")):
                return True
        return False

    #: Antwortklassen, die ihren Statuscode im Namen tragen.
    ANTWORTKLASSEN = {"HttpResponseNotFound": 404, "HttpResponseForbidden": 403,
                      "HttpResponseBadRequest": 400, "HttpResponseGone": 410,
                      "HttpResponseServerError": 500,
                      "HttpResponseNotAllowed": 405}

    @classmethod
    def _fehlerstatus(cls, knoten):
        """Statuscode der Antwort, die dieser Block liefert — oder None."""
        for k in ast.walk(knoten):
            if not isinstance(k, ast.Call):
                continue
            for s in k.keywords:
                if s.arg == "status" and isinstance(s.value, ast.Constant):
                    if isinstance(s.value.value, int):
                        return s.value.value
            name = (k.func.attr if isinstance(k.func, ast.Attribute)
                    else getattr(k.func, "id", ""))
            if name in cls.ANTWORTKLASSEN:
                return cls.ANTWORTKLASSEN[name]
        return None

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
