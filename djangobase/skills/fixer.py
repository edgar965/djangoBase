# -*- coding: utf-8 -*-
u"""Fixer - Werkzeuge, die einen Befund nicht nur finden, sondern BEHEBEN.

DER UNTERSCHIED ZU EINEM PRUEFWERKZEUG (16.08.2026)
===================================================
Ein Pruefwerkzeug liest. Ein Fixer SCHREIBT - und das ändert alles:

    * Er braucht eine VORSCHAU. Niemand löst eine Codeaenderung aus, ohne zu
      sehen, welche Dateien sie trifft.
    * Er braucht eine SICHERUNG. Jede geaenderte Datei liegt vorher im
      Sicherungsordner, mit Zeitstempel.
    * Er braucht ein NETZ. Nach dem Schreiben prüfen: kompiliert die Datei
      noch, ist nichts verloren gegangen, zeigt kein Aufruf ins Leere. Fällt
      eine Prüfung, wird zurueckgespielt - nicht gemeldet und liegengelassen.

WARUM DAS NETZ NICHT VERHANDELBAR IST
=====================================
Am 16.08.2026 sind bei genau diesen Umbauten sechs verschiedene Fehler
passiert, die alle erst zur LAUFZEIT auffallen: eine Funktion, die noch frei
gerufen wird; ein Konstruktor, der Werte verlangt, die erst seine Methoden
erzeugen; ein Sicherungsordner, der selbst mitgeprueft wurde und die Befundzahl
von 198 auf 228 trieb. Ein Fixer ohne Netz macht aus einem Befund zwei.

WAS EIN FIXER NICHT TUT
=======================
Er entscheidet nicht, OB umgebaut werden soll. Diese Frage - ist das Dictionary
ein Anzeigeformat? ist das Argument ein Feld oder ein Zwischenergebnis? - stellt
das zugehoerige Pruefwerkzeug, und beantworten muss sie ein Mensch. Der Fixer
führt aus, was schon entschieden ist.
"""
import shutil
import time
from pathlib import Path

from django.conf import settings

from .pfadteile import Pfadteile

__all__ = ["Fixer", "Vorschau", "Aenderung"]


class Aenderung:
    """Eine einzelne Datei, die ein Fixer anfassen wuerde."""

    def __init__(self, pfad, was, neuer_text=None, warnungen=(), begleiter=None):
        self.pfad = Path(pfad)
        #: Was mit dieser Datei geschieht, in einem Satz.
        self.was = was
        #: Der vollstaendige neue Inhalt - oder ``None``, wenn nur berichtet wird.
        self.neuer_text = neuer_text
        #: Gruende, warum der Eingriff hier NICHT laufen sollte.
        self.warnungen = list(warnungen)
        #: ``(pfad, text)`` einer ZWEITEN Datei, die mitentsteht - beim Teilen ist
        #: das die herausgeloeste Haelfte. Sie gehoert zur selben Aenderung: faellt
        #: das Netz, muessen BEIDE zurueck, sonst bleibt eine Waise liegen.
        self.begleiter = begleiter

    @property
    def machbar(self):
        return self.neuer_text is not None and not self.warnungen

    @property
    def name(self):
        try:
            return str(self.pfad.relative_to(Path(settings.BASE_DIR).parent))
        except (ValueError, AttributeError):
            return self.pfad.name

    def als_dict(self):
        return {"datei": self.name, "was": self.was,
                "machbar": "ja" if self.machbar else "nein",
                "grund": "; ".join(self.warnungen) if self.warnungen else ""}


class Vorschau:
    """Alles, was ein Fixer tun WUERDE - vor dem ersten Schreibzugriff."""

    def __init__(self, aenderungen, hinweis=""):
        self.aenderungen = list(aenderungen)
        self.hinweis = hinweis

    @property
    def machbar(self):
        return [a for a in self.aenderungen if a.machbar]

    @property
    def blockiert(self):
        return [a for a in self.aenderungen if not a.machbar]

    def als_dict(self):
        return {
            "spalten": ["datei", "was", "machbar", "grund"],
            "zeilen": [a.als_dict() for a in self.aenderungen],
            "anzahl": len(self.aenderungen),
            "zusammenfassung": "%d Dateien betroffen, %d davon jetzt machbar"
                               % (len(self.aenderungen), len(self.machbar)),
            "hinweis": self.hinweis,
        }


