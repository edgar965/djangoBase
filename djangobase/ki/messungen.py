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

#: DURCHSATZ je lokalem Modell: Token je Sekunde beim Erzeugen der Antwort, aus
#: den Zaehlern des Ollama-Antwort-JSON. Gemessen mit ``werkzeug/gpu_nutzen.py``.
#:
#: STAND 24.08.2026 - RTX PRO 4500 BLACKWELL (32 GB), Mittel aus ZWEI Durchgaengen,
#: alle Modelle vollstaendig im Grafikspeicher, Streuung 1-13 %.
#:
#: DIESE ZAHLEN SIND DIE ERSTEN BELASTBAREN. Alle frueheren - auch die der 3060 -
#: entstanden mit einem Skript, das die Modelle nach der Messung NICHT entlud.
#: Ollama haelt ein benutztes Modell fuenf Minuten geladen; bei sieben Modellen
#: hintereinander lagen drei gleichzeitig auf der Karte, und das zuletzt gemessene
#: bekam den Rest. gpt-oss:20b hatte dabei 1,1 statt 13,6 GB und kam auf 3,1
#: Token/s - sauber gemessen sind es 140,3, also Faktor 45. Wer alte Zahlen dieser
#: Seite mit neuen vergleicht, vergleicht zwei verschiedene Messfehler.
#:
#: WAS DIE ZAHLEN ZEIGEN:
#: 1. MoE SCHLAEGT DICHT, und zwar deutlich: gemma4 (26 Mrd. gesamt, 4 aktiv)
#:    127,8 Token/s gegen qwen3.8:27b (dicht) 38,5 - Faktor 3,3 bei fast gleicher
#:    Modellgroesse. qwen3.6:35b-a3b (35 Mrd., 3 aktiv) liegt mit 105,2 ebenfalls
#:    weit vorn. Fuer das Tempo zaehlt die AKTIVE Parameterzahl, fuer den Speicher
#:    die gesamte.
#: 2. QUANTISIERUNG KOSTET TEMPO UND SPEICHER: dasselbe Modell qwen3.8:27b
#:    liefert in Q4 38,5 und in Q8 26,2 Token/s bei 17,5 gegen 30,1 GB. Ob Q8
#:    dafuer inhaltlich mehr kann, ist NICHT gemessen: Der Pruefstein laeuft mit
#:    temperature 0,5 ohne Seed, und dieselbe Fassung streut zwischen zwei
#:    Laeufen um denselben Betrag wie die beiden Fassungen untereinander.
#: 3. EIN 70B PASST, IN Q2: nemotron:70b-instruct-q2_K belegt 26,4 GB und laeuft
#:    mit 23,7 Token/s. Es laedt allerdings nur mit OLLAMA_FLASH_ATTENTION=1 und
#:    OLLAMA_KV_CACHE_TYPE=q8_0; mit den Vorgaben scheitert es am KV-Cache.
TOKEN_JE_S = {
    "gpt-oss:20b":                          140.3,
    "gemma4:26b-a4b-it-qat":                127.8,
    "qwen3.6:35b-a3b-q4_K_M":               105.2,
    "nemotron-3.5-lightning:30b-a3b-q4_K_M": 67.2,
    "qwen3.8:27b":                           38.5,
    "qwen3.8:27b-q8_0":                      26.2,
    "nemotron:70b-instruct-q2_K":            23.7,
}

