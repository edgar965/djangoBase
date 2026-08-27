# -*- coding: utf-8 -*-
u"""AnlassfallCheck - lässt jedes Werkzeug seinen eigenen Anlassfall finden.

WOZU (17.08.2026)
=================
Ein Pruefwerkzeug, das nichts mehr findet, sieht aus wie ein sauberes Projekt.
Zweimal an einem Abend war es stattdessen Blindheit (siehe ``anlassfall.py``).
Dieser Sammellauf stellt jedem Werkzeug dieselbe Frage:

    Hier ist der Code, für den du gebaut wurdest. Siehst du ihn noch?

ZWEI LAEUFE JE WERKZEUG - der zweite ist der wichtigere
=======================================================
1. **Anlassfall**: die paar Zeilen, die einen Befund ausloesen MUESSEN.
   Kein Befund -> ``blind``.
2. **Leeres Verzeichnis**: dieselbe Frage ohne Code. Wer hier meldet, hat die
   übergebene Wurzel ignoriert und in Wahrheit das ganze Projekt durchsucht -
   dann sagt Lauf 1 nichts aus. Ohne diese Gegenprobe wäre der ganze Check
   ein Selbstbetrug.

WAS ER NICHT KANN
=================
Werkzeuge ohne dateibasierten Anlassfall (Seitenmessung über HTTP, Zeitmessung)
haben keinen - sie stehen im Bericht als ``ohne Anlassfall`` und werden NICHT
stillschweigend uebergangen. Ein Deckel, den niemand sieht, ist derselbe Fehler
nochmal.

Geschrieben wird ins PROJEKT (``<wurzel>/_anlassfall``), nie nach System-Temp,
und hinterher aufgeräumt.
"""
import shutil
import traceback
from pathlib import Path

from .werkzeug import Ergebnis, Werkzeug

#: Verzeichnisname unter der Projektwurzel. Steht in ``werkzeug.AUSGESCHLOSSEN``,
#: damit die Werkzeuge im NORMALEN Lauf nicht ihre eigenen Testdateien finden.
ORDNER = "_anlassfall"


