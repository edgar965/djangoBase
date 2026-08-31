# -*- coding: utf-8 -*-
u"""WerkzeugPartner — ein lokales Pruefwerkzeug als Gegenueber statt eines Modells.

WOZU (31.08.2026)
-----------------
Die Review-Seite kannte bis hierher genau eine Sorte Gegenueber: ein Modell,
das auf einen Chat-Endpunkt antwortet. Ein Pruefwerkzeug wie die CodeRabbit-CLI
passt da nicht hinein — es fuehrt kein Gespraech, es liest den Git-Stand des
Projekts und gibt Befunde aus.

Diese Klasse macht daraus einen Partner mit DERSELBEN Schnittstelle
(``fragen``, ``verlauf``, ``verbrauch``, ``modell``, ``name``). ``ReviewFaden``,
``ReviewLauf`` und die Seite muessen deshalb nicht wissen, was hinten dranhaengt.

DER UNTERSCHIED, DER NICHT VERSCHWIEGEN WERDEN DARF
---------------------------------------------------
Ein Modell bekommt das Codepaket der gewaehlten BEREICHE geschickt. Dieses
Werkzeug bekommt gar nichts geschickt: Es liest selbst, und zwar den DIFF des
Repositorys. „Bereich ORB-Engine" waere hier eine Behauptung, die niemand
einloest — geprueft wird, was sich geaendert hat. Deshalb nimmt der Partner eine
AUSWAHL entgegen (nicht committet / committet / gegen einen Zweig), und der
Auftragstext im Verlauf sagt genau das.

WARUM DER BEFEHL AUS DER KONFIGURATION KOMMT
--------------------------------------------
``befehl`` ist eine Liste aus ``DJANGOBASE["review_partner"]`` und wird ohne
Shell gestartet. Aus dem Browser kommt nur der SCHLUeSSEL einer vorbereiteten
Auswahl, nie ein Argument. Ein Freitextfeld, das in eine Kommandozeile wandert,
waere eine Fernsteuerung des Servers — und die Review-Seite steht in sechs
Projekten.

WAS DIESES MODUL NICHT WEISS
----------------------------
Wie die Ausgabe von ``cr review`` im Einzelnen aussieht. Sie wird deshalb
UNVERAENDERT durchgereicht (nur ANSI-Farbcodes fallen weg). Ein Parser, der ein
vermutetes Format zerlegt, wuerde bei der ersten Formatänderung still das
Falsche anzeigen — und ein Review, das Befunde verschluckt, ist schlimmer als
keins.
"""
import logging
import os
import re
import subprocess
import time
from pathlib import Path

from .partner import ReviewFehler

logger = logging.getLogger(__name__)

__all__ = ["WerkzeugPartner"]

#: ANSI-Steuerzeichen (Farben, Cursor). Eine CLI schreibt sie auch dann, wenn
#: niemand hinsieht; im Browser stuenden sonst Zeichenketten wie ``[32m``.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


