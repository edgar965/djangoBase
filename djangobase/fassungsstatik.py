# -*- coding: utf-8 -*-
u"""Statik unter einem Pfad, der die Fassung traegt.

DAS PROBLEM (05.09.2026, 3DTools)
=================================
ES-Module importieren ihre Geschwister relativ (``import … from
'./skinning.js'``). Eine Fassungskennung in der ABFRAGE hilft dabei nicht:
Der Browser loest ``./skinning.js`` gegen die Adresse des importierenden
Moduls auf, und die Abfrage wird dabei NICHT vererbt. Die Einstiegsdatei
kommt also frisch, die Geschwister aus dem Zwischenspeicher.

Was daraus wird, ist an einem Tag zweimal passiert:

    SyntaxError: The requested module './skinning.js' does not provide an
    export named 'skelettNachfuehren'          -> leere Seite, HTTP 200

und danach, nach dem Absichern gegen den Abbruch, die stille Variante: Die
Seite laeuft, aber die neue Funktion fehlt, weil ein Modul von gestern ist.

``Cache-Control: no-cache`` (``StatikKopfzeilen``) verhindert das ab dem
naechsten Abruf — aber eben erst ab dann. Eine Datei, die ohne diese
Kopfzeile in den Zwischenspeicher gelangt ist, darf der Browser bis zu
10 % ihres Alters ungefragt ausliefern; bei einer drei Wochen alten Datei
sind das zwei Tage. Gemessen im Serverlog, zwei Seitenaufrufe nacheinander:

    15:31:17  state.js 304, skinning.js 304, websocket.js 304, …
    15:31:47  websocket.js 304, netznachricht.js 304
              (kein Eintrag fuer skinning.js — aus dem Zwischenspeicher)

DIE LOESUNG: DIE FASSUNG IN DEN PFAD
====================================
``/statik/v-1788611870/viewer/viewer/index.js`` statt
``/static/viewer/viewer/index.js?t=…``. Ein relativer Import daraus wird zu
``/statik/v-1788611870/viewer/viewer/skinning.js`` — die Fassung erbt sich
also ueber den ganzen Modulbaum, ohne dass eine einzige Import-Adresse
angefasst werden muss. Das ist genau die Eigenschaft, die eine Abfrage
nicht hat.

Aendert sich eine Datei, aendert sich die Zahl und damit jede Adresse:
Kein Browser kann etwas Altes liefern. Aendert sich nichts, bleibt die
Adresse gleich und alles liegt ein Jahr im Zwischenspeicher — ``immutable``,
also nicht einmal eine Rueckfrage.

WARUM NICHT ``?v=`` IN DEN IMPORT-ADRESSEN
==========================================
Weil dieselbe Datei dann unter zwei Adressen laege (mit und ohne Kennung)
und der Browser sie ZWEIMAL laedt — mit getrennten Modulzustaenden. Das ist
in diesem Projekt schon einmal schiefgegangen und steht seither als Regel
in `CLAUDE.md`.
"""
import mimetypes
import os
import posixpath
import threading
import time

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import FileResponse, Http404
from django.urls import path, register_converter

from .cache_middleware import STATIK

__all__ = ['Fassungsstatik', 'urlpatterns']


