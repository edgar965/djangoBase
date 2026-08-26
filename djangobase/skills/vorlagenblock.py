# -*- coding: utf-8 -*-
u"""Vorlagenblock - ein `{% block %}`, den die Elternkette nicht kennt.

DER BEFUND (3DTools, 17.08.2026)
================================
`photo_analysis_jobs.html` beginnt mit `{% block extra_styles %}` und einem
`<style>`-Block von 62 Regeln. `base.html` kennt diesen Block nicht - es heißt
dort `extra_head`. Django verwirft einen unbekannten Block auf oberster Ebene
**still**: kein Fehler, keine Warnung, die Seite antwortet mit 200.

Was das auf der Seite bedeutete, im Browser gemessen:

* `.hb-width-60px` stand in KEINEM Stylesheet -> die 180 Foto- und
  Silhouetten-Bilder der Tabelle waren **0x0 Pixel** groß, also unsichtbar.
* `.btn-actions` war kein Flex, `.no-thumb` ohne Form, `.cb-cell` ohne Breite.
* `.hb-versteckt { display:none }` fehlte - was verborgen sein sollte, stand da.

Der Fehler steckte seit dem Umbau vom 16.08. in der Datei. Er ueberlebte einen
Testlauf (HTTP 200), eine Sichtpruefung im Browser (leere Spalten sehen aus wie
„keine Vorschau vorhanden") und mehrere Sitzungen.

WARUM „AUF OBERSTER EBENE"
=========================
Ein `{% block %}` INNERHALB eines Blocks, den die Elternkette kennt, wird an
seiner Stelle gerendert - es ist eine Erweiterungsstelle für eigene Kinder und
voellig richtig. Genau daran unterscheiden sich zwei Fälle im selben Projekt:
`character_viewer.html` führt acht solche Bloecke (`viewer_menubar`,
`tab_szene_content`, ...), alle in `content` geschachtelt - die funktionieren.
Nur `extra_styles` stand auf Ebene 0 und fiel damit heraus. Ohne diese
Unterscheidung meldet die Prüfung 11 statt 1 Fundstelle, und der eine echte Fall
geht unter.
"""
import re

from django.conf import settings

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug

__all__ = ["Vorlagenblock"]

EXTENDS = re.compile(r"{%\s*extends\s+[\"']([^\"']+)[\"']")
BLOCK = re.compile(r"{%\s*block\s+([\w.]+)\s*%}")
#: `block`- und `endblock`-Marken in Reihenfolge - fuer die Schachtelungstiefe.
MARKE = re.compile(r"{%\s*(block|endblock)\b[^%]*%}")
#: So tief wird einer `extends`-Kette gefolgt, bevor abgebrochen wird.
MAX_TIEFE = 8


