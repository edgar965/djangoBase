# -*- coding: utf-8 -*-
u"""Klassenreif — welches Modul wirklich eine Klasse werden sollte.

DIE ANSAGE (Edgar, 26.08.2026)
=============================
    „füge das als neuen Werkzeug-Code-Review-Testfall ein: Umbau von Modul
     in Klassen wenn … [vier Fragen]"

WARUM ES DIESES WERKZEUG NEBEN `freie-funktionen` GIBT
======================================================
`freie-funktionen` zählt Funktionen auf Modulebene. Nachgemessen an
CamTrack am 26.08.2026::

    806 Funktionen auf Modulebene
    630 Konstanten (GROSS)                  — harmlos
      5 veränderlicher Modulzustand         — hier sitzt das Risiko

Und von den fünf sind zwei Django-Konvention (`urlpatterns`). Ein Modul
mit zwanzig zustandslosen Funktionen ist **nicht** fehleranfällig; ein
Modul mit einem geteilten `Lock` ist es.

Belegt am selben Tag: Zwei Module wurden in Klassen umgebaut, und **genau
ein echter Fehler** kam dabei heraus — `marzahn_pi` hatte Host-Suche und
Tailscale-Status an EINER Sperre, ein `tailscale status` mit acht
Sekunden Frist blockierte jeden `base_url()`-Aufruf. Der Fehler steckte im
ZUSTAND, nicht in der Funktionszahl.

Dieses Werkzeug stellt deshalb die vier Fragen, bei denen sich eine Klasse
ihren Platz verdient — und nennt zu jedem Fund den Beleg, der sie mit Ja
beantwortet hat.

DIE VIER FRAGEN
===============
1. **Gibt es Zustand, den jemand besitzen und zurücksetzen muss?**
   `mqtt.py` hatte drei Modul-Globale und zwei ``global``-Anweisungen. Eine
   Prüfung, die den Zwischenspeicher leeren wollte, musste
   ``mqtt._client = None`` schreiben — an Interna fassen. Jetzt gibt es
   ``vergessen()``.

2. **Werden dieselben Werte durch viele Funktionen gefädelt?**
   `matcher.py`: neun Funktionen, jede mit denselben vier Argumenten
   ``(rule, event_type, data, jetzt)``. Das ist ein Konstruktor, der noch
   nicht geschrieben war.

3. **Liegen zwei Anliegen im selben Modul und teilen sich deshalb Zustand?**
   `marzahn_pi.py` — siehe oben. Zwei getrennte Zustands-Häufchen, die sich
   eine Sperre teilten, weil eine Datei nur eine hatte.

4. **Braucht es mehr als ein Exemplar?** (eines je Kamera, je Verbindung)
   Erkennbar an einem Wörterbuch auf Modulebene, das von Hand nach einem
   Schlüssel geführt wird — ``_FRAME_STATE[(rule.pk, cam_id, person_id)]``
   ist eine Instanzverwaltung, die noch keine Klasse hat.

WAS ES NICHT SIEHT
==================
Frage 4 lässt sich nur am Muster erkennen, nicht am Vorsatz: Ein
Wörterbuch mit festen Schlüsseln ist eine Tabelle, keines mit
zusammengesetzten ist eine Instanzverwaltung. Wo das Werkzeug irrt, steht
der Beleg dabei — dann ist es in zehn Sekunden zu widerlegen.
"""
import ast

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ['Klassenreif']

#: Aufrufe, die eine Sammlung VERAENDERN. Ein Modulzustand, den niemand
#: anfasst, ist eine Konstante mit kleinem Namen.
SCHREIBT = {'append', 'extend', 'insert', 'remove', 'pop', 'clear',
            'update', 'setdefault', 'add', 'discard', 'popitem', 'sort'}

#: Bauarten, die veraenderlichen Zustand halten.
SAMMLUNG = (ast.Dict, ast.List, ast.Set)
SAMMLUNG_RUF = {'dict', 'list', 'set', 'defaultdict', 'Counter', 'deque',
                'OrderedDict', 'Lock', 'RLock', 'Event', 'Semaphore',
                'BoundedSemaphore', 'Condition'}

