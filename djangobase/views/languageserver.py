# -*- coding: utf-8 -*-
u"""Hilfe · Werkzeug Language Server — ein Language Server auf Knopfdruck.

DIE ANSAGE (Edgar, 02.09.2026)
==============================
    „mach eine neue Seite Hilfe – Werkzeug Language Server, die so ähnlich
     aufgebaut ist wie Werkzeug Code Review, und das konfigurierbar auf
     Knopfdruck macht … mache beide (basedpyright und pyright) … Hintergrund
     thread … Dateien können umgeschrieben werden"

Aufbau wie ``skills.py``: EIN Formular, Karten untereinander, die Tabelle aus
``djangobase/_tabelle.html``. Anders als dort läuft die Rechnung nicht im
Request, sondern in ``ls_lauf.LAUF``; die Seite fragt den Zustand ab und lädt
sich neu. Ein GET rechnet NIE — dieselbe Regel wie Klassenmodell.

Das Ergebnis liegt in der Ablage (``umbau/ablage.py``), Schlüssel = Wurzel +
Abdruck der Einstellungen + Abdruck der Quellmodule. Andere Einstellungen,
anderes Ergebnis.
"""
import logging
import time
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin
from ..skills.werkzeug import Werkzeug
from ..umbau import ablage
from ..umbau import ausschlussliste as ausschlussliste_modul
from ..umbau import languageserver as languageserver_modul
from ..umbau import ls_befunde as ls_befunde_modul
from ..umbau import ls_konfig as ls_konfig_modul
from ..umbau.ablage import Speicher
from ..umbau.ausschlussliste import Ausschlussliste
from ..umbau.globalbestand import hauptaeste
from ..umbau.languageserver import LanguageServer
from ..umbau.ls_javascript import JsPruefer
from ..umbau.ls_befunde import LsBefunde
from ..umbau.ls_konfig import AUSSCHLUESSE, JS_REGELN, REGELN, STUFEN, LsKonfig
from ..umbau.ls_lauf import LAUF
from ..umbau.rahmenmodule import Rahmenmodule

logger = logging.getLogger("djangobase.languageserver")

__all__ = ["LanguageServerView", "LsSpeicher", "wurzel", "ordner", "konfig_laden",
           "schluessel", "extra_pfade", "static_wurzeln", "liste"]


# ── Orte ────────────────────────────────────────────────────────────────
def wurzel():
    u"""Die Projektwurzel — eine Ebene über BASE_DIR, wenn dort das Repo liegt
    (shortlongx: brain/, depot/, werkzeug/ neben shortlongxWeb/)."""
    return Werkzeug().wurzel()


def extra_pfade():
    u"""Import-Wurzeln neben der Projektwurzel.

    Zwei Stück, beide gemessen nötig:

    ``BASE_DIR`` — damit ``dashboard`` ohne Präfix auflösbar ist.

    **Der Ordner ÜBER dem djangobase-Paket** (02.09.2026). Alle sechs
    Konsumenten binden djangoBase als *editable install* ein
    (``pip install -e``). In ``site-packages`` liegt dann kein Paket,
    sondern ein Verweis — und dem folgt der Language Server nicht. Erster
    Lauf über CamTrack: **sieben** ``reportMissingImports``, alle auf
    ``djangobase.*``::

        app/context_processors.py:309   djangobase.conf
        app/logging_utils.py:9          djangobase.jobctx
        config/settings.py:300          djangobase.logging
        config/settings.py:365          djangobase.allauth_config
        app/services/navigation/…:243   djangobase.pflichtmenue
        tools/wartung/pruefen.py:22     djangobase.skills
        tools/wartung/vorlage_namen.py  djangobase.skills.vorlagenkontext

    Kein einziger davon war ein Fehler im Projekt — der Prüfer fand das
    Paket bloss nicht. Sieben rote Zeilen, die nichts bedeuten, kosten
    mehr als sie nützen: Sie bringen den Leser dazu, auch die echten zu
    überblättern.

    Liegt djangoBase doch fest installiert in ``site-packages``, ist der
    Pfad schon über ``venvPath`` erreichbar; ein zweites Mal schadet
    nicht, deshalb ohne Sonderfall.

    ``ls_extra_pfade`` aus der Projekt-Konfiguration (05.09.2026). Dieselbe
    Fehlerklasse noch einmal, nur projekteigen und deshalb nicht erratbar:
    HumanBodyWeb haengt ``A:\3DTools\HumanBody`` in ``settings.py`` per
    ``sys.path.insert`` ein, statt es zu installieren. Der Language Server
    sieht davon nichts und meldete **151 ``reportMissingImports``** auf
    ``humanbody_core.*`` — 12 % aller Befunde des Projekts, kein einziger
    davon ein Fehler. Leere Vorgabe, also unveraendert fuer alle, die den
    Schluessel nicht setzen.

    ZUSAMMENGEFÜHRT (02.09.2026)
        Zwei Sitzungen haben diese Funktion gleichzeitig gegen dasselbe
        Problem umgeschrieben. Übernommen ist der Weg über
        ``djangobase.__file__`` statt einer ``.parent``-Kette ab
        ``__file__``: Eine Kette zeigt nach jedem Datei-Umzug still
        woandershin, ohne Fehler zu werfen. Aus der anderen Fassung kommt
        die schärfere Bedingung ``startswith`` — sie greift auch, wenn
        djangoBase INNERHALB der Projektwurzel liegt, wo ``!=`` allein
        den Pfad doppelt melden würde.
    """
    aus = []
    basis = Path(settings.BASE_DIR)
    eigen = wurzel()
    if basis != eigen:
        aus.append(basis)
    import djangobase
    paket = Path(djangobase.__file__).resolve().parent.parent
    if paket not in aus and not str(paket).startswith(str(eigen)):
        aus.append(paket)
    for pfad in conf().get("ls_extra_pfade") or ():
        ort = Path(str(pfad)).resolve()
        if ort not in aus and not str(ort).startswith(str(eigen)):
            aus.append(ort)
    return aus


