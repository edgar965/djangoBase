"""Abhaengigkeiten — Importgraph des Projekts: Zyklen, Naben, Inseln."""

import ast
from collections import defaultdict

from .werkzeug_alt import Befund, Ergebnis, Werkzeug


class Modulknoten:
    """Ein Modul im Graph: wen es importiert und wer es importiert."""

    __slots__ = ('name', 'pfad', 'nach', 'von')

    def __init__(self, name, pfad):
        self.name = name
        self.pfad = pfad
        self.nach = set()
        self.von = set()


class Abhaengigkeiten(Werkzeug):

    slug = 'abhaengigkeiten'
    name = 'Abhängigkeiten'
    zweck = ('Baut den Importgraph der Projektmodule und meldet Zyklen, '
             'Module mit besonders vielen Abhaengigkeiten (Naben) und solche, '
             'die niemand importiert (Inseln).')
    wann = ('Wenn die Struktur unklar geworden ist — und nach jedem Schnitt '
            'grosser Dateien. Ein Zyklus zwingt spaeter zu Importen INNERHALB '
            'von Funktionen; genau daran erkennt man ihn oft zuerst.')
    beleg = ('Beim Zerlegen einer 6.000-Zeilen-Datei war die Frage "wer darf '
             'wen importieren" die eigentliche Arbeit: Endpunkte -> Dienste -> '
             'Kernbibliothek, nie zurueck.')
    dauer = 'Sekunden'
    eingabe = ('nabe_ab', 'Ab wie vielen Importeuren gilt ein Modul als Nabe?', '8')

    def pruefen(self, nabe_ab='8', **_argumente):
        try:
            nabengrenze = max(2, int(str(nabe_ab).strip() or 8))
        except ValueError:
            nabengrenze = 8

        knoten = self._graph()
        befunde = []

        for kreis in self._zyklen(knoten):
            befunde.append(Befund(
                kreis[0], 'ZYKLUS: ' + ' -> '.join(kreis + [kreis[0]]),
                'zwei Module brauchen einander — die Aufgaben sind nicht '
                'sauber getrennt', Befund.FEHLER))

        for modul in sorted(knoten.values(), key=lambda m: -len(m.von)):
            if len(modul.von) >= nabengrenze:
                befunde.append(Befund(
                    modul.name, 'NABE: von %d Modulen importiert' % len(modul.von),
                    'Aenderungen hier wirken weit — Schnittstelle klein halten',
                    Befund.HINWEIS))

        for modul in sorted(knoten.values(), key=lambda m: -len(m.nach)):
            if len(modul.nach) >= nabengrenze:
                befunde.append(Befund(
                    modul.name, 'BREIT: importiert %d Projektmodule' % len(modul.nach),
                    'viele Abhaengigkeiten in eine Richtung — meist ein Modul '
                    'mit mehreren Aufgaben', Befund.HINWEIS))

        kanten = sum(len(m.nach) for m in knoten.values())
        kopf = ['%d Projektmodule, %d Importbeziehungen' % (len(knoten), kanten),
                'Zyklen: %d' % sum(1 for b in befunde if 'ZYKLUS' in b.was)]
        return Ergebnis(self.name, kopf, befunde)

    # ------------------------------------------------------------------ intern

    def _graph(self):
        dateien = list(self.projektdateien('.py'))
        namen = {}
        for datei in dateien:
            namen[self._modulname(datei)] = datei
        knoten = {name: Modulknoten(name, self.kurz(pfad))
                  for name, pfad in namen.items()}
        for name, datei in namen.items():
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
            except (SyntaxError, OSError):
                continue
            for ziel in self._importe(baum, name, set(namen)):
                if ziel != name:
                    knoten[name].nach.add(ziel)
                    knoten[ziel].von.add(name)
        return knoten

    def _modulname(self, datei):
        """`core/api/netz.py` -> `core.api.netz`, relativ zu BASE_DIR."""
        kurz = self.kurz(datei).replace('\\', '/')
        if kurz.endswith('.py'):
            kurz = kurz[:-3]
        if kurz.endswith('/__init__'):
            kurz = kurz[:-len('/__init__')]
        return kurz.replace('/', '.')

    @staticmethod
    def _importe(baum, eigener_name, bekannte):
        """Importierte Projektmodule — relative Importe aufgeloest."""
        ziele = set()
        eigene_teile = eigener_name.split('.')
        for knoten in ast.walk(baum):
            kandidaten = []
            if isinstance(knoten, ast.Import):
                kandidaten = [a.name for a in knoten.names]
            elif isinstance(knoten, ast.ImportFrom):
                if knoten.level:
                    # `from ..dienste.x import Y` — Ebenen vom eigenen Paket ab.
                    basis = eigene_teile[:max(0, len(eigene_teile) - knoten.level)]
                    kandidaten = ['.'.join(basis + ([knoten.module]
                                                    if knoten.module else []))]
                elif knoten.module:
                    kandidaten = [knoten.module]
                # Auch `from paket import modul` erfassen: der importierte Name
                # kann selbst ein Modul sein.
                #
                # Diese Zeilen standen zuerst als Doppelschleife, die WAEHREND
                # der Iteration an dieselbe Liste anhaengte — damit verdoppelte
                # sich die Kandidatenliste mit jedem importierten Namen. Bei
                # zwanzig Namen in einer Zeile sind das eine Million Einträge,
                # und das Werkzeug lief nicht mehr fertig.
                erweitert = ['%s.%s' % (kandidat, name.name)
                             for kandidat in kandidaten
                             for name in knoten.names]
                kandidaten = kandidaten + erweitert
            for kandidat in kandidaten:
                if kandidat in bekannte:
                    ziele.add(kandidat)
        return ziele

    @staticmethod
    def _zyklen(knoten, hoechstens=15):
        """Zyklen per Tiefensuche. Jeder Kreis wird nur einmal gemeldet."""
        gefunden, gesehen = [], set()
        farbe = {}

        def suchen(name, weg):
            if len(gefunden) >= hoechstens:
                return
            farbe[name] = 'grau'
            weg.append(name)
            for ziel in sorted(knoten[name].nach):
                if farbe.get(ziel) == 'grau':
                    kreis = weg[weg.index(ziel):]
                    schluessel = tuple(sorted(kreis))
                    if schluessel not in gesehen:
                        gesehen.add(schluessel)
                        gefunden.append(kreis)
                elif farbe.get(ziel) is None:
                    suchen(ziel, weg)
            weg.pop()
            farbe[name] = 'schwarz'

        for name in sorted(knoten):
            if farbe.get(name) is None:
                suchen(name, [])
        return gefunden
