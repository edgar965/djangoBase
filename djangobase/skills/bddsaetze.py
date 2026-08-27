# -*- coding: utf-8 -*-
u"""Liest sich JEDE Prüfung des Projekts als Satz? — nicht nur achtzehn Beispiele.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „passe die BDD werkzeuge an, so dass sie den ganzen Code, alle testcases
     usw. überprüfen"

Vorausgegangen war der Einwand „es kann doch nicht sein, dass die testcases
grün sind! das sind völlig neue Anforderungen!!" — und er traf.
``testsatz.py`` wandelt eine Kennung in einen Satz, und ``test_testsatz.py``
belegt das an ACHTZEHN handverlesenen Beispielen. Sieben eingebaute
Beschädigungen machten alle achtzehn rot; die Prüfungen sind also echt.

Sie prüfen nur die falsche Sache. Die Zusage lautet nicht „der Umwandler
funktioniert", sondern:

    Ein Nicht-Programmierer liest die Prüfliste und versteht, was gelten soll.

Diese Zusage gilt für JEDE Kennung im Projekt, und dafür gab es nichts.
Erste Messung an djangoBase: 23 von 1.009 Kennungen ergeben keinen Satz.

WAS „KEIN SATZ" HEISST — UND WARUM NUR STRUKTUR, KEINE SPRACHE
==============================================================
Die Versuchung ist, auf ein Verb zu prüfen. Ohne Wörterbuch geht das nur über
Endungen, und dann wird aus ``test_der_wert_stimmt`` ein Treffer und aus
``test_die_liste_ist_leer`` keiner — beides falsch herum. Fehlalarme sind
teurer als fehlende Befunde: Sie verdecken die echten, und wer dem
Spitzenbefund folgt, benennt gesunde Prüfungen um.

Gemeldet wird deshalb nur, was OHNE Sprachwissen entscheidbar ist:

  1. ohne Aussage      Der Ergebnisteil ist EIN Wort. ``test_versionen``
                       wird zu „Versionen" — ein Gegenstand, keine Aussage.
                       Er sagt nicht, was daran stimmen soll.
  2. ohne Gegenstand   Keine Klasse davor; dann fehlt, WOVON die Rede ist.

Eine dritte Regel („Maschinenschrift im Satz") gab es im ersten Entwurf. Sie
brachte 34 Fehlalarme und war danach nicht mehr auslösbar — die Begründung
steht bei den Konstanten unten.

Was NICHT gemeldet wird, obwohl es verlockend wäre: kurze Sätze (drei Wörter
können eine vollständige Aussage sein), fehlende Umlaute (die Liste in
``testsatz.UMLAUTE`` ist bewusst endlich) und englische Fachwörter.

DER ANDERE STIL ZÄHLT MIT
=========================
Nicht jedes Projekt schreibt ``class X(TestCase)``. shortlongx registriert
seine Prüfungen über ``@pruefung(slug, frage, beschreibung)`` — dort steht der
Satz ausgeschrieben im Aufruf. Solche Prüfungen erfüllen die Zusage bereits
und werden gezählt, nicht gemeldet. Ein Werkzeug, das sie als Fund brächte,
wäre ausgerechnet in dem Projekt am lautesten, das es richtig macht.
"""
import ast

from ..testsatz import Testsatz
from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug

#: So viele Wörter braucht der ERGEBNISTEIL mindestens. Eins ist ein
#: Gegenstand („Versionen"), zwei tragen eine Aussage („Versionen laden").
MINDEST_WOERTER = 2

#: ES BLIEB KEINE DRITTE REGEL UEBRIG - UND DAS IST DAS ERGEBNIS
#: =============================================================
#: Hier stand ``BEZEICHNERREST``: Maschinenschrift im fertigen Satz. Der
#: erste Entwurf meldete verbliebenes CamelCase und allein stehende Zahlen
#: und brachte an djangoBase 49 Treffer, davon 34 falsch::
#:
#:     JsWaisenTest.test_findet_waise -> „JsWaisen: Findet waise"
#:     Kriterium18Test....            -> „Kriterium 18 ist bekannt"
#:
#: ``JsWaisen`` ist ein Eigenname (``testsatz.ZUSAMMEN`` klebt das ``Js``
#: absichtlich an), und „Kriterium 18 ist bekannt" ist ein tadelloser Satz.
#: Uebrig blieb der Unterstrich - und der KANN nicht vorkommen:
#: ``_trennen`` wirft ihn beim Zerlegen weg, ``ergebnis`` ersetzt ihn durch
#: ein Leerzeichen. Aufgefallen ist es erst, als die Gegenprobe
#: ``A_B_Test.test_der_wert_stimmt`` nichts meldete.
#:
#: Eine Regel, die nicht ausloesen kann, ist schlimmer als keine: Sie
#: behauptet eine Deckung, die es nicht gibt. Also weg damit. Es bleiben
#: zwei Regeln, und beide loesen nachweislich aus.


