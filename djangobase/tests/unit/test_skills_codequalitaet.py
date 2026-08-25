# -*- coding: utf-8 -*-
u"""Das eine Werkzeug im Ordner, das nicht selbst misst.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „fixe alle Fehler … und baue das Tool auch in die Code Review skills ein"

WARUM ES HIER ANDERS LÄUFT
==========================
Die übrigen Werkzeuge sind selbst geschrieben, weil sie Fragen stellen,
die kein Standardwerkzeug kennt („welche Klasse hält diese freie
Funktion?"). Komplexität, Wartbarkeit, tote Namen und PEP 8 sind dagegen
seit Jahren gelöst — `radon`, `pyflakes` und `pycodestyle` können das
besser, als ich es nachbauen würde.

DER FUND, DER DIE NOQA-REGEL ERZWANG
====================================
Der erste Lauf meldete **299 Meldungen, davon 245 unbenutzte Einfuhren**.
Nachgezählt trugen **211 davon ein `# noqa`** — die öffentliche
Schnittstelle der Pakete. Es blieben 19 echte Funde, darunter eine
Testmethode, die in derselben Klasse zweimal denselben Namen trug und
deshalb **nie lief**. Ein Bericht, in dem 211 gewollte Zeilen 19 echte
zudecken, wird weggeklickt — und findet dann gar nichts mehr.
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden
from djangobase.skills.befund import Befund

from ..base import BasisTest


class DasWerkzeugIstAngemeldet(BasisTest):

    def test_es_ist_ueber_den_slug_zu_finden(self):
        self.assertIsNotNone(werkzeug_finden('code-qualitaet'))

    def test_es_steht_in_der_liste_der_werkzeuge(self):
        from djangobase.skills import werkzeuge
        self.assertIn('code-qualitaet', [w.slug for w in werkzeuge()])

    def test_es_nennt_seine_werkzeuge_im_titel(self):
        u"""Damit nachlesbar ist, WER das behauptet."""
        titel = werkzeug_finden('code-qualitaet').titel
        for name in ('radon', 'pyflakes', 'pycodestyle'):
            self.assertIn(name, titel)

    def test_es_hat_einen_anlassfall(self):
        u"""Ein Werkzeug ohne Selbsttest kann still nichts mehr finden."""
        self.assertIsNotNone(werkzeug_finden('code-qualitaet').anlassfall)


class WasEsMeldet(BasisTest):

    QUELLE = (
        u'import os\n'
        u'import sys\n'
        u'\n'
        u'\n'
        u'def viel(a):\n'
        + u''.join(u'    if a == %d:\n        return %d\n' % (i, i)
                   for i in range(14))
    )

    def _satz(self, dateien):
        ordner = Path(tempfile.mkdtemp(prefix='cq_skill_'))
        for name, inhalt in dateien.items():
            ziel = ordner / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding='utf-8')
        werkzeug = werkzeug_finden('code-qualitaet')
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen()

    def test_ein_sauberes_projekt_bleibt_still(self):
        satz = self._satz({'gut.py': u'def wenig():\n    return 1\n'})
        self.assertFalse(satz.befunde)
        self.assertTrue(satz.kopf)

    def test_die_verwickelte_funktion_steht_drin(self):
        satz = self._satz({'schlecht.py': self.QUELLE})
        self.assertTrue(any('viel' in b.was for b in satz.befunde))

    def test_der_ort_traegt_die_zeilennummer(self):
        u"""Ohne sie ist ein Befund eine Behauptung ohne Adresse."""
        satz = self._satz({'schlecht.py': self.QUELLE})
        orte = [b.ort for b in satz.befunde if 'viel' in b.was]
        self.assertTrue(orte and ':' in orte[0], orte)

    def test_der_kopf_nennt_jedes_verfahren(self):
        satz = self._satz({'schlecht.py': self.QUELLE})
        kopf = ' '.join(satz.kopf)
        for teil in (u'Komplexität', u'Wartbarkeitsindex', u'Echte Fehler',
                     u'Stil'):
            self.assertIn(teil, kopf)


class NichtAllesIstGleichDringend(BasisTest):
    u"""Ein undefinierter Name ist ein Fehler, eine lange Zeile eine
    Formsache. Beides gleich zu gewichten ist der Grund, warum solche
    Berichte weggeklickt werden."""

    def _gewichte(self, dateien):
        ordner = Path(tempfile.mkdtemp(prefix='cq_gew_'))
        for name, inhalt in dateien.items():
            (ordner / name).write_text(inhalt, encoding='utf-8')
        werkzeug = werkzeug_finden('code-qualitaet')
        werkzeug.wurzel = lambda: ordner
        return dict((b.was, b.gewicht) for b in werkzeug.pruefen().befunde)

    def test_stil_ist_nur_ein_hinweis(self):
        gewichte = self._gewichte({'a.py': u'x = "%s"\n' % ('y' * 120)})
        stil = [g for w, g in gewichte.items() if 'Stil' in w]
        self.assertEqual(set(stil), {Befund.HINWEIS})

    def test_rang_f_ist_ein_fehler(self):
        viel = (u'def sehr(a):\n'
                + u''.join(u'    if a == %d:\n        return %d\n' % (i, i)
                           for i in range(45)))
        gewichte = self._gewichte({'a.py': viel})
        komplex = [g for w, g in gewichte.items() if 'Komplex' in w]
        self.assertIn(Befund.FEHLER, komplex)

    def test_ein_undefinierter_name_ist_ein_fehler(self):
        gewichte = self._gewichte(
            {'a.py': u'def machen():\n    return gibtsnicht\n'})
        fehler = [g for w, g in gewichte.items() if 'Echte Fehler' in w]
        self.assertEqual(set(fehler), {Befund.FEHLER})


class NoqaZaehltNichtAlsFund(BasisTest):
    u"""DER FUND VOM 24.08.2026: 211 von 245 waren ausdrücklich gewollt."""

    def _fehlerzeile(self, quelle):
        ordner = Path(tempfile.mkdtemp(prefix='cq_noqa_'))
        (ordner / 'a.py').write_text(quelle, encoding='utf-8')
        werkzeug = werkzeug_finden('code-qualitaet')
        werkzeug.wurzel = lambda: ordner
        satz = werkzeug.pruefen()
        return ([z for z in satz.kopf if 'Echte Fehler' in z] or [''])[0], satz

    def test_eine_markierte_einfuhr_ist_kein_befund(self):
        zeile, satz = self._fehlerzeile(u'import os  # noqa: F401\n')
        self.assertFalse([b for b in satz.befunde if 'Echte Fehler' in b.was])
        self.assertIn('0 Meldungen', zeile)

    def test_sie_wird_aber_gezaehlt_und_genannt(self):
        u"""Weggelassen wäre sie unsichtbar — und dann wüsste niemand,
        wie viele Ausnahmen im Projekt stehen."""
        zeile, _satz = self._fehlerzeile(u'import os  # noqa: F401\n')
        self.assertIn('1 ausdrücklich erlaubt', zeile)

    def test_ohne_marke_zaehlt_es_beim_zustaendigen_werkzeug(self):
        u"""Eine tote Einfuhr führt `tote-importe` — hier steht nur noch
        die Zahl, damit der Befund nicht verschwindet.

        „merge, keine Duplikate!" (Edgar, 25.08.2026). `pyflakes` meldet
        unbenutzte Einfuhren, und genau die meldet `tote-importe` seit
        Kriterium 5 — mit Wissen, das `pyflakes` nicht hat.
        """
        zeile, satz = self._fehlerzeile(u'import os\n')
        self.assertFalse([b for b in satz.befunde if 'Echte Fehler' in b.was])
        self.assertIn('tote-importe', zeile)

    def test_eine_unbenutzte_variable_bleibt_hier(self):
        u"""Nicht alles wandert ab — nur was ein eigenes Werkzeug hat."""
        _zeile, satz = self._fehlerzeile(
            u'def machen():\n    x = 1\n    return 2\n')
        self.assertTrue([b for b in satz.befunde if 'Echte Fehler' in b.was])


class GarKeineKappung(BasisTest):
    u"""DIE ANSAGE (Edgar, 24.08.2026)

        „die code qualität in den werkzeugen soll auch die fehler messen
         und als findings zurückgeben"

    Hier stand `JE_VERFAHREN = 8`. Das Werkzeug HATTE 217 Komplexitätsfunde
    und gab acht zurück — dieselbe stille Kappung wie beim vorigen Mal
    („der test soll sie alle melden"). Weder Ansicht noch Vorlage kappen
    etwas; die Acht waren allein meine.
    """

    def _satz(self, wie_viele):
        ordner = Path(tempfile.mkdtemp(prefix='cq_kapp_'))
        for i in range(wie_viele):
            (ordner / ('m%d.py' % i)).write_text(
                u'def viel%d(a):\n' % i
                + u''.join(u'    if a == %d:\n        return %d\n' % (j, j)
                           for j in range(14)), encoding='utf-8')
        werkzeug = werkzeug_finden('code-qualitaet')
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen()

    def test_jeder_fund_kommt_zurueck(self):
        satz = self._satz(12)
        komplex = [b for b in satz.befunde if 'Komplex' in b.was]
        self.assertEqual(len(komplex), 12)

    def test_nichts_wird_auf_spaeter_vertroestet(self):
        u"""Kein „… n weitere" mehr — es gibt keine weiteren."""
        satz = self._satz(12)
        self.assertFalse([b for b in satz.befunde if 'weitere' in b.was])

    def test_das_schwerste_steht_vorn(self):
        u"""Bei über zweihundert Befunden entscheidet die Reihenfolge
        darüber, ob jemand das Wichtige sieht."""
        ordner = Path(tempfile.mkdtemp(prefix='cq_reih_'))
        (ordner / 'lang.py').write_text(u'x = "%s"\n' % ('y' * 120),
                                        encoding='utf-8')
        (ordner / 'sehr.py').write_text(
            u'def sehr(a):\n'
            + u''.join(u'    if a == %d:\n        return %d\n' % (i, i)
                       for i in range(45)), encoding='utf-8')
        werkzeug = werkzeug_finden('code-qualitaet')
        werkzeug.wurzel = lambda: ordner
        gewichte = [b.gewicht for b in werkzeug.pruefen().befunde]
        self.assertEqual(gewichte, sorted(
            gewichte, key=lambda g: {Befund.FEHLER: 0, Befund.WARNUNG: 1,
                                     Befund.HINWEIS: 2}.get(g, 3)))


class EineGescheiterteMessungIstEinFund(BasisTest):
    u"""DER STUMME ZWEIG (24.08.2026)

    Jede Messung stand hinter einem `except: continue`. Eine Datei ohne
    gültige Syntax verschwand damit aus der Statistik UND aus dem Bericht
    — dabei ist sie der schwerste Fund, den es gibt. Genau so meldete
    `pycodestyle` einen ganzen Lauf lang „0 Abweichungen in 0 Regeln",
    während jede einzelne Datei am `assert not kwargs` scheiterte.
    """

    def _satz(self):
        ordner = Path(tempfile.mkdtemp(prefix='cq_panne_'))
        (ordner / 'gut.py').write_text(u'def eins():\n    return 1\n',
                                       encoding='utf-8')
        (ordner / 'kaputt.py').write_text(u'def (:\n', encoding='utf-8')
        werkzeug = werkzeug_finden('code-qualitaet')
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen()

    def test_die_kaputte_datei_wird_gemeldet(self):
        gescheitert = [b for b in self._satz().befunde
                       if 'gescheitert' in b.was]
        self.assertTrue(gescheitert)
        self.assertEqual(gescheitert[0].ort, 'kaputt.py')

    def test_sie_wiegt_am_schwersten(self):
        gescheitert = [b for b in self._satz().befunde
                       if 'gescheitert' in b.was]
        self.assertEqual(gescheitert[0].gewicht, Befund.FEHLER)

    def test_der_grund_steht_dabei(self):
        u"""„Ging nicht" ist keine Auskunft."""
        gescheitert = [b for b in self._satz().befunde
                       if 'gescheitert' in b.was]
        self.assertIn('SyntaxError', gescheitert[0].warum)

    def test_je_datei_eine_zeile(self):
        u"""Eine kaputte Datei lässt alle Verfahren scheitern — vier
        gleichlautende Zeilen sagen nicht mehr als eine."""
        gescheitert = [b for b in self._satz().befunde
                       if 'gescheitert' in b.was]
        self.assertEqual(len(gescheitert), 1)
        self.assertIn('Syntax', gescheitert[0].was)

    def test_der_kopf_nennt_die_zahl(self):
        u"""Sonst steht darunter eine Statistik über 1 Datei, die wie eine
        über 2 aussieht."""
        self.assertTrue(any('gescheitert' in z for z in self._satz().kopf))

    def test_die_gute_datei_wird_trotzdem_gemessen(self):
        u"""Ein Fehlschlag darf nicht den ganzen Lauf kosten."""
        self.assertTrue(any('1 Dateien unter' in z or '0 von 1' in z
                            for z in self._satz().kopf))
