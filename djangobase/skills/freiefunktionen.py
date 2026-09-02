"""FreieFunktionen — Funktionen auf Modulebene, die in eine Klasse gehören."""

import ast
import re
from collections import Counter, defaultdict

from .befund import Befund, Befundsatz, BefundWerkzeug
from .anlassfall import Anlassfall
from .rahmenvorschrift import Rahmenvorschrift


class Modulsicht:
    """Was auf Modulebene steht: freie Funktionen, Klassen, gemeinsame Praefixe."""

    __slots__ = ('pfad', 'funktionen', 'klassen', 'zeilen', 'weiterleitungen')

    def __init__(self, pfad, funktionen, klassen, zeilen, weiterleitungen=0):
        self.pfad = pfad
        #: [(name, zeile, zeilenzahl, erstes_argument)]
        self.funktionen = funktionen
        self.klassen = klassen
        self.zeilen = zeilen
        #: Wie viele davon nur ``return Klasse.methode()`` sind.
        self.weiterleitungen = weiterleitungen

    def ist_fassade(self):
        u"""Steht hier eine Klasse, und davor nur Einzeiler?

        Dann fehlt keine Klasse — dann steht eine Fassade davor. Ein
        anderer Befund, und ein viel weniger dringender.
        """
        return bool(self.klassen) and self.weiterleitungen >= max(
            2, len(self.funktionen) - 1)

    #: Namensteile, die KEINEN Gegenstand benennen, sondern eine Taetigkeit.
    #:
    #: WARUM DIE LISTE (24.08.2026)
    #: ===========================
    #: Fuer `app/integrations/path_resolver.py` schlug das Werkzeug
    #: `GetVerwaltung` vor — gebuendelt ueber `get_media_root`,
    #: `get_persons_dir`, `get_ffmpeg`. Das Verb ist allen gemeinsam, der
    #: Gegenstand keinem. Ein solcher Vorschlag ist schlechter als keiner,
    #: weil er so aussieht, als haette jemand nachgedacht.
    VERBEN = frozenset((
        'get', 'set', 'is', 'has', 'build', 'make', 'create', 'load',
        'save', 'read', 'write', 'publish', 'send', 'run', 'do', 'ensure',
        'check', 'try', 'init', 'update', 'delete', 'remove', 'add',
        'hole', 'setze', 'lade', 'schreibe', 'pruefe', 'melde', 'baue',
        'ist', 'hat', 'mach', 'lies',
    ))

    def gruppen(self):
        """Funktionen mit gemeinsamem Namensanfang — die deutlichsten Kandidaten.

        `lade_bvh`, `pruefe_bvh`, `schreibe_bvh` sind drei Funktionen mit
        demselben Gegenstand: zusammen eine Klasse. Gruppiert wird über den
        ersten Namensteil vor dem Unterstrich, in beide Richtungen (Praefix und
        Suffix), weil beide Schreibweisen ueblich sind.

        Ein Verb als Schlüssel zählt NICHT — siehe `VERBEN`.
        """
        nach_anfang = defaultdict(list)
        nach_ende = defaultdict(list)
        for name, zeile, laenge, _erstes in self.funktionen:
            teile = name.strip('_').split('_')
            if len(teile) > 1:
                nach_anfang[teile[0]].append((name, zeile, laenge))
                nach_ende[teile[-1]].append((name, zeile, laenge))
        gefunden = []
        for schluessel, eintraege in list(nach_anfang.items()) + list(nach_ende.items()):
            if len(eintraege) >= 3 and schluessel.lower() not in self.VERBEN:
                gefunden.append((schluessel, eintraege))
        # Nach Groesse: die dicksten Buendel zuerst.
        gefunden.sort(key=lambda paar: -len(paar[1]))
        return gefunden


