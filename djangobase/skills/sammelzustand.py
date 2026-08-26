# -*- coding: utf-8 -*-
u"""Sammelzustand — Zustand, der EINER Entitaet gehoert, aber gesammelt liegt.

DER VORFALL (CamTrack, 23.08.2026)
==================================
``LiveDetectorWorker`` bedient elf Kameras. Die Bilder je Kamera holte er aus
einem Verzeichnis (``self._detektoren[slug]``) — die ZAEHLER dazu hielt er
flach::

    class LiveDetectorWorker:
        def __init__(self):
            self._detektoren = {}          # je Kamera
            self.frames_processed = 0      # fuer ALLE zusammen
            self.errors_total = 0          # fuer ALLE zusammen
            self.stillstand = SilentFailureWatch()   # EINE fuer elf Kameras

Die Stillstands-Wache zaehlt Bilder, in denen der Erkenner eine Person sah und
trotzdem nichts entstand, und setzt bei jeder gelungenen Sichtung zurueck. Bei
einer gemeinsamen Wache setzte damit **jede funktionierende Kamera den Zaehler
der blind gewordenen zurueck**. Vier Kameras waren am 09.05.2026 zehn Stunden
blind; die Wache, die genau dafuer gebaut war, schlug kein einziges Mal an.

Dasselbe eine Ebene tiefer: „das Bewegungs-Tor verwirft 95 %" liess sich nicht
sagen, ohne es aus zwanzig Protokollzeilen zusammenzusuchen — die Rate stand nur
als Summe ueber alle Kameras da.

WARUM DIE VORHANDENEN WERKZEUGE DAS NICHT SEHEN
===============================================
``GlobalerZustand`` (Kriterium 18) fragt nach Zustand auf MODULEBENE. Der ist
hier tadellos: Alles steht in einer Klasse, als Instanz-Attribut, genau wie
gefordert. ``Klassenkandidat`` fragt, wo eine Klasse FEHLT — sie ist da.

Der Fehler sitzt eine Ebene weiter: Die Klasse ist die falsche. Ein Zaehler, der
je Kamera etwas bedeutet, gehoert an die Kamera — als **Unterinstanz**, nicht als
flaches Feld des Dienstes, der zufaellig alle bedient.

    Auftrag (Edgar, 23.08.2026): „Eigenschaften/Klassen, die einer anderen
    Klasse gehoeren, sollen nicht global gehalten werden, sondern als
    Unterinstanz der Klasse."

WORAN ES ERKANNT WIRD — DIE KLASSE BEWEIST ES SELBST
====================================================
Kein Raten an Namen. Zwei Dinge muessen in derselben Klasse zusammenkommen:

1. **Sie bedient mehrere Entitaeten.** Beweis: ein Verzeichnis, das mit einer
   VARIABLEN aufgeschlagen wird (``self._d[slug]``, ``self._d.get(cam)``). Ein
   fester Schluessel (``self._d['gesamt']``) zaehlt nicht — das ist eine
   Struktur, keine Verteilung.
2. **Sie haelt daneben flachen Zustand, der SICH AENDERT** — eine Zahl, die
   hochgezaehlt wird (``self.x += 1``), oder EINE Unterinstanz fuer alle
   (``self.wache.melde(...)``). Nur Veraenderliches; was in ``__init__``
   gesetzt und nie wieder angefasst wird, ist Einstellung und kein Befund.

Steht beides in DERSELBEN Methode, ist es eine WARNUNG: Dort wird je Entitaet
nachgesehen und gesammelt gezaehlt — der Vorfall oben, Zeile fuer Zeile.

WAS AUSDRUECKLICH NICHT GEMELDET WIRD
=====================================
Der teuerste Fehler eines Pruefwerkzeugs ist der Fehlalarm; er verdeckt die
echten Befunde (``~/.claude/rules/analysewerkzeuge.md``). Draussen bleiben:

* **Was dem Dienst selbst gehoert**, nicht seinen Entitaeten: ``_lock``,
  ``_thread``, ``_stop``, ``queue``, ``logger``. Ein Dienst hat EINEN Faden und
  EINE Sperre — das ist kein geteilter Zustand, das ist der Dienst.
* **Zaehler mit Vermerk** ``# geteilt gewollt: <Grund>``. Eine Gesamtzahl fuer
  die Startseite IST gewollt; sie soll nur dastehen, weil jemand sie wollte, und
  nicht, weil niemand nachgedacht hat.
* Das Verzeichnis je Entitaet selbst — es ist die Loesung, nicht das Problem.
* **Sammel-Behaelter** (``self.treffer.append(...)``) und **Kennungsfolgen**
  (``self.next_id += 1``). Beides ist absichtlich gemeinsam: das eine ist das
  Ergebnis der Klasse, das andere vergaebe je Entitaet doppelte Kennungen.
* **Testdateien.** Ein ``setUp`` legt je Pruefung ein Objekt an — das sieht aus
  wie der Befund und ist der Normalfall.

Und die Huerde davor: Ein Behaelter mit variablem Index ist noch KEIN
Verzeichnis je Entitaet. Verlangt wird, dass die Klasse ihn selbst als
``dict`` anlegt, dass der Schluessel kein eigenes Feld ist
(``self.punkte[self.stand]`` ist eine Position) und dass die Klasse kein
``@dataclass`` ist — ein Datensatz beschreibt EINE Sache.

Nichts davon ist ausgedacht; alles ist an zwei Laeufen gegen CamTrack
abgelesen. Gemessen: **41 gemeldete Felder und 12 Warnungen im ersten Lauf,
12 und 5 danach** — bei unveraendert gefundenem Vorfall. Von den 605 Klassen
bedienen 76 nachweislich mehrere Entitaeten.
"""

