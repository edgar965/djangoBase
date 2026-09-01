# -*- coding: utf-8 -*-
"""Welches KI-Modell taugt als Sparringspartner? - die eigenen Messungen.

WOZU
----
``ki_modelle.py`` sagt, welche Modelle es gibt und was sie kosten. Diese Datei
sagt, welche davon im EIGENEN Anwendungsfall etwas getaugt haben - gemessen am
11.08.2026 mit ``werkzeug/sparring_vergleich.py``.

WIE GEMESSEN WURDE
------------------
Drei Fragen aus der echten Projektarbeit, deren richtige Antwort inzwischen
bekannt ist, weil sie teuer erarbeitet wurde. Jede hat einen KERNPUNKT, den die
meisten uebersehen, und Standardpunkte, die jeder nennt:

    1. Die Zellen-Rechnung   Beim Weglassen von Trades RUECKEN ANDERE NACH (das
                             System hat ein Tageslimit von 4). Die Rechnung
                             "Zelle weg = Gewinn hoeher" hatte real das falsche
                             VORZEICHEN: geschaetzt +7.861, gerechnet -6.158 EUR.
    2. Die schwachen Jahre   Stop und Ziel skalieren mit der Spanne, die KOSTEN
                             sind feste Punktbetraege - bei niedrigem Index
                             fressen sie den Ertrag (77 % statt 27 % vom Brutto).
    3. Der beste Filter      Bei einer Suche ueber viele Varianten ist die beste
                             auch dann die beste, wenn alle nur rauschen.

WAS DIE ZAHLEN NICHT SIND
-------------------------
Die Treffer stammen aus einer STICHWORT-SUCHE ueber die Antworttexte. Sie findet
Formulierungen, keine Gedanken: Ein Modell kann richtig liegen und nicht gezaehlt
werden, oder das Stichwort ohne Verstaendnis streuen und gezaehlt werden. Das
``urteil`` je Zeile stammt deshalb aus dem GELESENEN Antworttext, nicht aus der
Trefferzahl - und weicht an mehreren Stellen von ihr ab.

DREI TREFFER MIT NUR EINEM LAUF: Jede Zeile ist EINE Messung. Wie wenig das
traegt, zeigt nemotron: dieselbe Frage, zwei Laeufe, einmal 2/2 und einmal 0/2.
"""

from .modellname import Modellname

#: GRAFIKSPEICHER der lokalen Modelle: (gesamt GB, davon auf der GPU, Rest im
#: Hauptspeicher). Gemessen mit ``werkzeug/ollama_vram.py``.
#:
#: STAND 24.08.2026 - RTX PRO 4500 BLACKWELL (32 GB). Bis dahin steckte eine
#: RTX 3060 mit 12 GB im Rechner, und die dritte Zahl war die wichtigste der
#: ganzen Seite: Was nicht auf die Karte passte, rechnete die CPU mit, und das
#: kostete ein Vielfaches. Auf der neuen Karte ist diese Spalte bei JEDEM
#: Modell null - der Engpass ist weg, nicht kleiner geworden.
#:
#: Die 3060-Werte stehen als ``VRAM_3060`` darunter. Sie werden gebraucht, weil
#: sich mehrere Befundtexte auf sie stuetzen - und weil man den Unterschied nur
#: sieht, wenn beide Zahlen dastehen.
VRAM = {
    "gpt-oss:20b":                          (13.6, 13.6, 0.0),
    "gemma4:26b-a4b-it-qat":                (16.7, 16.7, 0.0),
    "qwen3.8:27b":                          (17.5, 17.5, 0.0),
    "nemotron:70b-instruct-q2_K":           (26.4, 26.4, 0.0),
    "nemotron-3.5-lightning:30b-a3b-q4_K_M": (26.7, 26.7, 0.0),
    "qwen3.6:35b-a3b-q4_K_M":               (29.3, 29.3, 0.0),
    "qwen3.8:27b-q8_0":                     (30.1, 30.1, 0.0),
}

#: DIESELBE MESSUNG AUF DER ALTEN KARTE (RTX 3060, 12 GB; 11.08. und 18.08.2026).
#: Nicht loeschen: Der Vergleich ist der Beleg fuer den Kartenwechsel, und ohne
#: ihn stuenden die Nullen oben ohne Bezug da.
#:
#: qwen3.5:9b belegt oben MEHR als hier (15,3 statt 5,5 GB) - das Modell ist
#: dasselbe, Ollama legt den Kontextpuffer nur groesser an, wenn Platz ist.
#: Die Zahl ist also kein Bedarf, sondern eine Belegung.
VRAM_3060 = {
    "qwen3.5:9b":            (5.5, 5.5, 0.0),
    "gpt-oss:20b":           (13.8, 11.0, 2.8),
    "gemma4:26b-a4b-it-qat": (15.8, 9.5, 6.3),
    "qwen3.6:27b":           (17.1, 9.8, 7.3),
    # qwen3.6 ist am 18.08.2026 geloescht worden (Ansage Edgar); seine Zahlen
    # bleiben, weil die MoE-Begruendung sich auf sie stuetzt.
    "qwen3.8:27b":           (18.2, 9.0, 9.1),
}

