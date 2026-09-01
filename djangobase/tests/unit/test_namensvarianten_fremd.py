# -*- coding: utf-8 -*-
u"""Vorgefundene Namen sind keine Schreibweisen.

DER ANLASS (3DTools, 31.08.2026)
================================
Von 21 Befunden „in einer Sprache" waren SIEBZEHN Knochennamen fremder
Skelettformate::

    lcollar | lCollar · lcollar · l_collar | in einer Sprache

``lCollar`` heisst in Daz Genesis so, ``l_collar`` in MocapNET,
``LeftShoulder`` in Mixamo. Das sind drei FORMATE und nicht drei
Schreibweisen eines Namens. Wer dem Vorschlag folgt und sie angleicht,
macht drei Zuordnungstabellen kaputt — dieselbe teuerste Sorte
Fehlalarm wie ein Loeschvorschlag fuer lebenden Code
(``~/.claude/rules/analysewerkzeuge.md``).

Erkannt wird das an der ROLLE der Zeichenkette, nicht am Ordner und
nicht am Dateinamen. Fremdnamen stehen einer ZUORDNUNG gegenueber::

    BONE_MAP = {'lcollar': 'DEF-shoulder.L', ...}    # ab 12 Paaren
    skeleton.left_arm.shoulder = 'lCollar'           # Blender-Vorgabe

Nach der Schaerfung blieben von 21 noch 4 — und die vier waren echt.

DIE GEGENPROBE STEHT MIT DRIN: `EinEchterBruch` und `EineKleineTabelle`
halten fest, dass der Pruefer nicht blind geworden ist.

BDD - GEGEBEN / DANN
====================
    EineZuordnungstabelle    ... ihre Namen brechen nicht
    EineAttributvorgabe      ... auch nicht
    EineOrdnerkonstante      ... auch nicht
    EineKleineTabelle        ... zaehlt nicht als Zuordnung
    EinGewoehnlicherWert     ... bleibt ein Drahtname
    EinEchterBruch           ... wird weiter gemeldet
"""
from djangobase.skills.namensvarianten import Namensvarianten

from .test_neue_werkzeuge import WerkzeugBasis


def _tabelle(paare):
    zeilen = ',\n    '.join("'%s': 'DEF-%s'" % (a, b) for a, b in paare)
    return "BONE_MAP = {\n    %s,\n}\n" % zeilen


#: Zwoelf Paare — gerade genug, um als Zuordnung zu gelten.
GENUG = [('bone%02d' % i, 'ziel.%02d' % i) for i in range(12)]


class EineZuordnungstabelle(WerkzeugBasis):
    u"""Gegeben: Zwei Dateien mit den Namen zweier Fremdformate."""

    def test_die_namen_brechen_nicht(self):
        projekt = self.projekt({
            'mocapnet.py': _tabelle(GENUG + [('lcollar', 'shoulder.L')]),
            'daz.py': _tabelle(GENUG + [('l_collar', 'shoulder.L')]),
        })
        zeilen = projekt.fahren(Namensvarianten)
        echte = [z for z in zeilen if z['bruch'] == 'in einer Sprache']
        self.assertEqual(echte, [], echte)


class EineAttributvorgabe(WerkzeugBasis):
    u"""Gegeben: Eine Blender-Vorgabedatei, die Fremdnamen zuweist."""

    def test_die_namen_brechen_nicht(self):
        projekt = self.projekt({
            'daz.py': ("skeleton.left_arm.shoulder = 'lCollar'\n"
                       "skeleton.left_leg.foot = 'lFoot'\n"),
            'mixamo.py': ("skeleton.left_arm.shoulder = 'l_collar'\n"
                          "skeleton.left_leg.foot = 'l_foot'\n"),
        })
        echte = [z for z in projekt.fahren(Namensvarianten)
                 if z['bruch'] == 'in einer Sprache']
        self.assertEqual(echte, [], echte)


