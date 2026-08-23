# -*- coding: utf-8 -*-
u"""Objektwurzeln — wie viele Klassen entstehen ausserhalb jeder Klasse?

DER MASSSTAB (Edgar, 23.08.2026)
================================
    „ein gutes Objektmodell fängt mit einer Klasse an, und verzweigt immer
     weiter über Instanzen"

    „überprüfe doch die globalen Klassen, davon müsste es ganz wenige geben,
     im Idealfall nur eine"

Das ist ein messbarer Satz, und er misst etwas anderes als alle anderen
Werkzeuge hier. Sie fragen nach EINER Stelle — zu lang, zu doppelt, zu
still. Dieses fragt nach der FORM DES GANZEN.

Ein Objektmodell ist ein Baum. Oben steht eine Wurzel — die Anwendung, der
Dienst —, und alles andere haengt als Instanz an ihr: der Dienst haelt seine
Kameras, die Kamera ihren Leser, der Leser seinen Zaehler. Wer eine Kamera
sucht, geht den Weg. Wer den Dienst anhaelt, haelt alles an.

Wird eine Klasse dagegen auf MODULEBENE erzeugt, haengt sie an keinem Ast.
Sie entsteht beim Import, gehoert niemandem, lebt bis zum Prozessende und
ist von ueberall erreichbar. Jede solche Stelle ist eine zweite Wurzel — und
je mehr Wurzeln, desto weniger Baum.

NACHGEMESSEN AN CAMTRACK (23.08.2026)
=====================================
    Klassen im Projekt                556
    auf Modulebene erzeugt             37 verschiedene, an 71 Stellen
    davon eigene Projektklassen        29

Neunundzwanzig Wurzeln statt einer. Darunter ``LaufzeitRegister``, an
demselben Tag von mir gebaut — das Muster ist so bequem, dass es beim
Schreiben nicht auffaellt.

WAS DAS PRAKTISCH KOSTET
========================
Genau an diesem Tag zweimal bezahlt:

* Ein ``SilentFailureWatch`` fuer elf Kameras. Weil er niemandem gehoerte,
  setzte jede funktionierende Kamera den Zaehler der blind gewordenen
  zurueck. Vier Kameras liefen zehn Stunden blind.
* Zwei Zwischenspeicher auf Modulebene hielten Zustand ueber einen
  Dienst-Neustart hinweg, und der naechste Durchlauf rechnete mit Zahlen,
  die niemand mehr schrieb.

Haetten beide an ihrer Kamera gehangen, gaebe es beide Fehler nicht.

WAS NICHT GEZAEHLT WIRD
=======================
* **Fremde Klassen.** ``Lock``, ``Path``, ``Semaphore`` — Wertobjekte und
  Sperren der Standardbibliothek sind keine Aeste eines Objektmodells.
  Gezaehlt wird nur, was das Projekt selbst definiert.
* **Was das Rahmenwerk verlangt.** Django braucht ``register = Library()``
  auf Modulebene, sonst findet es die Vorlagen-Filter nicht. Wer das meldet,
  meldet eine Vorschrift.
* **Dateien, deren Modulebene die Datenstruktur IST** — ``settings.py``,
  ``urls.py``, ``apps.py``.
"""

import ast
import os

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug


class Wurzel:
    u"""Eine Klasse, die ausserhalb jeder Klasse erzeugt wird."""

    __slots__ = ('name', 'stellen', 'besitzer')

    def __init__(self, name, stellen, besitzer):
        self.name = name
        #: ``[(pfad, zeile)]`` — wo sie auf Modulebene entsteht.
        self.stellen = stellen
        #: Klassen, die dieselbe Klasse als ``self.x`` halten. Gibt es
        #: welche, ist der Ast schon da und die Wurzel daneben ueberfluessig.
        self.besitzer = besitzer

    @property
    def gewicht(self):
        # Steht sie ANDERSWO schon als Instanz-Attribut, ist der Fall klar:
        # Der Platz im Baum existiert, die globale Instanz ist der Umweg.
        if self.besitzer:
            return Befund.WARNUNG
        return Befund.HINWEIS


