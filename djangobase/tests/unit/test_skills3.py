"""Tests fuer den Skills-Werkzeugkasten.

Zwei Dinge sollen die Tests festhalten:

1. Die Werkzeuge laufen in JEDEM Projekt durch, ohne Konfiguration und ohne
   eine Ausnahme nach oben durchzureichen — sie sind ein Hilfsmittel, und ein
   Hilfsmittel darf die Hilfe-Seite nicht zerlegen.
2. Der Stand der Lehren wird richtig gespeichert und ist im Auslieferungs-
   zustand vollstaendig aktiv.

Der Lehren-Stand liegt in einer Datei neben den Einstellungen; die Tests lenken
ihn auf eine Temp-Datei um, damit sie den echten Stand des Host-Projekts nicht
ueberschreiben.
"""
import tempfile
from pathlib import Path

# Dieser Test gehoert zum ALTEN Werkzeugkasten. Er hiess bis zum
# 17.08.2026 skills und heisst seither skills3 — der Name
# skills gehoert jetzt dem zusammengefuehrten Master.
from djangobase.skills3 import WERKZEUGE, werkzeug_finden, werkzeuge
from djangobase.skills.lehren_review import BEREICHE, LEHREN, Lehrenstand
from djangobase.skills.werkzeug_alt import Ausgabe, Befund, Ergebnis, Werkzeug

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


class WerkzeugGrundlagenTest(BasisTest):

    def test_jedes_werkzeug_hat_die_pflichtangaben(self):
        for klasse in WERKZEUGE:
            with self.subTest(werkzeug=klasse.__name__):
                for feld in ('slug', 'name', 'zweck', 'wann', 'dauer'):
                    self.assertTrue(getattr(klasse, feld),
                                    '%s fehlt %s' % (klasse.__name__, feld))

    def test_kennungen_sind_eindeutig(self):
        slugs = [k.slug for k in WERKZEUGE]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_werkzeug_finden(self):
        self.assertIsNotNone(werkzeug_finden(WERKZEUGE[0].slug))
        self.assertIsNone(werkzeug_finden('gibtsnicht'))

    def test_eingabe_hat_drei_teile(self):
        for klasse in WERKZEUGE:
            if klasse.eingabe is not None:
                with self.subTest(werkzeug=klasse.__name__):
                    self.assertEqual(len(klasse.eingabe), 3)

    def test_fehler_wird_gefangen_nicht_geworfen(self):
        """Ein kaputtes Werkzeug darf die Seite nicht mitnehmen."""

        class Kaputt(Werkzeug):
            slug, name = 'kaputt', 'Kaputt'

            def pruefen(self, **_argumente):
                raise ValueError('absichtlich')

        ergebnis = Kaputt().laufen()
        self.assertIn('absichtlich', ergebnis.fehler)
        self.assertIn('ValueError', ergebnis.fehler)
        self.assertFalse(ergebnis.sauber)

    def test_dauer_wird_gemessen(self):
        class Schnell(Werkzeug):
            slug, name = 'schnell', 'Schnell'

            def pruefen(self, **_argumente):
                return Ergebnis(self.name)

        self.assertGreaterEqual(Schnell().laufen().dauer_s, 0.0)


class ErgebnisTest(BasisTest):

    def test_ohne_befunde_ist_sauber(self):
        self.assertTrue(Ergebnis('X').sauber)
        self.assertIn('Nichts gefunden', Ergebnis('X').text())

    def test_text_enthaelt_kopf_und_befunde(self):
        ergebnis = Ergebnis('X', ['zwei Dateien'],
                            [Befund('a.py:1', 'tot: n', 'weil')])
        text = ergebnis.text()
        self.assertIn('zwei Dateien', text)
        self.assertIn('a.py:1', text)
        self.assertIn('weil', text)
        self.assertIn('1 Befunde', text)
        self.assertFalse(ergebnis.sauber)

    def test_fehler_steht_im_text(self):
        self.assertIn('FEHLER: kaputt', Ergebnis('X', fehler='kaputt').text())


