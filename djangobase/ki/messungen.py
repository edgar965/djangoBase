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

#: GRAFIKSPEICHER der lokalen Modelle, gemessen am 11.08.2026 mit
#: ``werkzeug/ollama_vram.py`` auf einer RTX 3060 (12 GB):
#: (gesamt GB, davon auf der GPU, Rest im Hauptspeicher).
#:
#: DIESE DREI ZAHLEN ERKLAEREN DIE ANTWORTZEITEN. Was nicht auf die Karte passt,
#: rechnet die CPU mit - und das kostet ein Vielfaches. Bemerkenswert ist der
#: Vergleich der beiden grossen: gemma4 und qwen3.6 lagern fast gleich viel aus
#: (6,3 gegen 7,3 GB), aber gemma4 antwortet FUENFMAL schneller. Der Grund ist
#: die MoE-Bauweise: Je Token rechnen nur 4 der 26 Mrd. Parameter, die
#: ausgelagerten Experten werden seltener gebraucht.
VRAM = {
    "qwen3.5:9b":            (5.5, 5.5, 0.0),
    "gpt-oss:20b":           (13.8, 11.0, 2.8),
    "gemma4:26b-a4b-it-qat": (15.8, 9.5, 6.3),
    "qwen3.6:27b":           (17.1, 9.8, 7.3),
    # Nachgemessen am 18.08.2026 (derselbe Aufruf, dieselbe Karte). qwen3.8 ist
    # der Nachfolger von 3.6 und braucht noch mehr: 18,2 GB, davon 9,1 GB im
    # Hauptspeicher - die groesste Auslagerung im ganzen Feld. Gemessen kommt es
    # damit auf rund EIN Zeichen je Sekunde (167 Zeichen in 169,9 s); ein
    # Sparring-Durchgang lief in den Timeout, statt eine Note zu liefern.
    # qwen3.6 ist am 18.08.2026 geloescht worden (Ansage Edgar); seine Zahlen
    # bleiben hier, weil die MoE-Begruendung darunter sich auf sie stuetzt.
    "qwen3.8:27b":           (18.2, 9.0, 9.1),
}

#: DURCHSATZ je lokalem Modell, gemessen am 12.08.2026 mit
#: ``werkzeug/gpu_nutzen.py`` auf derselben RTX 3060: Token je Sekunde beim
#: Erzeugen der Antwort, aus den Zaehlern des Ollama-Antwort-JSON und damit
#: unabhaengig von der Antwortlaenge.
#:
#: DIESE VIER ZAHLEN SIND DAS ARGUMENT FUER MoE. qwen3.6 (dicht) lagert 6,4 GB
#: aus und faellt auf 3,1 Token/s; gemma4 lagert mit 4,6 GB fast genauso viel
#: aus und ist trotzdem achtmal schneller, weil je Token nur 4 der 26 Mrd.
#: Parameter rechnen. Nicht die MENGE des Ausgelagerten entscheidet, sondern wie
#: oft darauf zugegriffen wird. Ausfuehrlich: Hilfe > Architektur > GPU.
TOKEN_JE_S = {
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
        "ort": "online", "rang": 4, "sekunden": 82, "kern": 4, "standard": 5,
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
        "ort": "online", "rang": 5, "sekunden": 17, "kern": 4, "standard": 4,
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
        "ort": "lokal", "rang": 3, "sekunden": 139, "kern": 5, "standard": 3,
        "ct_je_frage": 0.0,
        "note": "2", "note_grund": "Bester lokaler Kritiker: Tiefe des 27B-Modells bei einem Fünftel der Wartezeit.",
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
        "ort": "lokal", "rang": None, "sekunden": 43, "kern": 1, "standard": 3,
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
        "ort": "online", "rang": 2, "sekunden": 221, "kern": 5, "standard": 4,
        "ct_je_frage": 0.93,
        "note": "2", "note_grund": "Beste Trefferzahl im Feld und die einzige eigenständige Signifikanz-Rechnung - dafür 74 s und knapp ein Cent je Frage.",
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
        "ort": "online", "rang": 7, "sekunden": 208, "kern": 4, "standard": 4,
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
        "ort": "online", "rang": 8, "sekunden": 33, "kern": 3, "standard": 3,
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
        "kennung": "qwen3.5:9b",
        "ort": "lokal", "rang": 6, "sekunden": 55, "kern": 4, "standard": 4,
        "ct_je_frage": 0.0,
        "note": "3", "note_grund": "Passt ganz auf die Grafikkarte und ist damit das schnellste lokale Modell - inhaltlich solide, aber weitschweifig.",
        "beispiel": "Selektionsbias durch Tageslimit (4 Trades/Tag): Mit einem harten Limit wird dein Ergebnis massiv verzerrt.",
        "urteil": "Der beste Kompromiss lokal: passt in den Grafikspeicher, knapp eine "
                  "Minute, brauchbare Einwände. Nannte das Tageslimit als einziges "
                  "lokales Modell überhaupt.",
        "einschraenkung": "Nannte es, ohne den Schluss zu ziehen („Oder andersrum: …“) - "
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
)

#: Was die Messung als Ganzes ergeben hat - die Saetze, die eine Tabelle nicht sagt.
BEFUNDE = (
    ("Keiner ist verlässlich",
     "Von acht Modellen hat genau eines den entscheidenden Mechanismus benannt - "
     "und im Wiederholungslauf nicht mehr. Ein zweites Modell ersetzt keine "
     "Gegenrechnung, es liefert Verdachtsmomente."),
    ("Der Nutzen liegt in der Unbefangenheit",
     "Wertvoll ist nicht das bessere Modell, sondern das Modell, das die eigenen "
     "Schlüsse nicht kennt. Genau deshalb fand nemotron den Punkt, den die "
     "eigene Zellen-Rechnung übersprang."),
    ("Groß hilft nicht automatisch",
     "550 Mrd. Parameter (nemotron) und 27 Mrd. (qwen3.6 lokal) fanden je einen "
     "der beiden versteckten Punkte. Das 9-Mrd.-Modell auf diesem Rechner lag "
     "gleichauf mit gemini-2.5-pro."),
    ("MoE hält, was es verspricht",
     "gemma4 rechnet je Token nur 4 seiner 26 Mrd. Parameter - und erreicht die "
     "Trefferzahl des dichten 27B-Modells in einem Fünftel der Zeit (139 s statt "
     "737 s für dieselben drei Fragen). Für lokale Modelle zählt die aktive "
     "Parameterzahl fürs Tempo, die gesamte für den Speicher."),
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