class EinPfadbestandteil(WerkzeugBasis):
    u"""Gegeben: Zwei Ordnernamen, die auf der Platte verschieden heissen.

    ``.../photoTo3D/SMPLX`` und ``.../3DObjects/SMPL-X`` sind ZWEI
    Verzeichnisse. Sie anzugleichen hiesse, einen Pfad zu erfinden, den
    es nicht gibt.
    """

    def test_die_ordner_brechen_nicht(self):
        projekt = self.projekt({
            'a.py': ("import os\n"
                     "ZIEL = os.path.join('A:', 'daten', 'SMPLX')\n"),
            'b.py': ("from pathlib import Path\n"
                     "QUELLE = Path('A:', 'objekte', 'SMPL-X')\n"),
        })
        echte = [z for z in projekt.fahren(Namensvarianten)
                 if z['bruch'] == 'in einer Sprache']
        self.assertEqual(echte, [], echte)


class EineKleineTabelle(WerkzeugBasis):
    u"""Gegeben: Ein Woerterbuch mit drei Eintraegen — keine Zuordnung.

    GEGENPROBE: Eine Handvoll Einstellungen darf nicht als
    Fremdformat durchgehen, sonst waere jede Zeichenkette entschuldigt.
    """

    def test_der_bruch_wird_gemeldet(self):
        projekt = self.projekt({
            'a.py': "EINSTELLUNG = {'bildRate': 30, 'x': 1, 'y': 2}\n",
            'b.py': "ANDERE = {'bild_rate': 60, 'p': 1, 'q': 2}\n",
        })
        zeilen = projekt.fahren(Namensvarianten)
        treffer = [z for z in zeilen if z['kern'] == 'bildrate']
        self.assertTrue(treffer, zeilen)
        self.assertEqual(treffer[0]['bruch'], 'in einer Sprache',
                         treffer[0])


class EinEchterBruch(WerkzeugBasis):
    u"""Gegeben: Dieselbe Sache, zweimal verschieden BENANNT.

    GEGENPROBE: Der Pruefer muss weiter finden, wofuer es ihn gibt.
    """

    def test_er_wird_gemeldet(self):
        projekt = self.projekt({
            'schreiber.py': "def sichern(meta_data):\n    return meta_data\n",
            'leser.py': "def laden(metaData):\n    return metaData\n",
        })
        zeilen = projekt.fahren(Namensvarianten)
        treffer = [z for z in zeilen if z['kern'] == 'metadata']
        self.assertTrue(treffer, zeilen)
        self.assertEqual(treffer[0]['bruch'], 'in einer Sprache',
                         treffer[0])


class EineOrdnerkonstante(WerkzeugBasis):
    u"""Gegeben: Ein Verzeichnisname in einer Konstante.

    DER ANLASS (3DTools, 01.09.2026): `ORDNER = 'photoTo3D'` neben der
    Adresse `photo_to_3d` galt als zwei Schreibweisen EINES Namens.
    Der Ordner heisst auf der Platte aber so — angleichen hiesse, die
    Daten nicht mehr zu finden.
    """

    def test_der_ordnername_bricht_nicht(self):
        projekt = self.projekt({
            'ablage.py': "class A:\n    ORDNER = 'photoTo3D'\n",
            'adressen.py': "def weg():\n    return photo_to_3d\n",
        })
        zeilen = projekt.fahren(Namensvarianten)
        treffer = [z for z in zeilen if z['kern'] == 'phototo3d']
        for zeile in treffer:
            self.assertNotEqual(zeile['bruch'], 'in einer Sprache', zeile)


class EinGewoehnlicherWert(WerkzeugBasis):
    u"""Gegeben: Eine Zeichenkette in einer Konstante OHNE Ordnerbezug.

    GEGENPROBE zur Ordnerkonstante: Nur Namen wie `ORDNER` oder
    `VERZEICHNIS` deuten auf die Platte. Eine gewoehnliche Konstante
    bleibt ein Drahtname und wird weiter verglichen.
    """

    def test_er_wird_weiter_gemeldet(self):
        projekt = self.projekt({
            'a.py': "class A:\n    MODUS = 'schnellLauf'\n",
            'b.py': "class B:\n    ANDERER = 'schnell_lauf'\n",
        })
        zeilen = projekt.fahren(Namensvarianten)
        treffer = [z for z in zeilen if z['kern'] == 'schnelllauf']
        self.assertTrue(treffer, zeilen)
        self.assertEqual(treffer[0]['bruch'], 'in einer Sprache', treffer[0])
