# -*- coding: utf-8 -*-
u"""Werkzeug/Ergebnis - das Grundgeruest ALLER Pruefwerkzeuge.

Skills2 sammelt die Pruefwerkzeuge und die Lehren aus dem grossen Review- und
Umbaudurchgang in shortlongx (August 2026). Sie liegen hier in djangoBase, weil
KEINE davon etwas ueber das Projekt weiss: Gesucht wird immer unter
``settings.BASE_DIR``, gelesen wird der Syntaxbaum.

Die Klasse hiess bis zum 18.08.2026 ``Werkzeug2`` - ein Name aus der Zeit, als
es zwei Kästen mit zwei Basisklassen gab. Beide sind zusammengefuehrt (Ansage:
„benenne um werkzeug2 in werkzeug, merge alles"); die befundbasierte Bauform
liegt in ``befund.py`` und erbt von hier.

Ein Werkzeug ist eine Klasse mit ``slug``, ``titel``, ``zweck``, ``befund`` und
``laufen()``. ``laufen()`` gibt ein :class:`Ergebnis` zurueck - nie einen
formatierten Text: Die Seite entscheidet ueber die Darstellung.
"""
import ast
from pathlib import Path

from django.conf import settings

__all__ = ["Werkzeug", "Ergebnis", "Quelldatei"]

#: Verzeichnisse, die nie zum Projektcode gehoeren.
#:
#: „sicherung"/„archiv"/„alt" stehen hier aus einem gemessenen Grund: In
#: shortlongx liegt unter ``werkzeug/sicherung`` eine Kopie von 405 Dateien
#: (der Stand vor dem letzten Umbau, aus dem 53 Werkzeuge lesen). Ohne den
#: Ausschluss meldete die Duplikat-Suche 1.426 Gruppen statt 329 - lauter
#: „Duplikate", die genau dafuer da sind, Kopien zu sein.
AUSGESCHLOSSEN = {".git", "__pycache__", "node_modules", "venv", "pythonVENV",
                  ".venv", "env", "site-packages", "migrations", "staticfiles",
                  ".mypy_cache", ".pytest_cache", "dist", "build",
                  "sicherung", "backup", "archiv", "alt", "_alt", "old",
                  # Der Wegwerf-Ordner des Anlassfall-Checks. Ohne ihn faenden
                  # die Werkzeuge im normalen Lauf ihre eigenen Testdateien -
                  # und meldeten absichtlich kaputten Code als Befund.
                  "_anlassfall",
                  # FREMDER CODE, der in gewachsenen Projekten NEBEN dem
                  # Quelltext liegt (belegt am 17.08.2026 im Projekt assistant:
                  # 34 % ALLER Befunde kamen von dort).
                  #
                  # * ``virensuche_quarantine`` - 585 MB, in die der eigene
                  #   Virenscanner Fundstuecke schiebt. Dort meldete ``jssyntax``
                  #   drei „kaputte ES-Module": verseuchte Dateien, die genau
                  #   deshalb dort liegen. Ein Werkzeug, das Schadcode zum
                  #   Aufraeumen vorschlaegt, ist schlimmer als keins.
                  # * ``chrome-profile`` / ``Extensions`` - ein abgelegtes
                  #   Browser-Profil, 437 JS-Dateien aus fremden Erweiterungen
                  #   (minifizierte webpack-Buendel). Daher kamen alle 16
                  #   Befunde von ``js-vererbung`` und die Haelfte von
                  #   ``jsregistrierung``.
                  # * ``var`` - Laufzeitablage (Protokolle, Bilder, Profile)
                  #   neben ``logs`` und ``media``, kein Quelltext.
                  "virensuche_quarantine", "quarantine", "quarantaene",
                  "chrome-profile", "Extensions", "var",
                  # EINE GRENZE FUER ALLE WERKZEUGE (17.08.2026)
                  # ==========================================
                  # Diese Namen standen bis dahin nur in
                  # ``basis.EigenesWerkzeug.ZUSATZ_RAUS`` — und die gilt fuer
                  # genau DREI Werkzeuge. Die anderen achtundzwanzig erben von
                  # ``Werkzeug`` und durchsuchten weiter alles.
                  #
                  # Gemessen am Projekt assistant: 40 % aller Befunde kamen aus
                  # fremdem Code. Bei ``doppelcode`` 39 von 40 gezeigten Zeilen,
                  # bei ``rueckgabetupel`` 38, bei ``doppelrumpf`` und
                  # ``dateigroesse`` 37. Der Spitzenbefund von ``dateigroesse``
                  # war eine 4.741-Zeilen-Datei in ``unsloth_compiled_cache`` —
                  # erzeugter Zwischenstand, den niemand aufteilt.
                  #
                  # Drei Listen fuer dieselbe Frage laufen auseinander; deshalb
                  # steht sie jetzt hier, an der Wurzel.
                  # `models` STAND HIER und ist am 29.08.2026 entfallen.
                  # Gedacht war es fuer Ordner mit ML-Gewichten; getroffen hat
                  # es Django-Modellpakete. In 3DTools verschwanden so
                  # `core/models/` mit vierzehn Dateien aus JEDER Pruefung —
                  # und zwar genau, weil das Projekt der Regel folgt, eine zu
                  # grosse `models.py` in ein Paket aufzuteilen.
                  #
                  # Ein Gewichte-Ordner enthaelt keine `.py`, `.js` oder
                  # `.html`; die Werkzeuge lesen nur diese drei. Der Ausschluss
                  # brachte dort also nichts und kostete hier alles. Wer ihn
                  # doch braucht: `DJANGOBASE["skills_ignorieren"]`.
                  "vendor", "tmp", "temp", "unsloth_compiled_cache",
                  "media", "logs", "output", "Output", "Datenbank", "fixtures",
                  ".claude", "docs", "htmlcov", ".idea", ".vscode",
                  # Eigenstaendige Programme im Projektbaum, die der
                  # Django-Testlaeufer nie faehrt (bei assistant: ein
                  # Windows-Diktiergeraet mit eigener venv).
                  "diktator"}


