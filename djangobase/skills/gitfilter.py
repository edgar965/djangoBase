# -*- coding: utf-8 -*-
u"""Gehoert eine Datei zum Projekt? Git weiß es besser als eine Namensliste.

DER ANLASS (Edgar, 18.08.2026)
==============================
    „kannst du die skills anpassen, dass der den Code von gitignore nicht prüft?"

In shortlongx meldete ``jswaisen`` 63 verwaiste JS-Dateien. Ein Drittel davon
war gar kein Projektcode:

    19  shortlongxWeb/tests_app/js/_web/…   Arbeitsordner des JS-Testlaeufers,
                                            bei jedem Lauf neu gespiegelt
     2  werkzeug/.chrome/WasmTtsEngine/…    heruntergeladenes Chrome-Profil

Beides steht in der ``.gitignore`` des Projekts. „Verwaist" ist dort ohne
Aussage: Eine Spiegelkopie lädt naturgemaess niemand, und fremder Code geht
das Projekt nichts an.

WARUM GIT FRAGEN UND NICHT DIE DATEI LESEN
==========================================
Die ``.gitignore``-Syntax hat Muster, Negationen (``!``), Verzeichnis-Suffixe,
``**`` und mehrere Dateien in verschachtelten Ordnern. Ein selbstgebauter Parser
trifft davon vielleicht 90 % - und die fehlenden 10 % erzeugen genau die Sorte
stiller Abweichung, die dieses Werkzeugkasten-Projekt sonst aufspuert.

Deshalb wird git selbst gefragt::

    git ls-files --cached --others --exclude-standard

Das listet alle Dateien, die git kennt ODER die nicht ignoriert werden - also
exakt die Menge „gehört zum Projekt". Ein Aufruf je Wurzel, gemerkt für die
Laufzeit des Prozesses; 44 Werkzeuge teilen sich also EINE Abfrage.

DIE LISTE WIRD EINMAL GEHOLT - UND DAS HAT EINE GRENZE
======================================================
44 Werkzeuge teilen sich eine Abfrage; wer während des Laufs eine Datei ANLEGT,
steht nicht darin und gilt als ignoriert. Für die Werkzeuge selbst ist das
richtig (sie lesen nur), für erzeugte Prüfdateien wäre es falsch. Der
``anlassfall-check`` ist davon nicht betroffen - er legt seine Fälle unter
``_anlassfall`` ab, das ohnehin in ``AUSGESCHLOSSEN`` steht, und meldet nach der
Umstellung unverändert „34 von 43 geprüft, alle bestanden". Wer ein Werkzeug
baut, das frisch erzeugte Dateien prüfen soll, umgeht diesen Filter bewusst.

WAS PASSIERT, WENN ES KEIN GIT GIBT
===================================
Kein Repo, kein ``git`` im Pfad, ein Fehler beim Aufruf - dann ist der Filter
UNTAETIG und alles wird geprüft wie vorher. Ein Werkzeugkasten, der ohne git
plötzlich die Haelfte des Projekts uebersieht, wäre schlimmer als einer, der zu
viel meldet: Der Warnhinweis im Kopf von ``frontendquellen.py`` gilt auch hier -
„Ein Massstab, der zu viel ausschliesst, macht aus einem sauberen Projekt ein
kaputtes."
"""
import subprocess
from pathlib import Path

__all__ = ["GitFilter"]


class GitFilter:
    """Welche Dateien git kennt - alles andere ist nicht der Code des Projekts."""

    #: Wurzel -> Menge der erlaubten Pfade (als aufgeloeste Zeichenketten).
    #: ``None`` heisst „git hat nicht geantwortet", der Filter bleibt dann untaetig.
    _gemerkt = {}

    #: Sekunden, die der git-Aufruf hoechstens dauern darf. Ein grosses Repo
    #: braucht Bruchteile davon; laeuft es laenger, stimmt etwas nicht, und der
    #: Werkzeugkasten soll nicht daran haengen bleiben.
    ZEITGRENZE_S = 30

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel).resolve()
        self.erlaubte = self._laden(self.wurzel)

    @classmethod
    def _laden(cls, wurzel):
        schluessel = str(wurzel)
        if schluessel in cls._gemerkt:
            return cls._gemerkt[schluessel]
        aus = None
        if (wurzel / ".git").exists():
            try:
                ergebnis = subprocess.run(
                    ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                    cwd=str(wurzel), capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=cls.ZEITGRENZE_S)
                if ergebnis.returncode == 0:
                    aus = {str((wurzel / zeile).resolve())
                           for zeile in (ergebnis.stdout or "").splitlines() if zeile}
            except (OSError, ValueError, subprocess.SubprocessError):
                aus = None
        cls._gemerkt[schluessel] = aus
        return aus

    @property
    def aktiv(self):
        """Hat git geantwortet? Sonst wird nichts gefiltert."""
        return self.erlaubte is not None

    def erlaubt(self, pfad):
        u"""Gehoert ``pfad`` zum Projekt?

        Ohne git-Antwort IMMER ``True`` - siehe Modulkopf. Eine Datei außerhalb
        der Wurzel wird ebenfalls durchgelassen: Sie kann git gar nicht kennen,
        und das ist die Entscheidung des Aufrufers, nicht dieses Filters.
        """
        if not self.aktiv:
            return True
        try:
            voll = Path(pfad).resolve()
        except OSError:
            return True
        if str(voll) in self.erlaubte:
            return True
        try:
            voll.relative_to(self.wurzel)
        except ValueError:
            return True                      # ausserhalb des Repos
        return False

    def bericht(self):
        """Eine Zeile für die Zusammenfassung eines Werkzeugs."""
        if not self.aktiv:
            return "ohne git-Filter (kein Repo oder git nicht erreichbar)"
        return "%d Dateien in git" % len(self.erlaubte)
