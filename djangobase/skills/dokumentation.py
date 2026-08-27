# -*- coding: utf-8 -*-
u"""Kriterium 20: Trifft die Dokumentation noch den Code?

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „Ich brauche dann auch Testcases die das überprüfen in der CodeReview
     Seite (Mach einen neuen Abschnitt: Dokumentation, wo auch getestet
     wird, ob es ein Klassendiagramm gibt wie in /hilfe/klassenmodell/"

WORUM ES GEHT — UND WORUM NICHT
===============================
Nicht darum, ob viel dokumentiert ist. Sondern darum, ob das, was
dasteht, noch stimmt. Eine Beschreibung, die einmal richtig war, ist
gefaehrlicher als gar keine: Man verlaesst sich darauf.

DER ANLASS, GEMESSEN
====================
``app/templates/app/help/workflow.html`` zeichnet den Aufnahme-Ablauf als
ASCII und schreibt „10-Minuten-Segmente". Nachgemessen am 27.08.2026:
Seit v0.83 schreibt der ffmpeg-Segment-Muxer STUNDEN-Dateien, seit v0.88
liegt der Hauptstrom in 10-SEKUNDEN-Bloecken mit Stundenordner. Die
Zeichnung war zwei Umbauten alt und sah unveraendert richtig aus.

Genau das faellt hier auf, denn die vier Pruefungen fragen nicht nach
Text, sondern nach Deckung mit dem Quelltext:

    1  Es gibt ein Klassenmodell-Bild      (Ansicht, Zeichner, Vorlage)
    2  Es gibt Workflow-Bilder             (dazu die Ermittlung)
    3  Jeder Kasten zeigt auf echten Code  FEHLER, wenn die Datei fehlt
    4  Jedes Bild sagt, wo es aufhoert     HINWEIS bei Abschnitt/Deckel

Punkt 3 ist der Kern. Er kann nur gruen sein, wenn die Bilder aus dem
Code gelesen wurden — eine von Hand gemalte Zeichnung faellt hier durch,
sobald jemand eine Klasse umbenennt. Das ist beabsichtigt.

WAS DIE WACHHUNDE AM 27.08.2026 KORRIGIERT HABEN
================================================
Der erste Wurf pruefte etwas ganz anderes: „sind die schwersten Wege
duenn gezeichnet" — eine Bedingung, die gar nicht eintreten KANN (fuenf
Klassen brauchen mindestens fuenf Schritte). Und er suchte die Bildwerke
nur beim Paket statt in der uebergebenen Wurzel.

``AnlassfallCheck`` hat beides gefasst: Das Werkzeug meldete auf einem
LEEREN Verzeichnis dasselbe wie auf dem echten Projekt — also blind. Ein
Werkzeug, das seinen eigenen Beispielfall nicht findet, prueft nichts.
"""
from __future__ import annotations

from pathlib import Path

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

#: Was vorhanden sein muss, damit „es gibt ein Bild" mehr ist als eine
#: Behauptung: die Ansicht, der Zeichner und die Vorlage.
BILDWERKE = (
    (u'Klassenmodell',
     ('djangobase/views/klassenmodell.py',
      'djangobase/umbau/klassenbild.py',
      'djangobase/templates/djangobase/hilfe/klassenmodell.html')),
    (u'Workflows',
     ('djangobase/views/workflows.py',
      'djangobase/umbau/workflowbild.py',
      'djangobase/umbau/workflows.py',
      'djangobase/umbau/wegenetz.py',
      'djangobase/umbau/ablauf.py',
      'djangobase/umbau/ablaufbild.py',
      'djangobase/templates/djangobase/hilfe/workflows.html')),
)

#: Eine Kette, die tiefer reicht, als gezeichnet wird — der Beispielfall.
KETTE = (
    'class Eins:\n    def a(self):\n        self.x.b()\n\n\n'
    'class Zwei:\n    def b(self):\n        self.x.c()\n\n\n'
    'class Drei:\n    def c(self):\n        self.x.d()\n\n\n'
    'class Vier:\n    def d(self):\n        self.x.e()\n\n\n'
    'class Fuenf:\n    def e(self):\n        self.x.f()\n\n\n'
    'class Sechs:\n    def f(self):\n        self.x.g()\n\n\n'
    'class Sieben:\n    def g(self):\n        return 7\n')


