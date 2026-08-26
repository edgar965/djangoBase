# -*- coding: utf-8 -*-
u"""Ein Gedankenstrich darf keine Prüfung reißen.

DER BEFUND (25.08.2026)
=======================
`GrundtestWerkzeugkatalog.test_katalog_steht_im_bericht` — der erste
Grundtest überhaupt — druckt alle 57 Werkzeuge mit Titel und Zweck. Auf
einer Windows-Konsole stürzte er ab::

    UnicodeEncodeError: 'charmap' codec can't encode character
    '\\u2192' in position 8181: character maps to <undefined>

`sys.stdout.encoding` ist dort **cp1252**, die Vorgabe. Der Katalog selbst
ist sauber in ASCII geschrieben („Hilfe -> Skills", „Einträge") — der
Pfeil kam aus den TEXTEN der Werkzeuge. Nachgezählt tragen **über 30 der
57** Gedankenstriche, Anführungszeichen oder Pfeile.

Das ist richtig so: Ein Bericht soll lesbar sein. Falsch war, dass die
Ausgabe daran zerbricht. Ein Schreiber, der bei einem Gedankenstrich eine
Prüfung reißen lässt, zwingt jeden Aufrufer zu ASCII — und dann steht in
den Berichten „läuft" statt „läuft".

WARUM UMSETZEN UND NICHT NUR ERSETZEN
=====================================
``errors='replace'`` allein macht aus „→" ein „?" und aus dem Katalog eine
Wand voller Fragezeichen — fast so wertlos wie der Absturz. Die Liste
setzt die Handvoll Zeichen um, die dieses Projekt wirklich benutzt; erst
was sie nicht kennt, wird ersetzt.
"""
import io

from djangobase.jobctx import TimestampedStream

from ..base import BasisTest


class _Strom:
    u"""Ein Strom, der behauptet, nur cp1252 zu können — und es einhält.

    Kein ``io.StringIO``-Abkömmling: Dessen ``encoding`` ist
    schreibgeschützt (``AttributeError: attribute 'encoding' of
    '_io._TextIOBase' objects is not writable``), und genau dieses Feld
    muss der Test stellen können.
    """

    def __init__(self, kodierung='cp1252'):
        self.encoding = kodierung
        self._teile = []

    def write(self, text):
        # Genau das, was die echte Konsole tut: Was nicht kodierbar ist,
        # wirft. Ohne diese Zeile prüfte der Test nichts.
        if self.encoding:
            text.encode(self.encoding)
        self._teile.append(text)
        return len(text)

    def flush(self):
        pass

    def getvalue(self):
        return ''.join(self._teile)


def _schreiben(text, kodierung='cp1252'):
    ziel = _Strom(kodierung)
    strom = TimestampedStream(ziel)
    strom.write(text)
    strom.flush()
    return ziel.getvalue()


class EinPfeilReisstNichtsMehr(BasisTest):

    def test_der_pfeil_wird_umgesetzt(self):
        u"""``→`` ist das Zeichen, an dem der Katalog zerbrach."""
        self.assertIn('->', _schreiben(u'Kachel → Strom\n'))

    def test_die_deutsche_typografie_bleibt_stehen(self):
        u"""cp1252 KANN Gedankenstrich und Anführungszeichen.

        Nachgemessen: ``— – „ " " ' ' … · •`` sind alle in cp1252
        enthalten; nur ``→ ← ✅ ❌ ⚠`` fehlen. Ein Fix, der vorsorglich
        alles umsetzt, verschlechterte die Ausgabe ohne Grund — also
        wird nur umgesetzt, was der Strom wirklich nicht kann.
        """
        ergebnis = _schreiben(u'er sagte „so nicht" — und ging …\n')
        self.assertIn(u'„so nicht"', ergebnis)
        self.assertIn(u'—', ergebnis)

    def test_bei_engerer_kodierung_greift_die_umsetzung_doch(self):
        u"""latin-1 kann den Gedankenstrich NICHT — dort trägt die Liste."""
        ergebnis = _schreiben(u'gemessen — nicht geraten\n', 'latin-1')
        self.assertIn('--', ergebnis)
        self.assertNotIn(u'—', ergebnis)

    def test_was_die_liste_nicht_kennt_wird_ersetzt(self):
        u"""Lieber ein Fragezeichen als ein abgebrochener Bericht."""
        ergebnis = _schreiben(u'Zustand: 中\n')
        self.assertIn('?', ergebnis)

    def test_umlaute_bleiben_umlaute(self):
        u"""ä, ö, ü und ß KANN cp1252 — sie dürfen nicht angefasst werden.

        Sonst löst dieser Fix genau das Problem aus, gegen das die harte
        Regel „Umlaute direkt schreiben" antritt.
        """
        self.assertIn(u'läuft grün, größer, weiß',
                      _schreiben(u'läuft grün, größer, weiß\n'))


class AufUtf8BleibtAllesWieEsIst(BasisTest):

    def test_der_pfeil_ueberlebt(self):
        self.assertIn(u'→', _schreiben(u'Kachel → Strom\n', 'utf-8'))

    def test_auch_was_die_liste_nicht_kennt(self):
        self.assertIn(u'中', _schreiben(u'Zustand: 中\n', 'utf-8'))


class DerRestBleibtWieVorher(BasisTest):

    def test_der_zeitstempel_steht_weiter_davor(self):
        ergebnis = _schreiben(u'eine Zeile\n')
        self.assertRegex(ergebnis, r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ')

    def test_eine_schon_gestempelte_zeile_bekommt_keinen_zweiten(self):
        ergebnis = _schreiben(u'2026-08-25 12:00:00 schon fertig\n')
        self.assertEqual(ergebnis.count('2026-08-25'), 1)

    def test_teilstuecke_werden_bis_zum_umbruch_gesammelt(self):
        u"""Sonst bekäme jeder tqdm-Tick einen eigenen Zeitstempel."""
        ziel = _Strom()
        strom = TimestampedStream(ziel)
        strom.write(u'halb')
        self.assertEqual(ziel.getvalue(), '')
        strom.write(u' und ganz\n')
        self.assertIn('halb und ganz', ziel.getvalue())

    def test_ein_strom_ohne_kodierung_wirft_nicht(self):
        u"""``getattr(..., 'encoding', None)`` kann None liefern."""
        ziel = io.StringIO()
        strom = TimestampedStream(ziel)
        strom.write(u'Kachel → Strom\n')
        strom.flush()
        self.assertIn(u'→', ziel.getvalue())