class FreieFunktionen(BefundWerkzeug):

    slug = 'freie-funktionen'

    #: Auftrags-Kriterium (kam bis 18.08.2026 aus der

    #: Tabelle ALT_KRITERIUM neben der Registrierung).

    kriterium = 1
    titel = 'Freie Funktionen'
    zweck = ('Zeigt Module mit vielen Funktionen auf Modulebene und findet '
             'Bündel gleichen Namensanfangs — die naheliegenden Kandidaten '
             'für eine Klasse.')
    abhilfe = ('Beim Umstieg auf Objektorientierung. Drei Funktionen mit demselben '
            'Namensanfang und demselben ersten Argument sind fast immer eine '
            'Klasse, die noch niemand geschrieben hat.')
    befund = ('So entstanden im Ursprungsprojekt u. a. Skingewichte, '
             'Bvhbibliothek und Animationsauswahl — vorher lose Funktionen mit '
             'globalen Zwischenspeichern in einer 6.000-Zeilen-Datei.')
    dauer = 'Sekunden'
    #: ALLE melden, nicht erst ab fuenf (24.08.2026, auf Ansage: „der test
    #: soll sie alle melden"). Die Vorgabe 5 versteckte an CamTrack 238 von
    #: 283 Modulen — gemeldet wurden 45. Wer die Zahl kleiner haben will,
    #: dreht sie hier hoch; die Voreinstellung darf nichts verschweigen.
    eingabe = ('ab', 'Ab wie vielen freien Funktionen je Datei melden?', '1')

    anlassfall = Anlassfall(
        {"helfer.py": "".join("def schritt%d(wert):\n    return wert + %d\n\n\n"
                              % (i, i) for i in range(1, 9))},
        mindestens=1, erwartet_in="helfer.py",
        warum="Acht lose Funktionen auf Modulebene: Der Zusammenhang steht "
              "nirgends, und jede trägt ihren Zustand selbst")

    def pruefen(self, ab='1', **_argumente):
        try:
            grenze = max(1, int(str(ab).strip() or 1))
        except ValueError:
            grenze = 1

        sichten, befunde = [], []
        rufer, ansichten = {}, set()
        # Was Django beim Namen aus den Einstellungen holt, MUSS auf
        # Modulebene stehen (siehe `rahmenvorschrift.py`). Einmal gelesen,
        # nicht je Datei.
        vorgeschrieben = Rahmenvorschrift.namen()
        for datei in self.projektdateien('.py'):
            self._ansichten_sammeln(datei, ansichten)
            sicht = self._modul(datei, rufer, vorgeschrieben)
            if sicht is not None:
                sichten.append(sicht)

        for sicht in sorted(sichten, key=lambda s: -len(s.funktionen)):
            if len(sicht.funktionen) < grenze:
                continue
            if sicht.ist_fassade():
                # Die Klasse gibt es schon — hier steht nur eine Fassade
                # davor. Kein Auftrag zum Schreiben, ein Hinweis zum Wissen.
                befunde.append(Befund(
                    sicht.pfad,
                    '%d Weiterleitungen vor %d Klasse(n)'
                    % (sicht.weiterleitungen, sicht.klassen),
                    'Die Klasse steht schon da; die freien Funktionen geben '
                    'nur weiter. Abreissen kostet so viele Änderungen, wie '
                    'es Aufrufstellen gibt — erst zählen, dann entscheiden.',
                    Befund.HINWEIS))
                continue

            gruppen = sicht.gruppen()
            if gruppen:
                schluessel, eintraege = gruppen[0]
            else:
                # DAS MODUL IST DAS BUENDEL (24.08.2026). Vorher stand hier
                # „kein gemeinsamer Namensanfang — einzeln pruefen", also die
                # Bankrotterklaerung. Dabei hat jede Datei einen Namen, der
                # ihren Gegenstand nennt: `mqtt.py` haelt `get_client`,
                # `publish_sighting`, `publish_offline` — kein gemeinsames
                # Wort, aber ganz offensichtlich EINE Sache.
                schluessel, eintraege = None, [(n, z, l) for n, z, l, _e
                                               in sicht.funktionen]
            platz = self._wo_hin(eintraege, rufer, ansichten, sicht.klassen)
            hinweis = ('%d Funktionen als Klasse `%s`: %s. %s'
                       % (len(eintraege),
                          self._klassenname(schluessel, sicht.pfad),
                          ', '.join(n for n, _z, _l in eintraege[:6]),
                          platz))
            befunde.append(Befund(
                sicht.pfad,
                '%d freie Funktionen, %d Klassen' % (len(sicht.funktionen),
                                                     sicht.klassen),
                hinweis,
                self._gewicht(sicht, grenze)))

        gesamt = sum(len(s.funktionen) for s in sichten)
        gebuendelt = sum(len(g[1]) for s in sichten for g in s.gruppen())
        kopf = ['%d Module, %d Funktionen auf Modulebene' % (len(sichten), gesamt),
                '%d Module mit mindestens %d freien Funktionen'
                % (len(befunde), grenze),
                '%d davon stehen in einem Bündel gleichen Namensanfangs — '
                'das sind die Klassen, die noch niemand geschrieben hat'
                % gebuendelt]
        return Befundsatz(self.titel, kopf, befunde)

    #: Klassen, an die nichts gehaengt wird. Ein Test RUFT den Code, er
    #: BESITZT ihn nicht — der erste Lauf schlug `ComputeAcceptThresholdTests`
    #: als Halter fuer drei Schwellen-Funktionen vor.
    KEIN_HALTER = ('Test', 'Tests', 'TestCase', 'Mixin')

    #: Rollen, in denen eine Funktion auf Modulebene die UEBLICHE Schreibweise
    #: ist — nicht eine Klasse, die niemand geschrieben hat.
    #:
    #: WARUM DIE UNTERSCHEIDUNG (Edgar, 26.08.2026)
    #: ===========================================
    #:     „wie kann es sein, dass die Code-Review-Tests alles gruen melden,
    #:      und du noch hunderte freier Funktionen hast usw??"
    #:
    #: Gemessen an CamTrack, 285 gemeldete Module::
    #:
    #:     Ansichten  101 Module / 348 Funktionen
    #:     Tests       67 /  123
    #:     Dienste     57 /  173   <- die eigentlichen Kandidaten
    #:     Erkennung   21 /   51
    #:     uebrige     39 /   58
    #:
    #: `def meine_ansicht(request)` auf Modulebene IST die Django-Schreibweise,
    #: und eine Testhilfe daneben ebenso. **59 % der Liste** waren damit
    #: Dinge, die so gehoeren — und eine Liste, die zu 59 % aus Richtigem
    #: besteht, arbeitet niemand durch. Genau deshalb hat sie niemand
    #: durchgearbeitet.
    #:
    #: Gemeldet wird weiter JEDES Modul; nur das Gewicht folgt der Rolle.
    #: Wer die echten Kandidaten will, filtert auf `warnung`.
    UEBLICH = ('Ansichten', 'Tests')

    def _gewicht(self, sicht, grenze):
        u"""Wie schwer wiegt dieser Fund?

        Eine Ansicht oder eine Testhilfe ist ein HINWEIS — sie steht dort
        richtig. Alles andere mit genuegend Funktionen ist eine WARNUNG.
        """
        from ..umbau.gliederung import rolle

        if rolle(sicht.pfad) in self.UEBLICH:
            return Befund.HINWEIS
        return (Befund.WARNUNG if len(sicht.funktionen) >= grenze * 2
                else Befund.HINWEIS)

    def _rufer_sammeln(self, baum, hinein, datei=None):
        u"""Welche KLASSE ruft welche Funktion beim Namen?

        Damit lässt sich die zweite Haelfte der Frage beantworten: nicht
        nur „diese drei gehören in eine Klasse", sondern auch „und diese
        Klasse gehört dorthin".
        """
        if datei is not None and ('test' in datei.name.lower()
                                 or 'tests' in datei.parts):
            return
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.ClassDef):
                continue
            if knoten.name.endswith(self.KEIN_HALTER):
                continue
            for teil in ast.walk(knoten):
                if isinstance(teil, ast.Call) and isinstance(teil.func, ast.Name):
                    hinein.setdefault(teil.func.id, Counter())[knoten.name] += 1

    @staticmethod
    def _klassenname(schluessel, pfad=None):
        u"""Ein Klassenname — aus dem Bündel, sonst aus dem DATEINAMEN.

        `person` -> `PersonVerwaltung`, `marzahn` -> `MarzahnVerwaltung`.

        Ohne Bündel gilt die Datei. `path_resolver.py` -> `PathResolver`,
        `mqtt.py` -> `Mqtt`, `ffmpeg_path.py` -> `FfmpegPath`. Der Dateiname
        ist der bessere Ausgangspunkt, sobald der gemeinsame Namensteil ein
        Verb wäre: für `path_resolver.py` kam vorher `GetVerwaltung`
        heraus — das Verb hatten alle gemeinsam, den Gegenstand keine.

        Ein Vorschlag, kein Befehl: Wer die Klasse schreibt, findet meist
        einen besseren Namen (aus `path_resolver.py` wurde `Pfade`). Aber
        ein Vorschlag ist leichter zu widersprechen als ein leeres Feld.
        """
        if schluessel:
            return (schluessel.strip('_').replace('_', ' ').title()
                    .replace(' ', '') + 'Verwaltung')
        stamm = str(pfad or '').replace('\\', '/').split('/')[-1]
        stamm = stamm[:-3] if stamm.endswith('.py') else stamm
        if stamm in ('__init__', ''):
            # `__init__.py` sagt nichts — dann gilt das Verzeichnis.
            teile = [t for t in str(pfad or '').replace('\\', '/').split('/')
                     if t and not t.endswith('.py')]
            stamm = teile[-1] if teile else 'Modul'
        return stamm.strip('_').replace('_', ' ').title().replace(' ', '')

    def _ansichten_sammeln(self, datei, hinein):
        u"""Namen, die in einer `urls.py` als Ansicht eingetragen sind.

        Sie werden vom URL-Router gerufen, nicht von einer Klasse. „Niemand
        ruft sie" wäre deshalb die falsche Auskunft — richtig ist: Django
        hat dafür die klassenbasierte Ansicht, und djangoBase benutzt sie
        durchgehend (`SkillsView(ZugriffMixin, View)`).
        """
        if datei.name != 'urls.py':
            return
        try:
            text = datei.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return
        for treffer in re.finditer(r'views\.(\w+)|path\([^,]+,\s*(\w+)', text):
            name = treffer.group(1) or treffer.group(2)
            if name:
                hinein.add(name)

    def _wo_hin(self, eintraege, rufer, ansichten, eigene_klassen):
        u"""In welchen Baum gehört die neue Klasse?

        DIE ZWEITE HAELFTE DER FRAGE (Edgar, 24.08.2026)
        ================================================
            „die sollen als Klassen zusammengefasst werden, und dann
             möglichst in dem Baum der sie braucht"

        Das Werkzeug meldete bisher nur „diese fünf gehören in eine
        Klasse". Wo diese Klasse dann hängt, blieb offen — und genau daran
        scheitert der Umbau: Eine neue Klasse ohne Platz im Baum ist wieder
        eine Wurzel, und davon gab es schon zu viele.

        Gezaehlt wird, welche vorhandene Klasse diese Funktionen am
        haeufigsten ruft. Wer sie braucht, soll sie halten.
        """
        gesamt = Counter()
        for name, _z, _l in eintraege:
            gesamt.update(rufer.get(name) or {})
        if gesamt:
            klasse, zahl = gesamt.most_common(1)[0]
            return ('Hängt an `%s` — die ruft sie %dx, wer sie braucht soll '
                    'sie halten.' % (klasse, zahl))
        treffer = sum(1 for n, _z, _l in eintraege if n in ansichten)
        if treffer:
            return ('%d davon sind Django-Ansichten: gehören in eine '
                    'klassenbasierte Ansicht (`View`), nicht in eine eigene '
                    'Klasse daneben.' % treffer)
        if eigene_klassen:
            return ('Im selben Modul steht schon eine Klasse — dort '
                    'anhaengen statt eine zweite Wurzel aufzumachen.')
        return ('Niemand ruft sie aus einer Klasse: eine neue Wurzel, '
                'sparsam einsetzen.')

    def _modul(self, datei, rufer=None, vorgeschrieben=()):
        try:
            baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
        except (SyntaxError, OSError):
            return None
        if rufer is not None:
            self._rufer_sammeln(baum, rufer, datei)
        # `manage.py`, `wsgi.py`, `asgi.py`: Der Rahmen ruft sie, nicht wir.
        if Rahmenvorschrift.eigene_datei(datei):
            return None
        # Was der `__main__`-Block dieser Datei selbst ruft, MUSS auf
        # Modulebene stehen — sonst startet das Werkzeug nicht mehr.
        vorgeschrieben = set(vorgeschrieben) | Rahmenvorschrift.selbst_gerufen(baum)
        funktionen, klassen, weiterleitungen = [], 0, 0
        for knoten in baum.body:          # nur Modulebene, nicht ast.walk
            if isinstance(knoten, ast.ClassDef):
                klassen += 1
            elif isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if knoten.name.startswith('__'):
                    continue
                # Kontextprozessor, Middleware-Fabrik & Co.: In eine Klasse
                # verschoben findet `import_string` sie nicht mehr.
                if knoten.name in vorgeschrieben:
                    continue
                # Signalhandler, Templatetags, Celery-Aufgaben: Der
                # Dekorator MELDET sie an. In einer Klasse meldet er
                # nichts mehr an — siehe `Rahmenvorschrift`.
                if Rahmenvorschrift.wird_angemeldet(knoten):
                    continue
                ende = getattr(knoten, 'end_lineno', knoten.lineno) or knoten.lineno
                erstes = (knoten.args.args[0].arg if knoten.args.args else '')
                funktionen.append((knoten.name, knoten.lineno,
                                   ende - knoten.lineno + 1, erstes))
                weiterleitungen += 1 if self._weiterleitung(knoten) else 0
        if not funktionen:
            return None
        return Modulsicht(self.kurz(datei), funktionen, klassen,
                          getattr(baum, 'end_lineno', 0) or 0, weiterleitungen)

    @staticmethod
    def _weiterleitung(knoten):
        u"""Ein Einzeiler, der nur weitergibt: ``return Pfade.medien()``.

        DER UNTERSCHIED, DER GEFEHLT HAT (24.08.2026)
        =============================================
        `app/integrations/` bekam sieben Mal „schreib eine Klasse". Gemessen:
        **fuenf der sechs Dateien HABEN die Klasse** — `Pfade`, `Dateien`,
        `FFmpeg`, `DiskSpace`, `Aufgabenplanung`. Davor stehen 15 Einzeiler
        als Fassade, und `get_media_root` allein an 146 Stellen gerufen.

        Das ist ein anderer Befund: nicht „hier fehlt eine Klasse", sondern
        „hier steht eine Fassade davor" — und die abzureissen kostet 146
        Aenderungen, waehrend die fehlende Klasse zu schreiben eine kostet.
        Ohne die Unterscheidung sieht beides gleich dringend aus.
        """
        koerper = [z for z in knoten.body
                   if not (isinstance(z, ast.Expr)
                           and isinstance(z.value, ast.Constant))]
        return (len(koerper) == 1 and isinstance(koerper[0], ast.Return)
                and isinstance(koerper[0].value, ast.Call))