class Quelldatei:
    """Eine Python-Datei mit ihrem Syntaxbaum - einmal gelesen, einmal geparst."""

    def __init__(self, pfad, wurzel):
        self.pfad = Path(pfad)
        self.name = self.pfad.relative_to(wurzel).as_posix()
        self._text = None
        self._baum = None
        self._fehler = None

    @property
    def text(self):
        if self._text is None:
            try:
                self._text = self.pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                self._text = ""
        return self._text

    @property
    def baum(self):
        """Der Syntaxbaum - oder None, wenn die Datei nicht parst."""
        if self._baum is None and self._fehler is None:
            try:
                self._baum = ast.parse(self.text)
            except (SyntaxError, ValueError) as e:
                self._fehler = str(e)
        return self._baum

    @property
    def zeilen(self):
        return self.text.count("\n") + 1 if self.text else 0

    def knoten(self, *arten):
        """Alle Knoten der genannten Arten im ganzen Baum."""
        if self.baum is None:
            return []
        return [k for k in ast.walk(self.baum) if isinstance(k, arten)]


class Ergebnis:
    """Was ein Werkzeug gefunden hat.

    ``zeilen`` sind Dictionaries mit den Spalten, die ``spalten`` nennt - hier
    ist das Dictionary richtig: Es geht unverändert als JSON an die Seite
    (siehe die Lehre „Dictionary oder Klasse?")."""

    def __init__(self, spalten, zeilen, zusammenfassung="", hinweis=""):
        self.spalten = list(spalten)
        self.zeilen = list(zeilen)
        self.zusammenfassung = zusammenfassung
        self.hinweis = hinweis

    def als_dict(self):
        return {"spalten": self.spalten, "zeilen": self.zeilen,
                "anzahl": len(self.zeilen),
                "zusammenfassung": self.zusammenfassung, "hinweis": self.hinweis}