class Probelauf:
    """Ein Werkzeug, einmal auf einem vorbereiteten Verzeichnis."""

    def __init__(self, klasse, wurzel):
        self.klasse = klasse
        self.wurzel = Path(wurzel)
        self.zeilen = []
        self.fehler = ""

    #: Ein Filter, der nichts filtert — fuer den Probelauf eines Fixers.
    class _AllesErlaubt:
        u"""``Fixer.pfade()`` geht ueber den Git-Filter.

        Der Anlassfall-Ordner liegt UNTER der Projektwurzel, also innerhalb
        des Repos — git antwortet dort, kennt die frisch geschriebenen
        Pruefdateien aber nicht. Der Fixer saehe also grundsaetzlich
        nichts und stuende immer als „blind" da.
        """

        aktiv = False

        @staticmethod
        def erlaubt(_pfad):
            return True

    def fahren(self):
        werkzeug = self.klasse()
        # Instanzattribut schlaegt Methode: das Werkzeug sucht ab HIER.
        werkzeug.wurzel = lambda: self.wurzel
        if not hasattr(werkzeug, "ausgeschlossen"):
            # EIN FIXER IST ANDERS GEBAUT (25.08.2026): Er hat kein
            # `ausgeschlossen()`, sondern `raus()` — und einen Git-Filter.
            # Beides muss fuer den Probelauf geoeffnet werden, sonst sieht
            # er den eigenen Anlassfall nicht.
            frei = werkzeug.raus() - {ORDNER}
            werkzeug.raus = lambda: frei
            werkzeug.gitfilter = lambda: self._AllesErlaubt()
            # `erlaubt()` ist eine KLASSENmethode und fragt `cls.raus()` —
            # die Instanz-Fassung oben erreicht sie nicht. Das ist Absicht:
            # Sie ist der SCHREIBSCHUTZ („nur zum Suchen, nicht als
            # Schreibschutz", `Fixer.pfade`). Hier wird nur `vorschau()`
            # gerufen und nie `anwenden()` — geschrieben wird also nichts,
            # und ohne diese Zeile verwirft jeder Fixer seinen eigenen
            # Anlassfall, weil dessen Ordner `_anlassfall` heisst.
            werkzeug.erlaubt = lambda p: not (set(Path(p).parts) & frei)
            return self._fixerlauf(werkzeug)
        # UND es muss hier auch hinsehen duerfen. ``_anlassfall`` steht in der
        # Ausschlussliste, damit die Werkzeuge im NORMALEN Lauf nicht ihre
        # eigenen Testdateien als Befund melden - im Probelauf filtert genau das
        # aber jede Datei weg. Erster Lauf: 26 Werkzeuge, 0 Treffer, und der
        # Check haette „blind" gemeldet, obwohl er selbst der Blinde war.
        offen = werkzeug.ausgeschlossen() - {ORDNER}
        werkzeug.ausgeschlossen = lambda: offen
        try:
            self.zeilen = list(werkzeug.laufen().zeilen)
        except Exception:                                     # noqa: BLE001
            self.fehler = traceback.format_exc(limit=2).strip().split("\n")[-1]
        return self

    def _fixerlauf(self, werkzeug):
        u"""Ein Fixer meldet ueber ``vorschau()``, nicht ueber ``laufen()``.

        EIN FIXER HEISST NICHT `laufen` (25.08.2026)
        ============================================
        Der Sammellauf ging nur ueber ``WERKZEUGE`` — und die sieben Fixer,
        also genau die, die in Dateien SCHREIBEN, blieben ungeprueft. Ein
        Fixer, der still aufhoert seinen Fall zu finden, faellt niemandem
        auf: Er meldet dann einfach „nichts zu tun".

        Dieselbe Verwechslung hatte kurz zuvor schon den Laeufer
        `tools/wartung/pruefen.py` im Wirtsprojekt abstuerzen lassen
        (``'Altlast' object has no attribute 'pruefen'``).

        GESCHRIEBEN WIRD NICHT: ``vorschau()`` allein, nie ``anwenden()``.
        Ein Selbsttest, der Dateien aendert, ist kein Selbsttest mehr.
        """
        try:
            self.zeilen = [a.als_dict()
                           for a in werkzeug.vorschau().aenderungen]
        except Exception:                                     # noqa: BLE001
            self.fehler = traceback.format_exc(limit=2).strip().split("\n")[-1]
        return self