#: DIESELBE MESSUNG AUF DER ALTEN KARTE (RTX 3060, 12 GB; 12.08.2026).
TOKEN_JE_S_3060 = {
    "qwen3.5:9b":            48.7,
    "gpt-oss:20b":           34.9,
    "gemma4:26b-a4b-it-qat": 26.5,
    "qwen3.6:27b":            3.1,
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
        "kennung": "qwen3.6:27b",
        "ort": "lokal", "rang": None, "sekunden": 737, "kern": 5, "standard": 5,
        "ct_je_frage": 0.0,
        # AM 18.08.2026 GELOESCHT (Ansage Edgar) - der Nachfolger qwen3.8:27b
        # liegt seither auf der Platte. Die Messung bleibt stehen: Sie ist
        # gemessen und begruendet die MoE-Lehre weiter oben. In der Tabelle
        # „lokal" taucht das Modell nicht mehr auf, die kommt aus ``ollama list``.
        "geloescht": "18.08.2026, ersetzt durch qwen3.8:27b",
        "note": "4", "note_grund": "Inhaltlich stark, praktisch unbrauchbar: vier Minuten je Frage, weil 7,3 GB im Hauptspeicher liegen. Am 18.08.2026 geloescht - Nachfolger qwen3.8:27b braucht mit 9,1 GB Auslagerung noch mehr.",
        "beispiel": "Long/Down: ~-6,7 EUR/Trade. Die Reduktion der Long/Down-Trades hat marginalen Einfluss auf das Gesamtkapital.",
        "urteil": "Sachlich stark - beste Antwort zu den schwachen Jahren inklusive "
                  "richtiger Gegenprobe, und es rechnete ungefragt aus, dass "
                  "Long/Abwärts nur 6,70 € je Trade kostet. Von gemma4 trotzdem "
                  "verdrängt: gleiche Trefferzahl, fünffache Wartezeit.",
        "einschraenkung": "12 Minuten für drei Fragen (11 Zeichen/s): 17 GB Modell auf "
                          "12 GB Grafikspeicher. Dazu zwei Sachfehler - 2020-2026 als "
                          "Phase „extrem niedriger Volatilität“ und der März 2020 als "
                          "„historisches Low“.",
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
                  "aber das schwaechste im Feld. Bei der Frage nach Belegen fuer "
                  "Orderbuch-Handel nannte es eine Arbeit mit Autoren, Jahr und "
                  "einer praezisen Zahl („0,5 Basispunkte net-alpha“), die es "
                  "nicht gibt. Bei der Stichprobenrechnung gab die eigene Formel "
                  "rund 71 BEOBACHTUNGEN, ausgegeben wurden „35-45 HANDELSTAGE“ - "
                  "bei 100-ms-Schnappschuessen sind das 36.000 Beobachtungen je "
                  "Tag, also Faktor 500 daneben. Nemotrons Herleitung derselben "
                  "Zahl liess sich dagegen Schritt fuer Schritt nachrechnen.",
        "einschraenkung": "Fiel bei der schwersten der vier Strategiefragen nach "
                          "zwei Versuchen ganz aus (leere Antwort). Markiert zwar "
                          "fleissig „UNSICHER“ - aber eben auch dort, wo es sich "
                          "sicher sein koennte, was die Markierung wertlos macht.",
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
        "urteil": "DER BELEG DAFUER, DASS DIE TREFFERZAHL NICHTS TAUGT. Fuenf von sechs "
                  "Kernpunkten - mehr als jedes andere lokale Modell - und beim Lesen "
                  "bleibt nichts uebrig: Die Antwort springt zwischen fuenf "
                  "„staerksten Einwaenden“ hin und her, nennt Look-Ahead-Bias, "
                  "Survivorship Bias, Mark-to-Market und Opportunitaetskosten - und das "
                  "Tageslimit, um das es geht, kein einziges Mal. Dazu erfundene "
                  "Dateinamen (backtest_engine.py, pnl_calculator.py) mit dem Zusatz "
                  "„Zeilennummer: [Unbekannt]“. Mit 105,2 Token/s allerdings sehr schnell.",
        "einschraenkung": "Wer nur auf die Trefferspalte sieht, haelt dieses Modell fuer "
                          "das beste lokale. Genau deshalb steht in dieser Datei, dass das "
                          "Urteil aus dem gelesenen Text kommt und nicht aus der Zahl.",
    },
    {
        "kennung": "qwen3.8:27b-q8_0",
        "ort": "lokal", "rang": None, "sekunden": 257, "kern": 4, "standard": 3,
        "ct_je_frage": 0.0,
        "note": "3", "note_grund": "Dasselbe Modell wie qwen3.8:27b, nur genauer quantisiert. Inhaltlich gleichwertig, aber doppelter Speicher und ein Drittel weniger Tempo - ob Q8 inhaltlich mehr kann, ist mit einem Lauf nicht messbar.",
        "beispiel": "Wenn das System ein globales Tageslimit von 4 Trades hat, und du sperrst Longs in Abwaertsphasen, dann sind an Abwaertstagen ploetzlich mehr Slots frei fuer Short-Trades.",
        "urteil": "DER Q4/Q8-VERGLEICH IST NICHT ENTSCHIEDEN - und das ist die "
                  "ehrlichere Auskunft als die Zahl. Belegt ist nur die Kostenseite: "
                  "dieselben 27,3 Mrd. Parameter, dieselbe Architektur, derselbe "
                  "Kontext (262.144) - aber 30,1 statt 17,5 GB Speicher und 26,2 statt "
                  "38,5 Token/s. Inhaltlich war die Antwort gleichwertig: Q8 fand "
                  "denselben Mechanismus, mit durchgespieltem Signalablauf. Die "
                  "Trefferzahl lag bei 4/6 gegen 5/6 - dieser eine Punkt ist jedoch "
                  "KEINE Aussage ueber die Quantisierung: Der Pruefstein laeuft mit "
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
        "beispiel": "In einer Abwaertsphase waere die Wahrscheinlichkeit hoch, dass die gesperrten Long-Positionen durch Short-Positionen ersetzt werden wuerden - das Sperren wuerde dazu fuehren, dass die Short-Strategie noch haeufiger zum Einsatz kommt.",
        "urteil": "Das lokale Gegenstueck zu nemotron-3-ultra, das online auf Rang 6 "
                  "steht. Es findet den Nachrueck-Mechanismus und rechnet ihn in einem "
                  "Szenario durch. Mit 67,2 Token/s und 38 s je Frage ist es zudem das "
                  "schnellste der grossen lokalen Modelle.",
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
        "beispiel": "Vereinfachung der Marktphasen und Richtungen: Die Aufteilung in nur zwei Marktphasen ueberspitzt die Komplexitaet des Marktes.",
        "urteil": "DIE ANTWORT AUF DIE FRAGE, OB EIN GROSSES MODELL GROB QUANTISIERT "
                  "BESSER IST ALS EIN KLEINERES FEIN: nein. Mit 26,4 GB passt das 70B in "
                  "Q2 auf die Karte - aber es liefert nur Lehrbuchfloskeln "
                  "mit Lehrbuchfloskeln zur Vereinfachung der Marktphasen und zur "
                  "fehlenden Kontrolle fuer Ueberfitting, dazu ein COVID-Beispiel - "
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
        "kennung": "qwen3.5:9b",
        "ort": "lokal (gelöscht)", "rang": None, "sekunden": 1523, "kern": 4, "standard": 3,
        "ct_je_frage": 0.0,
        "note": "5", "note_grund": "War auf der 3060 das schnellste lokale Modell (55 s); auf der RTX PRO 4500 mit 32k Kontext 1.523 s - Faktor 28 langsamer. Am 24.08.2026 gelöscht.",
        "beispiel": "Selektionsbias durch Tageslimit (4 Trades/Tag): Mit einem harten Limit wird dein Ergebnis massiv verzerrt.",
        "urteil": "Der beste Kompromiss lokal: passt in den Grafikspeicher, knapp eine "
                  "Minute, brauchbare Einwände. Nannte das Tageslimit als einziges "
                  "lokales Modell überhaupt.",
        "einschraenkung": "DIE ZAHLEN OBEN SIND DIE LETZTE MESSUNG (24.08.2026, RTX PRO "
                          "4500). Sie widersprechen der Durchsatzmessung desselben Tages, "
                          "die für dieses Modell mit 68,6 Token/s die HÖCHSTE Rate im Feld "
                          "ergab - gemessen allerdings mit Standard-Kontext, während das "
                          "Sparring mit 32k läuft. Dazu passt, dass es 15,3 GB belegte, "
                          "obwohl das Modell nur 6,6 GB groß ist: Der Rest war Kontextpuffer. "
                          "Aufgeklärt wurde der Widerspruch nicht - das Modell wurde am "
                          "24.08.2026 gelöscht (Ansage Edgar: „das ist sowieso alt“). "
                          "Ältere Beobachtung: Nannte es, ohne den Schluss zu ziehen („Oder andersrum: …“) - "
                          "und schweift aus.",
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
        "kennung": "qwen/qwen-plus-2025-07-28:thinking",
        "ort": "online", "rang": None, "sekunden": 201, "kern": 3, "standard": 4,
        "ct_je_frage": 0.08,
        "note": "4-", "note_grund": "Der Denk-Modus kostet das Achtfache an Zeit und bringt einen Kernpunkt mehr.",
        "beispiel": "Überanpassung an historische Regime; ohne Out-of-Sample-Test ist die Zahl nicht belastbar.",
        "urteil": "Der Denk-Modus kostete das Achtfache an Zeit gegenüber qwen-plus "
                  "und brachte genau einen Kernpunkt mehr.",
        "einschraenkung": "",
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
    {
        "kennung": "qwen3:14b",
        "ort": "lokal (gelöscht)", "rang": None, "sekunden": 107, "kern": 2, "standard": 1,
        "ct_je_frage": 0.0,
        "note": "6", "note_grund": "Schwächstes Ergebnis im Feld; am 11.08.2026 entfernt.",
        "beispiel": "(keine verwertbare Kritik - allgemeine Hinweise ohne Bezug zur Rechnung)",
        "urteil": "Schwächstes Ergebnis im Feld; am 11.08.2026 als veraltet entfernt.",
        "einschraenkung": "",
    },
    {
        # Gemessen am 22.08.2026 (Ansage Edgar: „aktiviere oxAlpha"), derselbe
        # Pruefstein wie alle anderen: werkzeug/sparring_vergleich.py, drei
        # Fragen, ein Durchgang. Antworten im Wortlaut in
        # werkzeug/sparring_oxalpha.md.
        "kennung": "stealth/ox-alpha",
        "ort": "online", "rang": 3, "sekunden": 472, "kern": 5, "standard": 4,
        "ct_je_frage": 0.0,
        "note": "1-", "note_grund": "Das einzige Modell, das den Prüfstein in ZWEI unabhängigen Läufen fand - beide Male mit durchgerechnetem Gegenbeispiel. Dafür 130-159 s je Frage.",
        "beispiel": "Freigewordene Slots können zuvor verdrängte Signale aktivieren, die im Original-Lauf gar nicht existieren. Der wahre Effekt der Sperre ist die Differenz zweier kompletter Simulationen, nicht −(−7861).",
        "urteil": "Benannte den versteckten Mechanismus der Zellen-Rechnung nicht nur, "
                  "sondern rechnete ihn in BEIDE Richtungen durch: einmal ein Tag, an dem "
                  "die Sperre einen verdrängten Short freigibt (Effekt +450 statt der "
                  "gebuchten +150), einmal ein Tag ohne verdrängtes Signal (Effekt −200 "
                  "statt +200). Beim besten Filter als einziges Modell die Effektstärke "
                  "ausgerechnet - 11.302/64.185 = 0,18 σ - und gegen den Erwartungswert "
                  "des Maximums aus zwölf Zufallsstichproben (rund 1,4 σ) gestellt: "
                  "„Das Ergebnis ist nicht auffällig gut - es ist unauffällig.“ Bei den "
                  "schwachen Jahren zusätzlich zwei Verdächtige, die niemand sonst nannte: "
                  "ein Datenschnitt um 2020 (Zeitzone/Sommerzeit) und ein fester "
                  "Punkt-Filter im Signal. Verweigerte ausdrücklich erfundene "
                  "Quellenangaben. Kostenlos, 1 Mio. Token Kontext. "
                  "IM ZWEITEN LAUF derselbe Treffer - mit eigener Tabelle: fünf "
                  "Signale, Original +340, die naive Rechnung verspricht +420, "
                  "resimuliert kommen +305 heraus. Dazu der Satz, der den realen "
                  "Befund trifft: „Größe und im Extremfall sogar das Vorzeichen "
                  "der 7861 sind ohne Resimulation nicht bestimmbar.“ Damit das "
                  "erste Modell im Feld, dessen Prüfstein-Treffer sich wiederholen "
                  "ließ.",
        "einschraenkung": "DREI LAEUFE, dreimal der Pruefstein getroffen (Kern 4/6, 5/6, 5/6) - das einzige Modell im Feld mit belegter Wiederholbarkeit. Dafuer schwankt das Tempo erheblich: 390, 477 und 548 s fuer dieselben drei Fragen, also 130 bis 183 s je Frage - nur qwen3.6 und qwen-plus:thinking waren "
                          "waren langsamer. Dazu ein Stealth-Modell: Der Anbieter nennt "
                          "sich nicht, das Modell kann jederzeit verschwinden, und jede "
                          "Frage geht an einen unbenannten Empfänger.",
    },
)