class BddSaetze(Werkzeug):

    slug = "bdd-saetze"
    kriterium = 19
    titel = u"Liest sich jede Prüfung als Satz?"
    zweck = (u"Wandelt JEDE Test-Kennung des Projekts über testsatz.Testsatz "
             u"in einen Satz und meldet die, die keiner werden — ohne "
             u"Aussage, ohne Gegenstand oder mit Bezeichner-Resten darin.")
    befund = (u"djangoBase, erster Lauf: 23 von 1.009 Kennungen. Darunter "
              u"HilfeViewsTest.test_versionen, gelesen als „Hilfe Views: "
              u"Versionen“ — ein Gegenstand, keine Aussage. Was soll "
              u"an den Versionen stimmen? Der Name sagt es nicht, und beim "
              u"roten Balken ist genau das die Frage.")
    abhilfe = (u"Die Methode nach dem ERGEBNIS benennen: test_versionen wird "
               u"zu test_die_versionsliste_kommt_aus_github. Der Satz steht "
               u"dann, wo er hingehört — im Namen, nicht in einer zweiten "
               u"Datei daneben, die beim nächsten Umbau ausschert.")
    dauer = u"1–3 s"

    anlassfall = Anlassfall(
        {'test_beispiel.py': (
            'class HilfeViewsTest:\n'
            '    def test_versionen(self):\n'
            '        pass\n'
            '\n'
            '    def test_die_liste_kommt_aus_github(self):\n'
            '        pass\n'
        )},
        mindestens=1, hoechstens=1,
        warum=(u"HilfeViewsTest.test_versionen aus djangoBase - „Hilfe Views: "
               u"Versionen“ nennt einen Gegenstand, keine Aussage. Die "
               u"zweite Methode daneben ist in Ordnung und darf NICHT "
               u"mitgemeldet werden."))

    # ── Suchen ──────────────────────────────────────────────────────────
    def kennungen(self):
        u"""``[(datei, zeile, Klasse, Methode)]`` aller unittest-Prüfungen."""
        raus = []
        for d in self.dateien():
            if not d.pfad.name.startswith("test_") or d.baum is None:
                continue
            for klasse in [k for k in ast.walk(d.baum)
                           if isinstance(k, ast.ClassDef)]:
                for m in klasse.body:
                    if (isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and m.name.startswith("test_")):
                        raus.append((d.name, m.lineno, klasse.name, m.name))
        return raus

    def dekorierte(self):
        u"""Prüfungen im ``@pruefung(...)``-Stil — nur gezählt, nie gemeldet.

        Ihr Satz steht ausgeschrieben im Aufruf. Gezählt werden sie trotzdem,
        damit die Zusammenfassung nicht behauptet, das Projekt habe nur eine
        Handvoll Prüfungen.
        """
        zahl = 0
        for d in self.dateien():
            if d.baum is None or "pruefung" not in d.text:
                continue
            for knoten in ast.walk(d.baum):
                if not isinstance(knoten, (ast.FunctionDef,
                                           ast.AsyncFunctionDef)):
                    continue
                for schmuck in knoten.decorator_list:
                    ziel = (schmuck.func if isinstance(schmuck, ast.Call)
                            else schmuck)
                    name = (getattr(ziel, "id", None)
                            or getattr(ziel, "attr", None))
                    if name == "pruefung":
                        zahl += 1
        return zahl

    # ── Bewerten ────────────────────────────────────────────────────────
    @staticmethod
    def maengel(klasse, methode):
        u"""Was diesem Namen zum Satz fehlt — leere Liste, wenn nichts."""
        t = Testsatz("%s.%s" % (klasse, methode))
        raus = []
        if not t.gegenstand():
            raus.append(u"ohne Gegenstand")
        if len(t.ergebnis().split()) < MINDEST_WOERTER:
            raus.append(u"ohne Aussage")
        return raus

    def laufen(self):
        alle = self.kennungen()
        zeilen = []
        for datei, zeile, klasse, methode in alle:
            fehlt = self.maengel(klasse, methode)
            if not fehlt:
                continue
            kennung = "%s.%s" % (klasse, methode)
            zeilen.append({"datei": datei, "zeile": zeile,
                           "kennung": kennung,
                           "satz": Testsatz(kennung).satz(),
                           "fehlt": ", ".join(fehlt)})
        zeilen.sort(key=lambda z: (z["datei"], z["zeile"]))
        dek = self.dekorierte()
        anteil = 100.0 * len(zeilen) / max(1, len(alle))
        return Ergebnis(
            spalten=[("kennung", u"Kennung"), ("satz", u"wird gelesen als"),
                     ("fehlt", u"was fehlt"), ("datei", u"Datei"),
                     ("zeile", u"Zeile")],
            zeilen=zeilen,
            zusammenfassung=(
                u"%d von %d Kennungen ergeben keinen Satz (%.1f %%)%s"
                % (len(zeilen), len(alle), anteil,
                   (u"; dazu %d Prüfungen im @pruefung-Stil, deren Satz im "
                    u"Aufruf steht" % dek) if dek else u"")),
            hinweis=(u"Gemeldet wird nur, was ohne Sprachwissen entscheidbar "
                     u"ist: ein Ergebnisteil aus einem Wort und ein "
                     u"fehlender Gegenstand. Auf ein Verb zu "
                     u"prüfen bräuchte ein Wörterbuch — und Fehlalarme sind "
                     u"hier teurer als fehlende Befunde."))