#: WANN DIESES MODELL ZULETZT IM SPARRING WAR (Ansage Edgar, 01.09.2026:
#: „eine zusaetzliche Spalte: Letzer Lauf").
#:
#: Die Daten stammen aus den Mitschriften ``werkzeug/sparring_*.md`` - je
#: Modell die juengste Datei, die es nennt. Sie stehen hier als ANGABE und
#: werden NICHT zur Laufzeit aus Dateizeitstempeln gelesen: Ein Datum, das
#: am mtime haengt, wandert beim Kopieren des Ordners, und dann zeigt die
#: Seite einen Lauf, den es nie gab.
#:
#: WOZU DIE SPALTE: Die Note eines Modells ist so alt wie ihr Lauf. Bei
#: gemini-2.5-pro liegt er drei Wochen zurueck - in dieser Zeit sind zwei
#: Modelle aus dem Katalog verschwunden und eines um den Faktor 6
#: eingebrochen. Ohne Datum sieht eine alte Bewertung aus wie eine frische.
#:
#: ``qwen3:14b`` fehlt: keine Mitschrift mehr vorhanden.
SPARRING_STAND = {
    "nvidia/nemotron-3-ultra-550b-a55b:free":  "2026-08-11",
    "google/gemini-3-flash-preview":           "2026-08-11",
    "gemma4:26b-a4b-it-qat":                   "2026-08-24",
    "gpt-oss:20b":                             "2026-08-24",
    "moonshotai/kimi-k3":                      "2026-08-11",
    "qwen/qwen3.8-max":                        "2026-08-11",
    "deepseek/deepseek-v4-flash":              "2026-08-11",
    "x-ai/grok-4.6":                           "2026-08-13",
    "deepseek/deepseek-v4-pro":                "2026-08-13",
    "qwen3.6:35b-a3b-q4_K_M":                  "2026-08-24",
    "qwen3.8:27b-q8_0":                        "2026-08-24",
    "nemotron-3.5-lightning:30b-a3b-q4_K_M":   "2026-08-24",
    "nemotron:70b-instruct-q2_K":              "2026-08-24",
    "qwen3.8:27b":                             "2026-08-24",
    "google/gemini-2.5-pro":                   "2026-08-11",
    "qwen/qwen-plus":                          "2026-08-11",
}

#: Datum der Tempo-Messung (``werkzeug/token_tempo.py``). Getrennt vom
#: Sparring-Datum, weil es zwei verschiedene Laeufe sind: Der eine misst
#: Qualitaet, der andere Token je Sekunde.
TOKEN_STAND = "2026-09-01"


#: DURCHSATZ je lokalem Modell: Token je Sekunde beim Erzeugen der Antwort.
#:
#: STAND 01.09.2026 - neu gemessen mit ``werkzeug/token_tempo.py`` (Ansage
#: Edgar: „mach die tokens messung"), Mittel aus zwei Durchgaengen, dieselbe
#: Frage und dieselben Parameter wie am 24.08.2026. Die Werte davor stehen
#: als ``TOKEN_JE_S_0824`` darunter - ohne sie waere der Einbruch bei
#: nemotron:70b nicht zu sehen.
#:
#: EIN MODELL IST UM DEN FAKTOR 6 EINGEBROCHEN, und das liegt nicht am
#: Modell: ``nemotron:70b-instruct-q2_K`` faellt von 23,7 auf 3,7 Token/s.
#: Nachgesehen am selben Tag: ``OLLAMA_FLASH_ATTENTION`` und
#: ``OLLAMA_KV_CACHE_TYPE`` sind auf diesem Rechner NICHT MEHR GESETZT -
#: weder fuer den Benutzer noch systemweit. Genau die beiden nennt der
#: Eintrag von damals als Bedingung („es laedt allerdings nur mit ...").
#: Die 3,7 sind also der Zustand HEUTE, nicht die Faehigkeit des Modells.
#: Wer die Variablen wieder setzt, misst neu.
#:
#: DIE STREUUNG STEHT DANEBEN, weil sie mitentscheidet, wie ernst die Zahl
#: zu nehmen ist: sechs Modelle liegen bei 1 bis 8 % zwischen den beiden
#: Durchgaengen, ``qwen3.8:27b`` bei 17 %. Bei diesem einen ist der
#: Unterschied zur Vormessung (38,5 -> 44,6) kleiner als seine eigene
#: Schwankung.
TOKEN_JE_S = {
    "gpt-oss:20b":                           142.8,
    "gemma4:26b-a4b-it-qat":                 131.9,
    "qwen3.6:35b-a3b-q4_K_M":                114.0,
    "nemotron-3.5-lightning:30b-a3b-q4_K_M":  53.0,
    "qwen3.8:27b":                            44.6,
    "qwen3.8:27b-q8_0":                       26.0,
    "nemotron:70b-instruct-q2_K":              3.7,
}

#: Die Streuung zwischen den beiden Durchgaengen in Prozent (01.09.2026).
#: Ueber ~15 % sagt die Zahl mehr ueber den Messtag als ueber das Modell.
TOKEN_STREUUNG = {
    "gpt-oss:20b":                            3,
    "gemma4:26b-a4b-it-qat":                  3,
    "qwen3.6:35b-a3b-q4_K_M":                 2,
    "nemotron-3.5-lightning:30b-a3b-q4_K_M":  8,
    "qwen3.8:27b":                           17,
    "qwen3.8:27b-q8_0":                       1,
    "nemotron:70b-instruct-q2_K":             5,
}

#: DIE MESSUNG VOM 24.08.2026 - dieselbe Karte, dieselbe Frage.
#: Nicht loeschen: Der Einbruch bei nemotron:70b ist nur im Vergleich
#: sichtbar, und mehrere Urteilstexte stuetzen sich auf diese Werte.
TOKEN_JE_S_0824 = {
    "gpt-oss:20b":                           140.3,
    "gemma4:26b-a4b-it-qat":                 127.8,
    "qwen3.6:35b-a3b-q4_K_M":                105.2,
    "nemotron-3.5-lightning:30b-a3b-q4_K_M":  67.2,
    "qwen3.8:27b":                            38.5,
    "qwen3.8:27b-q8_0":                       26.2,
    "nemotron:70b-instruct-q2_K":             23.7,
}