class Baumsicht:
    u"""Wie die Klassen eines Projekts zueinander stehen.

    Die vier Toepfe sind erschoepfend: Jede Klasse liegt in genau einem.

    NACHGEMESSEN AN CAMTRACK (23.08.2026) — und der Nutzer hatte recht mit
    seinem Zweifel ("Kann ich nicht glauben, hast du eine Basisklasse, und
    alle andere geht wie ein Baum davon ab??")::

        Klassen im Projekt                 556   100 %
          haengen als self.x an einer       74    13 %   <- der Baum
          entstehen auf Modulebene          29     5 %   <- Wurzeln
          nur oertlich in Funktionen        252    45 %
          NIRGENDS erzeugt                 202    36 %

    Die erste Fassung dieses Werkzeugs zaehlte nur die Wurzeln und schloss
    daraus, alles andere haenge an einem Baum. Das war eine Annahme, keine
    Messung — tatsaechlich haengen dreizehn Prozent. Es gibt nicht EINEN
    Baum, sondern fuenf mittelgrosse (PersonDetector 14 Klassen,
    LiveOrchestrator 11, StrictPersonDetector 10) und daneben 454 Klassen,
    die an keinem haengen.
    """

    __slots__ = ('alle', 'im_baum', 'wurzeln', 'nur_lokal', 'nie', 'haelt')

    def __init__(self, alle, im_baum, wurzeln, nie, haelt):
        self.alle = alle
        #: Wird von einer anderen Klasse als ``self.x`` gehalten.
        self.im_baum = im_baum
        #: Entsteht auf Modulebene.
        self.wurzeln = wurzeln
        #: Wird nirgends erzeugt (Basisklassen und Models sind schon raus).
        self.nie = nie
        #: Alles Uebrige: nur oertlich in einer Funktion erzeugt.
        self.nur_lokal = alle - im_baum - wurzeln - nie
        #: ``{Klasse: Zahl der gehaltenen}`` — die dicken Aeste.
        self.haelt = haelt

    def anteil(self, menge) -> float:
        return 100.0 * len(menge) / len(self.alle) if self.alle else 0.0

    def zeilen(self) -> list:
        return [
            '%d Klassen im Projekt' % len(self.alle),
            'im Baum (haengen als self.x an einer anderen): %d (%.0f %%)'
            % (len(self.im_baum), self.anteil(self.im_baum)),
            'Wurzeln (auf Modulebene erzeugt): %d (%.0f %%)'
            % (len(self.wurzeln), self.anteil(self.wurzeln)),
            'nur oertlich in Funktionen erzeugt: %d (%.0f %%)'
            % (len(self.nur_lokal), self.anteil(self.nur_lokal)),
            'nirgends erzeugt: %d (%.0f %%)'
            % (len(self.nie), self.anteil(self.nie)),
            'groesste Aeste: %s' % (', '.join(
                '%s (%d)' % (n, z) for n, z in
                sorted(self.haelt.items(), key=lambda p: -p[1])[:5]) or "—"),
        ]


