# -*- coding: utf-8 -*-
u"""Testziele - was ausgefuehrt werden DARF, an genau einer Stelle.

Die Tests-Seite startet Laeufe auf Zuruf des Browsers. Damit ist die Frage „was
darf in die Kommandozeile?" eine Sicherheitsfrage, und sie hatte bisher zwei
Antworten: eine in ``TestsView._lauf``/``_lauf_auswahl``, eine im Streaming-Lauf
des Projekts assistant. Zwei Prüfungen für dieselbe Sache laufen auseinander —
also steht sie jetzt hier.

DIE REGEL
=========
Erlaubt ist nur, was die Seite selbst kennt:

* eine **entdeckte Test-ID** (aus der Discovery),
* der **Slug eines konfigurierten Befehls** (``DJANGOBASE["test_befehle"]``)
  bzw. eines daraus abgeleiteten Sammelbefehls — dessen Ziele werden eingesetzt,
* ein **Karten-Label** (``Karten.label``), also das gemeinsame Modulpraefix
  einer angezeigten Liste.

Alles andere wird verworfen und GEZAEHLT: Der Name des Laufs sagt „(1 verworfen)",
statt so zu tun, als sei nichts gewesen.

Zusaetzlich die Form: Nur Buchstaben, Ziffern, Punkt, Unterstrich, Bindestrich.
Ein Eintrag mit Leerzeichen oder einem fuehrenden ``-`` waere ein zusaetzliches
Argument fuer ``manage.py`` — auch wenn ``subprocess`` eine Liste bekommt und
keine Shell im Spiel ist.
"""
import re

__all__ = ["Testziele"]


class Testziele:
    """Prüft angeforderte Kennungen und baut daraus Testlabels."""

    FORM = re.compile(r"^[\w.\-]+$")
    #: Laenge einer Kennung - alles darueber ist keine Test-ID mehr.
    MAXLAENGE = 300

    def __init__(self, bekannte_ids=(), befehle=(), sammelbefehle=(), labels=()):
        self.bekannte = set(bekannte_ids or ())
        self.labels = set(labels or ())
        self.nach_slug = {}
        for b in list(befehle or []) + list(sammelbefehle or []):
            slug = b.get("slug")
            if slug:
                self.nach_slug[slug] = b

    def pruefen(self, kennungen):
        u"""``(ziele, verworfen)`` - Reihenfolge erhalten, Doppelte entfernt."""
        ziele, verworfen = [], 0
        for kennung in (kennungen or []):
            kennung = str(kennung)[:self.MAXLAENGE]
            if not self.FORM.match(kennung):
                verworfen += 1
                continue
            if kennung in self.bekannte or kennung in self.labels:
                ziele.append(kennung)
            elif kennung in self.nach_slug:
                # Ein Befehl kann mehrere Ziele tragen („alle Unit-Tests").
                ziele.extend((self.nach_slug[kennung].get("ziel") or "").split())
            else:
                verworfen += 1
        # Zwei Haken koennen dasselbe Ziel meinen (eine Suite und ein Fall daraus).
        return list(dict.fromkeys(z for z in ziele if z)), verworfen

    def ganzes_projekt(self, kennungen):
        u"""Ist ein Sammelbefehl OHNE Ziel dabei? Dann ist alles gemeint.

        „Alles ausführen" traegt bewusst kein Label: ``manage.py test`` ohne Ziel
        faehrt das ganze Projekt. Die erste Fassung hat genau daraus „Keine
        gültige Auswahl — 0 Einträge verworfen" gemacht (gemessen 18.08.2026,
        der Knopf tat schlicht nichts): Der Slug war bekannt, sein ``ziel`` leer,
        also blieb die Liste leer — und Leere galt als Fehler.
        """
        for kennung in (kennungen or []):
            befehl = self.nach_slug.get(str(kennung)[:self.MAXLAENGE])
            if befehl is not None and not str(befehl.get("ziel") or "").strip():
                return True
        return False

    def befehl(self, kennungen, python, extra=()):
        u"""``(cmd, ziele, verworfen)`` - EIN ``manage.py test`` fuer alles.

        Ein Lauf statt einer Kette: Die Testdatenbank wird EINMAL aufgebaut. Bei
        zwanzig Haken waeren das sonst zwanzig Aufbauten fuer Sekunden Testzeit.
        Ohne gueltiges Ziel gibt es KEIN Kommando (``None``) — lieber nichts
        fahren als versehentlich das ganze Projekt.
        """
        ziele, verworfen = self.pruefen(kennungen)
        if not ziele and self.ganzes_projekt(kennungen):
            # Ohne Label heisst: das ganze Projekt.
            return ([str(python), "manage.py", "test", "--noinput", "-v", "2"]
                    + [str(x) for x in extra], [], verworfen)
        if not ziele:
            return None, [], verworfen
        cmd = [str(python), "manage.py", "test"] + ziele + ["--noinput", "-v", "2"]
        if any(".longrunner" in z or z.endswith("longrunner") for z in ziele):
            # Sonst filtert der Standard-Laeufer sie heraus, und die Liste
            # laeuft „erfolgreich" durch, ohne einen Test gefahren zu haben.
            cmd.append("--tag=longrunner")
        cmd.extend(str(x) for x in extra)
        return cmd, ziele, verworfen

    @staticmethod
    def name(ziele, verworfen):
        u"""Der Name, unter dem der Lauf in der Historie und im Ergebnis steht."""
        if not ziele:
            return "Alles (ganzes Projekt)"
        name = "Auswahl: %d Ziel%s" % (len(ziele), "" if len(ziele) == 1 else "e")
        if verworfen:
            name += " (%d verworfen)" % verworfen
        return name