#: Was die Messung als Ganzes ergeben hat - die Saetze, die eine Tabelle nicht sagt.
BEFUNDE = (
    ("Keiner ist verlässlich",
     "Von acht Modellen hat genau eines den entscheidenden Mechanismus benannt - "
     "und im Wiederholungslauf nicht mehr. Ein zweites Modell ersetzt keine "
     "Gegenrechnung, es liefert Verdachtsmomente. Nachtrag 22.08.2026: "
     "ox-alpha ist das erste Modell, bei dem der Prüfstein-Treffer sich "
     "wiederholen ließ - zweimal derselbe Mechanismus, beide Male mit eigenem "
     "Zahlenbeispiel. Ein Modell mit zwei Treffern aus zwei Läufen ist immer "
     "noch keine Gegenrechnung, aber es ist der erste Kandidat, den man "
     "wiederholt fragen kann."),
    ("Der Nutzen liegt in der Unbefangenheit",
     "Wertvoll ist nicht das bessere Modell, sondern das Modell, das die eigenen "
     "Schlüsse nicht kennt. Genau deshalb fand nemotron den Punkt, den die "
     "eigene Zellen-Rechnung übersprang."),
    ("Groß hilft nicht automatisch",
     "550 Mrd. Parameter (nemotron) und 27 Mrd. (qwen3.6 lokal) fanden je einen "
     "der beiden versteckten Punkte. Das 9-Mrd.-Modell auf diesem Rechner lag "
     "gleichauf mit gemini-2.5-pro."),
    ("MoE haelt, was es verspricht - sauber nachgemessen",
     "Dieser Befund stand am 24.08.2026 zweimal auf dem Kopf. Ursprünglich: "
     "gemma4 rechnet je Token nur 4 seiner 26 Mrd. Parameter und war achtmal "
     "schneller als das dichte qwen3.6. Dann schien eine Messung auf der neuen "
     "Karte das Gegenteil zu zeigen, und der Text wurde umgeschrieben. Diese "
     "Messung war fehlerhaft - das Werkzeug entlud die Modelle nicht, die "
     "späteren lagerten aus. Sauber gemessen, Mittel aus zwei Durchgängen: "
     "gemma4 (MoE, 4 von 26 Mrd. aktiv) 127,8 Token/s gegen qwen3.8:27b (dicht) "
     "38,5 - Faktor 3,3 bei fast gleicher Modellgröße. qwen3.6:35b-a3b (3 von 35 "
     "Mrd. aktiv) liegt mit 105,2 ebenfalls weit vorn. Für das Tempo zählt die "
     "AKTIVE Parameterzahl, für den Speicher die gesamte - und das gilt "
     "unabhängig davon, ob ausgelagert wird."),
    ("Der Engpass war der Speicher, nicht die Rechenleistung",
     "Der Wechsel von 12 auf 32 GB half sehr ungleich. qwen3.8:27b war auf der "
     "3060 nicht messbar (rund ein Zeichen je Sekunde, Sparring-Timeout) und "
     "liefert jetzt 38,5 Token/s. Modelle, die schon vorher hineinpassten, "
     "gewannen dagegen wenig. Wer den Nutzen einer Karte schätzt, schätzt fast "
     "immer die Rechenleistung; entschieden hat hier, ob das Modell hineinpasst. "
     "Der zweite Teil dieses Befundes ist eine Warnung in eigener Sache: Hier "
     "stand zwischenzeitlich, gpt-oss:20b sei auf der neuen Karte fünfmal "
     "LANGSAMER geworden - 34,9 auf 6,2 Token/s, Ursache offen. Die Ursache war "
     "das eigene Messwerkzeug, das die Modelle nicht entlud. Sauber gemessen "
     "sind es 140,3 Token/s, der schnellste Wert im ganzen Feld."),
    ("Ein Messwerkzeug kann sich selbst kaputtmessen",
     "Zwei Skripte dieses Projekts maßen Token/s und Antwortzeiten, ohne das "
     "Modell danach aus dem Grafikspeicher zu werfen. Ollama hält es fünf "
     "Minuten. Bei sieben Modellen zu je 13 bis 30 GB lagen dann drei "
     "gleichzeitig auf einer 32-GB-Karte, und wer zuletzt gemessen wurde, bekam "
     "den Rest: gpt-oss:20b hatte 1,1 statt 13,6 GB. Die Folge waren Zahlen, die "
     "zu erfundenen Erklärungen einluden - erst „MXFP4 auf Blackwell“, dann "
     "„Vulkan statt CUDA“, beides falsch. Auffällig war die Streuung: dasselbe "
     "Modell schwankte zwischen zwei Läufen um bis zu 72 %. Nach dem Fix sind es "
     "1 bis 13 %. Wenn eine Messung zwischen Wiederholungen stärker schwankt als "
     "zwischen den verglichenen Dingen, misst sie nicht das, was sie behauptet."),
    ("Seit dem 24.08.2026 ist lokal eine echte Alternative",
     "Die Frage „online oder lokal?“ war auf der 12-GB-Karte keine: Jedes Modell "
     "über 11 GB lagerte aus, qwen3.8:27b kam auf rund ein Zeichen je Sekunde und "
     "lieferte im Sparring gar keine Note. Auf der RTX PRO 4500 steht dasselbe "
     "Modell auf Rang 4 von 16 - vor nemotron, vor gemini-3-flash, vor "
     "qwen3.8-max -, findet als erstes lokales Modell den Prüfstein und braucht "
     "59 s je Frage. Die drei Modelle davor kosten 0 bis 0,93 ct je Frage; dieses "
     "kostet nichts, und keine Frage verlässt den Rechner. Für Auswertungen, in "
     "denen eigene Positionen, Kontostände oder Strategien vorkommen, ist das "
     "kein Nebenaspekt, sondern der Hauptgrund."),
    ("Kostenlos ist hier nicht schlechter",
     "Das beste und das drittbeste Modell der Messung kosten nichts - eines über "
     "OpenRouter, eines auf der eigenen Grafikkarte."),
    ("Von Anthropic gibt es nichts Lokales",
     "Claude hat nie offene Gewichte veröffentlicht - weder kostenlos noch "
     "bezahlt. Lokal geht ausschließlich über die API. Von OpenAI gibt es genau "
     "zwei offene Modelle (gpt-oss:20b und :120b, Apache 2.0, August 2025); das "
     "kleinere liegt auf diesem Rechner und ist in der Messung das schwächste "
     "Modell im Feld. Stand 12.08.2026."),
    ("Quellenangaben sind die gefährlichste Ausgabe",
     "Am 12.08.2026 wurden drei Modelle nach Belegen für Orderbuch-Handel "
     "gefragt, ausdrücklich mit der Bitte, Unsicheres zu markieren. Ergebnis "
     "nach Nachprüfung: gpt-oss erfand eine Arbeit samt Autoren, Jahr und einer "
     "präzisen Zahl; gemma4 schrieb VPIN Cont zu (es stammt von Easley, López "
     "de Prado & O'Hara) und verwechselte Joel Hasbrouck mit „M. Hasbrouck“; "
     "nur nemotron nannte durchweg existierende Arbeiten. Eine Quellenangabe "
     "aus einem Sprachmodell ist ein Suchbegriff, kein Beleg - und je präziser "
     "die mitgelieferte Zahl, desto verdächtiger."),
    ("Die Aufforderung „markiere Unsicheres“ hilft nur bedingt",
     "gpt-oss markierte fleißig UNSICHER - auch dort, wo es sich sicher sein "
     "konnte. Wer alles markiert, markiert nichts. Nemotron markierte sparsam "
     "und lag damit richtiger."),
)


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
                        "kontext": z.get("kontext"), "gb": z["gb"], "gb_geschaetzt": False}
        ges, aktiv = self.katalog.parameter_aus_name(kennung)
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
            aus.append(zeile)
        aus.sort(key=lambda z: (z["rang"] or 99, -z["kern"], z["sekunden"]))
        return aus