def static_wurzeln():
    u"""``static``-Ordner der installierten Apps, die NICHT im Projekt liegen.

    Die Vorlagen binden djangoBase-Module über die URL ein
    (``import … from '/static/djangobase/js/tabellen_sortierung.js'``). Diese
    Dateien liegen im Paket, nicht im Projektbaum — ohne sie meldet tsc vier
    unauflösbare Importe und alles, was daran hängt."""
    raus, eigen = [], str(wurzel())
    try:
        from django.contrib.staticfiles.finders import get_finders
        for finder in get_finders():
            for pfad in getattr(finder, "locations", []) or []:
                ort = pfad[1] if isinstance(pfad, (tuple, list)) else pfad
                if ort and not str(ort).startswith(eigen):
                    raus.append(str(ort))
            for ort in (getattr(finder, "storages", {}) or {}).values():
                ziel = getattr(ort, "location", "")
                if ziel and not str(ziel).startswith(eigen):
                    raus.append(str(ziel))
    except Exception:                                     # noqa: BLE001
        logger.exception("static-Ordner nicht ermittelbar")
    return sorted(set(raus))


def ordner():
    return ablage.ordner() / "languageserver"


def liste():
    u"""Die Ausschlussliste des Projekts — ``pruefausschluss.txt`` in der Wurzel."""
    return Ausschlussliste(wurzel())


def konfig_laden():
    u"""Einstellungen aus dem Ablage-Ordner, Ausschlussliste aus dem Projekt.

    Zwei Orte mit Absicht: Was nur diesen Rechner angeht (Interpreter, Deckel,
    Zeitlimit), bleibt im Zwischenspeicher; was das Projekt angeht, steht im
    Projekt und geht mit ins Repository."""
    konfig = LsKonfig.laden(ordner() / "konfig.json")
    konfig.zusatz = liste().muster()
    return konfig


def schluessel(konfig):
    return u"%s|%s" % (wurzel(), konfig.abdruck())


class LsSpeicher(Speicher):
    u"""Das Ergebnis des letzten Laufs — je Einstellungs-Abdruck eines."""

    bereich = "languageserver"
    quellen = (languageserver_modul, ls_konfig_modul, ls_befunde_modul,
               ausschlussliste_modul)

    @staticmethod
    def bauen(wurzel):                                    # pragma: no cover
        raise RuntimeError("der Language Server rechnet nur im Hintergrund-Lauf")

    @classmethod
    def ablegen(cls, wurzel_schluessel, ergebnis):
        u"""Gegenstück zu ``nachsehen``: derselbe zusammengesetzte Schlüssel."""
        abdruck = cls.abdruck()
        voll = u"%s#%s" % (wurzel_schluessel, abdruck) if abdruck else str(wurzel_schluessel)
        cls._gemerkt()[voll] = (ergebnis, time.time())
        ablage.schreiben(cls.bereich, voll, ergebnis)


# ── Aeste (einmal je Prozess gezählt) ────────────────────────────────────
_AESTE = {}


