# -*- coding: utf-8 -*-
u"""Die Kriterien-Blöcke auf ``/hilfe/skills/`` fragen die Registrierung.

DIE FRAGE (Edgar, 26.08.2026)
=============================
    „warum ist Logging & Tests auf http://localhost:8000/hilfe/skills/ noch
     anders, mit anderen Nummern usw?"
    „auch Klassen & Zustand?"

Sie war berechtigt. Der Block „Logging & Tests" lief über eine Liste von
drei von Hand eingetragenen Werkzeugen (``skills.EIGENE``). Nachgemessen
trugen aber FÜNF das Kriterium 16 oder 17::

    Kr 16  jsstumm          Stille Rückmeldung          FEHLTE
    Kr 16  schreibrouten    Ansicht schreibt auf GET    FEHLTE
    Kr 16  protokoll        Logging                     dabei
    Kr 17  testaufbau       Tests gegliedert            dabei
    Kr 17  testdeckung      Tests: was hat gar keinen?  dabei

Zwei Werkzeuge liefen also nie mit, wenn jemand „Logging & Tests prüfen"
drückte — und niemand sah es, weil die Karte ihre eigene Liste zeigte
statt der Registrierung.

Der Block zu Kriterium 18 machte es längst richtig, und sein Kommentar
sagte auch warum: „Hier wird gefragt statt aufgezählt." Der ältere Block
daneben tat es nicht. Genau die Sorte Fehler, die keine andere Prüfung
sieht: Die Seite antwortet, die Werkzeuge laufen, die Karte sieht
vollständig aus.

Diese Prüfung hält beide Blöcke an der Registrierung fest.
"""
from djangobase.skills import werkzeuge
from djangobase.views.skills import SkillsView

from ..base import BasisTest


def _slugs(*nummern):
    u"""Was die Registrierung zu diesen Kriterien führt."""
    gesucht = set(nummern)
    return sorted(w.slug for w in werkzeuge()
                  if getattr(w, 'kriterium', 0) in gesucht)


class BeideBloeckeKommenAusDerRegistrierung(BasisTest):

    def test_logging_und_tests_zeigt_alle_werkzeuge_zu_16_und_17(self):
        gezeigt = sorted(w.slug for w in SkillsView._zu_kriterien(16, 17))
        self.assertEqual(gezeigt, _slugs(16, 17),
                         'Die Karte „Logging & Tests" fuehrt eine eigene '
                         'Liste — dann laeuft sie an der Registrierung '
                         'vorbei, so wie bis zum 26.08.2026.')

    def test_klassen_und_zustand_zeigt_alle_werkzeuge_zu_18(self):
        gezeigt = sorted(w.slug for w in SkillsView._zu_kriterien(18))
        self.assertEqual(gezeigt, _slugs(18))

    def test_der_sammellauf_faehrt_genau_die_gezeigten(self):
        u"""Ein Knopf, der etwas anderes faehrt als die Karte zeigt, ist
        schlimmer als kein Knopf."""
        self.assertEqual(sorted(SkillsView._k1617_slugs()), _slugs(16, 17))
        self.assertEqual(sorted(SkillsView._k18_slugs()), _slugs(18))

    def test_die_beiden_bloecke_ueberschneiden_sich_nicht(self):
        self.assertEqual(set(_slugs(16, 17)) & set(_slugs(18)), set())


class JedesKriteriumMitWerkzeugenHatEinenPlatz(BasisTest):
    u"""Der Fehler von 2026-08-19, allgemein gefasst.

    Damals kam Kriterium 18 dazu und erschien NIRGENDS auf der Seite — die
    Werkzeuge liefen, aber der Auftrag, zu dem sie gehören, stand nicht da.
    Behoben wurde damals nur der eine Block.

    Diese Prüfung meldet, sobald ein Kriterium Werkzeuge trägt, für das es
    keinen Block gibt. Sie schreibt keinen vor — sie sagt nur Bescheid,
    bevor es wieder jemandem auffällt statt der Prüfung.
    """

    #: Kriterien, die einen eigenen Sammellauf-Block auf der Seite haben.
    MIT_BLOCK = {16, 17, 18}

    #: Kriterien, die absichtlich NUR in der großen Tabelle stehen — sie
    #: gehören zum laufenden Umbau, nicht zu einer Frage am Ende.
    OHNE_BLOCK_GEWOLLT = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}

    def test_kein_kriterium_faellt_zwischen_die_bloecke(self):
        vorhanden = {getattr(w, 'kriterium', 0) for w in werkzeuge()}
        unbekannt = vorhanden - self.MIT_BLOCK - self.OHNE_BLOCK_GEWOLLT
        self.assertEqual(
            unbekannt, set(),
            'Kriterium %s traegt Werkzeuge, steht aber in keinem Block der '
            'Seite und auch nicht in der Ausnahmeliste. Entweder einen Block '
            'dafuer anlegen oder es hier eintragen — sonst laufen die '
            'Werkzeuge, und der Auftrag dazu steht nirgends.'
            % sorted(unbekannt))