class AusgabeTest(BasisTest):
    """Die Textbox-Sammlung: Abschnitte je Werkzeug, Anhaengen statt Ersetzen."""

    class Beispiel(Werkzeug):
        slug, name = 'beispiel', 'Beispiel'

    def test_leere_sammlung(self):
        self.assertEqual(Ausgabe().text(), '')
        self.assertEqual(Ausgabe('   ').text(), '')

    def test_abschnitt_hat_ueberschrift_mit_kennung(self):
        text = (Ausgabe()
                .anhaengen(self.Beispiel(), Ergebnis('Beispiel', ['zwei Dateien']))
                .text())
        self.assertIn('# Beispiel  [beispiel]', text)
        self.assertIn('zwei Dateien', text)
        self.assertIn('nichts gefunden', text)

    def test_zwei_abschnitte_sind_getrennt(self):
        sammlung = Ausgabe()
        sammlung.anhaengen(self.Beispiel(), Ergebnis('A'))
        sammlung.anhaengen(self.Beispiel(), Ergebnis('B'))
        self.assertEqual(sammlung.text().count(Ausgabe.LINIE), 4)

    def test_bisheriger_inhalt_bleibt_vorne(self):
        text = Ausgabe('VORHER').anhaengen(self.Beispiel(), Ergebnis('A')).text()
        self.assertTrue(text.startswith('VORHER'))

    def test_befundzahl_steht_im_kopf(self):
        text = Ausgabe().anhaengen(
            self.Beispiel(),
            Ergebnis('A', befunde=[Befund('a.py:1', 'x')])).text()
        self.assertIn('1 Befunde', text)


class WerkzeugeLaufenTest(BasisTest):
    """Die Werkzeuge, die ohne Netz und ohne Endpunkte auskommen."""

    def test_dateilastige_werkzeuge_laufen_durch(self):
        for werkzeug in werkzeuge():
            if werkzeug.ruft_endpunkte_auf:
                continue     # eigener Test — die brauchen den Test-Client
            with self.subTest(werkzeug=werkzeug.slug):
                argumente = ({werkzeug.eingabe[0]: werkzeug.eingabe[2]}
                             if werkzeug.eingabe else {})
                ergebnis = werkzeug.laufen(**argumente)
                self.assertEqual(ergebnis.fehler, '')
                self.assertTrue(ergebnis.kopf)

    def test_vorlagen_variablen_setzt_den_zaehler_zurueck(self):
        """Bleibt der Zaehler haengen, verlangsamt er jede weitere Anfrage."""
        from django.template.base import Variable
        vorher = Variable._resolve_lookup
        werkzeug_finden('vorlagen-variablen').laufen(weg='/')
        self.assertIs(Variable._resolve_lookup, vorher)


class LehrenTest(LehrenstandIsolation, BasisTest):

    def setUp(self):
        super().setUp()
        self.lehren_isolieren()

    def test_jede_lehre_ist_vollstaendig(self):
        for lehre in LEHREN:
            with self.subTest(lehre=lehre.slug):
                self.assertTrue(lehre.titel)
                self.assertTrue(lehre.regel)
                self.assertTrue(lehre.warum, 'ohne Begruendung keine Regel')
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

    def test_neue_lehre_ist_an_ohne_erneutes_speichern(self):
        """Wer eine Lehre ergaenzt, soll sie nicht erst ankreuzen muessen."""
        Lehrenstand.speichern({LEHREN[0].slug})
        stand = Lehrenstand.laden()
        self.assertIn(LEHREN[-1].slug, stand)
        # Nur der gespeicherte Stand zaehlt — die uebrigen stehen auf aus,
        # weil sie beim Speichern bewusst abgewaehlt wurden.
        self.assertFalse(stand[LEHREN[-1].slug])

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