def aeste():
    w = str(wurzel())
    eintrag = _AESTE.get(w)
    if eintrag is None or time.time() - eintrag[0] > 600:
        try:
            gefunden = hauptaeste(w)
        except Exception:                                 # noqa: BLE001
            logger.exception("Hauptäste nicht zählbar")
            gefunden = []
        _AESTE[w] = (time.time(), gefunden)
        eintrag = _AESTE[w]
    return eintrag[1]


# ── Ansicht ─────────────────────────────────────────────────────────────
class LanguageServerView(ZugriffMixin, View):
    vorlage = "djangobase/hilfe/languageserver.html"

    def get(self, request):
        return self._seite(request, konfig_laden())

    def post(self, request):
        aktion = request.POST.get("aktion", "speichern")
        if aktion == "ausschluss":
            # VOR ``aus_formular`` (02.09.2026): Die Ausschlussliste hat ihr
            # eigenes Formular — ein Formular im Formular gibt es in HTML
            # nicht. Es schickt die Einstellungsfelder also NICHT mit, und
            # ``aus_formular`` läse jeden fehlenden Haken als „aus".
            anzahl, _fehler = liste().speichern(request.POST.get("liste", ""))
            return redirect("%s?ausschluss=%d" % (request.path, anzahl))
        konfig = LsKonfig.aus_formular(request.POST, konfig_laden())
        konfig.speichern(ordner() / "konfig.json")
        if aktion in ("lauf", "neu"):
            return self._starten(request, konfig, neu=(aktion == "neu"))
        return redirect(request.path)

    def _starten(self, request, konfig, neu):
        server = LanguageServer(konfig, wurzel(), ordner(), extra_pfade(),
                               static_wurzeln=static_wurzeln())
        key = schluessel(konfig)
        if neu:
            LsSpeicher.leeren()
        gestartet = LAUF.starten(server, lambda erg: LsSpeicher.ablegen(key, erg))
        antwort = {"gestartet": gestartet, "zustand": LAUF.zustand()}
        if request.headers.get("x-requested-with") == "fetch":
            return JsonResponse(antwort)
        return redirect(request.path)

    def _seite(self, request, konfig):
        server = LanguageServer(konfig, wurzel(), ordner(), extra_pfade(),
                               static_wurzeln=static_wurzeln())
        gefunden = server.finden()
        ergebnis, alter = LsSpeicher.nachsehen(schluessel(konfig))
        eigene = liste()
        daten = {
            "liste_text": eigene.text(),
            "liste_pfad": str(eigene.pfad()),
            "liste_da": eigene.vorhanden(),
            "liste_muster": eigene.muster(),
            "liste_namen": eigene.namen(),
            "liste_fehler": eigene.fehler(),
            "liste_gespeichert": request.GET.get("ausschluss"),
            "titel": u"Werkzeug Language Server",
            "aktiv": "languageserver",
            "konfig": konfig,
            "werkzeuge": LsKonfig.WERKZEUGE,
            "modi": LsKonfig.MODI,
            "stufen": STUFEN[:3],
            "regeln": [(r, konfig.regeln.get(r, s), t) for r, s, t in REGELN],
            "regel_stufen": STUFEN,
            "ausschluesse": [(k, konfig.ausschluss.get(k, v), l)
                             for k, _m, v, l in AUSSCHLUESSE],
            "js_regeln": [(r, r in konfig.js_stumm, t) for r, _s, t in JS_REGELN],
            "aeste": aeste(),
            "wurzel": str(wurzel()),
            "gefunden": gefunden,
            "tsc": JsPruefer(wurzel(), ordner()).finden(),
            "lauf": LAUF.zustand(),
            "alter": int(alter) if alter is not None else None,
            "ergebnis": ergebnis,
        }
        if ergebnis is not None:
            # ``Rahmenmodule`` liest Quelltext, aber nur von Dateien MIT Befund
            # — und nur, wenn der Haken steht. Es geht bewusst NICHT in
            # ``LsSpeicher.quellen``: Der Filter wirkt auf ein fertiges
            # Ergebnis, ein Umschalten darf keine Neurechnung auslösen.
            befunde = LsBefunde(ergebnis, konfig, Rahmenmodule(wurzel()))
            daten.update({
                "kennzahlen": befunde.kennzahlen(),
                "tabelle": befunde.tabelle(),
                "je_regel": befunde.je_regel(),
                "je_datei": befunde.je_datei(),
            })
        return render(request, self.vorlage, daten)
