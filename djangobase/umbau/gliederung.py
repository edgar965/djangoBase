# -*- coding: utf-8 -*-
u"""Rolle im Projekt — die Gliederung, die Klassen und Funktionen teilen.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „mache alle Klassen in allen Tabs und alle Funktionen aus allen Tabs
     auch als Gliederung mit Knöpfen"

Die Gliederung stand im ``Klassenmodell``. Sobald die Funktionen dieselbe
brauchen, gibt es zwei Möglichkeiten: kopieren oder herauslösen. Kopiert
liefen sie beim nächsten Zusatz auseinander — dann steht `views/` in der
einen Liste unter „Ansichten" und in der anderen unter „Übrige".

DIE ROLLE STEHT AM PFAD
=======================
Nicht am Namen: `views/` sind Ansichten, egal wie die Klassen darin heissen,
und `VideoCodecProbe` in `views/` ist keine Prüfung. Ein Django-Projekt hat
immer dieselben Rollen; die Verzeichnisnamen sind Konvention, kein Zufall.

Gemessen an CamTrack/app (1004 Klassen)::

    Tests 445 · Ansichten 227 · Dienste 142 · Erkennung 76 · Aufnahme 57
    Datenmodell 21 · Übrige 17 · Befehle 8 · Oberfläche 6 · Schnittstelle 5
"""

#: Rolle im Projekt, am Pfad erkannt. Die erste passende gewinnt.
ROLLEN = (
    ('Tests', ('tests', 'test')),
    ('Ansichten', ('views', 'view')),
    ('Dienste', ('services', 'service')),
    ('Datenmodell', ('models', 'migrations', 'model')),
    ('Befehle', ('management', 'commands')),
    ('Schnittstelle', ('api', 'api_v1')),
    ('Erkennung', ('detection', 'analysis', 'recognition', 'face_backends')),
    ('Aufnahme', ('live', 'recording', 'integrations')),
    ('Oberflaeche', ('forms', 'templatetags', 'widgets')),
)

#: Was in keine Rolle passt. Faellt nicht weg — sonst stimmt die Summe nicht.
UEBRIGE = 'Uebrige'

#: Bis zu so vielen Eintraegen steht eine Rolle FLACH — ohne die Ebene der
#: Verzeichnisse.
#:
#: WOZU DIE ZWEITE EBENE UEBERHAUPT (24.08.2026, gefragt: „was sollen die
#: untertabs bei Globale Funktionen?")
#: ====================================================================
#: Sie sagt, WO der Code liegt, und zerlegt eine Rolle, die sonst eine Wand
#: waere. Gemessen an CamTrack/app, Funktionen je Rolle::
#:
#:     Ansichten 370 (15 Gruppen)   Aufnahme    42 (5)
#:     Dienste   181 (13)           Uebrige     11 (3)
#:     Tests      96 (5)            Oberflaeche 10 (1)  <- Ebene ohne Nutzen
#:     Erkennung  56 (6)            Befehle      3 (1)  <- ebenso
#:
#: Bei 370 Eintraegen hilft die Ebene, bei 10 ist sie ein Klick ins Leere —
#: und bei EINER Untergruppe sagt sie gar nichts.
FLACH_BIS = 40


def rolle(datei):
    u"""Die Rolle einer Datei — ``'Tests'``, ``'Ansichten'``, …"""
    teile = [t.lower() for t in str(datei).replace('\\', '/').split('/')]
    for etikett, marken in ROLLEN:
        if any(t in marken for t in teile):
            return etikett
        # Auch am Dateinamen: `models.py` ist Datenmodell, `test_x.py` Test.
        letzte = teile[-1].split('.')[0] if teile else ''
        if letzte in marken or (etikett == 'Tests'
                                and teile and teile[-1].startswith('test_')):
            return etikett
    return UEBRIGE


def untergruppe(datei):
    u"""Das Verzeichnis — oder der Dateiname, wenn es keines gibt.

    „(Wurzel)" stand hier bis zum 24.08.2026 und sagte nichts („Entferne den
    Eintrag Wurzel bei den Kategorien, den verstehe ich nicht"). Jetzt heisst
    die Gruppe `models.py`, `admin.py`, `forms.py`.
    """
    teile = str(datei).replace('\\', '/').split('/')
    return '/'.join(teile[:2]) if len(teile) > 2 else teile[0]


def nach_rolle(eintraege):
    u"""Zwei Ebenen aus ``[(name, datei), …]``.

    Liefert ``[{name, zahl, gruppen: [{name, zahl, namen}]}]``, nach Groesse
    sortiert. Die Summe aller ``zahl`` ist die Zahl der Eintraege — ohne
    diese Eigenschaft ist eine Gliederung wertlos, weil man ihr nicht
    ansieht, ob etwas fehlt.
    """
    je_rolle = {}
    for name, datei in eintraege:
        je_rolle.setdefault(rolle(datei), {}).setdefault(
            untergruppe(datei), []).append(name)

    raus = []
    for etikett, gruppen in je_rolle.items():
        teile = [{'name': g, 'namen': sorted(v), 'zahl': len(v)}
                 for g, v in sorted(gruppen.items(),
                                    key=lambda p: (-len(p[1]), p[0]))]
        zahl = sum(t['zahl'] for t in teile)
        raus.append({
            'name': etikett, 'zahl': zahl, 'gruppen': teile,
            # Flach, wenn die Ebene nichts austraegt: eine einzige
            # Untergruppe oder eine kleine Rolle.
            'flach': len(teile) <= 1 or zahl <= FLACH_BIS,
            'namen': sorted(n for t in teile for n in t['namen']),
        })
    raus.sort(key=lambda r: (-r['zahl'], r['name']))
    return raus


__all__ = ['ROLLEN', 'UEBRIGE', 'rolle', 'untergruppe', 'nach_rolle']
