# -*- coding: utf-8 -*-
u"""Namensvarianten - dasselbe Ding, zwei Schreibweisen.

    Kriterium 7 des Auftrags: „keine abweichenden Namen"

WO DAS WEHTUT
=============
Zwischen Python und JavaScript liegen in einer Django-Anwendung mehrere
Uebersetzungen: Formularfeld -> JSON-Schluessel -> Modellfeld. Heisst dasselbe
Ding dort ``fill_delay``, ``fillDelay`` und ``filldelay``, dann funktioniert
alles - bis jemand eine der drei Stellen umbenennt. Danach ist nichts rot, es
wird nur still ein anderer Wert gerechnet.

In shortlongx hat genau das zwei Parameter gekostet: Einer war seit Tagen
wirksam, aber nicht bedienbar (jedes Speichern setzte ihn auf 0), der andere kam
beim Laden nie durch. Beide Male stimmten die Namen bis auf eine Schreibweise.

WAS DAS WERKZEUG TUT
====================
Es sammelt Bezeichner aus Python (Zuweisungen, Dict-Schluessel, Argumente) und
aus JS/Vorlagen (Objektschluessel, ``data-``-Attribute, ``id=``) und meldet
Namen, die sich NUR in Schreibweise oder Trennzeichen unterscheiden.

Nicht jeder Treffer ist ein Fehler - ``max_tage`` als Python-Feld und
``maxTage`` als JS-Variable koennen absichtlich verschieden heissen. Der Befund
sagt: Diese beiden gehoeren zusammen, sieh nach, ob sie es auch tun.
"""
import ast
import re
from collections import defaultdict

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug2


