# -*- coding: utf-8 -*-
u"""Schreibrouten - eine Ansicht, die loescht oder schreibt und GET beantwortet.

DER BEFUND (3DTools, 17.08.2026) - ZWEIMAL AN EINEM TAG
=======================================================
1. ``core/api/auftraege.delete_job`` loeschte **auf ein GET hin** den Auftrag
   samt seinen Dateien. In ``processed.html`` stand dafuer

       <a href="{% url 'delete_job' job.id %}"
          onclick="return confirm('Delete …?')">

   Das ``confirm`` schuetzt genau einen Fall: den menschlichen Klick. Ein
   Prefetch des Browsers, eine Link-Vorschau, ein Lesezeichen oder ein
   ``<img src>`` auf einer fremden Seite haetten gereicht.

2. ``core/api/bibliothek.scan_bvh_files`` las auf GET 7.067 BVH-Koepfe und
   schrieb die Bibliothek neu - 35 Abfragen je Aufruf, ausloesbar von aussen.

WARUM DIE MIDDLEWARE DAS NICHT FAENGT
=====================================
Die Ursprungspruefung (``GleicherUrsprung``, ``CsrfViewMiddleware``) prueft
schreibende METHODEN. GET gehoert bewusst nicht dazu - sonst wuerde jedes Bild
und jede Verknuepfung geprueft. Schutz gibt es hier nur ueber die Methode
selbst: ``@require_POST``.

WARUM DER NAME NICHT REICHT
===========================
Der erste Versuch war ein Namensfilter (``delete|save|scan|…``). Er meldete 11
Routen, davon **9 Fehlalarme**: ``cloth_preset_list`` und
``charmorph_presets`` trafen auf ``reset`` in „**preset**s", und
``photo_analysis_reprocess`` ist eine reine Weiterleitung. Die zwei echten
Faelle waren auf anderem Weg gefunden. Gemeldet wird deshalb nur, was im
Rumpf der Ansicht WIRKLICH steht.

BEKANNTE GRENZE, ausdruecklich
==============================
Gesucht wird im DIREKTEN Rumpf, ohne dem Aufrufgraph zu folgen. Eine Ansicht,
die ``Auftragssteuerung.alles_loeschen(job)`` ruft, faellt hier heraus. Ein
Aufrufgraph waere hier falsch am Platz: Er zieht ueber Django, das ORM und jede
Bibliothek und liefert mehr Vermutung als Befund. Was hier steht, ist belegt.
"""
import ast

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug

__all__ = ["Schreibrouten"]

#: Aufrufe, die Daten UNWIEDERBRINGLICH beseitigen.
#:
#: ``traeger`` sagt, wer den Aufruf tragen MUSS. Ohne diese Spalte gab es beim
#: ersten Lauf zwei Fehlalarme von drei: ``sys.path.remove(verzeichnis)`` in
#: zwei Ansichten von 3DTools, die einen Suchpfad wieder aufraeumen (17.08.2026).
#: Eine Liste hat auch ein ``remove`` — dass ein Name in beiden Welten vorkommt,
#: ist der Normalfall und kein Sonderfall.
#:
#: ``ohne_args`` verlangt einen Aufruf ohne Argumente. Djangos
#: ``objekt.delete()`` ist so; ``cache.delete("schluessel")`` nicht — und ein
#: Cache-Eintrag ist kein Datenverlust.
VERLUST = {
    "delete": ("loescht Datensaetze", None, True),
    "rmtree": ("loescht ein Verzeichnis samt Inhalt", {"shutil"}, False),
    "remove": ("loescht eine Datei", {"os"}, False),
    "unlink": ("loescht eine Datei", None, False),
    "move": ("verschiebt Dateien", {"shutil"}, False),
    "rename": ("benennt Dateien um", {"os"}, False),
}

#: Aufrufe, die schreiben, ohne etwas zu verlieren.
SCHREIBT = {
    "get_or_create": ("legt Datensaetze an", None, False),
    "bulk_create": ("legt Datensaetze an", None, False),
    "write_text": ("schreibt eine Datei", None, False),
    "write_bytes": ("schreibt eine Datei", None, False),
    "makedirs": ("legt Verzeichnisse an", {"os"}, False),
}