#: Namen, die Django (oder das Muster selbst) auf Modulebene VERLANGT.
#: `urlpatterns` ist keine Klasse, die niemand geschrieben hat.
NIE = {'urlpatterns', 'websocket_urlpatterns', 'app_name', 'handler404',
       'handler500', 'register', 'admin', 'default_app_config'}

#: Ab so vielen Funktionen mit denselben fuehrenden Argumenten gilt Frage 2.
GEFAEDELT_AB = 3
#: So viele gleiche fuehrende Argumente muessen es sein.
GEMEINSAM_AB = 2

class Argumentquellen:
    u"""Woher die Aufrufer die Argumente nehmen: gehalten oder frisch getippt.

    WARUM DAS DEN UNTERSCHIED MACHT (26.08.2026)
    ============================================
    Frage 2 meldete `app/services/config/parser.py`: vier Funktionen mit
    ``(key, default)``. Der Kopf stimmt — die Schlussfolgerung nicht.

    Ein Konstruktor lohnt sich, wenn der Aufrufer die Werte SCHON HAELT
    und sie nur weiterreicht:

        onvif_client.set_system_datetime(cam.ip_address, port, user, pw, …)
        Regelfilter._tor_kamera(rule, event_type, data, jetzt)

    Er lohnt sich nicht, wenn die Werte an jeder Aufrufstelle FRISCH
    dastehen:

        get_int('RETENTION_DAYS', 30)
        get_bool('AUTO_MERGE_REQUIRE_TOP', True)

    Dort gibt es nichts zu halten. `key` und `default` sind der Auftrag,
    nicht die Identitaet. Wer daraus eine Klasse macht, tauscht vier klare
    Aufrufe gegen ein Objekt, das bei jedem Aufruf etwas anderes ist.

    Die Klasse zählt deshalb je aufgerufenem Namen und Stelle mit, ob dort
    ein Literal oder ein gehaltener Wert steht.
    """

    #: Knoten, die einen Wert bezeichnen, den der Aufrufer schon hat.
    GEHALTEN = (ast.Name, ast.Attribute, ast.Subscript, ast.Call, ast.Starred)

    def __init__(self):
        #: name -> Liste je Aufruf: Tupel aus True (gehalten) / False.
        self.stellen = {}

    @classmethod
    def aus(cls, dateien):
        u"""Alle Aufrufe im ganzen Projekt einsammeln — auch aus Ansichten
        und Befehlen, denn dort stehen die Aufrufer der geprueften Module."""
        selbst = cls()
        for datei in dateien:
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8',
                                                 errors='replace'))
            except (SyntaxError, OSError, ValueError):
                continue
            selbst.lesen(baum)
        return selbst

    def lesen(self, baum):
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.Call):
                continue
            ziel = knoten.func
            name = (ziel.attr if isinstance(ziel, ast.Attribute)
                    else ziel.id if isinstance(ziel, ast.Name) else None)
            if not name:
                continue
            self.stellen.setdefault(name, []).append(
                tuple(isinstance(a, self.GEHALTEN) for a in knoten.args))

    def gehalten(self, namen, breite):
        u"""Reicht irgendein Aufrufer in ALLEN ersten `breite` Stellen
        gehaltene Werte durch?

        ``all``, nicht ``any`` — und das ist der Unterschied zwischen
        Fehlalarm und Fund. `recording_thumbs.py` ruft::

            get_int('THUMB_FFMPEG_TIMEOUT', _THUMB_FFMPEG_TIMEOUT)

        Die zweite Stelle ist gehalten, die erste ein Literal. Mit ``any``
        galt `parser.py` weiter als Konstruktor — obwohl der Schlüssel,
        also das eigentliche Merkmal, an jeder Stelle frisch dasteht. Ein
        Konstruktor nimmt ALLE Werte entgegen; wenn auch nur einer je
        Aufruf neu getippt wird, bleibt er ein Argument.

        Ohne jeden beobachteten Aufruf: ja. Ein Modul, das niemand
        aufruft, lässt sich so nicht widerlegen — und ein Befund, der
        nichts kostet, darf stehen bleiben.
        """
        gesehen = False
        for name in namen:
            for aufruf in self.stellen.get(name, ()):
                gesehen = True
                if len(aufruf) >= breite and all(aufruf[:breite]):
                    return True
        return not gesehen


