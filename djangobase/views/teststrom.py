# -*- coding: utf-8 -*-
u"""TestStromView - der Live-Lauf hinter Hilfe -> Tests.

    „live fortschritt in djangoBase einbauen" (Edgar, 17.08.2026)

POST ``{"ids": ["app.tests.unit.test_x.K.test_y", …]}`` und die Antwort kommt
zeilenweise, WAEHREND der Lauf läuft (siehe :mod:`..teststrom`). Die Seite
schreibt daraus ✓/✗ in die Tabellenzeilen und am Ende die Laufzeiten.

WARUM POST
==========
Der Aufruf startet einen Prozess, und bei „Alle auswählen" stehen hunderte
Kennungen in der Anfrage — das sprengt jede URL. Ein Reload soll einen Testlauf
auch nicht wiederholen.

WAS AUSGEFUEHRT WERDEN DARF
===========================
Ausschliesslich, was die Seite selbst kennt: entdeckte Test-IDs, Slugs
konfigurierter Befehle, Karten-Labels. Die Prüfung ist
:class:`~..testziele.Testziele` — dieselbe, die der normale Seitenlauf benutzt.
"""
import json
import logging

from django.http import JsonResponse, StreamingHttpResponse
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin
from ..testkarten import Karten
from ..testkategorien import Kategorien
from ..testsperre import Laufsperre
from ..teststrom import Teststrom
from ..testziele import Testziele

log = logging.getLogger("djangobase.tests")


class TestStromView(ZugriffMixin, View):
    """Fährt die angeforderten Ziele und streamt den Fortschritt."""

    def post(self, request):
        try:
            daten = json.loads(request.body.decode("utf-8") or "{}")
        except ValueError:
            return JsonResponse({"ok": False, "error": "kein JSON"}, status=400)
        if daten.get("abbrechen"):
            return self._abbrechen(request)
        # Frei? Dann erst pruefen, was gefahren werden soll. Die Sperre selbst
        # holt sich `Teststrom` — hier geht es nur darum, dem Browser eine
        # ehrliche Antwort zu geben, statt einen Strom zu oeffnen, der sofort
        # mit „belegt" endet.
        belegt = Laufsperre().zustand()
        if belegt:
            return JsonResponse(
                {"ok": False, "belegt": True,
                 "error": Laufsperre._grund(belegt)}, status=409)
        ids = daten.get("ids") or []
        if isinstance(ids, str):
            ids = [ids]
        if not isinstance(ids, list) or not ids:
            return JsonResponse({"ok": False, "error": "ids nötig"}, status=400)

        auswahl, python = self._auswahl()
        cmd, ziele, verworfen = auswahl.befehl(ids, python)
        if not cmd:
            log.warning("Live-Lauf ohne gültiges Ziel — %d Einträge verworfen",
                        verworfen)
            return JsonResponse(
                {"ok": False,
                 "error": "Keine gültige Auswahl — %d Einträge verworfen."
                          % verworfen}, status=409)
        name = Testziele.name(ziele, verworfen)
        log.info("Live-Lauf: %s durch %s — %s", name,
                 getattr(getattr(request, "user", None), "username", "?"),
                 " ".join(ziele[:5]) + (" …" if len(ziele) > 5 else ""))
        antwort = StreamingHttpResponse(
            Teststrom().fahren(cmd, name),
            content_type="application/x-ndjson")
        # Ohne das puffern Proxies (und manche Browser) die Antwort, bis sie
        # fertig ist — genau das, was der Live-Lauf vermeiden soll.
        antwort["Cache-Control"] = "no-cache, no-store"
        antwort["X-Accel-Buffering"] = "no"
        return antwort

    @staticmethod
    def _abbrechen(request):
        u"""Den laufenden Lauf beenden - samt Prozessbaum und Sperre.

        Ohne diesen Weg haelt ein haengender Lauf die Sperre bis zur Frist
        (eine Stunde), und niemand kann etwas tun ausser den Server neu zu
        starten.
        """
        erfolg, meldung = Laufsperre().abbrechen()
        log.warning("Abbruch angefordert durch %s: %s",
                    getattr(getattr(request, "user", None), "username", "?"),
                    meldung)
        return JsonResponse({"ok": erfolg, "meldung": meldung},
                            status=200 if erfolg else 409)

    @staticmethod
    def _auswahl():
        u"""Die erlaubten Ziele — aus derselben Quelle wie die Seite.

        Die Discovery ist gecacht (``TestsView._ids_gecacht``), der Aufruf kostet
        also nichts, solange die Seite kurz vorher geladen wurde.
        """
        from .tests import TestsView
        c = conf()
        befehle = c.get("test_befehle") or TestsView._befehle_abgeleitet()
        kat = Kategorien(befehle)
        discover = c.get("test_discover") or kat.discover()
        kategorien, bekannte = TestsView._einzeltests(
            discover, mit_djangobase=bool(c.get("tests_djangobase_sichtbar")))
        labels = {Karten.label(k.get("tests") or []) for k in kategorien}
        labels.discard("")
        return (Testziele(bekannte, befehle, kat.sammelbefehle(), labels),
                Kategorien.python(befehle))