#: Dekoratoren, die die Methode festlegen.
SCHUTZ = {"require_POST", "require_http_methods", "require_safe"}

#: Methodennamen einer klassenbasierten Ansicht, die schon an eine Methode
#: gebunden sind - dort ist Schreiben richtig.
GEBUNDEN = {"post", "put", "patch", "delete"}

#: Verzeichnisse, in denen eine schreibende Funktion mit ``request`` nichts
#: Gefaehrliches ist: Tests bauen ihre Lage selbst auf.
OHNE = ("tests", "migrations")


class Schreibrouten(Werkzeug):
    slug = "schreibrouten"
    titel = "Ansicht schreibt und beantwortet GET"
    zweck = ("Findet Ansichten, die im Rumpf löschen oder schreiben und dabei "
             "keine Methodenprüfung haben — per GET auslösbar.")
    befund = ("3DTools: `delete_job` löschte auf ein GET hin Auftrag und Dateien "
              "(der Link hatte nur ein `confirm`), `scan_bvh_files` schrieb bei "
              "jedem GET die Bibliothek neu — 7.067 Dateien, 35 Abfragen.")
    abhilfe = ("`@require_POST` setzen und die Aufrufstelle von `<a href>` auf "
               "ein POST-Formular umstellen (Rückfrage an `onsubmit`).")
    dauer = "1–3 s"
    kriterium = 16

    anlassfall = Anlassfall(
        {"seiten.py": '''# -*- coding: utf-8 -*-
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


def auftrag_loeschen(request, kennung):
    """Der echte Fall: loescht auf GET."""
    auftrag = Auftrag.objects.get(id=kennung)
    auftrag.delete()
    return redirect("liste")


@require_POST
def richtig_geschuetzt(request, kennung):
    """Die Ausnahme: derselbe Rumpf, aber nur per POST erreichbar."""
    Auftrag.objects.get(id=kennung).delete()
    return redirect("liste")


def nur_lesen(request):
    """Darf nicht gemeldet werden - schreibt nichts."""
    return redirect("liste")


def suchpfad_aufraeumen(request):
    """Der echte Fehlalarm aus dem ersten Lauf: eine LISTE hat auch `remove`."""
    import sys
    sys.path.insert(0, "/irgendwo")
    try:
        return redirect("liste")
    finally:
        sys.path.remove("/irgendwo")


def zwischenspeicher_leeren(request):
    """`cache.delete(schluessel)` ist kein Datenverlust - und hat Argumente."""
    from django.core.cache import cache
    cache.delete("liste")
    return redirect("liste")
'''},
        mindestens=1, hoechstens=1, erwartet_in="auftrag_loeschen",
        warum=("`delete_job` in 3DTools loeschte Auftrag und Dateien auf ein GET "
               "hin; der Schutz bestand aus einem JavaScript-`confirm`. Die zwei "
               "letzten Fälle sind die Fehlalarme des ersten Laufs — ohne sie "
               "meldete das Werkzeug 3 statt 1."))

    def laufen(self):
        zeilen = []
        for datei in self.dateien():
            if datei.baum is None or any(t in datei.name.split("/") for t in OHNE):
                continue
            zeilen += self._datei(datei)
        zeilen.sort(key=lambda z: (0 if z["art"] == "Datenverlust" else 1,
                                   z["stelle"]))
        verlust = sum(1 for z in zeilen if z["art"] == "Datenverlust")
        return Ergebnis(
            ["art", "stelle", "zeile", "ansicht", "aufruf", "abhilfe"], zeilen,
            "%d Ansichten schreiben und beantworten GET — %d davon löschen"
            % (len(zeilen), verlust),
            "Die Ursprungsprüfung der Middleware fasst GET bewusst nicht an. "
            "Schutz gibt es hier nur über die Methode.")

    # ------------------------------------------------------------------ Datei

    def _datei(self, datei):
        aus = []
        for knoten, in_klasse in self._funktionen(datei.baum):
            if not self._ist_ansicht(knoten, in_klasse):
                continue
            if self._geschuetzt(knoten, in_klasse):
                continue
            treffer = self._schreibt(knoten)
            if not treffer:
                continue
            name, zweck, verlust = treffer
            aus.append({
                "art": "Datenverlust" if verlust else "Schreibt",
                "stelle": datei.name, "zeile": knoten.lineno,
                "ansicht": knoten.name, "aufruf": "%s() — %s" % (name, zweck),
                "abhilfe": ("`@require_POST` und die Aufrufstelle auf ein "
                            "POST-Formular umstellen")})
        return aus

    @staticmethod
    def _funktionen(baum):
        """[(Funktionsknoten, Name der umgebenden Klasse oder None)]."""
        aus = []
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.ClassDef):
                for k in knoten.body:
                    if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        aus.append((k, knoten.name))
            elif isinstance(knoten, ast.Module):
                for k in knoten.body:
                    if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        aus.append((k, None))
        return aus

    @staticmethod
    def _ist_ansicht(knoten, in_klasse):
        """Erstes Argument ``request`` - so sieht eine Django-Ansicht aus.

        Bei einer Klasse ist es ``self, request`` (``dispatch``, ``get``) oder
        gar kein ``request`` (``get_context_data``). Deshalb zählt dort auch
        der Methodenname."""
        namen = [a.arg for a in knoten.args.args]
        if namen[:1] == ["request"]:
            return True
        if in_klasse and namen[:2] == ["self", "request"]:
            return True
        return bool(in_klasse) and knoten.name in ("get", "get_context_data")

    @classmethod
    def _geschuetzt(cls, knoten, in_klasse):
        """Dekorator, Methodenname oder eine Prüfung auf ``request.method``."""
        for d in knoten.decorator_list:
            if cls._dekoratorname(d) in SCHUTZ:
                return True
        if in_klasse and knoten.name in GEBUNDEN:
            return True
        # Ein Vergleich mit ``request.method`` irgendwo im Rumpf.
        for k in ast.walk(knoten):
            if isinstance(k, ast.Attribute) and k.attr == "method":
                if isinstance(k.value, ast.Name) and k.value.id == "request":
                    return True
        return False

    @staticmethod
    def _dekoratorname(d):
        if isinstance(d, ast.Call):
            d = d.func
        if isinstance(d, ast.Attribute):
            return d.attr
        return getattr(d, "id", "")

    @classmethod
    def _schreibt(cls, knoten):
        """(Name, Zweck, ist_verlust) des ersten schreibenden Aufrufs, sonst None.

        Verlust zählt vor blossem Schreiben: Wer beides tut, soll oben stehen.
        """
        gefunden = None
        for k in ast.walk(knoten):
            if not isinstance(k, ast.Call):
                continue
            name = (k.func.attr if isinstance(k.func, ast.Attribute)
                    else getattr(k.func, "id", ""))
            for tabelle, verlust in ((VERLUST, True), (SCHREIBT, False)):
                if name not in tabelle:
                    continue
                zweck, traeger, ohne_args = tabelle[name]
                if not cls._passt(k, traeger, ohne_args):
                    continue
                if verlust:
                    return name, zweck, True
                if gefunden is None:
                    gefunden = (name, zweck, False)
            # ``obj.save()`` OHNE Argumente ist Djangos Modell-Speichern.
            # ``bild.save(pfad)`` ist Pillow und schreibt eine Datei, die
            # jemand ohnehin gerade abholt - das waere ein Fehlalarm.
            if (name == "save" and not k.args and not k.keywords
                    and gefunden is None):
                gefunden = ("save", "speichert einen Datensatz", False)
        return gefunden

    @classmethod
    def _passt(cls, aufruf, traeger, ohne_args):
        """Trägt der Aufruf den verlangten Empfaenger, und die Argumentform?"""
        if ohne_args and (aufruf.args or aufruf.keywords):
            return False
        if traeger is None:
            return True
        return cls._empfaenger(aufruf.func) in traeger

    @staticmethod
    def _empfaenger(func):
        """Der WURZELNAME links vom Punkt: ``sys.path.remove`` -> ``sys``.

        Genau so fallen die beiden Fehlalarme heraus: ``sys.path.remove`` trägt
        ``sys``, verlangt ist ``os``.
        """
        if not isinstance(func, ast.Attribute):
            return ""
        knoten = func.value
        while isinstance(knoten, ast.Attribute):
            knoten = knoten.value
        return getattr(knoten, "id", "")
