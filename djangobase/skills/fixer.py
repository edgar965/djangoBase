# -*- coding: utf-8 -*-
u"""Fixer - Werkzeuge, die einen Befund nicht nur finden, sondern BEHEBEN.

DER UNTERSCHIED ZU EINEM PRUEFWERKZEUG (16.08.2026)
===================================================
Ein Pruefwerkzeug liest. Ein Fixer SCHREIBT - und das aendert alles:

    * Er braucht eine VORSCHAU. Niemand loest eine Codeaenderung aus, ohne zu
      sehen, welche Dateien sie trifft.
    * Er braucht eine SICHERUNG. Jede geaenderte Datei liegt vorher im
      Sicherungsordner, mit Zeitstempel.
    * Er braucht ein NETZ. Nach dem Schreiben pruefen: kompiliert die Datei
      noch, ist nichts verloren gegangen, zeigt kein Aufruf ins Leere. Faellt
      eine Pruefung, wird zurueckgespielt - nicht gemeldet und liegengelassen.

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
fuehrt aus, was schon entschieden ist.
"""
import shutil
import time
from pathlib import Path

from django.conf import settings

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
    """Basis fuer alles, was einen Befund behebt statt ihn nur zu melden."""

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
        eigen = ((getattr(settings, "DJANGOBASE", {}) or {})
                 .get("skills2_ignorieren") or [])
        return (set(AUSGESCHLOSSEN) | set(cls.ZUSATZ_RAUS)
                | {str(x) for x in eigen})

    @classmethod
    def erlaubt(cls, pfad):
        """Darf in diese Datei geschrieben werden?"""
        return not (set(Path(pfad).parts) & cls.raus())

    def wurzel(self):
        """Die REPO-Wurzel, nicht nur der Django-Teil - wie bei ``Werkzeug2``.

        MIT ``BASE_DIR`` LANDET DIE SICHERUNG AM FALSCHEN ORT (16.08.2026):
        ``shortlongxWeb/werkzeug/sicherung/`` statt ``werkzeug/sicherung/``. Der
        Ausnahme-Filter des Pruefwerks greift dort nicht, jede gesicherte Datei
        zaehlte als Duplikat ihres Originals - K6 sprang von 10 auf 214, ohne
        dass sich am Code etwas verschlechtert haette."""
        basis = Path(getattr(settings, "BASE_DIR", "."))
        eltern = basis.parent
        if (eltern / ".git").exists() and not (basis / ".git").exists():
            return eltern
        return basis

    @property
    def sicherung(self):
        """Wohin die Originale gehen - IM Projekt, nie in System-Temp."""
        return self.wurzel() / "werkzeug" / "sicherung" / "fixer"

    # ---- von den Unterklassen zu fuellen ------------------------------------
    def vorschau(self):
        """Welche Dateien wie geaendert wuerden - ohne zu schreiben."""
        raise NotImplementedError

    def pruefen(self, aenderung):
        """Nach dem Schreiben: Liste von Fehlern (leer = in Ordnung)."""
        return []

    # ---- der gemeinsame Ablauf ---------------------------------------------
    def anwenden(self, nur=None):
        """Die machbaren Aenderungen schreiben - mit Sicherung und Netz.

        ``nur``: Liste von Dateinamen; leer heisst alle machbaren. Faellt das
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
            if not self.erlaubt(a.pfad):
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

    def als_dict(self):
        return {"slug": self.slug, "titel": self.titel, "tut": self.tut,
                "warum": self.warum, "grenzen": self.grenzen,
                "kriterium": self.kriterium, "dauer": self.dauer}
