# -*- coding: utf-8 -*-
u"""Welches Modul wirklich eine Klasse werden sollte — und welches nicht.

DIE ANSAGE (Edgar, 26.08.2026)
=============================
    „füge das als neuen Werkzeug-Code-Review-Testfall ein: Umbau von Modul
     in Klassen wenn … [vier Fragen]"

und, im selben Atemzug, die Gegenseite:

    „Django-Ansichten, Befehle, Templatetags … Reine Funktionen … Der
     Preis: 20 Aufrufstellen ändern, um ein Modul aus einem Zähler zu
     nehmen. Und jede rein statische Klasse ist eine neue Wurzel."

Beide Hälften sind hier festgehalten. Ein Werkzeug, das nur antreibt und
den Preis verschweigt, macht mehr Arbeit als es spart — `freie-funktionen`
hat mit 285 Befunden genau das getan, und niemand hat sie durchgearbeitet.

WARUM DIE FRAGEN UND NICHT DIE ZAHL
===================================
Gemessen an CamTrack am 26.08.2026: **806** Funktionen auf Modulebene,
aber nur **fünf** Stellen mit veränderlichem Modulzustand — davon zwei
Django-Konvention. Zwei Module wurden an dem Tag umgebaut, und **genau ein
echter Fehler** kam heraus: `marzahn_pi` führte Host-Suche und
Tailscale-Status an derselben Sperre, ein `tailscale status` mit acht
Sekunden Frist blockierte jeden `base_url()`-Aufruf.

Der Fehler steckte im Zustand, nicht in der Funktionszahl.
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden
from djangobase.skills.befund import Befund

from ..base import BasisTest


def _lauf(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='kr_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    werkzeug = werkzeug_finden('klassenreif')
    werkzeug.wurzel = lambda: ordner
    return werkzeug.pruefen()


def _fragen(satz):
    u"""``{pfad: {Nummern}}`` — welche Fragen je Modul mit Ja beantwortet
    wurden.

    Als MENGE, nicht als Text: Bei mehreren steht dort „Frage 1, 3 mit Ja
    beantwortet", und ein `'Frage 3' in ...` findet das nicht. Meine erste
    Fassung dieser Pruefungen ist genau daran gescheitert — an der eigenen
    Zusicherung, nicht am Werkzeug.
    """
    import re
    raus = {}
    for b in satz.befunde:
        treffer = re.search(r'Frage ([\d, ]+) mit Ja', b.was)
        raus[b.ort] = ({int(z) for z in treffer.group(1).split(',')}
                       if treffer else set())
    return raus


class Frage1Zustand(BasisTest):
    u"""Gibt es Zustand, den jemand besitzen und zurücksetzen muss?

    `mqtt.py` hatte drei Modul-Globale und zwei `global`-Anweisungen. Eine
    Prüfung, die den Zwischenspeicher leeren wollte, musste
    `mqtt._client = None` schreiben — an Interna fassen.
    """

    MIT_GLOBAL = ('_client = None\n\n\n'
                  'def hole():\n'
                  '    global _client\n'
                  '    if _client is None:\n'
                  '        _client = object()\n'
                  '    return _client\n')

    def test_global_wird_erkannt(self):
        satz = _lauf({'speicher.py': self.MIT_GLOBAL})
        self.assertIn(1, _fragen(satz).get('speicher.py', set()))

    def test_der_name_steht_im_beleg(self):
        u"""„Frage 1 mit Ja" allein hilft niemandem beim Nachsehen."""
        satz = _lauf({'speicher.py': self.MIT_GLOBAL})
        self.assertIn('_client', satz.befunde[0].warum)

    def test_eine_sammlung_auf_modulebene_zaehlt_auch(self):
        satz = _lauf({'ablage.py': '_stand = {}\n\n\n'
                                   'def merken(x):\n'
                                   '    _stand.update(x)\n'})
        self.assertIn(1, _fragen(satz).get('ablage.py', set()))

    def test_eine_konstante_ist_kein_zustand(self):
        u"""GROSS geschrieben heisst Vorgabe. Beides mitzuzählen macht aus
        fünf echten Stellen 130 — und das sieht sich niemand an."""
        satz = _lauf({'vorgaben.py': 'GRENZEN = {"a": 1}\n\n\n'
                                     'def lesen():\n'
                                     '    return GRENZEN\n'})
        self.assertEqual(satz.befunde, [])

    def test_all_ist_keine_zustandsvariable(self):
        satz = _lauf({'paket.py': '__all__ = ["a"]\n\n\n'
                                  'def a():\n    return 1\n'})
        self.assertEqual(satz.befunde, [])


