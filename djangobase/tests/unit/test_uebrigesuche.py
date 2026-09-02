# -*- coding: utf-8 -*-
u"""Die „Übrigen" einer Endung finden und löschen.

DIE ANSAGE (Edgar, 02.09.2026)
==============================
    „mach mir in der Tabelle bei Statistik, in der Tabelle bei „Übrige"
     einen Button Löschen mit dem ich die die Dinger lösche"

Diese Tests sind kein Formalismus. Der Code löscht echte Dateien
endgültig, und jeder Fall hier steht für eine Art, wie das schiefgehen
kann: die falsche Endung treffen, eine bekannte Dateiart mitnehmen, aus
dem Projekt hinauslaufen, eine Ablage anfassen, die die Zählung
ausdrücklich ausspart.
"""
import tempfile
from pathlib import Path

from django.test import override_settings

from djangobase.umbau.uebrigesuche import UebrigeSuche

from ..base import BasisTest


class UebrigeFindenUndLoeschen(BasisTest):

    def _bauen(self, dateien):
        ordner = Path(tempfile.mkdtemp(prefix='putz_'))
        for name, inhalt in dateien.items():
            ziel = ordner / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding='utf-8')
        return ordner

    def test_findet_nur_die_gesuchte_endung(self):
        o = self._bauen({'a.dump': u'x', 'b.dump': u'x', 'c.log': u'x'})
        namen = sorted(p.name for p in UebrigeSuche(o).finden('.dump'))
        self.assertEqual(namen, ['a.dump', 'b.dump'])

    def test_bekannte_dateiarten_sind_nie_zu_finden(self):
        u"""Der wichtigste Fall: `.py` darf über diesen Weg nicht
        löschbar sein, auch wenn jemand die Endung von Hand schickt."""
        o = self._bauen({'a.py': u'x = 1\n', 'b.html': u'<p>x</p>'})
        self.assertEqual(UebrigeSuche(o).finden('.py'), [])
        self.assertEqual(UebrigeSuche(o).finden('.html'), [])

    def test_ohne_endung_ist_ein_eigener_fall(self):
        o = self._bauen({'Makefile': u'all:\n', 'a.dump': u'x'})
        namen = [p.name for p in UebrigeSuche(o).finden('')]
        self.assertEqual(namen, ['Makefile'])

    def test_laufzeitdaten_bleiben_unberuehrt(self):
        u"""Was die Zählung aussortiert, ist auch nicht löschbar —
        sonst räumte der Knopf `logs/` leer."""
        o = self._bauen({'logs/alt.dump': u'x', 'media/bild.dump': u'x',
                         'echt.dump': u'x'})
        namen = [p.name for p in UebrigeSuche(o).finden('.dump')]
        self.assertEqual(namen, ['echt.dump'])

    def test_angemeldete_ablagen_bleiben_unberuehrt(self):
        o = self._bauen({'archiv/post.dump': u'x', 'echt.dump': u'x'})
        with override_settings(MAIL_ARCHIVE_ROOT=str(o / 'archiv')):
            namen = [p.name for p in UebrigeSuche(o).finden('.dump')]
        self.assertEqual(namen, ['echt.dump'])

    def test_loeschen_entfernt_und_zaehlt(self):
        o = self._bauen({'a.dump': u'xx', 'b.dump': u'xxx',
                         'bleibt.py': u'x = 1\n'})
        bericht = UebrigeSuche(o).loeschen('.dump')
        self.assertEqual(bericht['geloescht'], 2)
        self.assertEqual(bericht['uebersprungen'], 0)
        self.assertEqual(bericht['bytes'], 5)
        self.assertEqual(sorted(p.name for p in o.iterdir()), ['bleibt.py'])

    def test_gegenprobe_die_nachbardatei_ueberlebt(self):
        u"""Ohne diesen Fall belegt der Test oben nur, dass etwas weg
        ist — nicht, dass das Richtige weg ist."""
        o = self._bauen({'a.dump': u'x', 'gleicher_name.py': u'x = 1\n'})
        UebrigeSuche(o).loeschen('.dump')
        self.assertTrue((o / 'gleicher_name.py').exists())

    def test_verzeichnisse_werden_nicht_angefasst(self):
        o = self._bauen({'ordner.dump/darin.txt': u'x'})
        bericht = UebrigeSuche(o).loeschen('.dump')
        self.assertEqual(bericht['geloescht'], 0)
        self.assertTrue((o / 'ordner.dump').is_dir())

    def test_die_letzte_pruefung_weist_fremdes_ab(self):
        u"""``_pruefen`` ist der eigentliche Schutz — er läuft
        unmittelbar vor jedem ``unlink`` und traut dem Aufrufer nicht."""
        o = self._bauen({'a.dump': u'x'})
        fremd = Path(tempfile.mkdtemp(prefix='fremd_')) / 'fremd.dump'
        fremd.write_text(u'x', encoding='utf-8')
        suche = UebrigeSuche(o)
        self.assertEqual(suche._pruefen(fremd, '.dump'),
                         u'ausserhalb des Projekts')
        self.assertEqual(suche._pruefen(o / 'a.dump', '.log'),
                         u'andere Endung')
        self.assertTrue(fremd.exists())

    def test_die_vorschau_nennt_menge_und_pfade(self):
        o = self._bauen(dict(('d%02d.dump' % i, u'x' * 100)
                             for i in range(7)))
        v = UebrigeSuche(o).vorschau('.dump')
        self.assertEqual(v['anzahl'], 7)
        self.assertEqual(v['bytes'], 700)
        self.assertEqual(len(v['pfade']), 7)
        # Die Einheit muss mitwandern — „0,00 MB" war der Anlass.
        self.assertTrue(v['groesse'].endswith('B'), v['groesse'])