import ast

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug


class Sammelfund:
    u"""Ein flaches Feld in einer Klasse, die mehrere Entitäten bedient."""

    __slots__ = ('pfad', 'klasse', 'name', 'zeile', 'art', 'methode',
                 'zusammen', 'schluessel')

    def __init__(self, pfad, klasse, name, zeile, art, methode, zusammen,
                 schluessel):
        self.pfad = pfad
        self.klasse = klasse
        #: Der Name des flachen Feldes — das, was umziehen muss.
        self.name = name
        self.zeile = zeile
        #: 'zaehler' (Zahl/Liste) oder 'unterobjekt' (eine Instanz fuer alle).
        self.art = art
        #: In welcher Methode es sich aendert.
        self.methode = methode
        #: True, wenn in DERSELBEN Methode je Entitaet nachgesehen wird — der
        #: harte Beweis, dass hier je Entitaet gehandelt und gesammelt gezaehlt
        #: wird.
        self.zusammen = zusammen
        #: Womit das Verzeichnis aufgeschlagen wird ('slug', 'cam', ...).
        self.schluessel = schluessel

    @property
    def gewicht(self):
        return Befund.WARNUNG if self.zusammen else Befund.HINWEIS


class Sammelzustand(BefundWerkzeug):

    slug = 'sammelzustand'
    kriterium = 18
    titel = 'Zustand je Entität, gesammelt gehalten'
    zweck = ('Findet Klassen, die nachweislich mehrere Entitäten bedienen '
             '(Verzeichnis mit variablem Schlüssel) und daneben flache '
             'Zähler oder eine geteilte Unterinstanz für alle halten.')
    abhilfe = ('Je Entität eine eigene Instanz: eine kleine Klasse mit diesen '
               'Feldern, gehalten im vorhandenen Verzeichnis '
               '(``self._je_x[schluessel].zaehler``). Ist die Summe wirklich '
               'gewollt, Vermerk „# geteilt gewollt: <Grund>" setzen.')
    befund = ('Eine Stillstands-Wache für elf Kameras: Jede funktionierende '
              'Kamera setzte den Zähler der blind gewordenen zurück. Vier '
              'Kameras waren zehn Stunden blind, die Wache schlug nie an.')
    dauer = 'Sekunden'

    #: Vermerk fuer den gewollten Fall — dieselbe Bauform wie „Dictionary
    #: gewollt" bei ``anzeigeformat``: Die Ausnahme steht AM CODE, nicht als
    #: Pfadliste im Pruefer.
    MARKER = 'geteilt gewollt'

    #: Was dem Dienst SELBST gehoert und nicht seinen Entitaeten. Verglichen
    #: wird tokenweise (``_stop_event`` -> ``stop``, ``event``), nicht als
    #: Teilzeichenkette: ``log`` als Teilstueck haette ``logik`` verschluckt.
    EIGEN = frozenset({
        'lock', 'locks', 'sperre', 'sperren', 'mutex', 'semaphore',
        'event', 'events', 'thread', 'threads', 'faden', 'worker',
        'proc', 'procs', 'process', 'prozess', 'pid',
        'queue', 'queues', 'warteschlange', 'logger', 'log',
        'running', 'laeuft', 'stop', 'stopped', 'stopping', 'start',
        'started', 'active', 'aktiv', 'closed', 'geschlossen', 'offen',
        'session', 'client', 'conn', 'connection', 'pool', 'executor',
        'timer', 'takt', 'settings', 'config', 'konfiguration',
    })

    #: Schluesselnamen, die eine Entitaet benennen. NICHT die Bedingung — das
    #: ist der variable Schluessel — sondern nur der Beleg in der Meldung.
    ENTITAET = frozenset({'slug', 'cam', 'camera', 'kamera', 'key', 'schluessel',
                          'name', 'id', 'pk', 'user', 'benutzer', 'kunde',
                          'kanal', 'channel', 'host', 'geraet', 'device'})

    #: Aufrufe, die ein Verzeichnis mit einem Schluessel aufschlagen.
    NACHSCHLAGEN = frozenset({'get', 'setdefault', 'pop', 'popitem'})

    #: Womit ein Verzeichnis je Entitaet angelegt wird. NICHT ``Counter`` und
    #: nicht ``list``/``ndarray``: Ein ``Counter`` zaehlt INNERHALB einer
    #: Entitaet aus (``self.votes[person_pk] += 1`` in ``TrackLockState``),
    #: ein Feld wird ueber die Position aufgeschlagen
    #: (``self.points[self.count]`` in ``TrackCenters``). Beides sieht im
    #: Syntaxbaum genauso aus wie eine Verteilung — beides ist keine. Aus
    #: diesem Loch kamen zwei der acht Warnungen im zweiten Lauf.
    VERZEICHNIS = frozenset({'dict', 'defaultdict', 'OrderedDict', 'WeakValueDictionary'})

    #: Namen, die eine LAUFENDE NUMMER fuehren. Eine Kennungsfolge ist
    #: absichtlich gemeinsam — je Entitaet gefuehrt vergaebe sie doppelte
    #: Kennungen. Beleg: ``LocalIdentityPool.next_id`` (CamTrack).
    FOLGE = frozenset({'next', 'seq', 'sequence', 'laufnummer', 'nummer',
                       'uid', 'uuid'})

    #: Aufrufe, deren Ergebnis kein eigenes Objekt mit Zustand ist.
    KEIN_OBJEKT = frozenset({'dict', 'list', 'set', 'tuple', 'frozenset',
                             'int', 'float', 'str', 'bool', 'bytes',
                             'defaultdict', 'OrderedDict', 'Counter',
                             'deque', 'getLogger', 'Lock', 'RLock', 'Event',
                             'Queue', 'Semaphore', 'Condition'})

    DATEIEN_AUS = ('settings.py', 'conf.py', 'urls.py', 'apps.py', 'wsgi.py',
                   'asgi.py', 'manage.py')

    #: Testdateien. Ein ``setUp`` legt je Pruefung ein Objekt an und ein
    #: Verzeichnis daneben — das SIEHT aus wie der Befund und ist der
    #: Normalfall. Drei der zwoelf Warnungen im ersten Lauf kamen von dort.
    TESTS_AUS = ('tests', 'test', 'testing')

    anlassfall = Anlassfall(
        {"wache.py": (
            "class Ueberwachung:\n"
            "    def __init__(self):\n"
            "        self._je_kamera = {}\n"
            "        self.fehler = 0\n"
            "        self.gesamt = 0\n"
            "        self._sperre = None\n\n"
            "    def bild(self, slug, gesehen):\n"
            "        stand = self._je_kamera.get(slug)\n"
            "        self.fehler += 1\n"
            "        self.gesamt += 1     # geteilt gewollt: Summe fuer die Seite\n"
            "        return stand\n")},
        mindestens=1, hoechstens=1, erwartet_in="fehler",
        warum="Eine Wache für elf Kameras (CamTrack, 09.05.2026): je Kamera "
              "nachgesehen, gesammelt gezählt — jede laufende Kamera setzte "
              "den Zähler der blinden zurück. `gesamt` trägt den Vermerk "
              "und darf NICHT mitgemeldet werden")

    # ---------------------------------------------------------------- Ablauf
    def pruefen(self, **_argumente):
        funde, klassen, bedienende = [], 0, 0
        for pfad in self.projektdateien('.py'):
            if pfad.name in self.DATEIEN_AUS or self._ist_test(pfad):
                continue
            baum, zeilen = self._lesen(pfad)
            if baum is None:
                continue
            for knoten in ast.walk(baum):
                if not isinstance(knoten, ast.ClassDef):
                    continue
                klassen += 1
                eigene = self._klasse(self.kurz(pfad), knoten, zeilen)
                if eigene is None:
                    continue
                bedienende += 1
                funde.extend(eigene)

        funde.sort(key=lambda f: (f.gewicht != Befund.WARNUNG, f.pfad, f.zeile))
        kopf = [
            '%d Klassen geprüft, %d bedienen mehrere Entitäten' % (klassen,
                                                                     bedienende),
            '%d gesammelt gehaltene Felder, davon %d in derselben Methode wie '
            'der Zugriff je Entität'
            % (len(funde), sum(1 for f in funde if f.zusammen)),
        ]
        return Befundsatz(self.titel, kopf,
                          [self._befund(f) for f in funde])

    def _lesen(self, pfad):
        try:
            text = pfad.read_text(encoding='utf-8', errors='replace')
            return ast.parse(text), text.splitlines()
        except (SyntaxError, OSError):
            return None, []

    # ----------------------------------------------------------- Eine Klasse
    def _klasse(self, kurz, knoten, zeilen):
        u"""Die Befunde EINER Klasse — oder ``None``, wenn sie keine ist.

        Erst wird gefragt, ob die Klasse ueberhaupt mehrere Entitäten bedient.
        Ohne diesen Beweis wird nichts gemeldet: Ein Zähler in einer Klasse,
        von der es je Kamera eine gibt, ist genau richtig aufgehoben — das ist
        der Normalfall und darf nie im Bericht auftauchen.
        """
        methoden = [k for k in knoten.body
                    if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not methoden:
            return None

        if self._ist_datensatz(knoten):
            return None

        # Nur was die Klasse SELBST als Verzeichnis anlegt. Ohne diese Huerde
        # gilt jeder Behaelter mit variablem Index als Verteilung.
        erklaert = self._erklaerte_verzeichnisse(knoten, methoden)
        if not erklaert:
            return None
        verzeichnisse, schluessel = self._je_entitaet(methoden)
        verzeichnisse &= erklaert
        if not verzeichnisse:
            return None

        objekte = self._unterobjekte(methoden)
        funde = []
        for methode in methoden:
            if methode.name == '__init__':
                continue
            hier = self._je_entitaet([methode])[0] & verzeichnisse
            for name, zeile, art in self._flach(methode, verzeichnisse, objekte):
                if self._vermerkt(zeilen, zeile):
                    continue
                funde.append(Sammelfund(kurz, knoten.name, name, zeile, art,
                                        methode.name, bool(hier), schluessel))
        return self._je_name(funde)

    @staticmethod
    def _je_name(funde):
        u"""Ein Befund je Feld, nicht je Fundstelle.

        Ein Zähler, der in vier Methoden hochgezaehlt wird, ist EIN Umbau. Vier
        Zeilen darueber im Bericht liessen ihn nach vier Baustellen aussehen —
        und die schwerste (die mit dem Zugriff je Entität daneben) ginge
        zwischen den anderen unter. Deshalb bleibt je Name die schwerste
        Fundstelle stehen.
        """
        beste = {}
        for f in funde:
            vorher = beste.get(f.name)
            if vorher is None or (f.zusammen and not vorher.zusammen):
                beste[f.name] = f
        return sorted(beste.values(), key=lambda f: f.zeile)

    def _befund(self, f):
        wo = '%s:%d' % (f.pfad, f.zeile)
        if f.art == 'unterobjekt':
            was = ('%s.%s — EINE Instanz für alle Entitäten (%s)'
                   % (f.klasse, f.name, f.methode))
            warum = ('Ihr Zustand vermischt sich über alle Entitäten: Was die '
                     'eine setzt, sieht die nächste. In das Verzeichnis je '
                     'Entität verschieben, dann hat jede ihre eigene.')
        else:
            was = ('%s.%s — gesammelt für alle Entitäten (%s)'
                   % (f.klasse, f.name, f.methode))
            warum = ('Der Wert bedeutet je Entität etwas, steht aber nur als '
                     'Summe da. Als Feld einer Instanz je Entität führen.')
        if f.zusammen:
            warum = ('In derselben Methode wird je %s nachgesehen und trotzdem '
                     'gesammelt geschrieben. ' % (f.schluessel or 'Schluessel')
                     + warum)
        return Befund(wo, was, warum, f.gewicht)

    # ------------------------------------------------------------- Erkennung
    def _je_entitaet(self, knoten_liste):
        u"""Welche ``self``-Verzeichnisse werden mit einer VARIABLEN geoeffnet?

        Ein fester Schluessel (``self._d['gesamt']``) beweist nichts — das ist
        eine Struktur mit benannten Faechern. Erst der variable Schluessel zeigt,
        dass hier je Entitaet abgelegt wird.
        """
        namen, schluessel = set(), ''
        for wurzel in knoten_liste:
            for k in ast.walk(wurzel):
                treffer = self._nachschlagen(k)
                if not treffer:
                    continue
                name, key = treffer
                namen.add(name)
                if not schluessel and key in self.ENTITAET:
                    schluessel = key
        return namen, schluessel

    def _nachschlagen(self, k):
        """``(feldname, schluesselname)`` — oder ``None``."""
        if isinstance(k, ast.Subscript):
            name = self._selbstfeld(k.value)
            if name and self._variabler_schluessel(k.slice):
                return name, self._namen_text(k.slice)
            return None
        if isinstance(k, ast.Call) and isinstance(k.func, ast.Attribute):
            if k.func.attr not in self.NACHSCHLAGEN or not k.args:
                return None
            name = self._selbstfeld(k.func.value)
            if name and self._variabler_schluessel(k.args[0]):
                return name, self._namen_text(k.args[0])
        return None

    def _unterobjekte(self, methoden):
        u"""``self.x = EinObjekt()`` — eine Instanz mit eigenem Zustand.

        Behaelter und Sperren zaehlen nicht: Ein ``dict`` ist der Ort, an den
        die Unterinstanzen gehoeren, und eine ``Lock`` gehoert dem Dienst.
        """
        namen = {}
        for methode in methoden:
            for k in ast.walk(methode):
                if not isinstance(k, ast.Assign) or not isinstance(k.value, ast.Call):
                    continue
                gerufen = self._gerufen(k.value.func)
                if not gerufen or gerufen in self.KEIN_OBJEKT:
                    continue
                if not gerufen[0].isupper():
                    continue
                for ziel in k.targets:
                    name = self._selbstfeld(ziel)
                    if name and not self._eigen(name):
                        namen[name] = k.lineno
        return namen

    def _flach(self, methode, verzeichnisse, objekte):
        u"""Flache Felder, die sich in dieser Methode AENDERN.

        Nur Veraenderliches. Ein Feld, das in ``__init__`` gesetzt und nie
        wieder angefasst wird, ist eine Einstellung — es je Entitaet zu fuehren
        waere Arbeit ohne Gewinn.

        AM ECHTEN PROJEKT NACHGESCHAERFT (CamTrack, 1036 Klassen, 23.08.2026).
        Der erste Wurf meldete 41 Felder; zwei Sorten davon waren keine, und
        beide haetten die echten Funde verdeckt:

        * **Sammel-Behaelter** (``self.to_keep.append(person)``): Das IST das
          Ergebnis der Klasse, nicht Zustand je Entitaet. In ``persons_cleanup``
          standen gleich zwei davon unter den zwoelf Warnungen. Deshalb zaehlen
          nur Zahlen und Unterinstanzen — ein ``append`` nie.
        * **Selbstbezug ohne Rechnung** (``self.x = leser.zahl(..., self.x)``):
          Der alte Wert dient als VORGABE, nicht als Rechengrundlage.
          ``EngineThresholds`` kam mit drei solchen Zeilen. Verlangt wird jetzt
          eine echte Rechenoperation, also ``self.x = self.x + 1``.
        """
        gefunden = []
        for k in ast.walk(methode):
            name, art = None, 'zaehler'
            if isinstance(k, ast.AugAssign):
                name = self._selbstfeld(k.target)
            elif isinstance(k, ast.Assign) and isinstance(k.value, ast.BinOp):
                # ``self.x = self.x + 1`` — dasselbe wie ``+=``, nur laenger.
                ziele = [z for z in (self._selbstfeld(t) for t in k.targets) if z]
                if ziele and ziele[0] in self._gelesene(k.value):
                    name = ziele[0]
            elif isinstance(k, ast.Call) and isinstance(k.func, ast.Attribute):
                traeger = self._selbstfeld(k.func.value)
                if traeger and traeger in objekte:
                    name, art = traeger, 'unterobjekt'
            if not name or name in verzeichnisse or self._eigen(name):
                continue
            gefunden.append((name, k.lineno, art))
        return gefunden

    # ------------------------------------------------------------ Werkzeuge
    def _eigen(self, name):
        u"""Gehoert das Feld dem Dienst selbst statt seinen Entitäten?"""
        blank = name.lstrip('_').lower()
        teile = [t for t in blank.split('_') if t]
        if blank in self.EIGEN or any(t in self.EIGEN for t in teile):
            return True
        # Eine Kennungsfolge ist absichtlich gemeinsam.
        return any(t in self.FOLGE for t in teile)

    @staticmethod
    def _variabler_schluessel(knoten):
        u"""Ein Schluessel, der eine Entitaet benennen KANN.

        Draussen bleiben feste Werte (``self._d['gesamt']`` ist eine Struktur),
        eigene Felder (``self.points[self.count]`` ist eine Position) und
        Bereiche (``self.puffer[1:]``).
        """
        if isinstance(knoten, (ast.Constant, ast.Slice)):
            return False
        # ``self.x`` als Index ist Buchfuehrung ueber die eigene Stelle.
        return not (isinstance(knoten, ast.Attribute)
                    and isinstance(knoten.value, ast.Name)
                    and knoten.value.id in ('self', 'cls'))

    @staticmethod
    def _ist_datensatz(knoten):
        u"""``@dataclass`` und Verwandte: ein Datensatz, kein Verteiler.

        Ein Datensatz beschreibt EINE Sache. Hält er ein Verzeichnis, sind das
        seine Daten — nicht mehrere Entitäten, die er bedient. ``TrackCenters``
        und ``TrackLockState`` (CamTrack) sind genau das.
        """
        for schmuck in knoten.decorator_list:
            name = getattr(schmuck, 'attr', '') or getattr(schmuck, 'id', '')
            if not name and isinstance(schmuck, ast.Call):
                name = (getattr(schmuck.func, 'attr', '')
                        or getattr(schmuck.func, 'id', ''))
            if 'dataclass' in name:
                return True
        return False

    def _erklaerte_verzeichnisse(self, knoten, methoden):
        u"""``self.x = {}`` bzw. ``x: dict = ...`` — was die Klasse anlegt."""
        namen = set()
        for k in list(knoten.body) + list(methoden):
            for teil in ast.walk(k):
                if isinstance(teil, ast.AnnAssign):
                    if self._dict_artig(teil.annotation) or self._dict_artig(teil.value):
                        namen.add(self._selbstfeld(teil.target)
                                  or self._namen_text(teil.target))
                elif isinstance(teil, ast.Assign) and self._dict_artig(teil.value):
                    for ziel in teil.targets:
                        namen.add(self._selbstfeld(ziel) or self._namen_text(ziel))
        return namen - {''}

    def _dict_artig(self, knoten):
        if isinstance(knoten, ast.Dict) or isinstance(knoten, ast.DictComp):
            return True
        if isinstance(knoten, ast.Call):
            return self._gerufen(knoten.func) in self.VERZEICHNIS
        if isinstance(knoten, ast.Subscript):        # ``dict[str, X]``
            return self._namen_text(knoten.value) in self.VERZEICHNIS
        return self._namen_text(knoten) in self.VERZEICHNIS

    def _ist_test(self, pfad):
        u"""Testdatei? Dort ist der Aufbau je Prüfung der Normalfall."""
        if pfad.name.startswith('test_') or pfad.name.endswith('_test.py'):
            return True
        return any(teil in self.TESTS_AUS for teil in pfad.parts)

    def _vermerkt(self, zeilen, zeile):
        u"""Steht ``# geteilt gewollt`` an der Zeile oder darueber?"""
        for nr in (zeile - 1, zeile - 2):
            if 0 <= nr < len(zeilen) and self.MARKER in zeilen[nr]:
                return True
        return False

    @staticmethod
    def _selbstfeld(knoten):
        """``self.x`` -> ``'x'``, sonst ``''``."""
        if (isinstance(knoten, ast.Attribute)
                and isinstance(knoten.value, ast.Name)
                and knoten.value.id in ('self', 'cls')):
            return knoten.attr
        return ''

    @staticmethod
    def _gerufen(func):
        if isinstance(func, ast.Name):
            return func.id
        return getattr(func, 'attr', '')

    @staticmethod
    def _namen_text(knoten):
        if isinstance(knoten, ast.Name):
            return knoten.id
        return getattr(knoten, 'attr', '')

    @classmethod
    def _gelesene(cls, knoten):
        """Alle ``self.x``, die in einem Ausdruck GELESEN werden."""
        if knoten is None:
            return set()
        return {cls._selbstfeld(k) for k in ast.walk(knoten)} - {''}


__all__ = ['Sammelzustand', 'Sammelfund']