class Fixer:
    """Basis für alles, was einen Befund behebt statt ihn nur zu melden."""

    #: Kennung in der URL und in der Tabelle.
    slug = ""
    titel = ""
    #: Was der Fixer tut - eine Zeile, im Imperativ.
    tut = ""
    #: Warum das der richtige Umbau ist, mit dem Fall dahinter.
    warum = ""
    #: Woran er scheitert und was dann zu tun ist.
    grenzen = ""
    #: Nummer des Auftrags-Kriteriums.
    kriterium = 0
    dauer = "wenige Sekunden"

    #: WO EIN FIXER NIE HINSCHREIBEN DARF (17.08.2026)
    #: ================================================
    #: ``FixDictKlasse`` fuehrte eine EIGENE Ausschlussliste - ohne ``vendor``,
    #: ohne ``.venv``, ohne ``site-packages``. Sie kannte ``venv``, der Ordner
    #: hiess aber ``.venv``. Folge: Der Fixer baute in
    #: ``vendor/ace-step-1.5/.venv/Lib/site-packages/`` um - in pandas, sympy,
    #: diffusers, modelscope. 40 fremde Dateien geaendert, 39 neue daneben
    #: gelegt. Das Netz fing nur die fuenf, die danach nicht mehr
    #: kompilierten; die anderen 74 sahen gesund aus.
    #:
    #: Deshalb steht die Grenze JETZT HIER, in der Basis, und wird aus
    #: derselben Liste gespeist wie die der Pruefwerkzeuge. Ein Fixer mit
    #: eigener Liste ist eine zweite Quelle, und die laeuft auseinander.
    ZUSATZ_RAUS = frozenset({"vendor", ".venv", "site-packages", "dist-info",
                             "diktator", "third_parts", "build"})

    @classmethod
    def raus(cls):
        """Ordnernamen, die kein Fixer anfassen darf."""
        from .werkzeug import AUSGESCHLOSSEN
        # Beide Schluessel, siehe Werkzeug.ausgeschlossen(): `skills2` ist der
        # alte Paketname und steht noch in den Einstellungen der Projekte. Ein
        # Fixer, der ihn nicht liest, SCHREIBT in Fremdcode.
        cfg = getattr(settings, "DJANGOBASE", {}) or {}
        eigen = (list(cfg.get("skills_ignorieren") or [])
                 + list(cfg.get("skills2_ignorieren") or []))
        return (set(AUSGESCHLOSSEN) | set(cls.ZUSATZ_RAUS)
                | {str(x) for x in eigen})

    @classmethod
    def erlaubt(cls, pfad, wurzel=None):
        """Darf in diese Datei geschrieben werden?

        GEGEN DIE TEILE UNTERHALB DER WURZEL (Befund CodeRabbit, 31.08.2026):
        ``pfade()`` sucht seit dem Umbau mit ``Pfadteile.trifft`` relativ zur
        Wurzel, dieser Schreibschutz pruefte weiter den ABSOLUTEN Pfad. Liegt
        das Projekt unterhalb eines Ordners namens ``vendor``, liefert die
        Suche also Dateien, die der Schutz danach ALLE als fremden Code
        ablehnt — die Vorschau zeigt Aenderungen, das Anwenden tut nichts.
        Zwei Fassungen derselben Regel, genau wie in ``pfadteile.py``
        beschrieben.
        """
        return not (set(Pfadteile.unter(pfad, wurzel)) & cls.raus())

    def wurzel(self):
        """Die REPO-Wurzel, nicht nur der Django-Teil - wie bei ``Werkzeug``.

        MIT ``BASE_DIR`` LANDET DIE SICHERUNG AM FALSCHEN ORT (16.08.2026):
        ``shortlongxWeb/werkzeug/sicherung/`` statt ``werkzeug/sicherung/``. Der
        Ausnahme-Filter des Pruefwerks greift dort nicht, jede gesicherte Datei
        zaehlte als Duplikat ihres Originals - K6 sprang von 10 auf 214, ohne
        dass sich am Code etwas verschlechtert hätte."""
        basis = Path(getattr(settings, "BASE_DIR", "."))
        eltern = basis.parent
        if (eltern / ".git").exists() and not (basis / ".git").exists():
            return eltern
        return basis

    def gitfilter(self):
        """Was in der ``.gitignore`` steht, ist nicht der Code des Projekts."""
        from .gitfilter import GitFilter
        if not hasattr(self, "_gitfilter"):
            self._gitfilter = GitFilter(self.wurzel())
        return self._gitfilter

    def pfade(self, muster="*.py"):
        u"""Die Dateien, die dieser Fixer ANSEHEN darf - wie ``Werkzeug.pfade``.

        NUR ZUM SUCHEN, NICHT ALS SCHREIBSCHUTZ (18.08.2026): ``erlaubt()``
        bleibt unverändert. Der Filter kennt nur Dateien, die es beim ersten
        Aufruf schon gab — eine frisch angelegte Sicherungskopie steht nicht
        darin. Als Schreibschutz eingesetzt, würde er dem Fixer verbieten, sein
        eigenes Original zu sichern (``werkzeug/sicherung/`` ist in mehreren
        Projekten ohnehin ignoriert).
        """
        raus = self.raus()
        git = self.gitfilter()
        wurzel = self.wurzel()
        # Gegen die Teile UNTERHALB der Wurzel — siehe `pfadteile.py`.
        # Gegen den absoluten Pfad geprueft, faellt jede Datei heraus,
        # deren WEG zur Wurzel zufaellig einen dieser Namen traegt.
        return [p for p in sorted(wurzel.rglob(muster))
                if not Pfadteile.trifft(p, wurzel, raus) and git.erlaubt(p)]

    @property
    def sicherung(self):
        """Wohin die Originale gehen - IM Projekt, nie in System-Temp."""
        return self.wurzel() / "werkzeug" / "sicherung" / "fixer"

    # ---- von den Unterklassen zu fuellen ------------------------------------
    def vorschau(self):
        """Welche Dateien wie geändert wuerden - ohne zu schreiben."""
        raise NotImplementedError

    def pruefen(self, aenderung):
        """Nach dem Schreiben: Liste von Fehlern (leer = in Ordnung)."""
        return []

    # ---- der gemeinsame Ablauf ---------------------------------------------
    def anwenden(self, nur=None):
        """Die machbaren Änderungen schreiben - mit Sicherung und Netz.

        ``nur``: Liste von Dateinamen; leer heißt alle machbaren. Fällt das
        Netz bei einer Datei, wird GENAU DIESE zurueckgespielt - die anderen
        bleiben. Ein halb angewandter Umbau ist unangenehm, ein stillschweigend
        kaputter schlimmer.

        HAT EINE AENDERUNG EINEN BEGLEITER (die herausgeloeste Haelfte beim
        Teilen), wird er hier mitgeschrieben und beim Zurueckspielen wieder
        ENTFERNT. Frueher stand dieser Ablauf ein zweites Mal in ``FixJsSchnitt``
        - und dort loeschte er die neue Datei nicht, wenn das Netz fiel: ein
        importiertes Modul, das es nicht mehr gab (16.08.2026)."""
        stempel = time.strftime("%Y%m%d_%H%M%S")
        ziel = self.sicherung / stempel
        aus = {"geschrieben": [], "zurueckgespielt": [], "uebersprungen": []}
        for a in self.vorschau().aenderungen:
            if nur and a.name not in nur:
                continue
            # ZWEITER RIEGEL, unmittelbar vor dem Schreiben. Der erste ist die
            # Ausschlussliste des einzelnen Fixers - und genau die hat am
            # 17.08.2026 versagt. Ein Riegel an der Stelle, an der wirklich
            # geschrieben wird, gilt fuer JEDEN Fixer, auch fuer den naechsten,
            # den jemand ohne Ausschlussliste baut.
            if not self.erlaubt(a.pfad, self.wurzel()):
                aus["uebersprungen"].append(
                    {"datei": a.name,
                     "grund": "fremder Code — kein Fixer schreibt dorthin"})
                continue
            if not a.machbar:
                aus["uebersprungen"].append({"datei": a.name,
                                             "grund": "; ".join(a.warnungen)})
                continue
            ziel.mkdir(parents=True, exist_ok=True)
            kopie = ziel / a.pfad.name
            shutil.copy2(a.pfad, kopie)
            a.pfad.write_text(a.neuer_text, encoding="utf-8")
            zusatz = ""
            if a.begleiter:
                begleitpfad, begleittext = a.begleiter
                Path(begleitpfad).write_text(begleittext, encoding="utf-8")
                zusatz = " (+ %s)" % Path(begleitpfad).name
            fehler = self.pruefen(a)
            if fehler:
                shutil.copy2(kopie, a.pfad)
                if a.begleiter:
                    Path(a.begleiter[0]).unlink(missing_ok=True)
                aus["zurueckgespielt"].append({"datei": a.name,
                                               "grund": "; ".join(fehler)})
            else:
                aus["geschrieben"].append({"datei": a.name + zusatz,
                                           "sicherung": str(kopie)})
        # Dictionary gewollt: geht unveraendert als JSON an die Seite.
        return aus

    #: Kennung des Werkzeugs, dessen Befund dieser Fixer behebt.
    #: Leer = keines (dann steht auf der Karte nichts).
    behebt = ''

    def nummer(self):
        u"""Die NUMMER der zugehoerigen Prüfung in der Tabelle.

            „passe noch an die Fix Werkzeuge, die erwaehnen kriterien die es
             nicht gibt. sie sollen sich auf die Nummer der testcases
             beziehen"

        Die Karten zeigten `Kr. 11`, `Kr. 16`, `Kr. 3`. Diese Nummern gibt
        es — aber NICHT auf dieser Seite: Die Tabelle darueber ist nach
        Raengen (1, 2, 3 …) und Bereichen geordnet, nicht nach Kriterien.
        Wer `Kr. 11` las, suchte eine 11, die nirgends stand.

        Jetzt steht die Nummer da, unter der die Prüfung wirklich in der
        Tabelle zu finden ist — und die sich mitverschiebt, wenn jemand den
        Rang ändert.
        """
        if not self.behebt:
            return None
        from .rangliste import rangliste
        from . import werkzeuge
        for abschnitt in rangliste().abschnitte(list(werkzeuge())):
            for rang, w in abschnitt["eintraege"]:
                if w.slug == self.behebt:
                    return {"nr": rang, "slug": w.slug, "titel": w.titel}
        return None

    def als_dict(self):
        return {"slug": self.slug, "titel": self.titel, "tut": self.tut,
                "warum": self.warum, "grenzen": self.grenzen,
                "kriterium": self.kriterium, "dauer": self.dauer,
                "behebt": self.behebt, "pruefung": self.nummer()}
