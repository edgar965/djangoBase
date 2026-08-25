# -*- coding: utf-8 -*-
u"""CodeQualitaet — vier etablierte Messwerkzeuge unter einem Knopf.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „fixe alle Fehler … und baue das Tool auch in die Code Review skills ein"

Die anderen Werkzeuge dieses Ordners sind selbst geschrieben, weil sie
Fragen stellen, die kein Standardwerkzeug kennt („welche Klasse haelt
diese freie Funktion?"). Hier ist es umgekehrt: Komplexitaet, Wartbarkeit,
tote Namen und PEP 8 sind seit Jahren geloest. Dieses Werkzeug misst nicht
selbst — es faehrt `radon`, `pyflakes` und `pycodestyle` und bringt deren
Ergebnis in dieselbe Form wie alle anderen Befunde.

WAS DER ERSTE LAUF LEHRTE
=========================
`pyflakes` meldete **299 Meldungen, davon 245 unbenutzte Einfuhren**.
Nachgezaehlt trugen **211 davon ein ``# noqa``** — die oeffentliche
Schnittstelle der Pakete, ausdruecklich so gewollt. `flake8` achtet auf die
Marke, die reine Bibliothek `pyflakes` nicht.

Es blieben 19 echte Funde. Darunter eine Testmethode, die in derselben
Klasse ZWEIMAL denselben Namen trug: Python ueberschreibt still, die
aeltere Fassung lief nie. Sie prüfte noch `WEBRTC_STACK` — einen
Schluessel, den v0.72 entfernt hat.

Deshalb rechnet dieses Werkzeug ``# noqa`` heraus und nennt die Zahl
trotzdem. Ein Bericht, in dem 211 gewollte Zeilen 19 echte zudecken, wird
weggeklickt — und dann findet er nichts mehr.
"""
from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

#: KEINE KAPPUNG (24.08.2026, auf Ansage: „die code qualität in den
#: werkzeugen soll auch die fehler messen und als findings zurückgeben").
#:
#: Hier stand `JE_VERFAHREN = 8`. Das Werkzeug HATTE 217 Komplexitaets-
#: funde und ZEIGTE acht — dieselbe stille Kappung, die schon einmal
#: beanstandet wurde („der test soll sie alle melden"). Die Seite kappt
#: nichts, die Vorlage kappt nichts; die Acht waren allein meine.
#:
#: Wer weniger will, filtert nach Gewicht: Rang F und undefinierte Namen
#: stehen als `fehler`, der Rest als `warnung` oder `hinweis`.


