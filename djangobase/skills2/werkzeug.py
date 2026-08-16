# -*- coding: utf-8 -*-
u"""Werkzeug2/Ergebnis - Grundgeruest der Skills2-Werkzeuge.

Skills2 sammelt die Pruefwerkzeuge und die Lehren aus dem grossen Review- und
Umbaudurchgang in shortlongx (August 2026). Sie liegen hier in djangoBase, weil
KEINE davon etwas ueber das Projekt weiss: Gesucht wird immer unter
``settings.BASE_DIR``, gelesen wird der Syntaxbaum.

Warum ein eigenes Paket neben ``skills``: Die beiden sind zeitgleich entstanden
(zwei Sitzungen, zwei Projekte). Getrennt zu halten war billiger, als zwei
halbfertige Fassungen derselben Basisklasse gegeneinander zu mergen; wer sie
spaeter zusammenlegt, hat hier eine vollstaendige, laufende Vorlage.

Ein Werkzeug ist eine Klasse mit ``slug``, ``titel``, ``zweck``, ``befund`` und
``laufen()``. ``laufen()`` gibt ein :class:`Ergebnis` zurueck - nie einen
formatierten Text: Die Seite entscheidet ueber die Darstellung.
"""
import ast
from pathlib import Path

from django.conf import settings

__all__ = ["Werkzeug2", "Ergebnis", "Quelldatei"]

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
                  "sicherung", "backup", "archiv", "alt", "_alt", "old"}


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
    ist das Dictionary richtig: Es geht unveraendert als JSON an die Seite
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


class Werkzeug2:
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

        Projekte können ergänzen: ``DJANGOBASE["skills2_ignorieren"] = [...]``."""
        eigen = (getattr(settings, "DJANGOBASE", {}) or {}).get("skills2_ignorieren") or []
        return AUSGESCHLOSSEN | {str(x) for x in eigen}

    def dateien(self, endung=".py"):
        """Alle Quelldateien des Projekts - ohne venv, Migrationen, Fremdcode."""
        wurzel = self.wurzel()
        raus = self.ausgeschlossen()
        aus = []
        for p in sorted(wurzel.rglob("*" + endung)):
            if any(teil in raus for teil in p.parts):
                continue
            aus.append(Quelldatei(p, wurzel) if endung == ".py" else p)
        return aus

    def laufen(self):                       # pragma: no cover - Schnittstelle
        raise NotImplementedError

    def als_dict(self):
        # Dictionary gewollt: geht unveraendert in die Vorlage bzw. als JSON hinaus.
        return {"slug": self.slug, "titel": self.titel, "zweck": self.zweck,
                "befund": self.befund, "abhilfe": self.abhilfe,
                "dauer": self.dauer, "kriterium": self.kriterium}