class Frage2Gefaedelt(BasisTest):
    u"""Werden dieselben Werte durch viele Funktionen gefädelt?

    `matcher.py`: neun Funktionen, jede mit `(rule, event_type, data,
    jetzt)`. Das ist ein Konstruktor, den niemand geschrieben hat.
    """

    DREI = ('def eins(regel, daten):\n    return 1\n\n\n'
            'def zwei(regel, daten):\n    return 2\n\n\n'
            'def drei(regel, daten):\n    return 3\n')

    def test_drei_gleiche_koepfe_reichen(self):
        satz = _lauf({'tore.py': self.DREI})
        self.assertIn(2, _fragen(satz).get('tore.py', set()))

    def test_die_argumente_stehen_im_beleg(self):
        satz = _lauf({'tore.py': self.DREI})
        self.assertIn('regel, daten', satz.befunde[0].warum)

    def test_zwei_reichen_nicht(self):
        satz = _lauf({'tore.py': ('def eins(a, b):\n    return 1\n\n\n'
                                  'def zwei(a, b):\n    return 2\n')})
        self.assertEqual(satz.befunde, [])

    def test_ein_gemeinsames_argument_reicht_nicht(self):
        u"""`(request)` haben alle Ansichten — das ist kein Konstruktor."""
        satz = _lauf({'tore.py': ('def eins(x):\n    return 1\n\n\n'
                                  'def zwei(x):\n    return 2\n\n\n'
                                  'def drei(x):\n    return 3\n')})
        self.assertEqual(satz.befunde, [])


class NurWennDerAufruferDieWerteHaelt(BasisTest):
    u"""Frage 2 gilt nur, wenn es etwas zu halten GIBT.

    Fehlalarm vom 26.08.2026: `app/services/config/parser.py` wurde
    gemeldet — vier Funktionen mit ``(key, default)``. Der Kopf stimmte,
    die Schlussfolgerung nicht. Jeder Aufruf lautet ``get_int('RETENTION_'
    'DAYS', 30)``: die Werte stehen frisch da, der Aufrufer haelt nichts.
    Ein Konstruktor haette dort bei jedem Aufruf etwas anderes bedeutet.

    Der Unterschied zu einem echten Fund ist mechanisch nachlesbar — nicht
    am Kopf der Funktion, sondern an der Aufrufstelle.
    """

    VIER = ('def get_int(key, default):\n    return 1\n\n\n'
            'def get_str(key, default):\n    return 2\n\n\n'
            'def get_bool(key, default):\n    return 3\n')

    def test_literale_an_der_aufrufstelle_sind_kein_konstruktor(self):
        satz = _lauf({'leser.py': self.VIER,
                      'nutzer.py': ('from leser import get_int, get_str\n\n\n'
                                    'def laden():\n'
                                    "    return get_int('TAGE', 30), get_str('X', '')\n")})
        self.assertEqual([b.ort for b in satz.befunde], [])

    def test_gehaltene_werte_bleiben_ein_fund(self):
        satz = _lauf({'leser.py': self.VIER,
                      'nutzer.py': ('from leser import get_int\n\n\n'
                                    'def laden(schluessel, vorgabe):\n'
                                    '    return get_int(schluessel, vorgabe)\n')})
        self.assertIn(2, _fragen(satz).get('leser.py', set()))

    def test_ein_attribut_zaehlt_als_gehalten(self):
        u"""``cam.ip_address`` ist gehalten — genau der onvif-Fall."""
        satz = _lauf({'leser.py': self.VIER,
                      'nutzer.py': ('from leser import get_int\n\n\n'
                                    'def laden(cam):\n'
                                    '    return get_int(cam.schluessel, cam.vorgabe)\n')})
        self.assertIn(2, _fragen(satz).get('leser.py', set()))

    def test_ein_literal_unter_gehaltenen_reicht_nicht(self):
        u"""``get_int('THUMB_FFMPEG_TIMEOUT', _GRENZE)`` — der Schluessel
        steht frisch da, nur der Vorgabewert ist gehalten. Genau daran ist
        meine erste Fassung mit ``any`` haengengeblieben."""
        satz = _lauf({'leser.py': self.VIER,
                      'nutzer.py': ('from leser import get_int\n\n'
                                    'GRENZE = 30\n\n\n'
                                    'def laden():\n'
                                    "    return get_int('TIMEOUT', GRENZE)\n")})
        self.assertEqual([b.ort for b in satz.befunde], [])

    def test_ohne_jeden_aufrufer_bleibt_der_fund_stehen(self):
        u"""Was niemand aufruft, laesst sich nicht widerlegen."""
        satz = _lauf({'leser.py': self.VIER})
        self.assertIn(2, _fragen(satz).get('leser.py', set()))


