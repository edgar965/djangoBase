"""ToteImporte — importierte Namen, die im Modul nirgends vorkommen."""

import ast

from .befund import Befund, Befundsatz, BefundWerkzeug


class ToteImporte(BefundWerkzeug):

    slug = 'tote-importe'

    #: Auftrags-Kriterium (kam bis 18.08.2026 aus der

    #: Tabelle ALT_KRITERIUM neben der Registrierung).

    kriterium = 5
    titel = 'Tote Importe'
    zweck = ('Findet importierte Namen, die in der Datei nirgends benutzt werden '
             '— inklusive der Faelle, die beim Herausloesen von Modulen '
             'zurueckbleiben.')
    abhilfe = ('Direkt nach jedem Modulschnitt. Ein toter Import kostet Ladezeit, '
            'haelt Abhaengigkeiten kuenstlich am Leben und verwischt, welches '
            'Modul wirklich wovon abhaengt.')
    befund = ('Beim Zerlegen der grossen API-Datei blieben reihenweise Importe '
             'stehen; zuletzt zwei in einer Datei, deren Funktion auf drei '
             'Zeilen geschrumpft war.')
    dauer = 'Sekunden'

    #: Diese Namen stehen absichtlich da, auch ohne Verwendung.
    ERLAUBT = {'annotations'}

    def pruefen(self, **_argumente):
        befunde = []
        geprueft = 0
        for datei in self.projektdateien('.py'):
            quelle = datei.read_text(encoding='utf-8', errors='replace')
            try:
                baum = ast.parse(quelle)
            except SyntaxError:
                continue
            geprueft += 1
            benutzt = self._benutzte_namen(baum)
            # `__all__` zaehlt als Verwendung: Namen darin werden re-exportiert.
            benutzt |= self._reexporte(baum)
            for knoten in ast.walk(baum):
                if not isinstance(knoten, (ast.Import, ast.ImportFrom)):
                    continue
                if isinstance(knoten, ast.ImportFrom) and knoten.module == '__future__':
                    continue
                for name in knoten.names:
                    if name.name == '*':
                        continue
                    kurzname = (name.asname or name.name).split('.')[0]
                    if kurzname in benutzt or kurzname in self.ERLAUBT:
                        continue
                    befunde.append(Befund(
                        '%s:%d' % (self.kurz(datei), knoten.lineno),
                        'unbenutzt: %s' % kurzname,
                        gewicht=Befund.HINWEIS))
        return Befundsatz(self.titel, ['%d Dateien geprueft' % geprueft], befunde)

    @staticmethod
    def _benutzte_namen(baum):
        """Alle Namen, die irgendwo gelesen werden — auch als `a.b.c`."""
        benutzt = set()
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Name):
                benutzt.add(knoten.id)
            elif isinstance(knoten, ast.Attribute):
                wurzel = knoten
                while isinstance(wurzel, ast.Attribute):
                    wurzel = wurzel.value
                if isinstance(wurzel, ast.Name):
                    benutzt.add(wurzel.id)
            elif isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
                # Typangaben als Zeichenkette ("Modell") und Django-Verweise
                # ("app.Modell") zaehlen als Verwendung.
                benutzt.update(teil for teil in knoten.value.replace('.', ' ')
                               .replace('[', ' ').replace(']', ' ').split())
        return benutzt

    @staticmethod
    def _reexporte(baum):
        namen = set()
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.Assign):
                continue
            for ziel in knoten.targets:
                if isinstance(ziel, ast.Name) and ziel.id == '__all__':
                    for eintrag in getattr(knoten.value, 'elts', []):
                        if isinstance(eintrag, ast.Constant):
                            namen.add(str(eintrag.value))
        return namen
