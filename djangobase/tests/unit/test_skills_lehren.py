# -*- coding: utf-8 -*-
u"""Die Lehren aus den Code-Reviews - Ankreuzliste, Stand und Auftragstext.

Bis zum 18.08.2026 stand diese Liste auf einer eigenen Seite („Skills3"). Sie
ist entfallen — Skills2 zeigte ohnehin dasselbe wie Skills, und von Skills3
blieb genau dieser Teil uebrig. Er steht jetzt auf der Skills-Seite, und diese
Tests halten fest, dass er dort wirklich funktioniert.

WAS HIER NICHT MEHR STEHT (und warum)
=====================================
Die alten Werkzeug-Tests dieser Datei pruefen die Schnittstelle der frueheren
Basisklasse (``name``, ``eingabe``, ``Ausgabe``). Die Werkzeuge laufen laengst
auf ``Werkzeug`` (``titel``, ``zweck``, ``kriterium``), und ``test_skills.py``
prueft sie dort. Beim Aufloesen von Skills3 habe ich die Datei zunaechst nur
umgebogen — 38 Fehler und ein ``AssertionError: 44 != 33``, weil ein Test der
ALTEN Welt gegen das NEUE Register lief. Genau davor warnt der Modulkopf von
``skills/__init__.py``.

Der Lehren-Stand liegt in einer Datei neben den Einstellungen; die Tests lenken
ihn auf eine Temp-Datei um, damit sie den Stand des Host-Projekts nicht
ueberschreiben.
"""
import tempfile
from pathlib import Path

from django.urls import reverse

from djangobase.skills.lehren_review import BEREICHE, LEHREN, Lehrenstand

from ..base import BasisTest


class LehrenstandIsolation:
    """Lenkt die Lehren-Datei auf eine Temp-Datei um."""

    def lehren_isolieren(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.close()
        self._lehren_tmp = Path(tmp.name)
        self._lehren_tmp.unlink()          # Startzustand: Datei fehlt
        original = Lehrenstand._pfad
        Lehrenstand._pfad = classmethod(lambda cls: self._lehren_tmp)
        self.addCleanup(self._lehren_zurueck, original)

    def _lehren_zurueck(self, original):
        Lehrenstand._pfad = original
        try:
            self._lehren_tmp.unlink()
        except OSError:
            pass


class LehrenTest(LehrenstandIsolation, BasisTest):

    def setUp(self):
        super().setUp()
        self.lehren_isolieren()

    def test_jede_lehre_ist_vollstaendig(self):
        for lehre in LEHREN:
            with self.subTest(lehre=lehre.slug):
                self.assertTrue(lehre.titel)
                self.assertTrue(lehre.regel)
                self.assertTrue(lehre.warum, 'ohne Begründung keine Regel')
                self.assertIn(lehre.bereich, BEREICHE)

    def test_kennungen_sind_eindeutig(self):
        slugs = [lehre.slug for lehre in LEHREN]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_vorgabe_ist_alles_an(self):
        stand = Lehrenstand.laden()
        self.assertEqual(len(stand), len(LEHREN))
        self.assertTrue(all(stand.values()))

    def test_speichern_und_laden(self):
        eine = LEHREN[0].slug
        Lehrenstand.speichern({eine})
        stand = Lehrenstand.laden()
        self.assertTrue(stand[eine])
        self.assertFalse(any(v for k, v in stand.items() if k != eine))

    def test_leere_auswahl_speichert_alles_aus(self):
        Lehrenstand.speichern(set())
        self.assertFalse(any(Lehrenstand.laden().values()))
        self.assertEqual(Lehrenstand.aktive(), [])

    def test_kaputte_datei_faellt_auf_die_vorgabe_zurueck(self):
        self._lehren_tmp.write_text('kein json', encoding='utf-8')
        self.assertTrue(all(Lehrenstand.laden().values()))

    def test_auftragstext_enthaelt_nur_aktive(self):
        eine = LEHREN[0]
        Lehrenstand.speichern({eine.slug})
        text = Lehrenstand.auftragstext()
        self.assertIn(eine.regel, text)
        self.assertIn('Warum:', text)
        andere = next(lehre for lehre in LEHREN if lehre.slug != eine.slug)
        self.assertNotIn(andere.regel, text)


class LehrenAufDerSkillsSeiteTest(LehrenstandIsolation, BasisTest):
    u"""Der Merge selbst: Die Liste muss auf der Skills-Seite bedienbar sein."""

    def setUp(self):
        super().setUp()
        self.lehren_isolieren()
        # Die Hilfe-Seiten sind zugriffsgeschuetzt (ZugriffMixin).
        self.client = self.staff_client()

    @property
    def adresse(self):
        return reverse('djangobase:skills')

    def test_seite_zeigt_jede_lehre(self):
        antwort = self.client.get(self.adresse)
        self.assertEqual(antwort.status_code, 200)
        inhalt = antwort.content.decode('utf-8')
        self.assertEqual(inhalt.count('name="lehre"'), len(LEHREN))
        for bereich in BEREICHE:
            with self.subTest(bereich=bereich):
                self.assertIn(bereich, inhalt)

    def test_speichern_setzt_den_stand(self):
        eine = LEHREN[0].slug
        antwort = self.client.post(self.adresse,
                                   {'aktion': 'lehren', 'lehre': [eine]})
        self.assertEqual(antwort.status_code, 302)
        stand = Lehrenstand.laden()
        self.assertTrue(stand[eine])
        self.assertFalse(any(v for k, v in stand.items() if k != eine))

    def test_auftragstext_kommt_als_textdatei(self):
        antwort = self.client.get(self.adresse + '?auftrag=1')
        self.assertEqual(antwort.status_code, 200)
        self.assertIn('text/plain', antwort['Content-Type'])
        self.assertIn(LEHREN[0].regel, antwort.content.decode('utf-8'))

    def test_die_alten_adressen_sind_weg(self):
        u"""Gegenprobe zum Aufloesen: Skills2/Skills3 gibt es nicht mehr."""
        from django.urls import NoReverseMatch
        for name in ('skills2', 'skills3'):
            with self.subTest(seite=name):
                with self.assertRaises(NoReverseMatch):
                    reverse('djangobase:' + name)