class Frage3ZweiAnliegen(BasisTest):
    u"""Liegen zwei Anliegen im selben Modul und teilen sich Zustand?

    `marzahn_pi.py` — Host-Suche und Tailscale-Status an EINER Sperre,
    nicht aus Absicht, sondern weil eine Datei nur eine hatte.
    """

    GETRENNT = ('_hosts = {}\n'
                '_tailnet = {}\n'
                '\n\n'
                'def finde_host():\n'
                '    return _hosts.get("a")\n'
                '\n\n'
                'def lies_tailnet():\n'
                '    return _tailnet.get("b")\n')

    def test_zwei_getrennte_zustaende_werden_erkannt(self):
        satz = _lauf({'zwei.py': self.GETRENNT})
        self.assertIn(3, _fragen(satz).get('zwei.py', set()))

    def test_beide_namen_stehen_im_beleg(self):
        satz = _lauf({'zwei.py': self.GETRENNT})
        self.assertIn('_hosts', satz.befunde[0].warum)
        self.assertIn('_tailnet', satz.befunde[0].warum)

    def test_wer_beide_anfasst_hat_ein_anliegen(self):
        u"""Zwei Wörterbücher, die dieselbe Funktion führt, sind EIN
        Anliegen mit zwei Ablagen — kein Fall für Frage 3."""
        satz = _lauf({'eins.py': ('_a = {}\n_b = {}\n\n\n'
                                  'def fuehren():\n'
                                  '    _a.update(_b)\n')})
        self.assertNotIn(3, _fragen(satz).get('eins.py', set()))


class Frage4MehrAlsEines(BasisTest):
    u"""Braucht es mehr als ein Exemplar?

    `_FRAME_STATE[(rule.pk, cam_id, person_id)]` ist eine
    Instanzverwaltung, die noch keine Klasse hat.
    """

    def test_ein_berechneter_schluessel_zaehlt(self):
        satz = _lauf({'zaehler.py': ('_stand = {}\n\n\n'
                                     'def zaehle(a, b):\n'
                                     '    k = (a, b)\n'
                                     '    _stand[k] = 1\n')})
        self.assertIn(4, _fragen(satz).get('zaehler.py', set()))

    def test_ein_fester_schluessel_ist_eine_tabelle(self):
        u"""`_state['host']` ist eine Ablage mit festen Feldern, keine
        Instanzverwaltung."""
        satz = _lauf({'tabelle.py': ('_stand = {}\n\n\n'
                                     'def setze():\n'
                                     "    _stand['host'] = 'a'\n")})
        self.assertNotIn(4, _fragen(satz).get('tabelle.py', set()))