class Werkzeug:
    """Basis aller Skills2-Werkzeuge."""

    slug = ""
    titel = ""
    #: Wonach es sucht - eine Zeile, steht in der Tabelle.
    zweck = ""
    #: Der reale Befund, der es ausgeloest hat - das macht den Unterschied
    #: zwischen „nettes Werkzeug" und „das brauchst du wirklich".
    befund = ""
    #: Was zu tun ist, wenn es etwas findet.
    abhilfe = ""
    #: Grobe Laufzeit, damit niemand versehentlich minutenlang wartet.
    dauer = "unter 1 s"
    #: Nummer des Auftrags-Kriteriums, das dieses Werkzeug bedient (0 = keines).
    kriterium = 0
    #: :class:`~.anlassfall.Anlassfall` - der Code, den dieses Werkzeug melden
    #: MUSS. Geprueft von ``anlassfall-check``: Ein Pruefer, der nach einem
    #: Umbau seinen eigenen Fall nicht mehr sieht, meldet null und sieht dabei
    #: aus wie ein sauberes Projekt (zweimal passiert am 17.08.2026).
    anlassfall = None

    #: Wer KEINEN Anlassfall hat, sagt hier in einem Satz warum - sonst gilt er
    #: als blind. Beispiele: ein Werkzeug, das nur MISST (Zeilen, Zeiten), oder
    #: eines, das den laufenden Server bzw. den Django-Renderer braucht; in
    #: einem Wegwerf-Verzeichnis gibt es dafuer nichts nachzubauen.
    #:
    #: Der Grund steht HIER und nicht in einer Liste woanders (bis zum
    #: 18.08.2026 fuehrte der Test dazu ein eigenes Namensregister). Zwei Orte
    #: fuer dieselbe Angabe laufen auseinander, und der zweite ist immer der,
    #: den man beim Umbau vergisst.
    ohne_anlassfall_weil = ""

    def wurzel(self):
        """Die Wurzel des PROJEKTS, nicht nur des Django-Teils.

        ``BASE_DIR`` zeigt auf das Verzeichnis mit ``manage.py``. In vielen
        Projekten liegt daneben noch Code, der genauso dazugehört (bei
        shortlongx: ``brain/``, ``depot/``, ``werkzeug/`` — zusammen zwei Drittel
        der Zeilen). Eine Prüfung, die den nicht sieht, meldet 19 statt 31
        Fundstellen und wirkt gründlicher, als sie ist.

        Deshalb: eine Ebene höher, wenn dort das Git-Repo beginnt."""
        basis = Path(getattr(settings, "BASE_DIR", "."))
        eltern = basis.parent
        if (eltern / ".git").exists() and not (basis / ".git").exists():
            return eltern
        return basis

    def ausgeschlossen(self):
        """Verzeichnisnamen, die übersprungen werden.

        Projekte können ergänzen: ``DJANGOBASE["skills_ignorieren"] = [...]``.

        Der alte Schlüssel ``skills2_ignorieren`` wird weiter gelesen: Als die
        drei Werkzeugkästen zu einem wurden (17.08.2026), verschwand das Paket
        ``skills2`` — die Einstellungen in den Projekten aber nicht. Ein
        stillschweigend ignorierter Schlüssel hätte dort auf einen Schlag
        Fremdcode in die Befunde geholt.
        """
        cfg = getattr(settings, "DJANGOBASE", {}) or {}
        eigen = list(cfg.get("skills_ignorieren") or [])
        eigen += list(cfg.get("skills2_ignorieren") or [])
        return AUSGESCHLOSSEN | {str(x) for x in eigen}

    def gitfilter(self):
        u"""Was in der ``.gitignore`` steht, ist nicht der Code des Projekts.

        Anlass (18.08.2026): ``jswaisen`` meldete in shortlongx 21 „verwaiste"
        Dateien, die alle ignoriert sind - der Arbeitsordner des JS-Testlaeufers
        und ein heruntergeladenes Chrome-Profil. Einzelheiten und der Rückfall
        ohne git stehen im Kopf von ``gitfilter.py``.
        """
        from .gitfilter import GitFilter
        if not hasattr(self, "_gitfilter"):
            self._gitfilter = GitFilter(self.wurzel())
        return self._gitfilter

    def frontendquellen(self):
        """Die Frontend-Dateien dieses Projekts — für alle Werkzeuge dieselben.

        Vor dem 17.08.2026 hatte jedes JS-Werkzeug seine eigene Ausschlussliste
        und seinen eigenen ``rglob``-Generator — acht Kopien in vier Fassungen.
        Die Werkzeuge waren sich damit nicht einig, welche Dateien zum Projekt
        gehören, und jede Zahl bezog sich auf eine andere Menge.
        """
        from .frontendquellen import Frontendquellen
        return Frontendquellen(self.wurzel(), self.ausgeschlossen(),
                               gitfilter=self.gitfilter())

    def pfade(self, muster="*.py", unter=None):
        u"""Alle Dateien zu einem glob-Muster — die Menge „gehört zum Projekt".

        DER EINE WEG INS DATEISYSTEM (18.08.2026)
        =========================================
        Der ``.gitignore``-Filter kam zuerst nur in ``dateien()`` und
        ``frontendquellen()`` an. Ein Dutzend Werkzeuge sucht aber selbst per
        ``rglob`` und ging daran vorbei — gemessen in shortlongx: **227 von 428
        JS-Dateien** (53 %) stehen dort in der ``.gitignore``
        (``werkzeug/.chrome/``, ``tests_app/js/_web/``). Wer über diese Methode
        geht, sieht dieselbe Menge wie alle anderen.

        In assistant und djangoBase ist der Unterschied 0 % — dort fängt die
        feste Ausschlussliste schon alles ab. Genau deshalb fiel die Lücke hier
        nie auf, und genau deshalb steht der Weg jetzt an EINER Stelle.

        ``unter`` schränkt auf ein Unterverzeichnis ein (statt eines eigenen
        ``rglob`` darauf).
        """
        wurzel = self.wurzel()
        raus = self.ausgeschlossen()
        git = self.gitfilter()
        return [p for p in sorted(Path(unter or wurzel).rglob(muster))
                if not any(teil in raus for teil in p.parts) and git.erlaubt(p)]

    def dateien(self, endung=".py"):
        """Alle Quelldateien des Projekts - ohne venv, Migrationen, Fremdcode."""
        wurzel = self.wurzel()
        return [Quelldatei(p, wurzel) if endung == ".py" else p
                for p in self.pfade("*" + endung)]

    def laufen(self):                       # pragma: no cover - Schnittstelle
        raise NotImplementedError

    def als_dict(self):
        # Dictionary gewollt: geht unveraendert in die Vorlage bzw. als JSON hinaus.
        return {"slug": self.slug, "titel": self.titel, "zweck": self.zweck,
                "befund": self.befund, "abhilfe": self.abhilfe,
                "dauer": self.dauer, "kriterium": self.kriterium}