class Pruefergebnis:
    """Das Urteil über EIN Werkzeug - mit dem Grund, nicht nur ok/nicht ok."""

    def __init__(self, klasse):
        self.klasse = klasse
        self.anlassfall = getattr(klasse, "anlassfall", None)
        self.gefunden = 0
        self.im_leeren = 0
        self.grund = ""

    @property
    def geprueft(self):
        return self.anlassfall is not None

    #: Die vier moeglichen Staende - EIN Feld statt Textvergleichen.
    #: Vorher lasen die Tests den Urteilstext gegen eine Liste erlaubter
    #: Formulierungen; eine neue Formulierung machte sie prompt rot, obwohl
    #: sich an der Sache nichts geaendert hatte (18.08.2026).
    SIEHT = "sieht"            # geprueft, findet seinen Fall
    BLIND = "blind"            # geprueft, findet ihn NICHT
    AUSNAHME = "ausnahme"      # geprueft, aber auf SCHWEIGEN (mindestens=0)
    ERKLAERT = "erklaert"      # kein Anlassfall moeglich, Grund steht am Werkzeug
    UNGEPRUEFT = "ungeprueft"  # kein Anlassfall, kein Grund

    @property
    def prueft_nur_die_ausnahme(self):
        u"""Ein Anlassfall mit ``mindestens=0`` verlangt SCHWEIGEN.

        WARUM DAS EIN EIGENER STAND IST (27.08.2026)
        ============================================
        ``dokumentation`` meldete bis heute jedes gekürzte Workflow-Bild.
        Seit das Bild seinen Fußvermerk selbst trägt, ist der Hinweis
        erledigt — und der alte Anlassfall (``mindestens=1``) fiel um.
        Auf ``mindestens=0, hoechstens=0`` gestellt, war er sofort wieder
        grün und stand als „sieht seinen Fall" in der Tabelle.

        Das ist die gefährlichere Lüge: Ein Anlassfall, der nur noch
        Schweigen verlangt, beweist NICHT, dass das Werkzeug noch etwas
        sehen kann. Er prüft die andere, ebenso wichtige Hälfte — dass
        eine Ausnahme greift. Beides ist berechtigt, aber es darf nicht
        gleich heißen.
        """
        return bool(self.anlassfall) and not self.anlassfall.mindestens

    @property
    def stand(self):
        if self.geprueft:
            if self.grund:
                return self.BLIND
            return (self.AUSNAHME if self.prueft_nur_die_ausnahme
                    else self.SIEHT)
        return (self.ERKLAERT if getattr(self.klasse, "ohne_anlassfall_weil", "")
                else self.UNGEPRUEFT)

    @property
    def urteil(self):
        if not self.geprueft:
            # Der Grund steht AM WERKZEUG (``ohne_anlassfall_weil``). Wer
            # keinen angibt, ist schlicht ungeprueft - und das soll man sehen.
            grund = getattr(self.klasse, "ohne_anlassfall_weil", "")
            return ("kein Anlassfall nötig: %s" % grund if grund
                    else "UNGEPRÜFT — kein Anlassfall, kein Grund angegeben")
        if self.grund:
            return self.grund
        if self.prueft_nur_die_ausnahme:
            # Nicht „sieht seinen Fall": Er verlangt Schweigen und beweist
            # damit gerade NICHT, dass das Werkzeug noch etwas findet.
            return "prüft die Ausnahme (verlangt Schweigen, nicht Befunde)"
        return "sieht seinen Fall"

    @property
    def rot(self):
        return self.geprueft and bool(self.grund)

    def als_zeile(self):
        return {"werkzeug": self.klasse.slug,
                "stand": self.stand,
                "kriterium": self.klasse.kriterium or "—",
                "im Anlassfall": self.gefunden if self.geprueft else "—",
                "im Leeren": self.im_leeren if self.geprueft else "—",
                "urteil": self.urteil,
                "nachgebaut": (self.anlassfall.warum if self.geprueft else
                               "kein dateibasierter Fall — von Hand prüfen")}