class WoDieFunktionRichtigSteht(BasisTest):
    u"""DIE GEGENSEITE (Edgar, 26.08.2026)

        „Django-Ansichten, Befehle, Templatetags — `def
         meine_ansicht(request)` ist die Schreibweise des Rahmenwerks.
         101 der 285 gemeldeten Module sind Ansichten."

    Diese Pfade werden GAR NICHT erst gefragt. Nicht weil dort nie etwas
    schiefginge, sondern weil die Antwort feststeht: Der Rahmen ruft die
    Funktion, nicht eine Klasse.
    """

    MIT_ZUSTAND = ('_zwischen = {}\n\n\n'
                   'def eine(request):\n'
                   '    _zwischen.update({})\n'
                   '    return 1\n')

    def test_ansichten_werden_nicht_gefragt(self):
        satz = _lauf({'views/seiten.py': self.MIT_ZUSTAND})
        self.assertEqual(satz.befunde, [])

    def test_befehle_ebenso(self):
        satz = _lauf({'management/commands/lauf.py': self.MIT_ZUSTAND})
        self.assertEqual(satz.befunde, [])

    def test_templatetags_ebenso(self):
        satz = _lauf({'templatetags/filter.py': self.MIT_ZUSTAND})
        self.assertEqual(satz.befunde, [])

    def test_urls_und_admin_ebenso(self):
        satz = _lauf({'urls.py': self.MIT_ZUSTAND,
                      'admin.py': self.MIT_ZUSTAND})
        self.assertEqual(satz.befunde, [])

    def test_reine_funktionen_ohne_zustand_bleiben_still(self):
        u"""`_in_static_window(t, start, end)` und `_erste_ipv4(...)` haben
        keinen Zustand und gehören in kein Objekt."""
        satz = _lauf({'rechnen.py': ('def fenster(t, start, ende):\n'
                                     '    return start <= t <= ende\n\n\n'
                                     'def erste(liste):\n'
                                     '    return liste[0] if liste else None\n')})
        self.assertEqual(satz.befunde, [])

    def test_der_kopf_nennt_die_ausgenommenen(self):
        u"""Weglassen wäre schlimmer als melden: Dann wüsste niemand, dass
        das Werkzeug dort bewusst nicht hinsieht."""
        satz = _lauf({'views/a.py': self.MIT_ZUSTAND,
                      'rechnen.py': 'def f(x):\n    return x\n'})
        self.assertTrue(any('gar nicht erst gefragt' in z for z in satz.kopf))


class DerPreisStehtDabei(BasisTest):
    u"""    „Der Preis: 20 Aufrufstellen ändern, um ein Modul aus einem
         Zähler zu nehmen. Und jede rein statische Klasse ist eine neue
         Wurzel."

    Gemessen: `marzahn_pi` kostete sieben Aufrufstellen in vier Dateien,
    und `objektwurzeln` stieg von 37 auf 39 — ein Befund gegen einen
    anderen getauscht. Das gehört in den Befund, bevor jemand anfängt.
    """

    ZUSTAND = ('_stand = {}\n\n\n'
               'def merken(x):\n'
               '    _stand.update(x)\n')

    def test_jeder_befund_nennt_den_preis(self):
        satz = _lauf({'ablage.py': self.ZUSTAND})
        self.assertIn('Preis:', satz.befunde[0].warum)

    def test_die_neue_wurzel_wird_genannt(self):
        satz = _lauf({'ablage.py': self.ZUSTAND})
        self.assertIn('objektwurzeln', satz.befunde[0].warum)

    def test_die_zahl_der_einfuehrenden_dateien(self):
        satz = _lauf({'ablage.py': self.ZUSTAND,
                      'nutzer.py': 'from ablage import merken\n\n\n'
                                   'def tun():\n    return merken({})\n'})
        eintrag = [b for b in satz.befunde if b.ort == 'ablage.py'][0]
        self.assertIn('Preis: 1 Datei', eintrag.warum)


class DasGewichtFolgtDerSchwere(BasisTest):

    def test_eine_frage_ist_eine_warnung(self):
        satz = _lauf({'a.py': ('_stand = {}\n\n\n'
                               'def f():\n    _stand.clear()\n')})
        self.assertEqual(satz.befunde[0].gewicht, Befund.WARNUNG)

    def test_zwei_fragen_sind_ein_fehler(self):
        u"""Zustand UND zwei Anliegen ist genau der Fall, an dem
        `marzahn_pi` einen echten Fehler versteckt hatte."""
        satz = _lauf({'a.py': Frage3ZweiAnliegen.GETRENNT})
        self.assertEqual(satz.befunde[0].gewicht, Befund.FEHLER)

    def test_ein_leeres_projekt_bleibt_still(self):
        satz = _lauf({})
        self.assertEqual(satz.befunde, [])
        self.assertTrue(satz.kopf)
