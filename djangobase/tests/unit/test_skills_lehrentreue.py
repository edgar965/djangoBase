# -*- coding: utf-8 -*-
u"""Lehrentreue — findet es die fünf prüfbaren Regeln, und nur die?

DIE ANSAGE (Edgar, 26.08.2026)
==============================
    „die lehren sollen die testcases beinhalten. du machst doch immer
     gleiche fixes, kannst du die werkzeuge dazu nicht speichern??"

Zehn der 22 Lehren hatten kein Werkzeug. Fünf davon sind ein Muster im
Quelltext und damit auffindbar; die anderen fünf sind Abwägungen
(„erst messen", „vorher ein Netz aufnehmen"), für die ein Werkzeug nur
Fehlalarme erzeugen würde.

WAS DAS WERKZEUG AM ERSTEN TAG GEFUNDEN HAT
===========================================
Vier ``values_list(...).distinct()`` ohne ``order_by()``. Django hängt
``Meta.ordering`` an die Auswahl an, und aus ``SELECT DISTINCT slug`` wird
``SELECT DISTINCT slug, created_at``:

    recluster_persons    6279 Zeilen statt 502 für dieselben 502 Paare
    camera_detection     acht gleiche Werte, gemeldet als „gemischt"

Der zweite ist ein echter Fehler in der Oberfläche — er fiel nur nicht
auf, weil zufällig zwei verschiedene fps eingestellt waren.
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden
from djangobase.skills.befund import Befund
from djangobase.skills.lehren_review import LEHREN

from ..base import BasisTest


def _lauf(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='lt_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    werkzeug = werkzeug_finden('lehren-treue')
    werkzeug.wurzel = lambda: ordner
    return werkzeug.pruefen()


def _lehren(satz):
    return {b.was.rsplit(u'„', 1)[-1].rstrip(u'")') for b in satz.befunde}


class EsFindetDieFuenfMuster(BasisTest):

    def test_wegwerf_datei_ohne_zielverzeichnis(self):
        satz = _lauf({'a.py': 'import tempfile\n\n\n'
                              'def f():\n    return tempfile.mkdtemp()\n'})
        self.assertIn('keine-temp-dateien-im-system', _lehren(satz))

    def test_unique_mit_achse(self):
        satz = _lauf({'a.py': 'import numpy as np\n\n\n'
                              'def f(p):\n    return np.unique(p, axis=0)\n'})
        self.assertIn('unique-axis-vermeiden', _lehren(satz))

    def test_add_at(self):
        satz = _lauf({'a.py': 'import numpy as np\n\n\n'
                              'def f(s, i, w):\n    np.add.at(s, i, w)\n'})
        self.assertIn('bincount-statt-add-at', _lehren(satz))

    def test_nachbarsuche_ohne_workers(self):
        satz = _lauf({'a.py': 'from scipy.spatial import cKDTree\n\n\n'
                              'def f(p):\n'
                              '    return cKDTree(p).query(p, k=2)\n'})
        self.assertIn('kdtree-workers', _lehren(satz))

    def test_distinct_ohne_ordnung(self):
        satz = _lauf({'a.py': 'def f(qs):\n'
                              "    return qs.values_list('x').distinct()\n"})
        self.assertIn('meta-ordering-distinct', _lehren(satz))

    def test_distinct_wiegt_schwerer(self):
        u"""Es ist das einzige Muster, das ein falsches ERGEBNIS liefert."""
        satz = _lauf({'a.py': 'def f(qs):\n'
                              "    return qs.values_list('x').distinct()\n"})
        self.assertEqual(satz.befunde[0].gewicht, Befund.FEHLER)


class EsMeldetNichtsFalsches(BasisTest):

    def test_mit_zielverzeichnis_ist_es_richtig(self):
        satz = _lauf({'a.py': 'import tempfile\n\n\n'
                              'def f():\n'
                              "    return tempfile.mkdtemp(dir='p/tmp')\n"})
        self.assertEqual(satz.befunde, [])

    def test_unique_ohne_achse_ist_richtig(self):
        satz = _lauf({'a.py': 'import numpy as np\n\n\n'
                              'def f(p):\n    return np.unique(p)\n'})
        self.assertEqual(satz.befunde, [])

    def test_bincount_ist_die_loesung_nicht_der_befund(self):
        satz = _lauf({'a.py': 'import numpy as np\n\n\n'
                              'def f(i, w):\n'
                              '    return np.bincount(i, weights=w)\n'})
        self.assertEqual(satz.befunde, [])

    def test_query_ohne_kdtree_zaehlt_nicht(self):
        u"""``.query()`` heisst anderswo etwas ganz anderes — bei Django
        zum Beispiel das SQL einer Abfrage."""
        satz = _lauf({'a.py': 'def f(qs):\n    return str(qs.query)\n\n\n'
                              'def g(client):\n'
                              "    return client.query('etwas')\n"})
        self.assertEqual(satz.befunde, [])

    def test_distinct_mit_ordnung_ist_richtig(self):
        satz = _lauf({'a.py': 'def f(qs):\n'
                              "    return qs.order_by().values_list('x')"
                              '.distinct()\n'})
        self.assertEqual(satz.befunde, [])

    def test_distinct_ohne_values_list_zaehlt_nicht(self):
        u"""``Model.objects.distinct()`` allein hat das Problem nicht."""
        satz = _lauf({'a.py': 'def f(qs):\n    return qs.distinct()\n'})
        self.assertEqual(satz.befunde, [])


class JedeGemeldeteLehreGibtEsAuch(BasisTest):

    def test_die_genannten_lehren_stehen_in_LEHREN(self):
        satz = _lauf({'a.py': 'import numpy as np\n'
                              'import tempfile\n'
                              'from scipy.spatial import cKDTree\n\n\n'
                              'def f(p, s, i, w, qs):\n'
                              '    tempfile.mkdtemp()\n'
                              '    cKDTree(p).query(p)\n'
                              '    np.unique(p, axis=0)\n'
                              '    np.add.at(s, i, w)\n'
                              "    return qs.values_list('x').distinct()\n"})
        bekannt = {l.slug for l in LEHREN}
        self.assertTrue(_lehren(satz) <= bekannt,
                        'Gemeldet, aber keine Lehre: %s'
                        % (_lehren(satz) - bekannt))
        self.assertEqual(len(_lehren(satz)), 5)

    def test_die_fuenf_lehren_zeigen_zurueck_auf_das_werkzeug(self):
        u"""Auf beiden Seiten dasselbe: Die Lehre nennt ihr Werkzeug, das
        Werkzeug nennt seine Lehre."""
        fuenf = ('meta-ordering-distinct', 'unique-axis-vermeiden',
                 'bincount-statt-add-at', 'kdtree-workers',
                 'keine-temp-dateien-im-system')
        da = {l.slug: l for l in LEHREN}
        for slug in fuenf:
            with self.subTest(lehre=slug):
                self.assertIn('lehren-treue', da[slug].werkzeuge)


class DerKopfZaehltJeLehre(BasisTest):

    def test_ohne_befund_steht_es_ausdruecklich_da(self):
        satz = _lauf({'a.py': 'x = 1\n'})
        self.assertTrue(any('Keiner' in z for z in satz.kopf), satz.kopf)

    def test_mit_befunden_steht_die_verteilung_da(self):
        satz = _lauf({'a.py': 'import tempfile\n\n\n'
                              'def f():\n'
                              '    return tempfile.mkdtemp(), tempfile.mkstemp()\n'})
        self.assertTrue(any('keine-temp-dateien-im-system' in z
                            for z in satz.kopf), satz.kopf)
