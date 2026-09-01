# -*- coding: utf-8 -*-
u"""Was die Messung als GANZES ergeben hat - die Saetze, die eine Tabelle nicht sagt.

HERAUSGELOEST AUS ``messungen.py`` (31.08.2026). Die Datei stand bei 646 Zeilen
und damit weit ueber der Projektgrenze von 200-300; wer sie anfasst, teilt den
angefassten Teil ab. Angefasst wurde genau dieser Block - fuer den Eintrag zu
Qwen3.8-Flash-Next.

Der Import in ``ki/__init__.py`` bleibt unveraendert: ``messungen.py`` reicht
``BEFUNDE`` weiter, damit kein Aufrufer etwas merkt.

WAS HIER HINEINGEHOERT: Erkenntnisse, die aus dem VERGLEICH entstehen und in
keiner Tabellenzeile Platz haben - auch die unbequemen (zwei der Eintraege
beschreiben eigene Messfehler). Was zu EINEM Modell gehoert, steht als
``urteil`` bei seiner Messung.
"""

__all__ = ["BEFUNDE"]


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
     "wiederholt fragen kann. "
     "NACHTRAG 01.09.2026: ox-alpha ist aus dem OpenRouter-Katalog "
     "verschwunden - die Kennung liefert 404, und im vollen "
     "Modellverzeichnis steht sie nicht mehr. Unter dem Namen „stealth“ "
     "veröffentlicht OpenRouter Modelle, deren Hersteller sich noch "
     "nicht nennt; sie verschwinden, sobald sie unter ihrem richtigen "
     "Namen erscheinen. Seine Zeile ist deshalb aus der Bestenliste "
     "genommen - der Befund bleibt, das Modell ist nicht mehr zu haben."),
    ("Der Nutzen liegt in der Unbefangenheit",
     "Wertvoll ist nicht das bessere Modell, sondern das Modell, das die eigenen "
     "Schlüsse nicht kennt. Genau deshalb fand nemotron den Punkt, den die "
     "eigene Zellen-Rechnung übersprang."),
    ("Groß hilft nicht automatisch",
     "550 Mrd. Parameter (nemotron) und 27 Mrd. (qwen3.6 lokal) fanden je einen "
     "der beiden versteckten Punkte. Das 9-Mrd.-Modell auf diesem Rechner lag "
     "gleichauf mit gemini-2.5-pro."),
    ("MoE hält, was es verspricht - sauber nachgemessen",
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
    ("Nicht jedes neue Modell ist ein Kandidat — Qwen3.8-Flash-Next",
     "Erschienen am 26.08.2026 als Vorschau auf die Qwen4-Architektur: 125 Mrd. "
     "Parameter als MoE, davon 6 Mrd. je Token aktiv. Auf dem Papier genau das "
     "Profil, das hier gewinnt (siehe „MoE hält, was es verspricht“). "
     "Geprüft am 31.08.2026, NICHT geladen — und der Grund liegt nicht am "
     "Modell, sondern am Format. Die Ollama-Bibliothek führt genau drei "
     "Fassungen: 125b-a6b-mlx-bf16 (360 GB), 125b-a6b-nvfp4 (105 GB) und "
     "125b-mlx (105 GB). MLX ist das Format für Apple-Silicon und läuft "
     "hier gar nicht; die nvfp4-Fassung passt zur Blackwell-Karte, sprengt mit "
     "105 GB aber jeden Speicher dieses Rechners (32 GB VRAM + 63,7 GB RAM). "
     "Eine GGUF-Fassung gibt es nur außerhalb der Bibliothek (unsloth auf "
     "HuggingFace); die kleinste ist UD-IQ1_S mit 67,6 GB, die nächste "
     "UD-Q2_K_XL mit 73,5 GB. Beide wären lauffähig, aber nur mit "
     "Auslagerung — und ein 1- bis 2-Bit-Modell gegen die hier gelisteten "
     "q4- und q8-Fassungen zu stellen, misst die Quantisierung statt des "
     "Modells. Über OpenRouter ist es nicht zu haben (dort stehen "
     "qwen3.8-flash, -27b, -2.4t-a95b und -max, aber kein -flash-next). Der "
     "Zustand ist damit „nicht messbar“, nicht „schlecht“ — "
     "der Unterschied gehört auf diese Seite, sonst steht das Modell "
     "irgendwann ohne Note da und sieht aus, als sei es durchgefallen. Erneut "
     "prüfen, sobald eine kleinere GGUF- oder eine beschnittene "
     "REAP-Fassung erscheint."),
    ("Eine 404-Antwort ist kein Beweis — die Registry-Falle",
     "Bei der Suche nach Qwen3.8-Flash-Next lieferte "
     "``registry.ollama.ai/v2/library/<name>/tags/list`` einen 404, und das sah "
     "nach „gibt es nicht“ aus. Die Gegenprobe mit ``qwen3.8`` — einem "
     "Modell, das auf dieser Platte liegt, also zweifelsfrei existiert — "
     "lieferte denselben 404. Die Adresse taugt schlicht nicht für diese "
     "Frage. Belastbar war erst das rohe Markup von "
     "``ollama.com/library/<name>/tags``: drei Tags, zwei Größenangaben, "
     "nachlesbar. Wer eine Existenzfrage mit einem Fehlercode beantwortet, "
     "sollte den Code vorher an einem Fall prüfen, dessen Antwort er kennt."),
)