class Objektwurzeln(BefundWerkzeug):

    slug = 'objektwurzeln'
    kriterium = 4
    titel = 'Wurzeln des Objektmodells'
    zweck = ('Zaehlt die Klassen, die auf Modulebene erzeugt werden. Ein '
             'Objektmodell hat idealerweise EINE Wurzel; alles andere haengt '
             'als Instanz daran.')
    abhilfe = ('Die Instanz dorthin verschieben, wo sie gebraucht wird — als '
               'Attribut der Klasse, die sie benutzt. Wird sie an mehreren '
               'Stellen gebraucht, gehoert sie der gemeinsamen Oberklasse '
               'bzw. dem Dienst, der beide haelt.')
    befund = ('CamTrack: 29 eigene Klassen entstehen auf Modulebene statt '
              'einer. Eine davon war eine Stillstands-Wache fuer elf '
              'Kameras — jede laufende Kamera setzte den Zaehler der blinden '
              'zurueck, vier liefen zehn Stunden blind.')
    dauer = 'Sekunden'
    eingabe = ('ab', 'Ab wie vielen Wurzeln melden? (0 = jede)', '1')

    #: Klassen der Standardbibliothek und gaengiger Pakete. Ein ``Lock`` ist
    #: kein Ast eines Objektmodells, sondern ein Wertobjekt.
    FREMD = frozenset({
        'Lock', 'RLock', 'Semaphore', 'Event', 'Condition', 'Barrier',
        'Path', 'PurePath', 'Queue', 'LifoQueue', 'PriorityQueue',
        'Decimal', 'Fraction', 'Counter', 'OrderedDict', 'ChainMap',
        'ThreadPoolExecutor', 'ProcessPoolExecutor', 'Logger', 'Template',
    })

    #: Was das Rahmenwerk auf Modulebene VERLANGT. Wer das meldet, meldet
    #: eine Vorschrift.
    RAHMENWERK = frozenset({'Library', 'Router', 'DefaultRouter', 'Signal',
                            'AdminSite', 'App', 'Blueprint'})

    #: Dateien, deren Modulebene die Datenstruktur IST.
    DATEIEN_AUS = ('settings.py', 'conf.py', 'urls.py', 'apps.py', 'wsgi.py',
                   'asgi.py', 'manage.py', 'routing.py', 'admin.py')

    #: Verzeichnisse, in denen Modulebene normal ist.
    ORDNER_AUS = ('tests', 'test', 'migrations')

    anlassfall = Anlassfall(
        {"wache.py": (
            "class Wache:\n"
            "    def __init__(self):\n"
            "        self.blind = 0\n\n\n"
            "WACHE = Wache()\n"),
         "zaehler.py": (
            "class Zaehler:\n"
            "    def __init__(self):\n"
            "        self.stand = 0\n\n\n"
            "ZAEHLER = Zaehler()\n"),
         "kamera.py": (
            "from wache import Wache\n\n\n"
            "class Kamera:\n"
            "    def __init__(self):\n"
            "        self.wache = Wache()\n")},
        mindestens=1, erwartet_in="Wache",
        warum="Eine Stillstands-Wache fuer elf Kameras (CamTrack, "
              "09.05.2026): Weil sie niemandem gehoerte, setzte jede "
              "laufende Kamera den Zaehler der blinden zurueck. `Kamera` "
              "haelt daneben schon eine eigene — der Platz im Baum ist da. "
              "ZWEI Wurzeln, denn EINE ist per Vorgabe kein Fehler: Der "
              "erste Wurf hatte nur eine und war damit blind, was der "
              "`anlassfall-check` sofort meldete")

    # ---------------------------------------------------------------- Ablauf
    def pruefen(self, ab='1', **_argumente):
        try:
            grenze = max(0, int(str(ab).strip() or 1))
        except ValueError:
            grenze = 1

        eigene, stellen, besitz = set(), {}, {}
        erzeugt, basen, geerbt, dateien = set(), set(), {}, 0
        for pfad in self.projektdateien('.py'):
            if self._ueberspringen(pfad):
                continue
            baum = self._lesen(pfad)
            if baum is None:
                continue
            dateien += 1
            self._klassen(baum, eigene, basen, geerbt)
            self._modulebene(baum, self.kurz(pfad), stellen)
            self._besitz(baum, besitz)
            self._erzeugt(baum, erzeugt)
            self._fabriken(baum, erzeugt)

        sicht = self._baumsicht(eigene, besitz, stellen, erzeugt,
                                basen, geerbt)
        wurzeln = [Wurzel(name, orte, sorted(besitz.get(name, ())))
                   for name, orte in stellen.items() if name in eigene]
        wurzeln.sort(key=lambda w: (w.gewicht != Befund.WARNUNG,
                                    -len(w.stellen), w.name))

        kopf = ['%d Dateien' % dateien] + sicht.zeilen()
        kopf.append('Idealwert: EINE Wurzel, alles andere haengt daran')

        befunde = []
        if len(wurzeln) > grenze:
            befunde += [self._befund(w) for w in wurzeln]
        befunde += [self._tot(name) for name in sorted(sicht.nie)]
        return Befundsatz(self.titel, kopf, befunde)

    def _baumsicht(self, eigene, besitz, stellen, erzeugt, basen, geerbt):
        u"""Die vier Toepfe — und wer beim "nirgends erzeugt" nicht zaehlt."""
        haelt = {}
        for kind, eltern in besitz.items():
            if kind not in eigene:
                continue
            for e in eltern:
                haelt[e] = haelt.get(e, 0) + 1
        im_baum = {n for n in eigene if besitz.get(n)}
        wurzeln = {n for n in eigene if n in stellen}
        nie = {n for n in eigene
               if n not in erzeugt
               and not self._darf_ruhen(n, basen, geerbt)}
        return Baumsicht(eigene, im_baum, wurzeln, nie, haelt)

    #: Erbt eine Klasse hiervon, erzeugt sie das Rahmenwerk — nicht der
    #: Quelltext. Ohne diese Liste meldet das Werkzeug halb Django als
    #: toten Bestand.
    RAHMEN_BASEN = frozenset({
        'Model', 'Form', 'ModelForm', 'Serializer', 'ModelSerializer',
        'BaseCommand', 'View', 'TemplateView', 'ListView', 'DetailView',
        'Migration', 'AppConfig', 'ModelAdmin', 'Manager', 'QuerySet',
        'Exception', 'BaseException', 'ValueError', 'RuntimeError',
        'Enum', 'IntEnum', 'StrEnum', 'Protocol', 'ABC', 'NamedTuple',
        'AsyncWebsocketConsumer', 'WebsocketConsumer', 'Thread',
    })

    def _darf_ruhen(self, name, basen, geerbt) -> bool:
        u"""Wird diese Klasse zu Recht nirgends mit ``X()`` erzeugt?

        Vier Faelle, alle legitim:

        * **Basisklasse.** Jemand erbt von ihr; erzeugt wird die
          Unterklasse.
        * **Datenbank-Model.** Der ORM erzeugt sie, nicht der Quelltext.
        * **Ansicht, Formular, Befehl.** Das Rahmenwerk erzeugt sie ueber
          die URL-Tabelle bzw. ``manage.py``.
        * **``Meta``** — eine Beschreibung, kein Objekt.
        """
        if name in basen or name == 'Meta':
            return True
        return any(elter in self.RAHMEN_BASEN
                   for elter in geerbt.get(name, ()))

    # --------------------------------------------------------------- Ausgabe
    @staticmethod
    def _befund(w):
        ort = '%s:%d' % w.stellen[0]
        mehr = (' (+%d weitere)' % (len(w.stellen) - 1)
                if len(w.stellen) > 1 else '')
        was = '%s wird auf Modulebene erzeugt%s' % (w.name, mehr)
        if w.besitzer:
            warum = ('%s haelt dieselbe Klasse schon als Instanz-Attribut — '
                     'der Platz im Baum ist da, die globale Instanz ist der '
                     'Umweg.' % ', '.join(w.besitzer[:3]))
        else:
            warum = ('Sie gehoert niemandem: entsteht beim Import, lebt bis '
                     'zum Prozessende, ist von ueberall erreichbar. Wer sie '
                     'benutzt, sollte sie halten.')
        return Befund(ort, was, warum, w.gewicht)

    # ------------------------------------------------------------------ Baum
    @staticmethod
    def _lesen(pfad):
        try:
            return ast.parse(pfad.read_text(encoding='utf-8', errors='replace'))
        except (SyntaxError, OSError):
            return None

    def _ueberspringen(self, pfad) -> bool:
        if pfad.name in self.DATEIEN_AUS:
            return True
        if pfad.name.startswith('test_'):
            return True
        return any(teil in self.ORDNER_AUS for teil in pfad.parts)

    @staticmethod
    def _klassen(baum, hinein: set, basen: set, geerbt: dict) -> None:
        u"""Klassen sammeln — samt ihrer Oberklassen.

        Die Oberklassen braucht es zweimal: Wer Oberklasse IST, wird zu
        Recht nie selbst erzeugt; und wer von einem Rahmenwerk-Typ erbt,
        wird vom Rahmenwerk erzeugt.
        """
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.ClassDef):
                continue
            hinein.add(knoten.name)
            for elter in knoten.bases:
                name = (elter.id if isinstance(elter, ast.Name)
                        else getattr(elter, 'attr', ''))
                if not name:
                    continue
                basen.add(name)
                geerbt.setdefault(knoten.name, set()).add(name)

    @staticmethod
    def _fabriken(baum, hinein: set) -> None:
        """``cls(...)`` in einer Klassenmethode erzeugt DIESE Klasse.

        Ohne das meldet das Werkzeug jede Klasse mit einer Fabrik-Methode
        als toten Bestand. Nachgemessen am 23.08.2026: `AusschnittNachzieher`
        stand unter den ersten zehn — er wird ueber
        ``get_instance()`` -> ``cls()`` erzeugt, an genau einer Stelle, und
        laeuft im Dienst.
        """
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.ClassDef):
                continue
            for teil in ast.walk(knoten):
                if (isinstance(teil, ast.Call)
                        and isinstance(teil.func, ast.Name)
                        and teil.func.id == 'cls'):
                    hinein.add(knoten.name)
                    break

    def _erzeugt(self, baum, hinein: set) -> None:
        u"""Jede Stelle, an der ueberhaupt ``Klasse(...)`` steht."""
        for knoten in ast.walk(baum):
            name = self._gerufene_klasse(knoten)
            if name:
                hinein.add(name)

    @staticmethod
    def _tot(name: str) -> Befund:
        return Befund(
            name, '%s wird nirgends erzeugt' % name,
            'Keine Oberklasse, kein Model, keine Ansicht — und niemand '
            'ruft `%s(...)`. Entweder toter Bestand oder ein Ast, den '
            'jemand abgeschnitten hat.' % name, Befund.HINWEIS)

    def _modulebene(self, baum, kurz: str, hinein: dict) -> None:
        u"""``X = Klasse(...)`` GANZ AUSSEN — nicht in Funktion oder Klasse."""
        for knoten in baum.body:              # NUR Modulebene
            if not isinstance(knoten, (ast.Assign, ast.AnnAssign)):
                continue
            name = self._gerufene_klasse(getattr(knoten, 'value', None))
            if name:
                hinein.setdefault(name, []).append((kurz, knoten.lineno))

    def _besitz(self, baum, hinein: dict) -> None:
        u"""``self.x = Klasse(...)`` — wer haelt wen?"""
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.ClassDef):
                continue
            for teil in ast.walk(knoten):
                if not isinstance(teil, ast.Assign):
                    continue
                name = self._gerufene_klasse(teil.value)
                if not name:
                    continue
                for ziel in teil.targets:
                    if (isinstance(ziel, ast.Attribute)
                            and isinstance(ziel.value, ast.Name)
                            and ziel.value.id == 'self'):
                        hinein.setdefault(name, set()).add(knoten.name)

    def _gerufene_klasse(self, wert) -> str:
        u"""Der Name der erzeugten Klasse — oder ``''``.

        Erkannt an der Grossschreibung. Das ist eine Uebereinkunft, keine
        Regel der Sprache — aber sie gilt in jedem Python-Projekt, und die
        Alternative (jeden Namen aufloesen) faende bei Importen ueber
        mehrere Ebenen ohnehin nicht mehr.
        """
        if not isinstance(wert, ast.Call):
            return ''
        ruf = wert.func
        name = (ruf.id if isinstance(ruf, ast.Name)
                else getattr(ruf, 'attr', ''))
        if not name or not name[:1].isupper():
            return ''
        if name in self.FREMD or name in self.RAHMENWERK:
            return ''
        return name


__all__ = ['Objektwurzeln', 'Wurzel']
