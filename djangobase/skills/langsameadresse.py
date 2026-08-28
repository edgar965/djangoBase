# -*- coding: utf-8 -*-
u"""Langsame Adresse — ``localhost`` in einer Adresse kostet unter Windows Sekunden.

DER FEHLER
==========
::

    OLLAMA_BASE_URL = "http://localhost:11434/v1"

Das sieht aus wie ``127.0.0.1`` und ist es nicht. ``getaddrinfo`` liefert
unter Windows ZUERST die IPv6-Adresse::

    >>> [a[4][0] for a in socket.getaddrinfo('localhost', 11434, ...)]
    ['::1', '127.0.0.1']

Lauscht der Dienst nur auf IPv4 — und das tun die meisten lokal
gestarteten Dienste in der Grundeinstellung — laeuft der erste
Verbindungsversuch in einen Timeout. Erst danach geht es ueber IPv4
weiter.

DIE MESSUNG (28.08.2026, assistant, Ollama auf 11434)
=====================================================
Je fuenf Aufrufe an ``/api/tags``, im Wechsel::

    localhost   min 2.831 ms   Median 2.923 ms
    127.0.0.1   min   777 ms   Median   840 ms
    [::1]       ConnectError nach 3.090 ms

Rund **zwei Sekunden Aufschlag je Verbindung**. Auf einem offenen
Client faellt er nur beim ersten Mal an (2.069 ms, dann 29 ms, dann
45 ms) — wer aber je Aufruf einen neuen Client oeffnet, zahlt ihn jedes
Mal. Genau so war es dort gebaut: dreizehn Stellen, jede mit eigenem
``httpx.Client``. Eine davon (``expand_query``) hatte acht Sekunden
Zeitgrenze, ein Viertel davon ging fuer die Aufloesung drauf.

WARUM ALS WERKZEUG UND NICHT ALS NOTIZ
======================================
Der Aufschlag ist konstant und rund — er sieht nach Last aus, nicht nach
einem Fehler. Er steht in keinem Log, wirft nichts, und die
Erreichbarkeitspruefung daneben war schnell, weil sie zufaellig
``127.0.0.1`` benutzte. Ohne Messung findet das niemand; mit Messung
findet man es einmal und schreibt es auf. Dies ist das Aufschreiben.

WAS GEMELDET WIRD
=================
``//localhost`` in einer Zeichenkette — jedes Schema (``http``,
``https``, ``ws``, ``postgres``).

WAS NICHT GEMELDET WIRD
=======================
* **Kommentare und Docstrings.** Wer den Fall beschreibt, macht ihn
  nicht. (Deshalb liest dieses Werkzeug Python ueber den Syntaxbaum und
  laesst Docstrings ausdruecklich aus — auch diese Datei hier waere
  sonst ihr eigener erster Befund.)
* **``ALLOWED_HOSTS = ['localhost']``** und aehnliche Namenslisten: Das
  ist kein Verbindungsziel, sondern ein Vergleich gegen den
  ``Host``-Kopf einer EINGEHENDEN Anfrage. Dort wird nichts aufgeloest.
  Erkannt am fehlenden ``//``.
* **``CSRF_TRUSTED_ORIGINS = ['http://localhost:8001']``** — dieselbe
  Sorte, nur MIT ``//``, weil eine Herkunft nun einmal so geschrieben
  wird. Beim ersten Lauf in assistant war das einer von zwei Befunden,
  und beide waren falsch. Ausgenommen sind deshalb Zeichenketten in
  Zuweisungen an GROSSGESCHRIEBENE Namen auf ``ORIGINS``, ``HOSTS``
  oder ``IPS`` — Django-Einstellungen fuer EINGEHENDE Anfragen.
* **Tests.** Der zweite Fehlalarm stand in einer Pruefung, die
  ``http://localhost/`` ausdruecklich ABWEIST (Schutz gegen SSRF). Sie
  MUSS die Adresse enthalten. Tests bauen ohnehin keine echten
  Verbindungen auf — was dort steht, kostet keine zwei Sekunden.
* **``0.0.0.0``**: die Adresse, auf der ein Server LAUSCHT — die ist
  richtig so und hat mit der Aufloesung nichts zu tun.
"""
import ast
import re

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["LangsameAdresse"]