class Namensvarianten(Werkzeug2):
    slug = "namensvarianten"
    titel = "Dasselbe Ding, zwei Schreibweisen"
    zweck = ("Bezeichner, die sich nur in Groß-/Kleinschreibung oder "
             "Trennzeichen unterscheiden — über Python, JS und Vorlagen hinweg.")
    befund = ("Zwei Parameter waren wirkungslos, weil Formular, JSON und Engine "
              "denselben Wert leicht verschieden schrieben. Nichts wurde rot; es "
              "wurde nur still etwas anderes gerechnet.")
    abhilfe = ("Eine Schreibweise festlegen und die Übersetzungen an den "
               "Schnittstellen einmalig prüfen — dort, wo der Wert die Sprache "
               "wechselt.")
    dauer = "5–15 s"
    kriterium = 7

    #: Zu kurze Namen erzeugen nur Rauschen.
    MIN_LAENGE = 5
    #: Namen, die ueberall vorkommen und nichts aussagen.
    RAUSCHEN = {"value", "values", "index", "result", "results", "config",
                "params", "options", "context", "request", "response"}

    #: DERSELBE Name in zwei Schreibweisen, nicht zwei verwandte Namen - beim
    #: ersten Versuch standen hier ``datenbasis_laden`` und
    #: ``daten_basis_pruefen``, deren Kerne sich unterscheiden (…laden gegen
    #: …pruefen). Verglichen wird der Kern ohne Trennzeichen und Grossschreibung.
    anlassfall = Anlassfall(
        {"konto.py": '''def laden(datenbasis):
    return {"name": datenbasis}


def pruefen(daten_basis):
    return bool(laden(daten_basis))
''',
         "sicht.py": '''def zeigen(datenBasis):
    return str(datenBasis)
'''},
        erwartet_in="daten",
        warum="Kriterium 7: zwei Parameter blieben wirkungslos, weil Formular, "
              "JSON und Engine denselben Wert leicht verschieden schrieben")

    def laufen(self):
        # kern -> name -> {(Datei, Welt)}
        vorkommen = defaultdict(lambda: defaultdict(set))
        for d in self.dateien():
            if d.baum is None:
                continue
            for name, welt in self._python_namen(d):
                self._merken(vorkommen, name, d.name, welt)
        # `frontendquellen()` statt `dateien(".js")`: Sonst zaehlt das
        # Vite-Buendel mit, und `backgroundColor`/`background-color` aus Three.js
        # steht als Projektbefund da (17.08.2026).
        for pfad, kurz in self.frontendquellen().paare(".js", ".html"):
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for name, welt in self._web_namen(text):
                self._merken(vorkommen, name, kurz, welt)

        zeilen = []
        for kern, namen in vorkommen.items():
            if len(namen) < 2:
                continue
            # NUR SCHREIBWEISEN-BRÜCHE, NICHT JEDE GROSSSCHREIBUNG (Korrektur
            # beim ersten Lauf): Ohne diese Bedingung meldete das Werkzeug 1.279
            # Paare - darunter jedes ``TradeSystem``/``tradeSystem``, also die
            # ganz normale Klasse-neben-Instanz. Interessant ist der Bruch
            # zwischen den Welten: mit Trennzeichen (Python) gegen ohne (JS).
            mit_trenner = {n for n in namen if self._hat_trenner(n)}
            ohne_trenner = set(namen) - mit_trenner
            if not (mit_trenner and ohne_trenner):
                continue
            geordnet = sorted(namen.items(), key=lambda x: -len(x[1]))
            dateien = {d for _, stellen in geordnet for d, _w in stellen}
            zeilen.append({
                "kern": kern,
                "varianten": " · ".join(n for n, _ in geordnet[:4]),
                "anzahl": len(namen),
                "bruch": self._bruch(namen),
                "wo": ", ".join(sorted(dateien)[:3]),
            })
        zeilen.sort(key=lambda z: (z["bruch"] != "in einer Sprache",
                                   -z["anzahl"], z["kern"]))
        eine = sum(1 for z in zeilen if z["bruch"] == "in einer Sprache")
        return Ergebnis(
            ["kern", "varianten", "anzahl", "bruch", "wo"], zeilen,
            "%d Namen mit mehreren Schreibweisen — %d davon INNERHALB einer "
            "Sprache (die echten)" % (len(zeilen), eine),
            "Über Sprachgrenzen ist der Unterschied Konvention: Python schreibt "
            "`body_type`, JavaScript `bodyType`, HTML `data-body-type`. "
            "Interessant ist, wo BEIDE Schreibweisen in derselben Sprache stehen.")

    @classmethod
    def _bruch(cls, namen):
        u"""Stehen beide Schreibweisen in DERSELBEN Welt?

        Der Unterschied entscheidet alles. In 3DTools waren von 147 Befunden die
        allermeisten Uebersetzungen ueber eine Grenze — ``job_id`` als
        Python-Bezeichner, ``"jobId"`` als Drahtname fuer JavaScript,
        ``data-job-id`` im Markup. Das ist keine Abweichung, das ist die
        Konvention der jeweiligen Seite; sie anzugleichen hiesse, gegen sie zu
        schreiben (17.08.2026).

        „Welt" ist deshalb nicht die Dateiendung, sondern die ROLLE: Python-Name,
        JavaScript-Name, Markup-Name, Drahtname. Eine Zeichenkette in einer
        Python-Datei ist ein Drahtname — sonst galt ``job_id`` neben ``"jobId"``
        als Bruch „in einer Sprache", obwohl beides in Python-Dateien stand.
        """
        # EIN NAME, DER AUF DEM DRAHT VORKOMMT, IST EIN DRAHTNAME — überall
        # (17.08.2026, 3DTools). `bildexport.js` hält seinen Zustand als
        # `{cropX: …}` und schickt ihn als `{crop_x: …}`; die Gegenseite liest
        # `daten.get('crop_x')`. Beide Schlüssel stehen in JavaScript, also galt
        # das als „in einer Sprache" — dabei ist die eine Schreibweise der
        # INTERNE Zustand und die andere der Vertrag mit dem Server. Wer sie
        # angleicht, ändert das Protokoll.
        #
        # Sobald eine Schreibweise irgendwo als Drahtname gesehen wurde, zählt
        # sie überall als Drahtname. Das waren acht der 24 „echten" Befunde
        # (crop_x/y/w/h, start_time, end_time und zwei weitere).
        drahtnamen = {name for name, stellen in namen.items()
                      if any(w == "Draht" for _d, w in stellen)}
        je_welt = {}
        for name, stellen in namen.items():
            for _datei, welt in stellen:
                if name in drahtnamen:
                    welt = "Draht"
                # Verglichen wird nur innerhalb DERSELBEN Rolle: `MeshData` ist
                # eine Klasse, `mesh_data` eine Variable, `BVHTEXT` eine
                # Konstante. Dass die drei verschieden geschrieben sind, VERLANGT
                # die Sprache — das waren 20 der 37 „echten" Befunde
                # (17.08.2026).
                je_welt.setdefault((welt, cls._rolle(name)), set()).add(name)
        for _schluessel, gesehen in je_welt.items():
            if len({cls._form(n) for n in gesehen}) > 1:
                return "in einer Sprache"
        return "über Grenze (%s)" % ", ".join(
            sorted({w for w, _r in je_welt}))

    @staticmethod
    def _rolle(name):
        """Klasse, Konstante oder Wert — an der Schreibung erkannt."""
        kern = name.strip("_-")
        if not kern:
            return "wert"
        if kern.isupper():
            return "konstante"
        if kern[0].isupper():
            return "klasse"
        return "wert"

    @staticmethod
    def _form(name):
        """`mit_trenner` oder `ohne` — die Schreibform ohne Rollenmarkierung."""
        return "mit" if Namensvarianten._hat_trenner(name) else "ohne"

    @staticmethod
    def _hat_trenner(name):
        u"""Trennzeichen INNERHALB des Namens — nicht am Rand.

        Ein führender Unterstrich sagt „privat", ein Anhang „…-" stammt aus
        einem Datenattribut. Beides ist eine ROLLE, keine Schreibweise. Ohne
        diese Unterscheidung meldete das Werkzeug `abstand · Abstand · ABSTAND ·
        _abstand` als vier Schreibweisen für dasselbe — also die ganz normale
        Reihe Variable/Klasse/Konstante/privates Feld, die jede Sprache so
        verlangt. Das waren in 3DTools über hundert Fehlalarme (17.08.2026).
        """
        return "_" in name.strip("_-") or "-" in name.strip("_-")

    def _merken(self, vorkommen, name, datei, welt):
        if len(name) < self.MIN_LAENGE or name.lower() in self.RAUSCHEN:
            return
        kern = re.sub(r"[^a-z0-9]", "", name.lower())
        if len(kern) < self.MIN_LAENGE:
            return
        vorkommen[kern][name].add((datei, welt))

    @staticmethod
    def _python_namen(d):
        u"""(Name, Welt) — Bezeichner und Drahtnamen getrennt.

        Eine ZEICHENKETTE in Python ist kein Python-Name: ``daten["jobId"]``
        schreibt bewusst so, wie der Empfaenger es liest. Beides in denselben
        Topf zu werfen liess ``job_id · jobId · job-id`` als Bruch „in einer
        Sprache" dastehen, obwohl alle drei Vorkommen in Python-Dateien lagen —
        zwei davon als Drahtnamen fuer JavaScript (17.08.2026).
        """
        module = Namensvarianten._modulnamen(d.baum)
        aus = set()
        for k in ast.walk(d.baum):
            if isinstance(k, ast.Name) and isinstance(k.ctx, ast.Store):
                aus.add((k.id, "Python"))
            elif isinstance(k, ast.arg):
                aus.add((k.arg, "Python"))
            elif isinstance(k, ast.Constant) and isinstance(k.value, str):
                if re.fullmatch(r"[A-Za-z][\w-]{3,40}", k.value):
                    aus.add((k.value, "Draht"))
            elif isinstance(k, ast.Attribute):
                welt = "Fremd" if Namensvarianten._wurzel(k) in module else "Python"
                aus.add((k.attr, welt))
        return aus

    @staticmethod
    def _modulnamen(baum):
        u"""Namen, die in dieser Datei ein importiertes MODUL bezeichnen."""
        aus = set()
        for k in ast.walk(baum):
            if isinstance(k, ast.Import):
                for name in k.names:
                    aus.add(name.asname or name.name.split(".")[0])
        return aus

    @staticmethod
    def _wurzel(knoten):
        """Der Name links vom ersten Punkt: ``os.path.isdir`` -> ``os``."""
        wert = knoten.value
        while isinstance(wert, ast.Attribute):
            wert = wert.value
        return getattr(wert, "id", "")

    @staticmethod
    def _web_namen(text):
        u"""(Name, Welt) — JS-Objektschluessel gegen Markup-Namen.

        ``data-…`` und ``id="…"`` folgen der HTML-Konvention (Bindestrich), ein
        Objektschluessel der von JavaScript (camelCase). Beide in einem Topf
        machten aus jedem ``bulkDeleteBtn``/``bulk-delete-btn`` einen Befund.
        """
        aus = set()
        for m in re.finditer(r"\b([a-zA-Z][\w-]{3,40})\s*:", text):     # Objektschlüssel
            aus.add((m.group(1), "JavaScript"))
        for m in re.finditer(r'\bdata-([\w-]{3,40})=', text):
            aus.add((m.group(1), "Markup"))
        for m in re.finditer(r'\bid="([\w-]{3,40})"', text):
            aus.add((m.group(1), "Markup"))
        return aus