#: DURCHSATZ DER KOSTENLOSEN ONLINE-MODELLE: (Token/s, Streuung in %).
#:
#: GEMESSEN AM 01.09.2026 mit ``werkzeug/token_tempo.py`` - derselben Frage
#: und derselben Rolle wie lokal, damit die Haelften vergleichbar sind.
#:
#: ES IST TROTZDEM NICHT DIESELBE GROESSE:
#:
#:   lokal   ``eval_count / eval_duration`` - die reine Erzeugungszeit auf
#:           der eigenen Karte, von Ollama selbst gezaehlt.
#:   online  gestoppt ab dem ERSTEN Token (Streaming), damit Verbindung und
#:           Warteschlange herausfallen.
#:
#: WAS DIE MESSUNG WIRKLICH ERGEBEN HAT, und es ist keine Zahl, sondern ein
#: Verhalten: Zwei Laeufe zu je zwei Durchgaengen lieferten 62,9 und 108,2
#: Token/s - ein Unterschied von 53 %. Zwei WEITERE Laeufe (vier und fuenf
#: Durchgaenge) bekamen ueberhaupt keine Antwort mehr („keine Token
#: empfangen"). Kostenlose Modelle laufen bei OpenRouter mit niedriger
#: Prioritaet; gemessen wird die Tageslast des Anbieters, nicht das Modell.
#:
#: Der Wert steht deshalb MIT seiner Streuung auf der Seite. Eine glatte
#: Zahl ohne diesen Zusatz waere hier eine Erfindung.
TOKEN_JE_S_ONLINE = {
    "nvidia/nemotron-3-ultra-550b-a55b:free": (85.6, 53),
}

#: DIESELBE MESSUNG AUF DER ALTEN KARTE (RTX 3060, 12 GB; 12.08.2026).
TOKEN_JE_S_3060 = {
    "qwen3.5:9b":            48.7,
    "gpt-oss:20b":           34.9,
    "qwen3.6:27b":            3.1,
    "gemma4:26b-a4b-it-qat": 26.5,
}