class Fassungsstatik:
    u"""Liefert statische Dateien unter ``/<PRAEFIX>/v-<fassung>/<pfad>``."""

    #: Ausserhalb von ``STATIC_URL``, sonst faengt der Statik-Handler von
    #: ``runserver`` die Adresse ab, bevor irgendein Code sie sieht.
    PRAEFIX = 'statik'

    #: So oft wird der Dateibaum hoechstens neu abgesucht. Ein Durchlauf ueber
    #: 427 Dateien kostet gemessene 17 ms — zu viel je Seitenaufruf, zu wenig,
    #: um beim Entwickeln zu stoeren.
    FRISCHE_S = 2.0

    _fassung = 0
    _geprueft = 0.0
    _schloss = threading.Lock()

    # ------------------------------------------------------------ Fassung

    @classmethod
    def fassung(cls):
        u"""Die Kennung: die juengste Aenderungszeit im Statik-Baum.

        Eine Zahl, die sich genau dann aendert, wenn sich eine Datei
        aendert — nicht bei jedem Seitenaufruf (dann laedt der Browser
        staendig alles neu) und nicht nie (dann kommt die Aenderung nie an).
        """
        jetzt = time.time()
        if cls._fassung and jetzt - cls._geprueft < cls.FRISCHE_S:
            return cls._fassung
        with cls._schloss:
            if cls._fassung and jetzt - cls._geprueft < cls.FRISCHE_S:
                return cls._fassung
            cls._fassung = cls._juengste()
            cls._geprueft = jetzt
            return cls._fassung

    @classmethod
    def _juengste(cls):
        juengste = 0
        for ordner in cls._ordner():
            for wurzel, _, dateien in os.walk(ordner):
                for name in dateien:
                    try:
                        zeit = os.stat(os.path.join(wurzel, name)).st_mtime
                    except OSError:
                        # stumm gewollt: Eine Datei, die zwischen `walk` und
                        # `stat` verschwindet, ist kein Fehler — beim naechsten
                        # Durchlauf ist sie ohnehin weg.
                        continue
                    if zeit > juengste:
                        juengste = zeit
        return int(juengste)

    @staticmethod
    def _ordner():
        u"""Die durchsuchten Baeume: ``STATICFILES_DIRS`` und ``STATIC_ROOT``.

        Bewusst NICHT die ``static``-Ordner der Anwendungen: Die aendern sich
        nur beim Aktualisieren eines Pakets, und der Durchlauf ueber
        ``site-packages`` waere teuer.
        """
        aus = [str(o[1] if isinstance(o, (tuple, list)) else o)
               for o in (getattr(settings, 'STATICFILES_DIRS', ()) or ())]
        wurzel = getattr(settings, 'STATIC_ROOT', None)
        if wurzel:
            aus.append(str(wurzel))
        return [o for o in aus if o and os.path.isdir(o)]

    # ------------------------------------------------------------ Adressen

    @classmethod
    def pfad(cls, relativ):
        u"""``'viewer/viewer/index.js'`` -> ``'/statik/v-123/viewer/…'``."""
        return '/%s/v-%d/%s' % (cls.PRAEFIX, cls.fassung(),
                                str(relativ).lstrip('/'))

    # ------------------------------------------------------------ Ausliefern

    @classmethod
    def ausliefern(cls, request, fassung, pfad):
        u"""Die Datei zu diesem Pfad — die Fassung selbst wird ignoriert.

        Sie steht nur in der Adresse, damit eine Aenderung eine neue Adresse
        ergibt. Zu pruefen, ob sie die aktuelle ist, waere falsch: Eine Seite,
        die vor der Aenderung geladen wurde, holt ihre restlichen Module noch
        unter der alten Fassung nach und braeuchte sie dann.
        """
        del fassung
        ort = cls._datei(pfad)
        if ort is None:
            raise Http404('Statische Datei nicht gefunden: %s' % pfad)
        typ = mimetypes.guess_type(ort)[0] or 'application/octet-stream'
        antwort = FileResponse(open(ort, 'rb'), content_type=typ)
        # Die Adresse traegt die Fassung, also darf sie ein Jahr liegen —
        # `immutable` spart sogar die Rueckfrage.
        antwort['Cache-Control'] = STATIK
        return antwort

    @staticmethod
    def _datei(pfad):
        u"""Der echte Ort auf der Platte — oder ``None``.

        ``normpath`` VOR der Pruefung: ``a/../../geheim`` sieht ohne sie
        harmlos aus. Und der Fund geht ueber die Finder, damit derselbe
        Suchweg gilt wie fuer ``{% static %}``.
        """
        sauber = posixpath.normpath('/' + str(pfad).replace('\\', '/')).lstrip('/')
        if not sauber or sauber.startswith('../') or sauber == '..':
            return None
        gefunden = finders.find(sauber)
        if isinstance(gefunden, (list, tuple)):
            gefunden = gefunden[0] if gefunden else None
        return gefunden if gefunden and os.path.isfile(gefunden) else None


class Fassungskennung:
    u"""``v-1788611870`` in der Adresse."""

    regex = r'v-\d+'

    def to_python(self, wert):
        return int(wert[2:])

    def to_url(self, wert):
        return 'v-%d' % int(wert)


register_converter(Fassungskennung, 'fassung')

urlpatterns = [
    path('%s/<fassung:fassung>/<path:pfad>' % Fassungsstatik.PRAEFIX,
         Fassungsstatik.ausliefern, name='fassungsstatik'),
]