class MehrereEndungenAufEinmal(BasisTest):
    u"""Mehrfachauswahl und Sammellöschung (Edgar, 02.09.2026: „mach auch
    Multi Auswahl (check boxen) und batch delete")."""

    DATEIEN = {'a.dump': u'x', 'b.dump': u'xx', 'c.log': u'xxx',
               'Makefile': u'all:\n', 'bleibt.py': u'x = 1\n'}

    def _bauen(self):
        ordner = Path(tempfile.mkdtemp(prefix='putz_multi_'))
        for name, inhalt in self.DATEIEN.items():
            (ordner / name).write_text(inhalt, encoding='utf-8')
        return ordner

    def test_sammeln_trennt_die_endungen(self):
        o = self._bauen()
        gefunden = UebrigeSuche(o).sammeln(['.dump', '.log', ''])
        self.assertEqual(
            dict((e, sorted(p.name for p in pfade))
                 for e, pfade in gefunden.items()),
            {'.dump': ['a.dump', 'b.dump'], '.log': ['c.log'],
             '': ['Makefile']})

    def test_eine_endung_ohne_treffer_bleibt_leer_statt_zu_fehlen(self):
        u"""Ein fehlender Schlüssel liesse den Aufrufer raten."""
        o = self._bauen()
        self.assertEqual(UebrigeSuche(o).sammeln(['.gibtsnicht']),
                         {'.gibtsnicht': []})

    def test_vorschau_mehrere_summiert_und_teilt_auf(self):
        o = self._bauen()
        v = UebrigeSuche(o).vorschau_mehrere(['.dump', '.log'])
        self.assertEqual(v['anzahl'], 3)
        self.assertEqual(v['bytes'], 6)
        # Grösste Gruppe zuerst — sie trägt die Entscheidung.
        self.assertEqual([a['endung'] for a in v['arten']], ['.dump', '.log'])

    def test_loeschen_mehrere_raeumt_alle_gewaehlten(self):
        o = self._bauen()
        b = UebrigeSuche(o).loeschen_mehrere(['.dump', '.log'])
        self.assertEqual(b['geloescht'], 3)
        self.assertEqual(b['bytes'], 6)
        self.assertEqual(sorted(p.name for p in o.iterdir()),
                         ['Makefile', 'bleibt.py'])

    def test_gegenprobe_nicht_gewaehltes_ueberlebt(self):
        u"""Ohne diesen Fall belegt der Test oben nur, dass etwas weg ist."""
        o = self._bauen()
        UebrigeSuche(o).loeschen_mehrere(['.dump'])
        self.assertTrue((o / 'c.log').exists())
        self.assertTrue((o / 'Makefile').exists())

    def test_der_bericht_nennt_jede_endung_einzeln(self):
        o = self._bauen()
        b = UebrigeSuche(o).loeschen_mehrere(['.dump', '.log'])
        self.assertEqual(
            sorted((e['endung'], e['geloescht']) for e in b['je_endung']),
            [('.dump', 2), ('.log', 1)])


class DerBaumWirdBeschnitten(BasisTest):
    u"""Der Geschwindigkeits-Umbau darf das Ergebnis nicht ändern.

    ``os.walk`` betritt ausgeschlossene Verzeichnisse gar nicht erst —
    auf `assistant` 16,5 s → 0,13 s. Gemessen wurde ausserdem, dass beide
    Verfahren dieselben 373 Dateien über 44 Endungen liefern; hier steht
    der Fall, der das im Kleinen festhält.
    """

    def test_ein_ausgeschlossener_baum_wird_nicht_betreten(self):
        ordner = Path(tempfile.mkdtemp(prefix='putz_walk_'))
        for tief in ('logs/a/b/c', 'media/x/y', 'node_modules/p/q'):
            ziel = ordner / tief
            ziel.mkdir(parents=True)
            (ziel / 'tief.dump').write_text(u'x', encoding='utf-8')
        (ordner / 'echt.dump').write_text(u'x', encoding='utf-8')
        namen = [p.name for p in UebrigeSuche(ordner).finden('.dump')]
        self.assertEqual(namen, ['echt.dump'])

    def test_zu_grosse_dateien_bleiben_draussen(self):
        u"""Chrome-Cache-Dateien im Projektbaum sind mehrere MB gross —
        über der Quelltextgrenze und deshalb kein Fall für dieses
        Werkzeug (nachgesehen am 02.09.2026: 4,2 MB je Stück)."""
        ordner = Path(tempfile.mkdtemp(prefix='putz_gross_'))
        (ordner / 'riesig.dump').write_text(u'x' * (3 * 1024 * 1024),
                                            encoding='utf-8')
        (ordner / 'klein.dump').write_text(u'x', encoding='utf-8')
        namen = [p.name for p in UebrigeSuche(ordner).finden('.dump')]
        self.assertEqual(namen, ['klein.dump'])