class AnlassfallCheck(Werkzeug):
    slug = "anlassfall-check"
    titel = "Sehen die Werkzeuge noch, wofür sie gebaut wurden?"
    zweck = ("Schreibt jedem Werkzeug seinen eigenen Anlassfall hin und prüft, "
             "ob es ihn meldet — plus Gegenprobe auf leerem Verzeichnis.")
    befund = ("Zwei Werkzeuge waren blind, ohne dass es auffiel: "
              "``getattr-namen`` meldete null, weil sein Maßstab zu weit war "
              "und den eigenen Anlassfall verschluckte; ``js-vererbung`` hätte "
              "einen bewusst globalen Namen als Absturz gemeldet. Eine Null "
              "sieht aus wie ein sauberes Projekt.")
    abhilfe = ("‚blind‘ heißt: Der Prüfer wurde verschärft oder umgebaut und "
               "sieht seinen Fall nicht mehr — erst reparieren, dann seinen "
               "Zahlen wieder glauben. ‚meldet im Leeren‘ heißt: Er ignoriert "
               "die übergebene Wurzel; dann ist auch der grüne Lauf wertlos.")
    # Kriterium 19 (26.08.2026): „BDD ohne Gherkin" — dieses Werkzeug IST
    # die Zusicherung, dass jede Regel ein Beispiel hat.
    kriterium = 19
    dauer = "10–30 s"

    #: DAS EINZIGE WERKZEUG OHNE EIGENEN ANLASSFALL — und zwar begruendet
    #: (26.08.2026). Es stand vorher schweigend da, und ein Schweigen sieht
    #: aus wie Vergessen.
    #:
    #: Sein Fall waere es selbst: ein Wegwerf-Projekt mit einem Werkzeug,
    #: dessen Anlassfall nicht mehr greift. Das laesst sich bauen — nur
    #: pruefte es dann sich selbst durch sich selbst, und ein Fehler in der
    #: Mechanik faellt dabei auf beiden Seiten zugleich aus. Die Pruefung
    #: dafuer steht deshalb ausserhalb, in
    #: ``tests/unit/test_fixer_anlassfall.py``.
    ohne_anlassfall_weil = ("prüft die ANDEREN Werkzeuge — sein eigener Fall "
                            "wäre er selbst, und dann pruefte die Mechanik "
                            "sich durch sich selbst; die Prüfung dafür "
                            "steht in tests/unit/test_fixer_anlassfall.py")

    SPALTEN = ("werkzeug", "stand", "kriterium", "im Anlassfall", "im Leeren",
               "urteil", "nachgebaut")

    def laufen(self):
        # AUCH DIE FIXER (25.08.2026, auf Ansage: „mach alle die
        # Verbesserungen"). Sie standen nicht in dieser Schleife — und das
        # sind genau die Werkzeuge, die in Dateien SCHREIBEN. Von sieben
        # hatte einer einen Anlassfall.
        from . import FIXER, WERKZEUGE
        basis = self.wurzel() / ORDNER
        self._aufraeumen(basis)
        ergebnisse = []
        try:
            leer = (basis / "leer")
            leer.mkdir(parents=True, exist_ok=True)
            for klasse in list(WERKZEUGE) + list(FIXER):
                if klasse is type(self):
                    continue
                ergebnisse.append(self._eines(klasse, basis, leer))
        finally:
            self._aufraeumen(basis)

        zeilen = [e.als_zeile() for e in ergebnisse]
        return Ergebnis(list(self.SPALTEN), zeilen,
                        self._fazit(ergebnisse),
                        "Ein Werkzeug ohne Anlassfall ist nicht falsch — es ist "
                        "ungeprüft. Wer eines schreibt, schreibt den Fall "
                        "daneben (siehe ``anlassfall.py``).")

    def _eines(self, klasse, basis, leer):
        aus = Pruefergebnis(klasse)
        if not aus.geprueft:
            return aus
        ordner = aus.anlassfall.schreiben(basis / klasse.slug.replace("/", "_"))

        lauf = Probelauf(klasse, ordner).fahren()
        if lauf.fehler:
            aus.grund = "wirft: %s" % lauf.fehler[:90]
            return aus
        # Befunde, die gar nicht an einer Datei haengen (``ohne_arten``, etwa
        # die LOGGING-Einstellung bei ``protokoll``), gehoeren in keine der
        # beiden Zahlen — siehe `Anlassfall.ohne_arten`.
        gefundene = aus.anlassfall.dateibezogen(lauf.zeilen)
        aus.gefunden = len(gefundene)

        gegen = Probelauf(klasse, leer).fahren()
        leere = aus.anlassfall.dateibezogen(gegen.zeilen)
        aus.im_leeren = len(leere)
        if leere:
            # ZUERST melden: Ein Werkzeug, das im Leeren etwas findet, sucht
            # woanders - dann sagt der Anlassfall-Lauf nichts aus, auch wenn
            # er gruen ist.
            aus.grund = ("meldet im Leeren %d — sucht nicht in der "
                         "übergebenen Wurzel" % len(leere))
            return aus
        aus.grund = aus.anlassfall.urteil(gefundene)
        return aus

    @staticmethod
    def _fazit(ergebnisse):
        geprueft = [e for e in ergebnisse if e.geprueft]
        rot = [e for e in geprueft if e.rot]
        satz = ("%d von %d Werkzeugen an ihrem eigenen Anlassfall geprüft"
                % (len(geprueft), len(ergebnisse)))
        if rot:
            return "%s — %d sehen ihn NICHT: %s." % (
                satz, len(rot), ", ".join(e.klasse.slug for e in rot))
        ohne = len(ergebnisse) - len(geprueft)
        return "%s, alle bestanden%s." % (
            satz, "; %d ohne Anlassfall" % ohne if ohne else "")

    @staticmethod
    def _aufraeumen(basis):
        """Loescht NUR den selbst angelegten Ordner - und nur diesen Namen.

        Rekursives Löschen ohne Prüfung hat in diesem Umfeld schon einmal 972
        Dateien eines laufenden Programms erwischt. Deshalb: Name muss stimmen,
        sonst passiert nichts."""
        basis = Path(basis)
        if basis.name != ORDNER or not basis.is_dir():
            return
        shutil.rmtree(basis, ignore_errors=True)