class LangsameAdresse(BefundWerkzeug):
    u"""``localhost`` als Verbindungsziel — zwei Sekunden je Verbindung."""

    slug = "langsame-adresse"
    titel = "localhost als Verbindungsziel"
    zweck = ("Findet `http://localhost:…` im Code. Unter Windows loest das "
             "zuerst auf `::1` auf; lauscht der Dienst nur auf IPv4, kostet "
             "jede Verbindung rund zwei Sekunden.")
    befund = ("Gemessen am 28.08.2026 gegen Ollama: 2.923 ms ueber "
              "`localhost`, 840 ms ueber `127.0.0.1` — dreizehn Stellen im "
              "Projekt, jede mit eigenem Client, also jede mit vollem "
              "Aufschlag.")
    abhilfe = ("`127.0.0.1` schreiben. Der Aufschlag steht in keinem Log und "
               "wirft nichts — er sieht nach Last aus.")
    dauer = "unter 1 s"
    kriterium = 0

    anlassfall = Anlassfall(
        {"klient.py": (
            "import httpx\n"
            "\n"
            "BASIS = 'http://localhost:11434'\n"
            "\n"
            "\n"
            "def holen():\n"
            "    return httpx.get(BASIS + '/api/tags')\n"),
         "sauber.py": (
            u'u"""Hier stand frueher http://localhost:11434 — jetzt nicht.\n'
            u'"""\n'
            "import httpx\n"
            "\n"
            "# Nicht http://localhost: das loest zuerst auf ::1 auf.\n"
            "BASIS = 'http://127.0.0.1:11434'\n"
            "ALLOWED_HOSTS = ['localhost', '127.0.0.1']\n"
            "\n"
            "\n"
            "def holen():\n"
            "    return httpx.get(BASIS + '/api/tags')\n")},
        mindestens=1, hoechstens=1, erwartet_in="klient.py",
        warum="Zwei Sekunden je Verbindung, gemessen. `sauber.py` steht "
              "daneben, weil die drei Ausnahmen sonst unbemerkt wegfallen "
              "koennten: der Docstring, der den Fall beschreibt, der "
              "Kommentar daneben, und `ALLOWED_HOSTS` — eine Namensliste "
              "fuer EINGEHENDE Anfragen, wo nichts aufgeloest wird.")

    #: ``//localhost`` mit beliebigem Schema davor. Das ``//`` ist der
    #: Unterschied zwischen einem Verbindungsziel und einem blossen Namen
    #: in einer Liste.
    #:
    #: Der Teil ``(?:[^/@\s]*@)?`` ist NACHGETRAGEN: Ohne ihn fiel
    #: ``postgres://nutzer@localhost:5432/db`` durch — ein
    #: Datenbankzugang mit Benutzernamen in der Adresse, also genau die
    #: Sorte Verbindung, bei der zwei Sekunden am meisten wehtun.
    ZIEL = re.compile(r"//(?:[^/@\s]*@)?localhost\b")

    #: Dateien, die den Fall beschreiben statt ihn zu machen.
    AUSNAHMEN = ("langsameadresse.py",)

    #: Einstellungen fuer EINGEHENDE Anfragen. Was dort steht, wird
    #: verglichen, nicht aufgeloest.
    EINGEHEND = re.compile(r"^[A-Z0-9_]*(ORIGINS|HOSTS|IPS)$")

    def pruefen(self, **_argumente):
        befunde = []
        dateien = 0
        for pfad in self.projektdateien(".py"):
            if pfad.name in self.AUSNAHMEN or self._ist_test(pfad):
                continue
            baum = self._baum(pfad)
            if baum is None:
                continue
            dateien += 1
            befunde += self._aus_baum(baum, self.kurz(pfad))
        for pfad in self.projektdateien(".js"):
            if self._ist_test(pfad):
                continue
            dateien += 1
            befunde += self._aus_text(pfad.read_text(encoding="utf-8",
                                                     errors="replace"),
                                      self.kurz(pfad))
        kopf = ["%d Dateien gelesen" % dateien,
                "%d Verbindungsziele auf `localhost`" % len(befunde)]
        return Befundsatz(self.titel, kopf, befunde)

    @staticmethod
    def _ist_test(pfad):
        u"""Eine Pruefung darf die Adresse nennen, die sie abweist.

        Der Anlass: ``test_meyer_features`` prueft, dass
        ``http://localhost/`` als Ziel ABGELEHNT wird (Schutz gegen
        SSRF). Ohne die Zeichenkette gaebe es die Pruefung nicht.

        Der Ordner wird als GANZER Name verglichen, nicht als Anfang:
        ``any(teil.startswith("test") …)`` haette auch ``testdaten/``
        und ``tester.py`` verschluckt — und die Namenspruefung daneben
        gleich mit, ohne dass ein Fall rot geworden waere. Aufgefallen
        bei der Gegenprobe: die erste Haelfte liess sich entfernen, alle
        Faelle blieben gruen.
        """
        return (pfad.name.startswith("test_")
                or "tests" in pfad.parts
                or "test" in pfad.parts)

    @staticmethod
    def _baum(pfad):
        try:
            return ast.parse(pfad.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            return None

    def _aus_baum(self, baum, name):
        u"""Jede Zeichenkette ausser den Docstrings.

        Kommentare stehen ohnehin nicht im Syntaxbaum — sie fallen also
        von selbst weg.
        """
        raus = []
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.Constant):
                continue
            if not isinstance(knoten.value, str):
                continue
            if knoten in self._docstrings(baum):
                continue
            if knoten in self._eingehend(baum):
                continue
            if not self.ZIEL.search(knoten.value):
                continue
            raus.append(self._befund("%s:%d" % (name, knoten.lineno),
                                     knoten.value))
        return raus

    @staticmethod
    def _docstrings(baum):
        u"""Die Zeichenketten, die als Beschreibung dastehen.

        Einmal je Baum gesammelt und gemerkt: ``ast.walk`` laeuft sonst
        fuer jede Zeichenkette erneut ueber den ganzen Baum.
        """
        gemerkt = getattr(baum, "_docstringknoten", None)
        if gemerkt is not None:
            return gemerkt
        gemerkt = set()
        traeger = (ast.Module, ast.ClassDef, ast.FunctionDef,
                   ast.AsyncFunctionDef)
        for knoten in ast.walk(baum):
            if not isinstance(knoten, traeger):
                continue
            erste = (knoten.body or [None])[0]
            if (isinstance(erste, ast.Expr)
                    and isinstance(erste.value, ast.Constant)
                    and isinstance(erste.value.value, str)):
                gemerkt.add(erste.value)
        baum._docstringknoten = gemerkt
        return gemerkt

    @classmethod
    def _eingehend(cls, baum):
        u"""Zeichenketten in ``ALLOWED_HOSTS`` und Verwandten.

        Django vergleicht sie gegen den Kopf einer EINGEHENDEN Anfrage —
        aufgeloest wird dabei nichts. ``CSRF_TRUSTED_ORIGINS`` traegt
        sogar ein ``//``, weil eine Herkunft so geschrieben wird.
        """
        gemerkt = getattr(baum, "_eingehendknoten", None)
        if gemerkt is not None:
            return gemerkt
        gemerkt = set()
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.Assign):
                continue
            namen = [z.id for z in knoten.targets if isinstance(z, ast.Name)]
            if not any(cls.EINGEHEND.match(n) for n in namen):
                continue
            for teil in ast.walk(knoten.value):
                if isinstance(teil, ast.Constant) and isinstance(teil.value,
                                                                 str):
                    gemerkt.add(teil)
        baum._eingehendknoten = gemerkt
        return gemerkt

    def _aus_text(self, text, name):
        u"""Zeilenweise fuer JavaScript — ohne Zeilenkommentare.

        Grob, aber in die richtige Richtung: Eine echte Adresse in einem
        Kommentar wird uebersehen, ein Kommentar aber nie faelschlich
        gemeldet.
        """
        raus = []
        for nummer, zeile in enumerate(text.splitlines(), 1):
            blank = zeile.strip()
            if blank.startswith(("//", "*", "/*")):
                continue
            if self.ZIEL.search(zeile):
                raus.append(self._befund("%s:%d" % (name, nummer), blank))
        return raus

    @staticmethod
    def _befund(ort, text):
        return Befund(
            ort,
            "Verbindungsziel `localhost`: %s" % text[:70],
            "Unter Windows zuerst `::1`. Lauscht der Dienst nur auf IPv4, "
            "kostet jede Verbindung rund zwei Sekunden — ohne Log, ohne "
            "Fehler, es sieht nach Last aus.",
            Befund.WARNUNG)
