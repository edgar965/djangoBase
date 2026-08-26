# -*- coding: utf-8 -*-
"""ReviewLauf — eine Sitzung mit einem Modell, in drei Betriebsarten.

    frage     Eine Frage, eine Antwort. Fuer „Was haelst du von dieser Stelle?"
    dialog    Ein Bereich, beliebig viele Runden. Nachfassen ist der Punkt:
              Die erste Antwort eines Modells ist erfahrungsgemaess eine Liste
              plausibler Lehrbuchbefunde; erst die Nachfrage mit einer Messung
              trennt sie von den echten.
    bereiche  Mehrere Bereiche GLEICHZEITIG, je ein eigener Verlauf. Nachfassen
              geht einzeln oder an alle.

WARUM DAS PAKET AUS DEM ECHTEN QUELLTEXT GEBAUT WIRD und nicht von Hand
zusammenkopiert: Ein Paket, das von der Platte abweicht, erzeugt Befunde zu
Code, den es nicht gibt — und bis das auffaellt, ist mehr Zeit weg als das
Bauen je gekostet hat.

Alles laeuft im Hintergrund-Faden: Eine Runde dauert je nach Modell und
Paketgroesse eine bis fuenf Minuten. Die Seite fragt den Zustand ab.
"""
import logging
import os
import threading
import uuid
from pathlib import Path

from .faden import ReviewFaden
from .partner import ReviewPartner

logger = logging.getLogger(__name__)

#: Auf WIDERSPRUCH getrimmt. Ein Modell, das zustimmt, ist als Sparringspartner
#: wertlos — und eines, das Fehler erfindet, kostet nur Zeit. Deshalb wird
#: beides verlangt: die ausloesende Eingabe nennen ODER sagen, was fehlt.
ROLLE = (
    "Du bist ein skeptischer Senior-Reviewer. Deine Aufgabe ist WIDERSPRUCH, "
    "nicht Zustimmung: Suche Denkfehler, falsche Annahmen, Nebenlaeufigkeit, "
    "Zahlenfehler, Sicherheitsluecken und fehlende Gegenproben.\n"
    "REGELN:\n"
    "1. Jeder Befund nennt DATEI + FUNKTION und beschreibt, wie man ihn ausloest. "
    "Ohne ausloesenden Fall ist es kein Befund, sondern Geschmack.\n"
    "2. Fehlen dir Angaben, sage GENAU welche Datei oder Funktion du brauchst. "
    "Erfinde keinen Code, den du nicht gesehen hast.\n"
    "3. Sortiere nach Schaden: was Daten verliert, was hängt, was nur haesslich ist.\n"
    "4. Antworte auf DEUTSCH, knapp, in Stichpunkten. Keine Zusammenfassung des "
    "Codes — der Fragende kennt ihn.\n"
    "5. Wirst du widerlegt, zieh den Befund ausdruecklich zurück. Ein Modell, das "
    "seine Fehler verteidigt, ist als Kritiker unbrauchbar."
)

#: Vorgefertigte Nachfassfragen der Oberflaeche. Sie sind der eigentliche Wert
#: des Dialogs: Sie zwingen zu dem, was eine erste Antwort nie liefert.
NACHFASSEN = {
    "widerlegen": (
        "Greife jetzt DEINE EIGENE Antwort an. Welcher deiner Befunde hält einer "
        "Gegenprobe nicht stand, welcher ist Lehrbuchwissen ohne Ausloeser in "
        "diesem Code? Nenne mindestens einen, den du zuruecknimmst."),
    "rangfolge": (
        "Genau DREI Änderungen, die ich heute machen soll — nicht vier. Je einen "
        "Satz Begründung. Und sag dazu, was du bewusst NICHT in die drei nimmst "
        "und warum."),
    "fehlt": (
        "Was fehlt dir, um sicher zu urteilen? Nenne konkrete Dateien oder "
        "Funktionen, die du sehen musst, und schreibe zu jeder, welche Frage sie "
        "dir beantworten wuerde."),
    "ausloesen": (
        "Nimm deinen schwerwiegendsten Befund und beschreibe ihn als Ablauf, den "
        "ich nachstellen kann: Eingabe, Schritte, erwartetes falsches Ergebnis. "
        "Wenn du das nicht kannst, sag es — dann ist es kein Befund."),
}


