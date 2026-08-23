"""ToteImporte — importierte Namen, die im Modul nirgends vorkommen."""

import ast

from .befund import Befund, Befundsatz, BefundWerkzeug
from .anlassfall import Anlassfall


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

    #: Module, deren blosser Import etwas bewirkt. Sie werden nie „benutzt" und
    #: gehoeren trotzdem dorthin - ``from . import signals`` in ``apps.ready()``
    #: registriert die Empfaenger, sonst laeuft kein einziges Signal.
    SEITENEFFEKT = {'signals', 'receivers', 'checks', 'tasks', 'admin'}

    anlassfall = Anlassfall(
        {"laden.py": "import json\nimport os\n\n\n"
                     "def lesen(pfad):\n"
                     "    return json.loads(open(pfad).read())\n"},
        mindestens=1, hoechstens=1, erwartet_in="os",
        warum="Ein Import, den niemand mehr braucht, ueberlebt jeden Umbau "
              "und liest sich wie eine Abhaengigkeit, die es nicht gibt")

    def pruefen(self, **_argumente):
        befunde = []
        geprueft = 0
        von_aussen = self._verweise_von_aussen()
        for datei in self.projektdateien('.py'):
            quelle = datei.read_text(encoding='utf-8', errors='replace')
            try:
                baum = ast.parse(quelle)
            except SyntaxError:
                continue
            geprueft += 1
            # Ein `__init__.py` hat als Aufgabe, Namen weiterzureichen. Dort ist
            # „im Modul unbenutzt" der Normalfall, kein Befund.
            if datei.name == '__init__.py':
                continue
            zeilen = quelle.splitlines()
            modul = datei.stem
            in_tests = 'test' in self.kurz(datei).replace('\\', '/').lower()
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
                    if self._gewollt(kurzname, modul, knoten, zeilen,
                                     in_tests, von_aussen):
                        continue
                    befunde.append(Befund(
                        '%s:%d' % (self.kurz(datei), knoten.lineno),
                        'unbenutzt: %s' % kurzname,
                        gewicht=Befund.HINWEIS))
        return Befundsatz(self.titel, ['%d Dateien geprueft' % geprueft], befunde)

    def _gewollt(self, kurzname, modul, knoten, zeilen, in_tests, von_aussen):
        u"""Steht der Name absichtlich da, obwohl ihn die Datei nicht benutzt?

        DIE TEUERSTE SORTE FEHLALARM (assistant, 22.08.2026)
        ====================================================
        Der Pruefer schaut in EINE Datei und schliesst aus „kommt hier nicht
        vor" auf „tot". Ein Name kann aber gerade deshalb dastehen, weil ihn
        jemand ANDERES braucht. Beim ersten Lauf im ``assistant`` waren von
        fuenf Stichproben fuenf solche Faelle - darunter 55 Endpunkte in
        ``search/views.py``, deren Loeschung 55 URLs zerlegt haette::

            # Re-Export der ausgelagerten Endpoints (search/views_chat_api.py).
            from .views_chat_api import (  # noqa: F401
                ki_memory_api, ...          # urls.py: views.ki_memory_api

        Die Zeile trug einen erklaerenden Kommentar UND ein ``# noqa`` - der
        Pruefer uebergeht beides. Vier Muster sind seither ausgenommen:
        """
        # 1. `# noqa` ist die ausdrueckliche Ansage des Autors.
        zeile = zeilen[knoten.lineno - 1] if knoten.lineno <= len(zeilen) else ''
        if 'noqa' in zeile.lower():
            return True
        # 2. Seiteneffekt-Module: der Import IST die Wirkung.
        if kurzname in self.SEITENEFFEKT:
            return True
        # 3. In Testmodulen importierte Testklassen finden die Testlaeufer -
        #    ohne den Import verschwinden die Faelle lautlos aus der Suite.
        if in_tests and 'test' in kurzname.lower():
            return True
        # 4. Weiterreichen: Benutzt eine ANDERE Datei den Namen ueber dieses
        #    Modul (`views.ki_memory_api`) oder holt sie ihn von hier
        #    (`from ...views import ki_memory_api`), ist er alles andere als tot.
        return (modul, kurzname) in von_aussen

    def _verweise_von_aussen(self):
        u"""{(modul, name)} - jeder Zugriff der Form ``modul.name`` und jedes
        ``from … modul import name`` im ganzen Projekt.

        Einmal gesammelt statt je Befund gesucht: Bei 179 Kandidaten waere die
        Einzelsuche 179 Dateilaeufe."""
        paare = set()
        for datei in self.projektdateien('.py'):
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
            except (OSError, SyntaxError, ValueError):
                continue
            for knoten in ast.walk(baum):
                if isinstance(knoten, ast.Attribute) and isinstance(knoten.value, ast.Name):
                    paare.add((knoten.value.id, knoten.attr))
                elif isinstance(knoten, ast.ImportFrom) and knoten.module:
                    letztes = knoten.module.rsplit('.', 1)[-1]
                    for n in knoten.names:
                        paare.add((letztes, n.name))
        return paare

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