class WerkzeugPartner:
    u"""Startet ein Pruefwerkzeug und gibt dessen Ausgabe als „Antwort" zurueck."""

    #: Kennzeichnung in der Konfiguration (``ziel``).
    ZIEL = "werkzeug"

    #: Auswahlen, die ein Werkzeug anbieten kann, wenn es keine eigenen nennt.
    #: Die Schluessel sind das, was der Browser schicken darf.
    STANDARD_AUSWAHL = {}

    #: Ein Review dauert je nach Umfang eine bis fuenf Minuten.
    TIMEOUT = 900

    def __init__(self, slug, name, befehl, wurzel, *, modell="", timeout=None,
                 auswahl=None, auswahlen=None, schluessel_datei=None,
                 schluessel_argument=None, umgebung=None):
        self.slug = slug
        self.name = name or slug
        self.ziel = self.ZIEL
        self.befehl = list(befehl or [])
        self.wurzel = Path(wurzel)
        self.timeout = int(timeout or self.TIMEOUT)
        self.auswahlen = self._auswahlen_lesen(auswahlen)
        # EIN UNBEKANNTER WERT IST EIN FEHLER, KEIN RUECKFALL (Befund
        # CodeRabbit, 31.08.2026): Vorher lief bei einem unbekannten Schluessel
        # still die ERSTE Auswahl - waehrend ``ReviewLauf.zustand()`` weiterhin
        # den angefragten Wert meldete. Die Seite haette dann einen Git-Stand
        # angezeigt und einen anderen geprueft. Leer bleibt der ausdrueckliche
        # Fall „nimm die erste".
        if auswahl and auswahl not in self.auswahlen:
            raise ReviewFehler(
                u"Unbekannte Auswahl %r — bekannt sind: %s"
                % (auswahl, ", ".join(self.auswahlen) or u"(keine)"))
        self.auswahl = auswahl or self._erste_auswahl()
        #: Datei mit dem Zugangsschluessel — EINE Zeile, ausserhalb des Projekts.
        #:
        #: WARUM DAS NOETIG IST (gemessen 31.08.2026): Der Serverprozess laeuft
        #: hier als Dienstkonto SYSTEM. Dessen Benutzerprofil ist
        #: ``C:\\Windows\\system32\\config\\systemprofile`` — die Anmeldung, die
        #: jemand in seiner eigenen Konsole hinterlegt hat, liegt dort nicht.
        #: Ein Werkzeug, das „schon angemeldet" ist, ist es fuer diesen Prozess
        #: also NICHT, und die Meldung dazu ist englisch und unspezifisch.
        self.schluessel_datei = schluessel_datei
        self.schluessel_argument = schluessel_argument
        #: Zusaetzliche Umgebungsvariablen fuer den Aufruf.
        #:
        #: WOFUER (gemessen 31.08.2026): Die CodeRabbit-CLI legt ihre Anmeldung
        #: unter ``%LOCALAPPDATA%\\coderabbit\\auth.json`` ab — also im Profil
        #: DESSEN, der sich angemeldet hat. Der Serverprozess laeuft hier als
        #: SYSTEM und sucht sie folglich im Dienstkonto-Profil, wo keine liegt.
        #: Mit ``{"LOCALAPPDATA": "C:\\Users\\e\\AppData\\Local"}`` liest er die
        #: vorhandene Anmeldung, statt einen zweiten Zugang zu brauchen.
        #:
        #: KEIN ERSATZ, SONDERN ERGAENZUNG der geerbten Umgebung: Ohne PATH und
        #: SystemRoot startet unter Windows kaum ein Programm.
        self.umgebung = dict(umgebung or {})
        #: Steht in der Mitschrift und im Zustand an der Stelle, an der bei
        #: einem Modell der Modellname steht.
        self.modell = modell or " ".join(self.befehl) or slug
        #: Damit die Seite denselben Verlauf zeigen kann wie bei einem Modell.
        self.verlauf = [{"role": "system", "content":
                         u"Pruefwerkzeug: %s" % self.modell}]
        self.verbrauch = []

    @classmethod
    def _auswahlen_lesen(cls, auswahlen):
        u"""``{Wert: [Argumente]}`` aus der Konfiguration.

        Zwei Schreibweisen sind erlaubt, weil sie zwei Zwecken dienen:

            Liste  [{"wert": "uncommitted", "name": "Noch nicht committet",
                     "argumente": ["--uncommitted"]}, ...]
                   Die Seite braucht eine Beschriftung und eine Reihenfolge.
            Dict   {"uncommitted": ["--uncommitted"]}
                   Kurzform fuer Skripte, die keine Oberflaeche haben.
        """
        if not auswahlen:
            return dict(cls.STANDARD_AUSWAHL)
        if isinstance(auswahlen, dict):
            return {k: list(v) for k, v in auswahlen.items()}
        raus = {}
        for e in auswahlen:
            wert = (e or {}).get("wert")
            if wert:
                raus[wert] = list(e.get("argumente") or [])
        return raus

    @staticmethod
    def anzeige_auswahlen(partner_cfg):
        u"""``[{wert, name}]`` fuer die Seite — ohne die Argumente.

        Die Kommandozeile gehoert nicht ins HTML: Sie ist Serversache, und im
        Browser waere sie eine Einladung, daran zu drehen.
        """
        auswahlen = (partner_cfg or {}).get("auswahlen") or []
        if isinstance(auswahlen, dict):
            return [{"wert": k, "name": k} for k in auswahlen]
        return [{"wert": e.get("wert", ""), "name": e.get("name") or e.get("wert", "")}
                for e in auswahlen if (e or {}).get("wert")]

    def _erste_auswahl(self):
        return next(iter(self.auswahlen), "")

    def _befehl_bauen(self, mit_schluessel):
        u"""Der volle Aufruf. ``mit_schluessel=False`` fuer die Anzeige.

        Der Schluessel darf in die Kommandozeile, aber NIE in die Mitschrift
        auf der Platte und nie ins HTML: Beide werden gelesen, weitergegeben
        und liegen laenger als der Lauf.
        """
        befehl = self.befehl + list(self.auswahlen.get(self.auswahl) or [])
        if not self.schluessel_argument:
            return befehl
        schluessel = self._schluessel()
        if not schluessel:
            return befehl
        return befehl + [self.schluessel_argument,
                         schluessel if mit_schluessel else u"…"]

    def _schluessel(self):
        u"""Erste Zeile der Schluesseldatei — oder leer.

        Kein Absturz, wenn die Datei fehlt: Dann laeuft das Werkzeug ohne
        Schluessel und sagt selbst, dass es keinen hat. Diese Meldung ist
        praeziser als eine, die diese Klasse sich ausdenkt.
        """
        if not self.schluessel_datei:
            return ""
        try:
            pfad = Path(self.schluessel_datei).expanduser()
            return pfad.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        except (OSError, IndexError) as e:
            logger.warning("Schluesseldatei '%s' nicht lesbar: %s",
                           self.schluessel_datei, e)
            return ""

    def auftrag(self, frage=""):
        u"""Der Text, der als „Frage" im Verlauf und in der Mitschrift steht.

        Er nennt AUSDRUeCKLICH, was geprueft wird — sonst steht in der
        Mitschrift ein Bereichsname, und geprueft wurde der Diff.
        """
        teile = [u"# Pruefwerkzeug: %s" % self.name,
                 u"",
                 # OHNE Schluessel: Dieser Text landet in der Mitschrift.
                 u"Aufruf: `%s`" % " ".join(self._befehl_bauen(mit_schluessel=False)),
                 u"Verzeichnis: `%s`" % self.wurzel,
                 u"",
                 u"Geprueft wird der Git-Stand dieses Verzeichnisses — NICHT "
                 u"die auf der Seite gewaehlten Codebereiche."]
        if frage.strip():
            teile += [u"", u"## Notiz", u"", frage.strip()]
        return "\n".join(teile)

    # ------------------------------------------------------------------ fragen

    def fragen(self, text):
        u"""Das Werkzeug starten. ``text`` ist der Auftrag, nicht die Eingabe.

        Der Auftragstext geht NICHT an das Werkzeug — es nimmt keine Frage
        entgegen. Er steht im Verlauf und in der Mitschrift, damit spaeter
        nachvollziehbar ist, was geprueft werden sollte.
        """
        self.verlauf.append({"role": "user", "content": text})
        befehl = self._befehl_bauen(mit_schluessel=True)
        # LEEREN BEFEHL ABFANGEN (Befund CodeRabbit, 31.08.2026): ``befehl[0]``
        # in den Fehlerzweigen unten haette einen IndexError geworfen - eine
        # Ausnahme ueber die fehlende Ausnahme, die niemandem sagt, was fehlt.
        if not befehl:
            self.verlauf.pop()
            raise ReviewFehler(
                u"Fuer %s ist kein Befehl konfiguriert (``befehl`` in "
                u"DJANGOBASE[\"review_partner\"])." % self.name)
        t0 = time.time()
        try:
            ergebnis = subprocess.run(
                befehl, cwd=str(self.wurzel), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=self.timeout,
                shell=False, stdin=subprocess.DEVNULL,
                env=(dict(os.environ, **self.umgebung) if self.umgebung else None))
        except FileNotFoundError as e:
            self.verlauf.pop()
            raise ReviewFehler(
                u"Werkzeug nicht gefunden: %s. Ist es installiert und im PATH "
                u"des Serverprozesses? (Der PATH einer geplanten Aufgabe ist "
                u"nicht der der Anmeldesitzung.)" % befehl[0]) from e
        except subprocess.TimeoutExpired as e:
            self.verlauf.pop()
            raise ReviewFehler(u"%s hat nach %d s nicht geantwortet."
                               % (befehl[0], self.timeout)) from e
        except OSError as e:
            self.verlauf.pop()
            raise ReviewFehler(u"%s liess sich nicht starten: %s"
                               % (befehl[0], e)) from e

        dauer = time.time() - t0
        ausgabe = self._saeubern(ergebnis.stdout)
        fehlertext = self._saeubern(ergebnis.stderr)

        if ergebnis.returncode != 0 and not ausgabe.strip():
            self.verlauf.pop()
            raise ReviewFehler(self._klartext(befehl[0], ergebnis.returncode,
                                              fehlertext))
        if ergebnis.returncode != 0:
            # Ausgabe DA, Ende-Code schlecht: Beides zeigen. Ein Werkzeug, das
            # Befunde liefert und trotzdem mit 1 endet, ist der Normalfall bei
            # Pruefwerkzeugen — die Befunde sind die Nachricht.
            ausgabe += (u"\n\n---\n_Ende-Code %d_" % ergebnis.returncode)
            if fehlertext.strip():
                ausgabe += u"\n\n```\n%s\n```" % fehlertext.strip()

        antwort = ausgabe.strip() or u"_Das Werkzeug hat nichts ausgegeben._"
        hinweis = self._hinweis_zur_ausgabe(antwort, befehl[0])
        if hinweis:
            antwort = hinweis + u"\n\n---\n\n" + antwort
        self.verlauf.append({"role": "assistant", "content": antwort})
        self.verbrauch.append({"sekunden": round(dauer, 1),
                               "ende_code": ergebnis.returncode,
                               "zeichen": len(antwort)})
        return antwort

    # ------------------------------------------------------------------ Hilfen

    @staticmethod
    def _saeubern(text):
        return _ANSI.sub("", text or "")

    @staticmethod
    def _hinweis_zur_ausgabe(ausgabe, werkzeug):
        u"""Ein deutscher Satz VOR eine englische Absage setzen — wo er hilft.

        Der Serverprozess hat kein Terminal. Die CodeRabbit-CLI antwortet
        darauf mit „Non-interactive environment detected. Use --api-key for
        authentication." — richtig, aber niemand weiss, was zu tun ist. Der
        belegte Weg (Doku, 31.08.2026) ist EIN einmaliger Aufruf, der den
        Schluessel ablegt; danach braucht kein Lauf mehr ein Argument, und der
        Schluessel steht in keiner Kommandozeile, die in ein Protokoll gerät.

        NUR VORANGESTELLT, NIE ERSETZT: Die Originalmeldung bleibt darunter
        stehen. Wer sie sucht, findet sie — ein Werkzeug, dessen Ausgabe von
        der Oberflaeche umgeschrieben wird, ist beim naechsten Format nicht
        mehr zu debuggen.
        """
        niedrig = (ausgabe or "").lower()
        if "non-interactive" in niedrig and "api-key" in niedrig:
            return (u"**Nicht angemeldet — der Serverprozess hat kein Terminal.** "
                    u"Einmalig in einer Konsole:\n\n"
                    u"```\n%s auth login --api-key cr-…\n```\n\n"
                    u"Den Schlüssel gibt es auf app.coderabbit.ai unter „API Keys“. "
                    u"Danach laufen die Prüfungen von dieser Seite aus ohne "
                    u"weitere Angabe." % werkzeug)
        if "rate limit" in niedrig or "too many requests" in niedrig:
            return (u"**Kontingent erschöpft.** Im kostenlosen Plan sind es drei "
                    u"Läufe je Stunde (Pro fünf, Pro+ zehn).")
        return ""

    @staticmethod
    def _klartext(werkzeug, code, fehlertext):
        u"""Aus einem Ende-Code eine Zeile machen, die weiterhilft.

        Die haeufigsten Faelle stehen zuerst — wer die Seite benutzt, soll
        nicht in einem Stapel englischer Zeilen nach dem Grund suchen. Was
        nicht erkannt wird, wird UNVERAENDERT gezeigt statt gedeutet.
        """
        knapp = (fehlertext or "").strip()
        niedrig = knapp.lower()
        if "auth" in niedrig or "log in" in niedrig or "sign in" in niedrig \
                or "unauthorized" in niedrig or "401" in niedrig:
            return (u"%s ist nicht angemeldet. Einmalig `%s auth login` in einer "
                    u"Konsole ausfuehren — der Anmeldevorgang oeffnet den "
                    u"Browser.\n\n%s" % (werkzeug, werkzeug, knapp))
        if "rate limit" in niedrig or "too many" in niedrig or "429" in niedrig:
            return (u"%s meldet, dass das Kontingent erschoepft ist. Im "
                    u"kostenlosen Plan sind es drei Laeufe je Stunde.\n\n%s"
                    % (werkzeug, knapp))
        if "not a git repository" in niedrig:
            return (u"Das Verzeichnis ist kein Git-Repository — %s prueft den "
                    u"Diff und braucht eines.\n\n%s" % (werkzeug, knapp))
        return u"%s endete mit Code %d.\n\n%s" % (werkzeug, code,
                                                  knapp or u"(keine Meldung)")