class ReviewLauf:
    """Eine Sitzung: ein Partner, ein oder mehrere Faeden."""

    #: Obergrenze je Datei im Paket. Groesseres wird GEKUERZT und im Paket als
    #: gekuerzt ausgewiesen — stillschweigend abschneiden hiesse, das Modell
    #: ueber den Umfang zu taeuschen.
    MAX_ZEICHEN_DATEI = 120_000
    MAX_ZEICHEN_PAKET = 400_000

    def __init__(self, modus, partner_cfg, *, wurzel, ablage, rolle=None,
                 schluessel_datei=None, ollama_url=None, online_url=None):
        self.id = uuid.uuid4().hex[:12]
        self.modus = modus
        self.partner_cfg = partner_cfg
        self.wurzel = Path(wurzel).resolve()
        self.ablage = Path(ablage)
        self.rolle = rolle or ROLLE
        self.schluessel_datei = schluessel_datei
        self.ollama_url = ollama_url
        self.online_url = online_url
        self.titel = ""
        self.faeden = {}                   # slug -> ReviewFaden
        self.reihenfolge = []
        self.fehler = ""

    # ------------------------------------------------------------------ starten

    def starten(self, *, bereiche=(), frage="", titel=""):
        """Faeden anlegen und die erste Runde im Hintergrund stellen."""
        self.titel = titel or (bereiche[0]["name"] if bereiche else "Freie Frage")
        if bereiche:
            for b in bereiche:
                self._faden_anlegen(b["slug"], b["name"])
        else:
            self._faden_anlegen("frage", "Freie Frage")

        for i, slug in enumerate(self.reihenfolge):
            bereich = bereiche[i] if bereiche else None
            text = self._paket(bereich, frage)
            faden = self.faeden[slug]
            faden.beansprucht()          # frisch angelegt, gewinnt immer
            threading.Thread(target=faden.fragen,
                             args=(text, "Runde 1"), kwargs={"schon_beansprucht": True},
                             name="review-%s-%s" % (self.id, slug),
                             daemon=True).start()
        return self

    def _faden_anlegen(self, slug, titel):
        p = self.partner_cfg
        partner = ReviewPartner(
            slug=p.get("slug", "partner"), name=p.get("name", ""),
            ziel=p.get("ziel", "lokal"), modell=p.get("modell", ""),
            rolle=self.rolle,
            url=self.ollama_url if p.get("ziel") == "lokal" else self.online_url,
            schluessel_datei=self.schluessel_datei,
            num_ctx=p.get("num_ctx"))
        self.faeden[slug] = ReviewFaden(
            slug, titel, partner,
            mitschrift=self.ablage / ("review_%s_%s.md" % (self.id, slug)))
        self.reihenfolge.append(slug)

    # ---------------------------------------------------------------- nachfassen

    def nachfassen(self, text, slug=None):
        """Weitere Runde — in einem Faden oder in allen gleichzeitig."""
        ziele = [slug] if slug else list(self.reihenfolge)
        gestartet = []
        for s in ziele:
            faden = self.faeden.get(s)
            # Beanspruchen UND pruefen in einem Schritt (siehe
            # ReviewFaden.beansprucht): Ein `if faden.status == "laeuft"` davor
            # war ein Wettrennen — zwei gleichzeitige Anfragen kamen beide durch.
            if faden is None or not faden.beansprucht():
                continue
            marke = "Runde %d" % (len(faden.runden) + 1)
            threading.Thread(target=faden.fragen,
                             args=(text, marke), kwargs={"schon_beansprucht": True},
                             name="review-%s-%s" % (self.id, s), daemon=True).start()
            gestartet.append(s)
        return gestartet

    # -------------------------------------------------------------------- Paket

    def _paket(self, bereich, frage):
        """Die erste Nachricht: Frage + echter Quelltext."""
        teile = []
        if bereich:
            teile.append("# Codebereich: %s\n" % bereich["name"])
            if bereich.get("hinweis"):
                teile.append(bereich["hinweis"].strip() + "\n")
        if frage.strip():
            teile.append("## Meine Frage\n\n" + frage.strip() + "\n")
        elif bereich and bereich.get("fragen"):
            teile.append("## Fragen\n\n" + "\n".join(
                "%d. %s" % (i + 1, f) for i, f in enumerate(bereich["fragen"])) + "\n")

        dateien = list((bereich or {}).get("dateien") or [])
        if dateien:
            teile.append("## Quelltext (vollständig, von der Platte gelesen)\n")
            gesamt = 0
            # Ein Bereich darf eine EIGENE Wurzel mitbringen. Grund: Das geteilte
            # Paket (djangoBase) liegt ausserhalb jedes Projektverzeichnisses,
            # haengt aber in sechs Projekten drin — und gerade der Code, den alle
            # benutzen, sollte pruefbar sein. Die Pruefung bleibt scharf: Jede
            # Datei muss unter DER Wurzel liegen, die ihr Bereich nennt.
            wurzel = self._bereichs_wurzel(bereich)
            for eintrag in dateien:
                # Ein Eintrag ist ein Pfad ODER {"pfad": ..., "funktionen": [...]}.
                # Letzteres schneidet einzelne Funktionen/Klassen heraus — ohne das
                # ist eine 6.400-Zeilen-Datei nicht besprechbar: Sie sprengt das
                # Paket, und eine Antwort darauf wird beliebig.
                rel, funktionen = self._eintrag_zerlegen(eintrag)
                # `kuerzen=False` bei Funktionsauswahl, und das ist keine Feinheit:
                # Der erste Wurf kuerzte die Datei ZUERST auf 120.000 Zeichen und
                # schnitt dann die Funktionen heraus — alles, was weiter hinten in
                # einer 250-KB-Datei stand, war „nicht gefunden". Erst schneiden,
                # dann kuerzen (gefunden 13.08.2026, weil der Hinweis es sagte).
                text, hinweis = self._datei_lesen(rel, wurzel, kuerzen=not funktionen)
                if text is not None and funktionen:
                    text, hinweis2 = self._funktionen_schneiden(rel, text, funktionen)
                    if text is not None and len(text) > self.MAX_ZEICHEN_DATEI:
                        text = text[:self.MAX_ZEICHEN_DATEI]
                        hinweis2 += " / danach auf %d Zeichen gekuerzt" % self.MAX_ZEICHEN_DATEI
                    hinweis = ' / '.join(h for h in (hinweis, hinweis2) if h)
                if text is None:
                    teile.append("### %s\n\n_%s_\n" % (rel, hinweis))
                    continue
                if gesamt + len(text) > self.MAX_ZEICHEN_PAKET:
                    teile.append("### %s\n\n_Nicht mehr eingefuegt: Paketgrenze "
                                 "erreicht._\n" % rel)
                    continue
                gesamt += len(text)
                teile.append("### %s%s\n\n```%s\n%s\n```\n"
                             % (rel, (" — " + hinweis) if hinweis else "",
                                self._sprache(rel), text))
        return "\n".join(teile)

    @staticmethod
    def _eintrag_zerlegen(eintrag):
        """(Pfad, Funktionsnamen) aus einem Bereichs-Eintrag."""
        if isinstance(eintrag, dict):
            return eintrag.get("pfad") or "", list(eintrag.get("funktionen") or [])
        return eintrag, []

    @staticmethod
    def _funktionen_schneiden(rel, text, namen):
        """Nur die genannten Funktionen/Klassen zurueckgeben (nur Python).

        MIT ZEILENNUMMERN als Anker: Ein Befund soll auf die Stelle in der
        ECHTEN Datei zeigen, nicht auf eine Zeile im Ausschnitt. Und was NICHT
        gefunden wurde, steht ausdruecklich dabei — sonst beurteilt das Modell
        einen Ausschnitt, dessen Umfang es für vollständig hält."""
        import ast
        if not rel.lower().endswith(".py"):
            return text, "Funktionsauswahl nur für Python möglich — ganze Datei"
        try:
            baum = ast.parse(text)
        except SyntaxError as e:
            return text, "nicht zerlegbar (%s) — ganze Datei" % e
        zeilen = text.split("\n")
        gesucht, teile, gefunden = set(namen), [], set()
        for k in baum.body:
            if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and k.name in gesucht:
                anfang = min([d.lineno for d in k.decorator_list] or [k.lineno]) - 1
                teile.append("# --- %s  (%s, Zeile %d) ---\n%s"
                             % (k.name, rel, k.lineno,
                                "\n".join(zeilen[anfang:k.end_lineno])))
                gefunden.add(k.name)
        if not teile:
            return None, ("keine der Funktionen gefunden: %s"
                          % ", ".join(sorted(gesucht)))
        fehlt = sorted(gesucht - gefunden)
        hinweis = ("AUSSCHNITT: %d von %d Funktionen dieser Datei"
                   % (len(gefunden), len(namen)))
        if fehlt:
            hinweis += " — NICHT gefunden: %s" % ", ".join(fehlt)
        return "\n\n".join(teile), hinweis

    def _bereichs_wurzel(self, bereich):
        """Eigene Wurzel des Bereichs, sonst die des Laufs."""
        eigen = (bereich or {}).get("wurzel")
        if not eigen:
            return self.wurzel
        try:
            return Path(eigen).resolve()
        except OSError:
            logger.warning("Review: Bereichs-Wurzel nicht aufloesbar: %r", eigen)
            return self.wurzel

    def _datei_lesen(self, rel, wurzel=None, kuerzen=True):
        """Datei unterhalb der Wurzel lesen. Gibt (text, hinweis) zurueck.

        `kuerzen=False` liefert die Datei ungekuerzt — noetig, wenn danach noch
        einzelne Funktionen herausgeschnitten werden (siehe `_paket`).

        Die Wurzelpruefung ist kein Misstrauen gegen die eigene Konfiguration,
        sondern gegen Tippfehler: Ein `../..` im Pfad soll eine Meldung geben und
        nicht stillschweigend eine fremde Datei an ein Online-Modell schicken."""
        wurzel = wurzel or self.wurzel
        try:
            ziel = (wurzel / rel).resolve()
        except OSError as e:
            return None, "Pfad nicht aufloesbar: %s" % e
        if not self._liegt_in(ziel, wurzel):
            logger.warning("Review: Datei außerhalb der Wurzel abgelehnt: %s", ziel)
            return None, "Liegt außerhalb der Bereichs-Wurzel — nicht gesendet."
        try:
            text = ziel.read_text(encoding="utf-8", errors="replace").rstrip()
        except OSError as e:
            return None, "Nicht lesbar: %s" % e
        if kuerzen and len(text) > self.MAX_ZEICHEN_DATEI:
            return (text[:self.MAX_ZEICHEN_DATEI],
                    "GEKUERZT auf %d von %d Zeichen" % (self.MAX_ZEICHEN_DATEI, len(text)))
        return text, ""

    @staticmethod
    def _liegt_in(ziel, wurzel):
        """Enthaeltnis-Pruefung, unter Windows ohne Ruecksicht auf Gross-/Klein.

        `is_relative_to` vergleicht Zeichenketten. Steht in der Konfiguration
        `A:\\Shared\\djangoBase` und liefert `resolve()` `a:\\shared\\djangobase`,
        wird eine voellig legitime Datei abgelehnt (Befund aus dem Review dieses
        Werkzeugs, 13.08.2026). Das ist kein Loch, sondern eine Absage an der
        falschen Stelle — laut aber nutzlos. `os.path.normcase` ist auf anderen
        Systemen wirkungslos, dort ist Gross-/Kleinschreibung bedeutsam."""
        z, w = Path(os.path.normcase(ziel)), Path(os.path.normcase(wurzel))
        try:
            return z == w or z.is_relative_to(w)
        except ValueError:
            return False

    @staticmethod
    def _sprache(rel):
        endung = Path(rel).suffix.lower()
        return {".py": "python", ".js": "javascript", ".html": "html",
                ".css": "css", ".json": "json"}.get(endung, "")

    # ------------------------------------------------------------------ Anzeige

    def zustand(self, mit_text=True):
        return {
            "id": self.id, "modus": self.modus, "titel": self.titel,
            "partner": self.partner_cfg.get("name") or self.partner_cfg.get("slug"),
            "fehler": self.fehler,
            "laeuft": any(f.status == "laeuft" for f in self.faeden.values()),
            "faeden": [self.faeden[s].zustand(mit_text) for s in self.reihenfolge],
        }