class SkillsSeiteTest(LehrenstandIsolation, BasisTest):
    """Die Seite selbst — rendern, Werkzeug starten, Stand speichern."""

    def setUp(self):
        super().setUp()
        self.lehren_isolieren()
        self.klient = self.staff_client()

    def url(self):
        from django.urls import reverse
        return reverse('djangobase:skills3')

    def test_seite_rendert(self):
        antwort = self.klient.get(self.url())
        self.assertEqual(antwort.status_code, 200)
        self.assertContains(antwort, 'Werkzeuge')
        self.assertContains(antwort, 'Lehren')

    def test_alle_werkzeuge_stehen_in_der_tabelle(self):
        antwort = self.klient.get(self.url())
        for klasse in WERKZEUGE:
            self.assertContains(antwort, klasse.name)

    def test_unbekannte_kennung_startet_nichts(self):
        """Ausgefuehrt wird nur, was in der Liste steht."""
        antwort = self.klient.get(self.url(), {'run': 'rm -rf /'})
        self.assertEqual(antwort.status_code, 200)
        self.assertEqual(antwort.context['gelaufen'], [])
        self.assertEqual(antwort.context['ausgabe'], '')

    def test_werkzeug_laeuft_ueber_die_seite(self):
        antwort = self.klient.get(self.url(), {'run': 'tote-importe'})
        self.assertEqual(antwort.status_code, 200)
        self.assertEqual(antwort.context['gelaufen'], ['tote-importe'])
        self.assertIn('tote-importe', antwort.context['ausgabe'])

    def test_stapellauf_trennt_die_abschnitte(self):
        """Mehrere Werkzeuge in einem Lauf — je Werkzeug eine Ueberschrift."""
        antwort = self.klient.post(self.url(), {
            'werkzeug': ['tote-importe', 'klassen-je-datei']})
        text = antwort.context['ausgabe']
        self.assertIn('[tote-importe]', text)
        self.assertIn('[klassen-je-datei]', text)
        self.assertEqual(text.count('=' * 78), 4)   # zwei Linien je Abschnitt

    def test_vorheriger_inhalt_bleibt_erhalten(self):
        """Die Textbox schickt ihren Stand mit und wird ergaenzt, nicht ersetzt."""
        antwort = self.klient.post(self.url(), {
            'werkzeug': ['tote-importe'], 'ausgabe': 'ALTER INHALT'})
        text = antwort.context['ausgabe']
        self.assertTrue(text.startswith('ALTER INHALT'))
        self.assertIn('[tote-importe]', text)

    def test_vorgabefeld_wird_uebernommen(self):
        antwort = self.klient.post(self.url(), {
            'werkzeug': ['klassen-je-datei'], 'arg_klassen-je-datei': '99'})
        self.assertIn('mindestens 99 Klassen', antwort.context['ausgabe'])

    def test_tabelle_hat_eine_zeile_je_werkzeug(self):
        tabelle = self.klient.get(self.url()).context['tabelle']
        self.assertEqual(len(tabelle['zeilen']), len(WERKZEUGE))
        self.assertEqual(tabelle['key'], 'db-skills')

    def test_speichern_setzt_den_stand(self):
        eine = LEHREN[0].slug
        antwort = self.klient.post(self.url(), {'aktion': 'lehren',
                                                'lehre': [eine]})
        self.assertEqual(antwort.status_code, 302)
        stand = Lehrenstand.laden()
        self.assertTrue(stand[eine])
        self.assertFalse(stand[LEHREN[1].slug])

    def test_auftragstext_kommt_als_textdatei(self):
        antwort = self.klient.get(self.url(), {'auftrag': '1'})
        self.assertEqual(antwort.status_code, 200)
        self.assertTrue(antwort['Content-Type'].startswith('text/plain'))
        self.assertIn('Regeln fuer diesen Umbau', antwort.content.decode('utf-8'))