#: Sekunden und Treffer je Modell ueber alle DREI Fragen zusammen.
#: ``rang`` ist ein Urteil, keine Rechnung - vergeben nach dem Lesen aller
#: Antworten, mit Begruendung in ``urteil``. ``None`` heisst: nicht empfohlen.
#:
#: ``note`` ist die Einschaetzung fuer den EIGENEN Zweck (Rueckfrage Edgar,
#: 11.08.2026: „eine Einschaetzung wie gut die sind") - Schulnote, nach dem Lesen
#: aller Antworten vergeben. Sie bewertet die PRAXISTAUGLICHKEIT als
#: Sparringspartner, nicht die Faehigkeiten des Modells im Allgemeinen: Ein
#: Modell, auf das man vier Minuten wartet, wird nicht gefragt, und ein Modell,
#: das eine leere Antwort schickt, ist unbrauchbar - egal wie klug der Rest war.
#:
#: ``beispiel`` ist der charakteristischste Satz aus der Antwort auf Frage 1
#: (dem Pruefstein). Damit laesst sich das Urteil nachpruefen, statt es zu
#: glauben. Alle Antworten in voller Laenge: werkzeug/sparring_*.md
MESSUNGEN = (
    {
        "kennung": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "ort": "online", "rang": 6, "sekunden": 82, "kern": 4, "standard": 5,
        "ct_je_frage": 0.0,
        "note": "1-", "note_grund": "Fand den echten Mechanismus als ERSTES - aber nur in einem von zwei Läufen; qwen3.8-max fand ihn später beim ersten Versuch.",
        "beispiel": "Sperrst du Longs, veränderst du das Tageslimit (max 4 Trades). Evtl. rutschen Short-Trades nach, die sonst vom Limit blockiert waren.",
        "urteil": "Das ERSTE Modell, das den Kernfehler fand - und zwar "
                  "in 28 Sekunden: „Sperrst du Longs, veränderst du das Tageslimit "
                  "(max 4 Trades). Evtl. rutschen Short-Trades nach, die sonst vom "
                  "Limit blockiert waren.“ Genau daran war die eigene Rechnung "
                  "gescheitert. Kostenlos.",
        "einschraenkung": "Im zweiten Lauf mit derselben Frage kam derselbe Gedanke "
                          "NICHT mehr. Ein Treffer, kein Verlass.",
    },
    {
        "kennung": "google/gemini-3-flash-preview",
        "ort": "online", "rang": 7, "sekunden": 17, "kern": 4, "standard": 4,
        "ct_je_frage": 0.18,
        "note": "2", "note_grund": "Zuverlässig bei den Standardeinwänden, sechs Sekunden je Frage, Zehntelcent - aber ohne Tiefe.",
        "beispiel": "Das setzt voraus, dass du ex ante (zu Handelsbeginn) mit 100%iger Sicherheit wusstest, dass heute ein Abwärtstag ist.",
        "urteil": "Der Alltagskandidat: 31-mal schneller als das nächstbeste Modell "
                  "und für Zehntelcent zu haben. Findet die Standardeinwände "
                  "zuverlässig, den versteckten Mechanismus nicht.",
        "einschraenkung": "Antwortet knapp - was Zeit spart und Tiefe kostet.",
    },
    {
        "kennung": "gemma4:26b-a4b-it-qat",
        "ort": "lokal", "rang": 5, "sekunden": 66, "kern": 4, "standard": 3,
        "ct_je_frage": 0.0,
        "note": "2-", "note_grund": "War der beste lokale Kritiker, solange qwen3.8:27b auf der 12-GB-Karte unbrauchbar war. Auf der RTX PRO 4500 findet qwen3.8 mehr und ist kaum langsamer.",
        "beispiel": "Wenn die Ersparnis von +7.861 € (was bei deiner Trade-Anzahl nur ca. 1,15 € pro Trade entspricht!) geringer ist als Spread und Slippage, ist dein Gewinn rein fiktiv.",
        "urteil": "Der beste lokale Kritiker - und der Beleg, dass MoE hält, was es "
                  "verspricht: dieselbe Trefferzahl wie das 27B-Modell in einem "
                  "Fünftel der Zeit, weil je Token nur 4 der 26 Mrd. Parameter "
                  "rechnen. Bei den schwachen Jahren die schärfste Antwort im ganzen "
                  "Feld („mathematisches Artefakt der Kostenstruktur, kein Alpha“) "
                  "mit fünf konkreten Prüfverfahren.",
        "einschraenkung": "Den Kernfehler der Zellen-Rechnung fand es nicht. Es rechnete "
                          "aber - wie qwen3.6 - von selbst auf Ertrag je Trade um, und "
                          "genau dort lag der Denkfehler.",
    },
    {
        # NACHGETRAGEN 12.08.2026 auf die Frage „gibt es kostenlose Anthropic- und
        # ChatGPT-Modelle fuer lokal?". Die Antwort in einem Satz: Von Anthropic
        # gibt es KEINE offenen Gewichte, von OpenAI genau zwei (gpt-oss:20b und
        # :120b, Apache 2.0). Das kleinere liegt auf diesem Rechner - und war in
        # der Messung das schwaechste Modell im ganzen Feld.
        "kennung": "gpt-oss:20b",
        "ort": "lokal", "rang": None, "sekunden": 46, "kern": 1, "standard": 2,
        "ct_je_frage": 0.0,
        "note": "5", "note_grund": "Erfindet Quellen mitsamt praeziser Zahlen und verrechnet sich um Faktor 500. Schnell und unbrauchbar.",
        "beispiel": "Kandasamy, Shukla & Ranjan (2018), „Liquidity-driven trading strategies in the LOB“: positiver net-alpha von ca. 0,5 Basispunkten pro Trade.",
        "urteil": "Die einzigen offenen OpenAI-Gewichte seit GPT-2 und mit "
                  "34,9 Token/s das zweitschnellste lokale Modell - inhaltlich "
                  "aber das schwaechste im Feld. Bei der Frage nach Belegen für "
                  "Orderbuch-Handel nannte es eine Arbeit mit Autoren, Jahr und "
                  "einer praezisen Zahl („0,5 Basispunkte net-alpha“), die es "
                  "nicht gibt. Bei der Stichprobenrechnung gab die eigene Formel "
                  "rund 71 BEOBACHTUNGEN, ausgegeben wurden „35-45 HANDELSTAGE“ - "
                  "bei 100-ms-Schnappschuessen sind das 36.000 Beobachtungen je "
                  "Tag, also Faktor 500 daneben. Nemotrons Herleitung derselben "
                  "Zahl liess sich dagegen Schritt für Schritt nachrechnen.",
        "einschraenkung": "Fiel bei der schwersten der vier Strategiefragen nach "
                          "zwei Versuchen ganz aus (leere Antwort). Markiert zwar "
                          "fleissig „UNSICHER“ - aber eben auch dort, wo es sich "
                          "sicher sein könnte, was die Markierung wertlos macht.",
    },
    {
        "kennung": "moonshotai/kimi-k3",
        "ort": "online", "rang": 4, "sekunden": 221, "kern": 5, "standard": 4,
        "ct_je_frage": 0.93,
        "note": "2", "note_grund": "Beste Trefferzahl im Feld und die erste eigenständige Signifikanz-Rechnung - dafür 74 s und knapp ein Cent je Frage.",
        "beispiel": "-7.861 € / 1.170 Trades = -6,7 € pro Trade. Bei typischer ORB-Streuung läge t grob bei ~1,5 - statistisch nichts.",
        "urteil": "Das statistisch schärfste Modell im Feld: Es rechnete den t-Wert "
                  "der Zellen-Rechnung selbst überschlägig aus und kam auf ~1,5 - "
                  "also Rauschen. Dazu der Hinweis auf Clustering (Trades sind "
                  "wegen Tageslimit und Regime-Blöcken nicht unabhängig, n_eff ist "
                  "kleiner als n) und die Frage, ob die Phasen-Definition "
                  "Look-ahead enthält.",
        "einschraenkung": "Den Nachrück-Mechanismus fand es nicht. Und mit 74 s je "
                          "Frage plus ~1 ct ist es für eine schnelle Gegenprobe zu träge.",
    },
    {
        "kennung": "qwen/qwen3.8-max",
        "ort": "online", "rang": 8, "sekunden": 208, "kern": 4, "standard": 4,
        "ct_je_frage": 0.4,
        "note": "1-", "note_grund": "Die sauberste Antwort auf den Prüfstein im ganzen Feld - fand den versteckten Mechanismus beim ersten Versuch und benannte ihn präziser als nemotron.",
        "beispiel": "Durch das Tageslimit von max. 4 Trades sind die Trades nicht unabhängig. Die Rechnung nimmt implizit an: „Alle anderen Trades bleiben exakt gleich.“ Das ist bei einem Tageslimit nicht automatisch wahr.",
        "urteil": "Das zweite Modell, das den Kernfehler wirklich fand - und es "
                  "formulierte ihn klarer als nemotron: nicht nur „Trades rücken "
                  "nach“, sondern die versteckte Annahme dahinter („alle anderen "
                  "Trades bleiben gleich“). Beim ersten Versuch, ohne Wiederholung.",
        "einschraenkung": "69 s je Frage und 0,4 ct - für eine schnelle Gegenprobe zu "
                          "träge. ERST NACH RÜCKFRAGE richtig bewertet: Die "
                          "Stichwortsuche zählte 4/6 wie beim viel schwächeren "
                          "qwen3.5:9b, weil beide das Wort „Tageslimit“ enthalten. "
                          "Nur eines hat den Gedanken.",
    },
    {
        "kennung": "deepseek/deepseek-v4-flash",
        "ort": "online", "rang": 9, "sekunden": 33, "kern": 3, "standard": 3,
        "ct_je_frage": 0.02,
        "note": "2-", "note_grund": "Inhaltlich nur Mittelmaß, aber 11 s je Frage für zwei Hundertstel Cent - das beste Verhältnis im ganzen Feld.",
        "beispiel": "Selektionseffekt: Anzahl Trades je Phase stark ungleich (2.241 vs. 1.170) - deutet auf implizite Filterung, die nicht erklärt wird.",
        "urteil": "Der Schnellschuss-Kandidat: 11 Sekunden je Frage, zwei "
                  "Hundertstel Cent, und trotzdem drei der sechs versteckten "
                  "Punkte. Für die Frage „übersehe ich gerade etwas Offensichtliches?“ "
                  "gibt es nichts Besseres - das ganze Dreifragen-Set kostete 0,08 ct.",
        "einschraenkung": "Beim Prüfstein 0/2: nur Lehrbuch-Einwände, kein eigener "
                          "Gedanke. Für die schwere Frage taugt es nicht.",
    },
    {
        "kennung": "x-ai/grok-4.6",
        "ort": "online", "rang": 1, "sekunden": 113, "kern": 5, "standard": 5,
        "ct_je_frage": 0.30,
        "note": "1-", "note_grund": "Findet 5 der 6 versteckten Kernpunkte - mehr als jedes andere gemessene Modell, lokal wie online.",
        "beispiel": "Sie unterstellt Additivität (neues PnL = altes PnL − (−7861)). Das gilt bei Tageslimit nicht.",
        "urteil": "Das beste Ergebnis im ganzen Feld (gemessen 13.08.2026, 1,5 Bio. "
                  "Parameter, API-only). Benannte als einziges Modell die "
                  "Additivitäts-Annahme der Zellen-Rechnung UND die "
                  "In-Sample-Selektion - und bei den schwachen Jahren die "
                  "Kosten-Skalierung vollständig.",
        "einschraenkung": "Langsamster der beiden Neuzugänge (113 s) und keine offenen "
                          "Gewichte - läuft nur über die API, nie lokal. Der "
                          "Kostenwert ist aus dem Listenpreis GERECHNET, nicht "
                          "wie bei den übrigen Zeilen abgerechnet gemessen.",
    },
    {
        "kennung": "deepseek/deepseek-v4-pro",
        "ort": "online", "rang": None, "sekunden": 65, "kern": 2, "standard": 5,
        "ct_je_frage": 0.22,
        "note": "3-", "note_grund": "Schnell und billig, findet aber nur 2 der 6 Kernpunkte - bei der Zellen-Rechnung und den schwachen Jahren gar keinen.",
        "beispiel": "(Zellen-Rechnung: nur die Lehrbuch-Einwände, kein Wort zum Tageslimit)",
        "urteil": "Der Preis-Leistungs-Kandidat, der die Leistung nicht bringt "
                  "(gemessen 13.08.2026, 1,6 Bio. Parameter MoE, 49 Mrd. aktiv). "
                  "Beim dritten Fragenblock voll da (2/2), bei den ersten beiden "
                  "null Kernpunkte. Die Architektur ist beeindruckend, die "
                  "Sparring-Qualität nicht.",
        "einschraenkung": "MIT-lizenzierte Gewichte gibt es nur für den April-Preview, "
                          "nicht für diesen 0813-Stand - und 1,6 Bio. Parameter laufen "
                          "ohnehin auf keiner Einzelkarte. Der Kostenwert ist aus dem "
                          "Listenpreis (0,435/0,87 $ je Mio. Token) GERECHNET, nicht "
                          "abgerechnet gemessen.",
    },
    {
        # Vier Modelle am 24.08.2026 dazugekauft und mit denselben drei Pruefsteinen
        # gemessen (werkzeug/sparring_neue4.md). Zwei Fragen sollten sie beantworten:
        # Schlaegt mehr Groesse die feinere Quantisierung? Und bringt Q8 gegenueber
        # Q4 etwas? Beide Antworten stehen unten - beide lauten nein.
        "kennung": "qwen3.6:35b-a3b-q4_K_M",
        "ort": "lokal", "rang": None, "sekunden": 145, "kern": 5, "standard": 2,
        "ct_je_frage": 0.0,
        "note": "4", "note_grund": "Hoechste Trefferzahl aller lokalen Modelle (5/6) - und trotzdem schwach: Die Treffer sind gestreute Stichworte, der Mechanismus fehlt.",
        "beispiel": "Der staerkste Einwand betrifft die Ignorierung der Opportunitaetskosten ... aber noch gravierender: die Verzerrung durch Look-Ahead-Bias ... Aber der klassische ORB-Fehler ist: Survivorship Bias",
        "urteil": "DER BELEG DAFUER, DASS DIE TREFFERZAHL NICHTS TAUGT. Fünf von sechs "
                  "Kernpunkten - mehr als jedes andere lokale Modell - und beim Lesen "
                  "bleibt nichts übrig: Die Antwort springt zwischen fünf "
                  "„staerksten Einwaenden“ hin und her, nennt Look-Ahead-Bias, "
                  "Survivorship Bias, Mark-to-Market und Opportunitaetskosten - und das "
                  "Tageslimit, um das es geht, kein einziges Mal. Dazu erfundene "
                  "Dateinamen (backtest_engine.py, pnl_calculator.py) mit dem Zusatz "
                  "„Zeilennummer: [Unbekannt]“. Mit 105,2 Token/s allerdings sehr schnell.",
        "einschraenkung": "Wer nur auf die Trefferspalte sieht, hält dieses Modell für "
                          "das beste lokale. Genau deshalb steht in dieser Datei, dass das "
                          "Urteil aus dem gelesenen Text kommt und nicht aus der Zahl.",
    },
    {
        "kennung": "qwen3.8:27b-q8_0",
        "ort": "lokal", "rang": None, "sekunden": 257, "kern": 4, "standard": 3,
        "ct_je_frage": 0.0,
        "note": "3", "note_grund": "Dasselbe Modell wie qwen3.8:27b, nur genauer quantisiert. Inhaltlich gleichwertig, aber doppelter Speicher und ein Drittel weniger Tempo - ob Q8 inhaltlich mehr kann, ist mit einem Lauf nicht messbar.",
        "beispiel": "Wenn das System ein globales Tageslimit von 4 Trades hat, und du sperrst Longs in Abwaertsphasen, dann sind an Abwaertstagen ploetzlich mehr Slots frei für Short-Trades.",
        "urteil": "DER Q4/Q8-VERGLEICH IST NICHT ENTSCHIEDEN - und das ist die "
                  "ehrlichere Auskunft als die Zahl. Belegt ist nur die Kostenseite: "
                  "dieselben 27,3 Mrd. Parameter, dieselbe Architektur, derselbe "
                  "Kontext (262.144) - aber 30,1 statt 17,5 GB Speicher und 26,2 statt "
                  "38,5 Token/s. Inhaltlich war die Antwort gleichwertig: Q8 fand "
                  "denselben Mechanismus, mit durchgespieltem Signalablauf. Die "
                  "Trefferzahl lag bei 4/6 gegen 5/6 - dieser eine Punkt ist jedoch "
                  "KEINE Aussage über die Quantisierung: Der Pruefstein läuft mit "
                  "temperature 0,5 ohne festen Seed, und dieselbe Q4-Fassung lieferte "
                  "an einem Tag einmal 4/6 und einmal 5/6. Der Unterschied liegt in "
                  "der Streuung des Verfahrens, nicht zwischen den Fassungen.",
        "einschraenkung": "WER DEN VERGLEICH SAUBER WILL, braucht temperature 0 "
                          "oder mehrere Laeufe je Fassung. Mit je einem Lauf bei "
                          "temperature 0,5 ist ein Unterschied von einem Trefferpunkt "
                          "nicht aufloesbar - das Verfahren streut staerker als der "
                          "gemessene Abstand. Bis dahin gilt nur: Q8 kostet doppelten "
                          "Speicher und ein Drittel Tempo.",
    },
    {
        "kennung": "nemotron-3.5-lightning:30b-a3b-q4_K_M",
        "ort": "lokal", "rang": None, "sekunden": 113, "kern": 2, "standard": 3,
        "ct_je_frage": 0.0,
        "note": "3", "note_grund": "Findet den Mechanismus mit durchgerechnetem Szenario - und stellt daneben eine Rechnung mit falschem Vorzeichen auf. 38 s je Frage.",
        "beispiel": "In einer Abwaertsphase wäre die Wahrscheinlichkeit hoch, dass die gesperrten Long-Positionen durch Short-Positionen ersetzt werden wuerden - das Sperren wuerde dazu führen, dass die Short-Strategie noch häufiger zum Einsatz kommt.",
        "urteil": "Das lokale Gegenstueck zu nemotron-3-ultra, das online auf Rang 6 "
                  "steht. Es findet den Nachrueck-Mechanismus und rechnet ihn in einem "
                  "Szenario durch. Mit 67,2 Token/s und 38 s je Frage ist es zudem das "
                  "schnellste der großen lokalen Modelle.",
        "einschraenkung": "Direkt daneben steht ein grober Denkfehler: Der Wegfall der "
                          "-7.861 EUR sei „ein Verlust von 7.861 EUR“, der als "
                          "Opportunitaetskosten zu werten sei. Das ist das Vorzeichen "
                          "verdreht. Ein Modell, das den richtigen Mechanismus neben eine "
                          "falsche Rechnung stellt, braucht einen Leser, der beides trennt.",
    },
    {
        "kennung": "nemotron:70b-instruct-q2_K",
        "ort": "lokal", "rang": None, "sekunden": 133, "kern": 1, "standard": 2,
        "ct_je_frage": 0.0,
        "note": "5", "note_grund": "70 Mrd. Parameter in Q2 - und das schwaechste Ergebnis im lokalen Feld. Grobe Quantisierung kostet mehr, als die Parameter einbringen.",
        "beispiel": "Vereinfachung der Marktphasen und Richtungen: Die Aufteilung in nur zwei Marktphasen ueberspitzt die Komplexität des Marktes.",
        "urteil": "DIE ANTWORT AUF DIE FRAGE, OB EIN GROSSES MODELL GROB QUANTISIERT "
                  "BESSER IST ALS EIN KLEINERES FEIN: nein. Mit 26,4 GB passt das 70B in "
                  "Q2 auf die Karte - aber es liefert nur Lehrbuchfloskeln "
                  "mit Lehrbuchfloskeln zur Vereinfachung der Marktphasen und zur "
                  "fehlenden Kontrolle für Ueberfitting, dazu ein COVID-Beispiel - "
                  "und nennt das Tageslimit "
                  "kein einziges Mal. Das 30B-Modell derselben Familie in Q4 findet den "
                  "Mechanismus - bei 3 Mrd. aktiven Parametern und halbem Speicherbedarf.",
        "einschraenkung": "Laedt ueberhaupt nur mit OLLAMA_FLASH_ATTENTION=1 und "
                          "OLLAMA_KV_CACHE_TYPE=q8_0; mit den Ollama-Vorgaben scheitert es "
                          "am KV-Cache (HTTP 500). Mit 23,7 Token/s zudem das langsamste "
                          "Modell im Feld.",
    },
    {
        # Erstmals gemessen am 24.08.2026 auf der RTX PRO 4500. Auf der 3060 gab
        # es KEINE Zeile: Das Modell lagerte 9,1 GB in den Hauptspeicher aus, kam
        # auf rund ein Zeichen je Sekunde und lief in den Timeout, statt eine
        # Note zu liefern. Antworten im Wortlaut: werkzeug/sparring_lokal_4500.md
        "kennung": "qwen3.8:27b",
        "ort": "lokal", "rang": 2, "sekunden": 150, "kern": 5, "standard": 3,
        "ct_je_frage": 0.0,
        "note": "1-", "note_grund": "Findet 5 der 6 Kernpunkte - so viele wie die besten Online-Modelle -, braucht 50 s je Frage und kostet nichts. Das beste lokale Modell, das hier je gemessen wurde.",
        "beispiel": "Deine Rechnung ignoriert, dass das Tageslimit eine knappe Ressource ist. Die -7861 EUR sind nicht isoliert zu betrachten, sondern als Opportunitätskosten für die Nutzung des Limits.",
        "urteil": "Kein lokales Modell hatte den Kernfehler der Zellen-Rechnung je "
                  "gefunden - gemma4 nicht, qwen3.6 nicht, gpt-oss nicht. Dieses schon, "
                  "und mit durchgerechnetem Gegenbeispiel: vier Trades ohne Sperre "
                  "+1.100 EUR, mit Sperre +900 EUR, weil der frei gewordene Platz mit "
                  "einem schlechteren Signal gefüllt wird. Damit landet der Punkt, für "
                  "den es bisher ein Online-Modell brauchte, auf der eigenen Karte - "
                  "ohne Cent und ohne dass eine Frage das Haus verlässt.",
        "einschraenkung": "Weitschweifig: 14.495 Zeichen für drei Fragen, mit Passagen, "
                          "die über die Zahlen hinausraten („statistisch wahrscheinlich, "
                          "dass diese zusätzlichen Trades ebenfalls Verluste machen“). "
                          "Und es ist EIN Lauf - siehe nemotron, bei dem sich derselbe "
                          "Treffer im zweiten Durchgang nicht wiederholte.",
    },
    {
        "kennung": "google/gemini-2.5-pro",
        "ort": "online", "rang": None, "sekunden": 186, "kern": 4, "standard": 4,
        "ct_je_frage": 0.60,
        "note": "5", "note_grund": "Ein Totalausfall unter drei Fragen disqualifiziert - dazu dreimal teurer und elfmal langsamer als das eigene Nachfolgemodell.",
        "beispiel": "(leere Antwort nach 144 Sekunden Rechenzeit)",
        "urteil": "Von der eigenen Hausmarke überholt: dieselbe Trefferzahl wie "
                  "gemini-3-flash, aber elfmal langsamer und dreimal teurer.",
        "einschraenkung": "EIN TOTALAUSFALL: 144 Sekunden gerechnet, dann eine leere "
                          "Antwort zurückgegeben.",
    },
    {
        "kennung": "qwen/qwen-plus",
        "ort": "online", "rang": None, "sekunden": 25, "kern": 2, "standard": 4,
        "ct_je_frage": 0.05,
        "note": "5", "note_grund": "Nennt zuverlässig die Lehrbuch-Einwände und keinen der beiden versteckten Punkte.",
        "beispiel": "Overfitting-Gefahr: Die Aufteilung nach Marktphase ist eine nachträgliche Segmentierung.",
        "urteil": "Schnell und höflich - nennt die Lehrbucheinwände und keinen der "
                  "beiden versteckten Punkte.",
        "einschraenkung": "",
    },
)

