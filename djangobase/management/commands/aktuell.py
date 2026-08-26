# -*- coding: utf-8 -*-
"""`manage.py aktuell` — einen Eintrag in Hilfe -> Aktuell schreiben.

WARUM EIN VERWALTUNGSBEFEHL und kein HTTP-Endpunkt (13.08.2026): Die
Claude-CLI arbeitet im Projektverzeichnis, nicht im Browser. Ein
Verwaltungsbefehl braucht kein Token, keine Anmeldung und keinen laufenden
Server — und es entsteht kein offener Schreib-Endpunkt, den auch eine fremde
Webseite bedienen koennte.

    manage.py aktuell --titel "SafePath: Doppelpunkt-Loch geschlossen" --art fix
    manage.py aktuell --titel "Testlauf" --art messung --text "56 Tests gruen"
    manage.py test core 2>&1 | manage.py aktuell --titel "Testlauf" --art messung
    manage.py aktuell --leeren

Der Text kommt von ``--text`` oder, wenn das fehlt und etwas anliegt, von
stdin. Damit laesst sich die Ausgabe eines Laufs direkt hineinleiten.

SHELL-FALLE (13.08.2026 selbst hineingetreten): In ``--text "..."`` wertet die
Shell Backticks und ``$`` aus. Der Satz ``Behoben mit `or`:`` wurde zu einem
Versuch, ein Programm namens ``or`` zu starten — im Eintrag fehlte danach ein
Wort, und die Shell meldete "command not found". Wer Code im Text hat, nimmt
einfache Anfuehrungszeichen oder besser stdin:

    manage.py aktuell --titel "Fix" --text 'Behoben mit `or`: a or b'
    printf '%s' "$TEXT" | manage.py aktuell --titel "Fix"
"""
import sys

from django.core.management.base import BaseCommand, CommandError

from ...aktuell import ARTEN, feed


class Command(BaseCommand):
    help = "Einen Eintrag in das rollierende Fenster (Hilfe -> Aktuell) schreiben."

    def add_arguments(self, p):
        p.add_argument("--titel", default="", help="Kopfzeile des Eintrags")
        p.add_argument("--text", default=None,
                       help="Inhalt (fehlt er, wird stdin gelesen)")
        p.add_argument("--art", default="notiz",
                       help="notiz | befund | fix | messung | offen | frage")
        p.add_argument("--quelle", default="claude-cli",
                       help="Wer hat es geschrieben (Vorgabe: claude-cli)")
        p.add_argument("--leeren", action="store_true",
                       help="Das Fenster leeren (fragt nicht nach)")
        p.add_argument("--zeigen", type=int, default=0,
                       help="Die letzten N Einträge ausgeben statt zu schreiben")

    def handle(self, *args, **o):
        f = feed()

        if o["leeren"]:
            f.leeren()
            self.stdout.write(self.style.SUCCESS("Fenster geleert: %s" % f.pfad))
            return

        if o["zeigen"]:
            for e in f.lesen(limit=o["zeigen"]):
                self.stdout.write("%s  [%s]  %s" % (e.get("zeit"), e.get("art"), e.get("titel")))
            return

        if not o["titel"]:
            raise CommandError("--titel fehlt (oder --zeigen / --leeren benutzen)")

        text = o["text"]
        if text is None:
            # Nur lesen, wenn wirklich etwas anliegt: Ohne diese Pruefung
            # blockiert der Befehl im Terminal auf eine Eingabe, die nie kommt.
            text = "" if sys.stdin.isatty() else sys.stdin.read()

        art = o["art"].strip().lower()
        if art not in ARTEN:
            self.stdout.write(self.style.WARNING(
                "Unbekannte Art %r — wird ungefaerbt angezeigt (bekannt: %s)"
                % (art, ", ".join(ARTEN))))

        e = f.anhaengen(o["titel"], text=text, art=art, quelle=o["quelle"])
        self.stdout.write(self.style.SUCCESS(
            "%s  [%s]  %s  (%d Zeichen Text) -> %s"
            % (e["zeit"], e["art"], e["titel"], len(e["text"]), f.pfad)))