#: WO EINE FUNKTION AUF MODULEBENE RICHTIG STEHT (Edgar, 26.08.2026)
#: =================================================================
#:     „Django-Ansichten, Befehle, Templatetags — `def meine_ansicht(request)`
#:      ist die Schreibweise des Rahmenwerks. 101 der 285 gemeldeten Module
#:      sind Ansichten."
#:
#: Diese Pfade werden GAR NICHT erst gefragt. Nicht weil dort nie etwas
#: schiefginge, sondern weil die Antwort schon feststeht: Der Rahmen ruft
#: die Funktion, nicht eine Klasse. Wer sie umbaut, kaempft gegen Django.
#:
#: `freie-funktionen` meldete sie mit — und genau das hat die Liste
#: unbrauchbar gemacht: 59 % Richtiges, das niemand durcharbeitet.
AUSGENOMMEN_TEILE = ('views', 'view', 'commands', 'management',
                     'templatetags', 'migrations', 'urls', 'admin',
                     'apps', 'conftest', 'asgi', 'wsgi', 'settings')

#: Was der Umbau KOSTET, gehoert in jeden Befund.
#:
#:     „Der Preis: 20 Aufrufstellen aendern, um ein Modul aus einem Zaehler
#:      zu nehmen. Und jede rein statische Klasse ist eine neue Wurzel."
#:
#: Gemessen am 26.08.2026: `marzahn_pi` von 14 freien Funktionen auf zwei
#: Klassen — sieben Aufrufstellen in vier Dateien, und `objektwurzeln`
#: stieg von 37 auf 39. Ein Befund gegen einen anderen getauscht.
PREIS_HINWEIS = ('Preis: %d Datei(en) führen dieses Modul ein; eine rein '
                 'statisch benutzte Klasse ist außerdem eine neue Wurzel '
                 '(`objektwurzeln`).')


class Modulbefund:
    u"""Ein Modul und die Fragen, die es mit Ja beantwortet."""

    def __init__(self, pfad):
        self.pfad = pfad
        #: ``[(nummer, kurz, beleg)]``
        self.fragen = []
        #: Wie viele Dateien fuehren dieses Modul ein — der PREIS des Umbaus.
        self.preis = 0

    def dazu(self, nummer, kurz, beleg):
        self.fragen.append((nummer, kurz, beleg))

    @property
    def reif(self):
        return bool(self.fragen)

    def als_befund(self):
        nummern = sorted(n for n, _k, _b in self.fragen)
        was = 'Frage %s mit Ja beantwortet' % ', '.join(str(n) for n in nummern)
        warum = ' | '.join('%d. %s: %s' % (n, k, b)
                           for n, k, b in sorted(self.fragen))
        warum += '  ' + PREIS_HINWEIS % self.preis
        # Zwei Fragen sind kein doppelter Hinweis, sondern ein anderer
        # Befund: Ein Modul mit Zustand UND zwei Anliegen ist genau der
        # Fall, an dem `marzahn_pi` einen echten Fehler versteckt hatte.
        gewicht = Befund.FEHLER if len(nummern) >= 2 else Befund.WARNUNG
        return Befund(self.pfad, was, warum, gewicht)


class Modulsicht:
    u"""Was auf Modulebene steht — und wer davon was anfasst."""

    def __init__(self, baum):
        self.funktionen = [k for k in baum.body
                           if isinstance(k, (ast.FunctionDef,
                                             ast.AsyncFunctionDef))]
        self.klassen = [k for k in baum.body if isinstance(k, ast.ClassDef)]
        self.zustand = self._zustand(baum)

    @staticmethod
    def _zustand(baum):
        u"""Veraenderliche Namen auf Modulebene — ohne Konstanten.

        GROSS geschriebene Namen sind Vorgaben, keine Zustandshalter, und
        `__all__` ist eine Ausfuhrliste. Beides mitzuzaehlen macht aus 5
        echten Stellen 130 (nachgemessen 26.08.2026) — und eine Liste, die
        zu 96 % aus Richtigem besteht, sieht sich niemand an.
        """
        raus = {}
        for k in baum.body:
            if not isinstance(k, ast.Assign):
                continue
            for ziel in k.targets:
                if not isinstance(ziel, ast.Name):
                    continue
                if (ziel.id.isupper() or ziel.id.startswith('__')
                        or ziel.id in NIE):
                    continue
                if isinstance(k.value, SAMMLUNG) or (
                        isinstance(k.value, ast.Call)
                        and getattr(k.value.func, 'id', '') in SAMMLUNG_RUF):
                    raus[ziel.id] = k.lineno
        return raus

    def beruehrt(self, funktion):
        u"""Welche Modulzustaende fasst DIESE Funktion an?"""
        namen = set()
        for teil in ast.walk(funktion):
            if isinstance(teil, ast.Name) and teil.id in self.zustand:
                namen.add(teil.id)
        return namen