class Dokumentation(BefundWerkzeug):

    kriterium = 20
    slug = 'dokumentation'
    titel = u'Dokumentation: deckt sich das Bild noch mit dem Code?'
    zweck = (u'Prüft nicht, ob viel dokumentiert ist, sondern ob es stimmt: '
             u'Gibt es ein Klassendiagramm und Workflow-Bilder, zeigt jeder '
             u'Kasten auf Code, der wirklich existiert, und sagt jedes Bild '
             u'selbst, wo es aufhört?')
    abhilfe = (u'Nach jedem Umbau, der Klassen umbenennt oder verschiebt. '
               u'Genau dann verfällt eine Zeichnung, ohne dass man es ihr '
               u'ansieht.')
    befund = (u'Der Anlass: Eine Hilfeseite zeichnete den Aufnahme-Ablauf mit '
              u'„10-Minuten-Segmenten". Gemessen schreibt der Segment-Muxer '
              u'seit v0.83 Stunden-Dateien und der Hauptstrom liegt seit '
              u'v0.88 in 10-Sekunden-Blöcken — die Zeichnung war zwei '
              u'Umbauten alt und sah unverändert richtig aus.')
    dauer = u'wenige Sekunden'

    anlassfall = Anlassfall(
        {'urls.py': "from django.urls import path\n"
                    "from . import views\n"
                    "urlpatterns = [path('tief/', views.tief, name='tief')]\n",
         'views.py': 'def tief(request):\n'
                     '    Eins().a()\n',
         'kette.py': KETTE},
        mindestens=1, erwartet_in='abgeschnitten',
        warum=u'Eine Kette über sieben Klassen, gezeichnet wird bis Tiefe '
              u'fünf. Das Bild zeigt also weniger als den ganzen Weg — und '
              u'muss das selbst sagen, statt Vollständigkeit vorzutäuschen')

    # ------------------------------------------------------------------
    def pruefen(self, **_argumente):
        befunde = []
        befunde.extend(self._bilder_vorhanden())
        deckung = self._deckung()
        befunde.extend(deckung['befunde'])
        return Befundsatz(self.titel, self._kopf(deckung), befunde)

    @staticmethod
    def _kopf(deckung):
        return [u'%d Bildwerke' % len(BILDWERKE),
                u'%d Wege gezeichnet' % deckung['wege'],
                u'%d Kästen gegen den Quelltext gehalten' % deckung['kaesten'],
                u'%d Namen blieben mehrdeutig' % deckung['offen']]

    # ── 1 und 2: Gibt es die Bilder ueberhaupt? ──────────────────

    @staticmethod
    def _bildwurzel():
        u"""Wo die Bildwerke liegen: beim Paket, nicht beim Projekt.

        djangoBase liegt NEBEN dem Projekt, das es bedient — hier
        ``C:/CamTrack/djangoBase`` neben ``C:/CamTrack/CamTrackDjango``.
        Der erste Wurf suchte unter ``self.wurzel()`` und meldete beide
        Bildwerke als fehlend, obwohl beide dastanden: ein Fehlbefund, der
        die Pruefung wertlos gemacht haette, weil sie IMMER rot war.
        """
        import djangobase
        return Path(djangobase.__file__).resolve().parent.parent

    def _bilder_vorhanden(self):
        u"""Erst im geprüften Projekt nachsehen, dann beim Paket.

        BEIDE WURZELN — UND WARUM DAS NICHT BEQUEMLICHKEIT IST
        =====================================================
        Der erste Wurf sah nur beim Paket nach. Das verletzte die
        Grundregel jedes Werkzeugs: Es sucht in der Wurzel, die man ihm
        gibt. ``AnlassfallCheck`` hat es sofort gefasst — das Werkzeug
        meldete auf einem LEEREN Verzeichnis dasselbe wie auf dem echten
        Projekt und war damit blind.

        Der zweite Wurf sah nur im Projekt nach und meldete beide
        Bildwerke als fehlend, obwohl beide dastanden: djangoBase liegt
        NEBEN dem Projekt, das es bedient.

        Beide also. Gefunden ist gefunden — und auf einem leeren
        Verzeichnis schweigt das Werkzeug, weil das Paket dort steht, wo
        es hingehört.
        """
        aus = []
        wurzeln = (Path(self.wurzel()), self._bildwurzel())
        for name, teile in BILDWERKE:
            fehlend = [t for t in teile
                       if not any((w / t).exists() for w in wurzeln)]
            if fehlend:
                aus.append(Befund(
                    fehlend[0],
                    u'%s: kein Bild im Projekt' % name,
                    u'Fehlt: %s. Ohne Ansicht, Zeichner UND Vorlage gibt es '
                    u'kein Bild, sondern höchstens die Absicht, eines zu '
                    u'bauen.' % ', '.join(fehlend),
                    Befund.FEHLER))
        return aus

    # ── 3 und 4: Trifft das Bild den Code? ──────────────────────

    def _deckung(self):
        u"""Jeden Kasten der Workflow-Bilder gegen den Quelltext halten.

        Gelesen wird dazu dasselbe, was die Seite zeigt — nicht eine
        zweite Ermittlung daneben. Zwei Wege zur selben Zahl laufen
        auseinander, sobald einer angefasst wird.
        """
        try:
            from ..umbau.workflows import DECKEL, GRENZE, Workflowliste
        except ImportError:                            # pragma: no cover
            return {'befunde': [], 'kaesten': 0, 'wege': 0, 'offen': 0}
        self._deckel, self._grenze = DECKEL, GRENZE
        liste = Workflowliste(self.wurzel()).lesen()
        befunde, kaesten, offen = [], 0, 0
        for weg in liste.wege:
            offen += len(set(weg.offen))
            for schritt in weg.schritte:
                kaesten += 1
                bezug = schritt.bezug
                if not bezug.datei or not bezug.datei.exists():
                    befunde.append(Befund(
                        str(bezug.datei),
                        u'Kasten zeigt ins Leere: %s' % bezug.anzeige,
                        u'Im Bild von „%s" steht ein Kasten, dessen Datei es '
                        u'nicht mehr gibt.' % weg.einstieg.titel,
                        Befund.FEHLER))
        befunde.extend(self._abgeschnittene(liste))
        befunde.extend(self._nicht_in_der_liste(liste))
        return {'befunde': befunde, 'kaesten': kaesten,
                'wege': len(liste.wege), 'offen': offen}

    @staticmethod
    def _abgeschnittene(liste):
        u"""Bilder, die ihre eigene Grenze VERSCHWEIGEN.

        Kein Fehler, sondern ein Hinweis: Die Tiefengrenze ist Absicht —
        ohne sie laufen alle Wege bei den Hilfsfunktionen zusammen und
        jedes Bild sieht aus wie jedes andere. Gemeldet wurde es trotzdem,
        denn ein Bild, das seine eigene Grenze verschweigt, wird für das
        Ganze gehalten.

        DAS ABSCHNEIDEN ALLEIN IST SEIT DEM 27.08.2026 KEIN BEFUND MEHR
        ===============================================================
        ``Workflowbild._abschluss`` setzt jetzt einen Fussvermerk unter
        jedes gekürzte Bild („… hier geht der Weg weiter, als das Bild
        zeigt"). Damit ist die Begründung oben erfüllt — das Bild
        verschweigt nichts mehr, und 33 von 34 Hinweisen an assistant
        waren erledigt, ohne dass etwas unterdrückt wurde.

        Was hier bleibt, ist die Gegenprobe: Kann das Bild den Vermerk
        gar nicht setzen (weil ihm die Angabe fehlt), steht der Hinweis
        wieder da. Ein stillschweigend gekürztes Bild soll nie wieder
        möglich sein.
        """
        from ..umbau.workflowbild import Workflowbild

        befunde = []
        for weg in liste.wege:
            if not weg.abgeschnitten:
                continue
            try:
                # ``<text class="wf-mehr"`` und NICHT nur ``wf-mehr``:
                # Der Name steht auch im Stilblock, den jedes Bild
                # mitbringt — die Prüfung wäre immer wahr gewesen und
                # hätte nie etwas gemeldet. Die Gegenprobe (Vermerk
                # abschalten → muss rot werden) hat das gefasst,
                # 27.08.2026.
                zeigt_es = '<text class="wf-mehr"' in Workflowbild(weg).svg()
            except Exception:
                zeigt_es = False
            if zeigt_es:
                continue
            befunde.append(Befund(
                str(weg.einstieg.datei),
                u'Bild verschweigt seine Grenze: %s' % weg.einstieg.titel,
                u'%d Klassen in %d Schritten gezeichnet — dahinter geht der '
                u'Weg weiter, und das Bild sagt es nicht.'
                % (len(weg.klassen), len(weg.schritte)),
                Befund.HINWEIS))
        return befunde

    def _nicht_in_der_liste(self, liste):
        u"""Wege, die schwer genug wären, aber nicht mehr hineinpassen.

        Der Deckel hält die Liste lesbar. Was er abschneidet, ist damit
        NICHT dokumentiert — und das gehört gesagt statt verschwiegen.
        """
        uebrig = (liste.kennzahlen.get('einstiege', 0) - liste.verworfen
                  - len(liste.wege))
        if uebrig <= 0:
            return []
        return [Befund(
            'djangobase/umbau/workflows.py',
            u'%d Wege über der Grenze, aber nicht gezeichnet' % uebrig,
            u'Sie berühren mindestens %d Klassen und wären damit '
            u'dokumentationswürdig, passen aber nicht mehr in die Liste von '
            u'%d.' % (getattr(self, '_grenze', 0), getattr(self, '_deckel', 0)),
            Befund.HINWEIS)]