class CodeQualitaet(BefundWerkzeug):

    slug = 'code-qualitaet'
    kriterium = 0
    titel = 'Code-Qualitaet (radon, pyflakes, pycodestyle)'
    zweck = ('Faehrt vier etablierte Messwerkzeuge ueber den Quelltext: '
             'zyklomatische Komplexitaet und Wartbarkeitsindex (radon), '
             'echte Fehler (pyflakes) und PEP 8 (pycodestyle).')
    abhilfe = ('Vor jedem groesseren Umbau und nach jedem Merge. Die vier '
               'widersprechen einander regelmaessig, und das ist der Nutzen: '
               'Eine Datei kann fehlerfrei nach pyflakes sein und trotzdem '
               'einen Wartbarkeitsindex im Keller haben — dann ist nichts '
               'kaputt, aber niemand traut sich hinein.')
    befund = ('Erster Lauf an CamTrack: 216 von 6817 Funktionen ab Rang C, '
              'vier auf F (schlimmste mit 86 Verzweigungen), und unter den '
              'pyflakes-Meldungen eine Testmethode, die zweimal denselben '
              'Namen trug und deshalb nie lief.')
    dauer = 'etwa 20 Sekunden bei 700 Dateien'

    anlassfall = Anlassfall(
        {'verwickelt.py': (
            'import os\n'
            'import sys\n'
            '\n'
            '\n'
            'def viel(a):\n'
            + ''.join('    if a == %d:\n        return %d\n' % (i, i)
                      for i in range(14))
            + '\n\n'
            'def lang():\n'
            '    return "%s"\n' % ('y' * 120))},
        mindestens=2, erwartet_in='verwickelt.py',
        warum='Eine Funktion mit vierzehn Verzweigungen, zwei tote Einfuhren '
              'und eine Zeile ueber 79 Zeichen — drei verschiedene Fragen, '
              'die drei verschiedene Werkzeuge beantworten')

    def pruefen(self, **_argumente):
        from ..umbau.codequalitaet import Codequalitaet

        # Denselben Git-Filter wie jedes andere Werkzeug — sonst
        # misst dieses hier eine andere Menge als `tote-importe`
        # daneben, und die Zahlen sind nicht vergleichbar.
        messung = Codequalitaet(self.wurzel(),
                                gitfilter=self.gitfilter()).messen()
        befunde, kopf = [], ['%d Python-Dateien' % len(messung.dateien)]
        fehlend = []

        # DIE MESSFEHLER ZUERST, und zwar als schwerste Befunde. Eine Datei
        # ohne gueltige Syntax ist kein „Sonderfall zum Ueberspringen",
        # sondern der teuerste Fund ueberhaupt — und sie stand vorher
        # hinter einem stummen `except: continue`.
        #
        # JE DATEI EINE ZEILE, nicht je Verfahren: Eine kaputte Datei laesst
        # alle vier scheitern und haette sonst vier gleichlautende Zeilen
        # erzeugt. Welche Verfahren es traf, steht im Befund.
        for datei, verfahren, grund in self._je_datei(messung.pannen):
            befunde.append(Befund(
                datei, 'Messung gescheitert — %s' % verfahren, grund,
                Befund.FEHLER))

        for verfahren in messung.verfahren:
            if verfahren.fehlt:
                fehlend.append(verfahren.fehlt)
                continue
            kopf.append('%s: %s' % (verfahren.name, verfahren.satz))
            for treffer in verfahren.treffer:
                ort = treffer.datei
                if treffer.zeile:
                    ort = '%s:%d' % (ort, treffer.zeile)
                befunde.append(Befund(
                    ort,
                    '%s — %s' % (verfahren.name, treffer.name),
                    treffer.text,
                    self._gewicht(verfahren, treffer)))

        if messung.pannen:
            kopf.insert(1, '%d Messungen gescheitert' % len(messung.pannen))
        if fehlend:
            kopf.append('nicht gelaufen: %s' % ', '.join(sorted(set(fehlend))))
        # Schwerstes zuerst — bei ueber zweihundert Befunden entscheidet die
        # Reihenfolge darueber, ob jemand das Wichtige sieht.
        rang = {Befund.FEHLER: 0, Befund.WARNUNG: 1, Befund.HINWEIS: 2}
        befunde.sort(key=lambda b: (rang.get(b.gewicht, 3), b.ort))
        return Befundsatz(self.titel, kopf, befunde)

    @staticmethod
    def _je_datei(pannen):
        u"""``[(datei, verfahren, grund)]`` auf eine Zeile je Datei.

        Eine Datei ohne gueltige Syntax laesst ALLE Verfahren scheitern.
        Vier gleichlautende Zeilen sagen nicht mehr als eine, die die
        betroffenen Verfahren aufzaehlt.
        """
        gesammelt = {}
        for datei, verfahren, grund in pannen:
            eintrag = gesammelt.setdefault(datei, ([], grund))
            eintrag[0].append(verfahren)
        raus = []
        for datei, (verfahren, grund) in sorted(gesammelt.items()):
            raus.append((datei, ', '.join(sorted(set(verfahren))), grund))
        return raus

    @staticmethod
    def _gewicht(verfahren, treffer):
        u"""Nicht alles ist gleich dringend.

        Ein undefinierter Name ist ein Fehler, eine zu lange Zeile eine
        Formsache. Beides gleich zu gewichten ist der Grund, warum solche
        Berichte weggeklickt werden.
        """
        if verfahren.werkzeug == 'pycodestyle':
            return Befund.HINWEIS
        if verfahren.werkzeug == 'pyflakes':
            schwer = ('Undefined', 'Redefined', 'Import*')
            return (Befund.FEHLER
                    if any(treffer.name.startswith(w) for w in schwer)
                    else Befund.WARNUNG)
        # radon: Rang C ist nicht dasselbe wie Rang F.
        #
        # DIE VERTEILUNG ENTSCHEIDET (25.08.2026)
        # =======================================
        # Alles unter 40 stand als `warnung` — und damit 195 Funktionen,
        # die radon selbst nur „leicht verwickelt" nennt. Gemessen an
        # CamTrack::
        #
        #     A 5826   B 772   C 195   D 13   E 3   F 4
        #
        # 195 gleich dringend gemeldete Warnungen decken die 20 zu, auf
        # die es ankommt. Gemeldet wird weiterhin JEDE — die Zahl 215
        # steht unverändert im Kopf, und die Verteilung A–F daneben. Nur
        # das GEWICHT folgt jetzt radons eigener Skala:
        #
        #     C (11-20)   hinweis   „leicht verwickelt"
        #     D (21-30)   warnung   wird Arbeit
        #     E/F (>30)   fehler    niemand fasst das mehr an
        if 'Komplex' in verfahren.name:
            if treffer.wert > 30:
                return Befund.FEHLER
            return (Befund.WARNUNG if treffer.wert > 20 else Befund.HINWEIS)
        return Befund.WARNUNG if treffer.wert < 10 else Befund.HINWEIS


__all__ = ['CodeQualitaet']
