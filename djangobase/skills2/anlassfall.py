# -*- coding: utf-8 -*-
u"""Anlassfall - der Code, an dem ein Werkzeug beweisen muss, dass es sieht.

DIE FRAGE, DIE ZWEIMAL ETWAS GEFUNDEN HAT (17.08.2026)
======================================================
    „Findet die Pruefung noch den Fall, fuer den sie gebaut wurde?"

Zweimal an einem Abend hat sie einen blinden Pruefer entlarvt:

* ``getattr-namen`` meldete NULL. Sein Massstab liess jede Zeichenkette als
  Beleg gelten - und ``orb_nacht``, sein eigener Anlassfall, steht als
  Zeichenkette in der Pruefung, die ihn dokumentiert. Enger gefasst: 2 statt 0.
* ``js-vererbung`` haette ``SignaleTab`` als Absturz gemeldet, obwohl der Name
  ausdruecklich ans Fenster gehaengt wird.

Beides waere unbemerkt geblieben. Eine Null sieht aus wie ein sauberes Projekt,
und niemand prueft nach, ob der Pruefer ueberhaupt noch etwas sehen KANN.

Deshalb traegt jedes Werkzeug seinen Anlassfall bei sich: ein paar Zeilen Code,
die es melden MUSS. ``AnlassfallCheck`` schreibt sie in ein eigenes Verzeichnis,
laesst das Werkzeug nur dort laufen und vergleicht.

WARUM DER FALL AM WERKZEUG HAENGT UND NICHT IN EINER LISTE
==========================================================
Eine zentrale Liste ist eine zweite Quelle, und die laeuft auseinander - genau
so war ``Skills1`` gebaut, lief und stand in keinem Menue. Wer ein Werkzeug
schreibt, schreibt seinen Anlassfall daneben; wer keinen angibt, taucht im
Bericht als ``ohne Anlassfall`` auf und wird nicht stillschweigend uebergangen.
"""

__all__ = ["Anlassfall"]


class Anlassfall:
    """Ein Mini-Projekt aus ein paar Dateien - plus das erwartete Urteil.

    ``dateien`` bildet relative Pfade auf ihren Inhalt ab; Unterverzeichnisse
    (``"a/b.py"``) werden angelegt. ``mindestens`` ist die Zahl der Befunde, die
    das Werkzeug hier finden MUSS - fast immer 1.

    ``erwartet_in`` ist optional: ein Text, der in irgendeiner Befundzeile
    vorkommen muss. Damit laesst sich pruefen, dass das Werkzeug die RICHTIGE
    Stelle meldet und nicht irgendeine.

    ``hoechstens`` ist die andere Haelfte und mindestens so wichtig: Viele
    Werkzeuge haben eine AUSNAHME (den Vermerk „Dictionary gewollt", „in der
    Schleife gewollt", „geteilt gewollt"). Wer sie verliert, meldet plotzlich
    doppelt so viel - und niemand merkt es, weil mehr Befunde nach mehr
    Gruendlichkeit aussehen. Steht im Anlassfall neben dem echten Fall auch der
    ausgenommene, faengt ``hoechstens=1`` genau das ab.
    """

    def __init__(self, dateien, mindestens=1, hoechstens=None, erwartet_in="",
                 warum=""):
        self.dateien = dict(dateien)
        self.mindestens = mindestens
        self.hoechstens = hoechstens
        self.erwartet_in = erwartet_in
        #: Ein Satz: welcher reale Vorfall hier nachgebaut ist.
        self.warum = warum

    @property
    def umfang(self):
        return "%d Datei(en), %d Zeilen" % (
            len(self.dateien),
            sum(t.count("\n") + 1 for t in self.dateien.values()))

    def schreiben(self, ziel):
        """Legt die Dateien unter ``ziel`` an (Pathlib-Verzeichnis)."""
        ziel.mkdir(parents=True, exist_ok=True)
        for name, inhalt in self.dateien.items():
            pfad = ziel / name
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(inhalt, encoding="utf-8")
        return ziel

    def urteil(self, zeilen):
        """``""`` wenn alles stimmt, sonst der Grund."""
        if len(zeilen) < self.mindestens:
            return ("blind: %d Befund(e) statt mindestens %d"
                    % (len(zeilen), self.mindestens))
        if self.hoechstens is not None and len(zeilen) > self.hoechstens:
            return ("zu grob: %d Befund(e) statt höchstens %d — die Ausnahme "
                    "greift nicht mehr" % (len(zeilen), self.hoechstens))
        if self.erwartet_in:
            text = " ".join(str(v) for z in zeilen for v in z.values())
            if self.erwartet_in not in text:
                return ("meldet etwas anderes: %r kommt in keiner Zeile vor"
                        % self.erwartet_in)
        return ""