class Vorlagenblock(Werkzeug):
    slug = "vorlagenblock"
    titel = "Vorlagen: Block läuft ins Leere"
    zweck = ("Findet `{% block x %}` auf oberster Ebene, den die `extends`-Kette "
             "nicht kennt. Django verwirft ihn still — der Inhalt erscheint nie.")
    befund = ("3DTools: `{% block extra_styles %}` statt `extra_head` liess den "
              "ganzen Stilblock einer Seite verschwinden. Folge: 180 "
              "Vorschaubilder mit 0x0 Pixeln, unsichtbar, bei HTTP 200.")
    abhilfe = ("Blocknamen an die Elternvorlage angleichen — oder den Block dort "
               "einführen. Welche Namen es gibt, steht in der Spalte „bekannt\".")
    dauer = "unter 1 s"
    kriterium = 5

    #: Ein Block, den die Elternvorlage nicht kennt (``extra_styles`` statt
    #: ``extra_head``) - und daneben ein GESCHACHTELTER Block, der zwar auch
    #: unbekannt ist, aber an seiner Stelle gerendert wird und deshalb NICHT
    #: zaehlen darf. Ohne diese Unterscheidung meldete die Pruefung 11 statt 1.
    anlassfall = Anlassfall(
        {"eltern.html": '''<html><head>{% block extra_head %}{% endblock %}</head>
<body>{% block inhalt %}{% endblock %}</body></html>
''',
         "kind.html": '''{% extends "eltern.html" %}
{% block extra_styles %}<style>p{color:red}</style>{% endblock %}
{% block inhalt %}
  {% block eigene_stelle %}Text{% endblock %}
{% endblock %}
'''},
        mindestens=1, hoechstens=1,
        erwartet_in="extra_styles",
        warum="``{% block extra_styles %}`` statt ``extra_head`` ließ einen "
              "ganzen Stilblock verschwinden — 180 Vorschaubilder 0x0, bei "
              "HTTP 200")

    def laufen(self):
        vorlagen = self._vorlagen()
        zeilen = []
        geprueft = 0
        for pfad, name in vorlagen.items():
            text = self._text(pfad)
            eltern = EXTENDS.search(text)
            if not eltern:
                continue
            geprueft += 1
            bekannt, fehlend = self._kette(eltern.group(1), vorlagen)
            if fehlend:
                zeilen.append({"art": "Elternvorlage fehlt", "vorlage": name,
                               "block": eltern.group(1), "bekannt": ""})
                continue
            for block in self._oberste(text):
                if block not in bekannt:
                    zeilen.append({
                        "art": "Block unbekannt", "vorlage": name,
                        "block": block,
                        "bekannt": ", ".join(sorted(bekannt)[:8])})
        return Ergebnis(
            ["art", "vorlage", "block", "bekannt"], zeilen,
            zusammenfassung="%d Vorlagen mit `extends` geprüft, %d Bloecke "
                            "laufen ins Leere" % (geprueft, len(zeilen)),
            hinweis="Nur Bloecke auf OBERSTER Ebene können verworfen werden. Ein "
                    "geschachtelter Block ist eine Erweiterungsstelle und wird an "
                    "seiner Stelle gerendert — ohne diese Unterscheidung meldet "
                    "die Prüfung ein Vielfaches an Fehlalarmen.")

    # ------------------------------------------------------------------ intern
    def _vorlagen(self):
        u"""{Pfad: Anzeigename} aller Vorlagen — Projekt UND djangoBase.

        Die Elternkette endet fast immer in einer mitgelieferten Vorlage
        (`djangobase/base.html`). Wer nur im Projekt sucht, meldet „Elternvorlage
        fehlt" für jede Seite und uebersieht den echten Fall.
        """
        raus = {}
        for pfad in self.dateien(".html"):
            raus[pfad] = pfad.relative_to(self.wurzel()).as_posix()
        try:
            import djangobase
            from pathlib import Path
            eigen = Path(djangobase.__file__).resolve().parent / "templates"
            for pfad in sorted(eigen.rglob("*.html")):
                raus.setdefault(pfad, "djangobase/" + pfad.name)
        except Exception:                                       # noqa: BLE001
            pass
        return raus

    #: ``{% comment %}…{% endcomment %}`` und ``{# … #}`` — beides wird beim
    #: Rendern verworfen und enthaelt deshalb keine echten Bloecke.
    KOMMENTAR = re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}"
                           r"|\{#.*?#\}", re.S)

    @classmethod
    def _text(cls, pfad):
        u"""Der Vorlagentext OHNE Kommentare.

        EIN BLOCK-TAG IM KOMMENTAR IST KEIN BLOCK (17.08.2026): In
        ``steuer_web/.../_base_steuer.html`` erklärt der Kopfkommentar den
        Aufbau der Datei und schreibt dabei ``{% block steuer_title %}`` hin.
        Die Rohtext-Suche zaehlte das als Block auf oberster Ebene — und
        meldete ihn als „läuft ins Leere", obwohl der echte, verschachtelte
        Block einwandfrei rendert (nachgemessen: die Unterseite zeigt ihren
        Titel-Zusatz).

        Dieselbe Fehlerklasse wie „``{% … %}`` im HTML kann kein unaufgeloester
        Vorlagenrest sein": Wer den Rohtext liest, muss das wegnehmen, was beim
        Rendern gar nicht mitspielt.
        """
        try:
            roh = pfad.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return cls.KOMMENTAR.sub("", roh)

    def _finden(self, name, vorlagen):
        u"""Vorlage zu einem `extends`-Namen — über das Pfadende."""
        ziel = name.replace("\\", "/")
        for pfad in vorlagen:
            if pfad.as_posix().endswith("/" + ziel) or pfad.name == ziel:
                return pfad
        return None

    def _kette(self, name, vorlagen, tiefe=0):
        u"""(bekannte Blocknamen der Elternkette, fehlender Elternname)."""
        pfad = self._finden(name, vorlagen)
        if pfad is None:
            return set(), name
        if tiefe >= MAX_TIEFE:
            return set(), None
        text = self._text(pfad)
        eigene = set(BLOCK.findall(text))
        eltern = EXTENDS.search(text)
        if not eltern:
            return eigene, None
        oben, fehlend = self._kette(eltern.group(1), vorlagen, tiefe + 1)
        return eigene | oben, fehlend

    @staticmethod
    def _oberste(text):
        u"""Blocknamen auf Schachtelungsebene 0."""
        raus, ebene = [], 0
        for marke in MARKE.finditer(text):
            if marke.group(1) == "block":
                if ebene == 0:
                    raus.append(re.search(r"block\s+([\w.]+)",
                                          marke.group(0)).group(1))
                ebene += 1
            else:
                ebene = max(0, ebene - 1)
        return raus