class Klassenreif(BefundWerkzeug):

    slug = 'klassenreif'
    kriterium = 18
    titel = 'Modul, das eine Klasse werden sollte'
    zweck = ('Stellt die vier Fragen, bei denen sich eine Klasse ihren Platz '
             'verdient: eigener Zustand, gefädelte Argumente, zwei Anliegen '
             'in einer Datei, mehr als ein Exemplar nötig.')
    abhilfe = ('Bevor man ein Modul „aufraeumt". Ein Modul IST bereits ein '
               'Namensraum und ein Einzelstueck — eine Klasse mit lauter '
               'Klassenmethoden ist dasselbe mit mehr Syntax. Umgebaut wird, '
               'wo eine der vier Fragen mit Ja beantwortet wird, nicht wo '
               'viele Funktionen stehen.')
    befund = ('CamTrack, 26.08.2026: 806 Funktionen auf Modulebene, aber nur '
              'fünf Stellen mit veraenderlichem Modulzustand — und zwei '
              'davon sind Django-Konvention. Zwei Module wurden an diesem Tag '
              'umgebaut; genau EIN echter Fehler kam heraus, und der steckte '
              'im geteilten Lock von `marzahn_pi`, nicht in der Funktionszahl.')
    dauer = 'wenige Sekunden'

    anlassfall = Anlassfall(
        {
            # Frage 1: Zustand mit `global`.
            'zwischenspeicher.py':
                'import threading\n'
                '\n'
                '_client = None\n'
                '_sperre = threading.Lock()\n'
                '\n\n'
                'def hole():\n'
                '    global _client\n'
                '    with _sperre:\n'
                '        if _client is None:\n'
                '            _client = object()\n'
                '    return _client\n',
            # Frage 2: dieselben Werte durch viele Funktionen gefaedelt.
            'tore.py':
                'def tor_eins(regel, daten, jetzt):\n'
                '    return bool(regel)\n'
                '\n\n'
                'def tor_zwei(regel, daten, jetzt):\n'
                '    return bool(daten)\n'
                '\n\n'
                'def tor_drei(regel, daten, jetzt):\n'
                '    return bool(jetzt)\n',
            # Frage 4: Woerterbuch als Instanzverwaltung von Hand.
            'zaehler.py':
                '_stand = {}\n'
                '\n\n'
                'def hochzaehlen(regel, kamera, person):\n'
                '    schlüssel = (regel, kamera, person)\n'
                '    _stand[schlüssel] = _stand.get(schlüssel, 0) + 1\n'
                '    return _stand[schluessel]\n',
        },
        mindestens=3, erwartet_in='zwischenspeicher.py',
        warum='Drei Module, drei verschiedene Gruende: eines hält Zustand '
              'mit `global`, eines fädelt dieselben drei Werte durch drei '
              'Funktionen, eines führt eine Instanzverwaltung von Hand')

    # ------------------------------------------------------------------
    def pruefen(self, **_argumente):
        befunde, geprueft, ausgenommen = [], 0, 0
        baeume = []
        for datei in self.projektdateien('.py'):
            kurz = self.kurz(datei)
            if self._ausgenommen(kurz):
                ausgenommen += 1
                continue
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8',
                                                 errors='replace'))
            except (SyntaxError, OSError, ValueError):
                continue
            geprueft += 1
            baeume.append((kurz, baum))

        einfuhren = self._einfuhren()
        quellen = Argumentquellen.aus(self.projektdateien('.py'))
        for kurz, baum in baeume:
            fund = self._eines(kurz, baum, quellen)
            if fund.reif:
                stamm = kurz.rsplit('/', 1)[-1][:-3]
                fund.preis = einfuhren.get(stamm, 0)
                befunde.append(fund.als_befund())

        schwer = sum(1 for b in befunde if b.gewicht == Befund.FEHLER)
        kopf = ['%d Module gelesen' % geprueft,
                '%d beantworten mindestens eine der vier Fragen mit Ja'
                % len(befunde),
                '%d davon zwei oder mehr — dort steckt der Zustand, an dem '
                'sich Fehler festmachen' % schwer,
                '%d Module gar nicht erst gefragt: Ansichten, Befehle, '
                'Templatetags — dort IST die Funktion auf Modulebene die '
                'Schreibweise des Rahmenwerks' % ausgenommen]
        return Befundsatz(self.titel, kopf, befunde)

    @staticmethod
    def _ausgenommen(kurz):
        u"""Steht die Funktion hier richtig, egal was die vier Fragen sagen?"""
        teile = [t.lower() for t in kurz.replace('\\', '/').split('/')]
        letzter = teile[-1][:-3] if teile[-1].endswith('.py') else teile[-1]
        return (any(t in AUSGENOMMEN_TEILE for t in teile[:-1])
                or letzter in AUSGENOMMEN_TEILE)

    def _einfuhren(self):
        u"""Wie viele Dateien führen welches Modul ein?

        DER PREIS GEHOERT IN DEN BEFUND. Ein Umbau, der zwanzig
        Aufrufstellen kostet, um ein Modul aus einem Zähler zu nehmen, ist
        schlecht angelegte Zeit — und das soll dranstehen, bevor jemand
        anfaengt, nicht danach.
        """
        zahl = {}
        for datei in self.projektdateien('.py'):
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8',
                                                 errors='replace'))
            except (SyntaxError, OSError, ValueError):
                continue
            gesehen = set()
            for k in ast.walk(baum):
                if isinstance(k, ast.ImportFrom) and k.module:
                    gesehen.add(k.module.rsplit('.', 1)[-1])
                    gesehen.update(a.name for a in k.names)
                elif isinstance(k, ast.Import):
                    gesehen.update(a.name.rsplit('.', 1)[-1] for a in k.names)
            for name in gesehen:
                zahl[name] = zahl.get(name, 0) + 1
        return zahl

    def _eines(self, pfad, baum, quellen=None):
        fund = Modulbefund(pfad)
        sicht = Modulsicht(baum)
        if not sicht.funktionen:
            return fund              # nur Klassen oder nur Vorgaben
        self._frage1_zustand(fund, sicht)
        self._frage2_gefaedelt(fund, sicht, quellen)
        self._frage3_zwei_anliegen(fund, sicht)
        self._frage4_exemplare(fund, sicht, baum)
        return fund

    # ── 1. Zustand, den jemand besitzen und zuruecksetzen muss ──────
    @staticmethod
    def _frage1_zustand(fund, sicht):
        u"""``global`` oder ein veraenderter Modulzustand.

        `mqtt.py` hatte drei Globale und zwei ``global``-Anweisungen. Eine
        Prüfung, die den Zwischenspeicher leeren wollte, musste
        ``mqtt._client = None`` schreiben.
        """
        globale = set()
        for funktion in sicht.funktionen:
            for teil in ast.walk(funktion):
                if isinstance(teil, ast.Global):
                    globale.update(teil.names)
        if globale:
            fund.dazu(1, 'Zustand mit `global`',
                      '%s — wer ihn zuruecksetzen will, muss an Interna '
                      'fassen' % ', '.join(sorted(globale)))
            return
        if sicht.zustand:
            fund.dazu(1, 'veraenderlicher Modulzustand',
                      '%s (Zeile %s)'
                      % (', '.join(sorted(sicht.zustand)),
                         ', '.join(str(z) for z in sorted(
                             sicht.zustand.values()))))

    # ── 2. Dieselben Werte durch viele Funktionen ───────────────────
    @staticmethod
    def _frage2_gefaedelt(fund, sicht, quellen=None):
        u"""Gleiche fuehrende Argumente in mehreren Funktionen.

        `matcher.py`: neun Funktionen mit ``(rule, event_type, data,
        jetzt)``. Das ist ein Konstruktor, den niemand geschrieben hat.
        """
        koepfe = {}
        for funktion in sicht.funktionen:
            namen = tuple(a.arg for a in funktion.args.args)
            if len(namen) < GEMEINSAM_AB:
                continue
            for laenge in range(GEMEINSAM_AB, len(namen) + 1):
                koepfe.setdefault(namen[:laenge], []).append(funktion.name)
        beste = [(len(f), k, f) for k, f in koepfe.items()
                 if len(f) >= GEFAEDELT_AB]
        if not beste:
            return
        # Der laengste gemeinsame Kopf mit den meisten Funktionen.
        beste.sort(key=lambda z: (z[0], len(z[1])), reverse=True)
        zahl, kopf, namen = beste[0]
        # Nur wenn die Aufrufer die Werte auch HALTEN.
        if quellen is not None and not quellen.gehalten(namen, len(kopf)):
            return
        fund.dazu(2, '%d Funktionen faedeln dieselben Werte' % zahl,
                  '(%s) in %s%s' % (', '.join(kopf), ', '.join(namen[:5]),
                                    ' …' if len(namen) > 5 else ''))

    # ── 3. Zwei Anliegen, die sich Zustand teilen ───────────────────
    @staticmethod
    def _frage3_zwei_anliegen(fund, sicht):
        u"""Zwei getrennte Zustands-Haeufchen in einer Datei.

        `marzahn_pi.py`: Host-Suche (`_state`) und Tailscale-Status
        (`_self_cache`) — beide teilten sich EINE Sperre, nicht aus
        Absicht, sondern weil eine Datei nur eine hatte. Ein `tailscale
        status` mit acht Sekunden Frist blockierte damit jeden
        `base_url()`-Aufruf.
        """
        if len(sicht.zustand) < 2:
            return
        # Welche Funktion fasst welchen Zustand an?
        gruppen = {}
        for funktion in sicht.funktionen:
            beruehrt = sicht.beruehrt(funktion)
            if beruehrt:
                gruppen[funktion.name] = beruehrt
        if len(gruppen) < 2:
            return
        # Zwei Zustaende gelten als GETRENNT, wenn keine Funktion beide
        # anfasst — dann sind es zwei Anliegen, die nur zufaellig in einer
        # Datei stehen.
        namen = sorted(sicht.zustand)
        getrennt = []
        for i, a in enumerate(namen):
            for b in namen[i + 1:]:
                if not any(a in s and b in s for s in gruppen.values()):
                    getrennt.append((a, b))
        if getrennt:
            a, b = getrennt[0]
            fund.dazu(3, 'zwei getrennte Anliegen',
                      '`%s` und `%s` werden von verschiedenen Funktionen '
                      'geführt — keine fasst beide an' % (a, b))

    # ── 4. Mehr als ein Exemplar noetig ─────────────────────────────
    @staticmethod
    def _frage4_exemplare(fund, sicht, baum):
        u"""Ein Woerterbuch, das von Hand nach einem Schlüssel geführt wird.

        ``_FRAME_STATE[(rule.pk, cam_id, person_id)]`` ist eine
        Instanzverwaltung ohne Klasse: je Regel, je Kamera, je Person ein
        Zustand. Ein Woerterbuch mit FESTEN Schlüsseln ist dagegen eine
        Tabelle und bleibt eine.
        """
        if not sicht.zustand:
            return
        for teil in ast.walk(baum):
            if not isinstance(teil, ast.Subscript):
                continue
            if not (isinstance(teil.value, ast.Name)
                    and teil.value.id in sicht.zustand):
                continue
            schluessel = teil.slice
            # Ein fester Schluessel (`_state['host']`) ist eine Tabelle.
            if isinstance(schluessel, ast.Constant):
                continue
            fund.dazu(4, 'Instanzverwaltung von Hand',
                      '`%s[…]` wird nach einem berechneten Schlüssel '
                      'geführt — je Exemplar ein Eintrag, aber keine Klasse'
                      % teil.value.id)
            return