#: HERAUSGELOEST (31.08.2026): Die Erkenntnis-Texte stehen jetzt in
#: ``befunde.py`` - diese Datei war mit 646 Zeilen weit ueber der
#: Projektgrenze. Weitergereicht, damit ``ki/__init__.py`` und jeder
#: andere Aufrufer unveraendert bleiben.
from .befunde import BEFUNDE      # noqa: F401 - oeffentlicher Name dieser Datei


class Bestenliste:
    """Die Messungen, angereichert um Katalogdaten (Parameter, Kontext, Platte).

    Die Verbindung laeuft ueber die Modellkennung. Findet sich zu einer Messung
    kein Katalogeintrag - etwa bei lokalen Modellen, die es online nicht gibt -,
    bleiben die Katalogfelder leer statt geraten zu werden.
    """

    def __init__(self, katalog):
        self.katalog = katalog

    def _katalogdaten(self, kennung):
        """Parameter/Kontext/Platte zu einer Kennung - aus Online- ODER Ollama-Liste."""
        for z in self.katalog.online_roh():
            if z["id"] == kennung:
                gefunden = self.katalog._zeile(z)
                # Dictionary gewollt: geht als JSON an hilfe_ki_modelle.html, offscreen_compiled.js, architektur_gpu.html (5 von 5 Schlüsseln stehen dort wörtlich, geprüft mit Skills2 → Anzeigeformat).
                return {"param_gesamt": gefunden["param_gesamt"],
                        "param_aktiv": gefunden["param_aktiv"],
                        "kontext": gefunden["kontext"],
                        "gb": gefunden["gb"], "gb_geschaetzt": True}
        for z in self.katalog.lokal():
            if z["kennung"] == kennung:
                # ECHTER Plattenplatz, keine Schaetzung - deshalb ``gb_geschaetzt``
                # aus, und die Anzeige laesst das ``~`` weg.
                # Dictionary gewollt: geht als JSON an hilfe_ki_modelle.html, offscreen_compiled.js, architektur_gpu.html (5 von 5 Schlüsseln stehen dort wörtlich, geprüft mit Skills2 → Anzeigeformat).
                return {"param_gesamt": z["param_gesamt"], "param_aktiv": z["param_aktiv"],
                        "kontext": z.get("kontext"), "gb": z["gb"],
                        # WELCHE Fassung genau (01.09.2026): Am Namen
                        # ``qwen3.8:27b`` ist nicht zu sehen, dass es
                        # Q4_K_M ist - am Tempo dafuer sehr.
                        "quant": z.get("quant") or "",
                        "familie": z.get("familie") or "",
                        "experten": z.get("experten"),
                        "gb_geschaetzt": False}
        ges, aktiv = Modellname.parameter(kennung)
        # Dictionary gewollt: geht als JSON an hilfe_ki_modelle.html, offscreen_compiled.js, architektur_gpu.html (5 von 5 Schlüsseln stehen dort wörtlich, geprüft mit Skills2 → Anzeigeformat).
        return {"param_gesamt": ges, "param_aktiv": aktiv, "kontext": None,
                "gb": None, "gb_geschaetzt": False}

    def zeilen(self, nur_empfohlen=False):
        """Die Messungen als Anzeigezeilen - Empfohlene zuerst, dann nach Treffern."""
        aus = []
        for m in MESSUNGEN:
            if nur_empfohlen and not m["rang"]:
                continue
            zeile = dict(m)
            zeile.update(self._katalogdaten(m["kennung"]))
            zeile["kern_moeglich"] = 6
            zeile["standard_moeglich"] = 6
            # WIE LANGE DAUERT EINE FRAGE? Die gemessene Zeit gilt fuer alle drei
            # Fragen zusammen; geteilt durch drei ist sie die Zahl, nach der man
            # im Alltag entscheidet, ob man dieses Modell ueberhaupt fragt.
            zeile["sek_je_frage"] = round(m["sekunden"] / 3.0)
            # GRAFIKSPEICHER - nur fuer lokale Modelle, und nur gemessen.
            v = VRAM.get(m["kennung"])
            zeile["vram_gesamt"], zeile["vram_gpu"], zeile["vram_ram"] = v if v else (None, None, None)
            # Die Zahl, die im Alltag zaehlt: Passt es ganz auf die Karte?
            zeile["ganz_auf_gpu"] = bool(v) and v[2] <= 0.05
            # DURCHSATZ - zwei getrennte Quellen, weil es zwei verschiedene
            # Groessen sind (siehe TOKEN_JE_S_ONLINE): lokal die reine
            # Erzeugungszeit der eigenen Karte, online die Rate ab dem ersten
            # Token beim Anbieter. ``token_quelle`` sagt der Seite, welche der
            # beiden sie vor sich hat - eine Spalte, die beide als dieselbe
            # Zahl zeigt, vergleicht Ungleiches.
            zeile["token_je_s"] = TOKEN_JE_S.get(m["kennung"])
            zeile["token_quelle"] = "lokal" if zeile["token_je_s"] else ""
            zeile["token_spanne"] = None
            if not zeile["token_je_s"]:
                online = TOKEN_JE_S_ONLINE.get(m["kennung"])
                if online:
                    zeile["token_je_s"], zeile["token_spanne"] = online
                    zeile["token_quelle"] = "online"
            # LETZTER LAUF - ERST HIER, NACH BEIDEN QUELLEN (Befund
            # 01.09.2026): Stand die Zuweisung vorher, blieb ``tempo_stand``
            # bei jedem ONLINE-Modell leer, und die Spalte zeigte den alten
            # Sparring-Tag - obwohl am selben Tag gemessen worden war.
            zeile["sparring_stand"] = SPARRING_STAND.get(m["kennung"], "")
            zeile["tempo_stand"] = TOKEN_STAND if zeile["token_je_s"] else ""
            zeile["letzter_lauf"] = max(zeile["sparring_stand"],
                                        zeile["tempo_stand"]) or ""
            # Deutsch fuer die Anzeige, ISO zum Sortieren - sonst stuende der
            # 11.08. hinter dem 01.09.
            zeile["letzter_lauf_de"] = self._de_datum(zeile["letzter_lauf"])
            zeile["sparring_stand_de"] = self._de_datum(zeile["sparring_stand"])
            zeile["tempo_stand_de"] = self._de_datum(zeile["tempo_stand"])
            aus.append(zeile)
        aus.sort(key=lambda z: (z["rang"] or 99, -z["kern"], z["sekunden"]))
        return aus

    @staticmethod
    def _de_datum(iso):
        u"""``2026-09-01`` -> ``01.09.2026``. Leer bleibt leer.

        Die Oberflaeche ist deutsch; ein ISO-Datum in der Zelle ist eine
        Maschinenschreibweise. Sortiert wird weiter nach ISO - die Zelle
        traegt es in ``data-sort``."""
        if not iso or len(iso) != 10:
            return ""
        jahr, monat, tag = iso.split("-")
        return "%s.%s.%s" % (tag, monat, jahr)
