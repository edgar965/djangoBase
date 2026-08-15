# -*- coding: utf-8 -*-
"""Wächter: Zwei gleichzeitige Speichervorgänge dürfen keine Änderung verlieren.

WARUM (Review 13.08.2026, mit Gegenprobe belegt)
------------------------------------------------
Das SCHREIBEN der Einstellungsdatei war schon unteilbar (Nebendatei +
`os.replace`) — das Lesen-Ändern-Schreiben nicht:

    Ausgangsstand            {'titel': 'Anfangswert', 'sidebar_default': 250}
    nacheinander gespeichert {'titel': 'von A',       'sidebar_default': 999}
    verschränkt gespeichert  {'titel': 'Anfangswert', 'sidebar_default': 999}

Zwei Vorgänge, die VERSCHIEDENE Gruppen speichern, lasen denselben Stand; der
zweite schrieb seine Gruppe plus die ALTEN Werte der ersten zurück. Die Änderung
der ersten war still verschwunden — kein Fehler, keine Meldung.

Das betrifft alle Projekte, die djangoBase einbinden; zwei offene
Einstellungs-Tabs genügen. Deshalb steht der Fall hier als Test und nicht nur
als Notiz.
"""
import tempfile
import threading
from pathlib import Path

from django.test import SimpleTestCase

from djangobase import store


class StoreSperreTest(SimpleTestCase):

    def setUp(self):
        self.datei = Path(tempfile.mkdtemp(prefix='store-test-')) / 'einstellungen.json'
        self._echt = store._pfad
        store._pfad = lambda: self.datei
        self.addCleanup(self._wiederherstellen)
        store.speichern({'titel': 'Anfangswert', 'sidebar_default': 250})

    def _wiederherstellen(self):
        store._pfad = self._echt

    def test_zwei_gruppen_gleichzeitig_verlieren_nichts(self):
        """Der eigentliche Fall: zwei Tabs, zwei Gruppen, gleichzeitig gespeichert."""
        start = threading.Barrier(2)
        fehler = []

        def speichern(gruppe, werte):
            try:
                start.wait(timeout=5)          # beide so gleichzeitig wie möglich
                for _ in range(15):            # mehrfach, um das Fenster zu treffen
                    store.speichern_gruppe(gruppe, werte)
            except Exception as e:             # noqa: BLE001
                fehler.append(repr(e))

        faeden = [
            threading.Thread(target=speichern, args=('website', {'titel': 'von A'})),
            threading.Thread(target=speichern, args=('djangobase', {'sidebar_default': 999})),
        ]
        for f in faeden:
            f.start()
        for f in faeden:
            f.join(30)

        self.assertEqual(fehler, [])
        werte = store.laden()
        self.assertEqual(werte.get('titel'), 'von A',
                         'die Änderung der Gruppe "website" ist verloren gegangen')
        self.assertEqual(werte.get('sidebar_default'), 999,
                         'die Änderung der Gruppe "djangobase" ist verloren gegangen')

    def test_verschachtelter_aufruf_blockiert_nicht(self):
        """`speichern_gruppe` ruft intern `laden()` und `speichern()` auf.

        Mit einer einfachen (nicht wiedereintrittsfähigen) Sperre wäre das ein
        Selbstblock — der Test würde hier hängen bleiben statt fehlzuschlagen,
        deshalb steht er ausdrücklich hier."""
        store.speichern_gruppe('website', {'titel': 'verschachtelt'})
        self.assertEqual(store.laden().get('titel'), 'verschachtelt')

    def test_liegengebliebene_sperrdatei_blockiert_nicht_dauerhaft(self):
        """Stirbt ein Prozess mit gehaltener Sperre, darf niemand aussperrt sein.

        Nach kurzem Warten wird trotzdem gespeichert — ein verlorenes Speichern
        wäre schlimmer als ein unwahrscheinliches Wettrennen."""
        sperre = self.datei.with_suffix(self.datei.suffix + '.lock')
        sperre.write_text('', encoding='utf-8')
        try:
            store._Sperre.VERSUCHE, alt = 2, store._Sperre.VERSUCHE
            store.speichern_gruppe('website', {'titel': 'trotz Sperre'})
            self.assertEqual(store.laden().get('titel'), 'trotz Sperre')
        finally:
            store._Sperre.VERSUCHE = alt
            sperre.unlink()
