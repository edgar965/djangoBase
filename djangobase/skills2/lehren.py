# -*- coding: utf-8 -*-
u"""Lehren - was der Review-Durchgang gekostet hat, in Saetzen.

Jede Lehre steht hier mit dem FALL, aus dem sie stammt. Ohne den Fall ist eine
Regel eine Meinung; mit ihm kann man entscheiden, ob sie im eigenen Projekt
gilt. Die Haken auf der Seite sind eine Arbeitsliste - ab damit durchs naechste
Projekt.

Reihenfolge: erst die, die Fehler VERHINDERN, dann die, die beim Aufraeumen
helfen, dann die ueber Werkzeuge und Messungen.
"""

__all__ = ["LEHREN", "gruppen"]

#: (slug, gruppe, titel, was zu tun ist, der Fall dahinter)
LEHREN = [
    ("modulzustand", "Fehler verhindern",
     "Kein veränderlicher Zustand auf Modulebene",
     "Listen, Dicts und Sets auf Modulebene gelten für ALLE Anfragen "
     "gleichzeitig — der Entwicklungsserver ist multithreaded. Was eine Anfrage "
     "lang gelten soll, gehört in ein Objekt oder in threading.local.",
     "Eine Liste wurde in einer Datei gefüllt, in zwei anderen geleert und in "
     "einer vierten gelesen. Der mechanische Rechenweg leerte sie nie — er "
     "meldete Warnungen eines fremden, längst beendeten Laufs. Neun Zeilen "
     "darüber stand im Code, der Server sei multithreaded; direkt darunter, er "
     "bearbeite eine Anfrage nach der anderen."),

    ("dict-klasse", "Fehler verhindern",
     "Dictionary nur dort, wo es hinausgeht",
     "Mehr als drei feste Schlüssel und der Datensatz wandert durch mehrere "
     "Funktionen? Dann eine Klasse mit benannten Feldern. Geht er direkt als "
     "JSON hinaus oder liegt so in der Datenbank, bleibt es ein Dictionary — "
     "dann aber mit Vermerk, wohin.",
     "Ein Tippfehler in d[\"schlüssel\"] ist kein Fehler, den jemand sieht: Er "
     "legt still einen neuen Eintrag an, den nie jemand liest."),

    ("umleitung", "Fehler verhindern",
     "Umleitungen über vars(Klasse), nie über getattr",
     "Ein Klassenattribut zum Testen ersetzen und danach zurückschreiben: Der "
     "Originalwert muss aus vars(Klasse)[name] kommen. getattr packt "
     "staticmethod/classmethod aus — die Rückgabe macht daraus eine normale "
     "Methode.",
     "Ein Test stellte @staticmethod so „zurück“, dass ab da self mitgebunden "
     "wurde. Sichtbar wurde es zwei Tests später und NUR im vollen Suitenlauf: "
     "„nimmt 6 Argumente, bekam 7“. Vierter Fall derselben Klasse im Projekt."),

    ("test-messen", "Fehler verhindern",
     "Ein Testfeld ist nur grün, wenn gemessen wurde",
     "Findet ein Test seine Voraussetzung nicht vor (Börse zu, Gerät fehlt), ist "
     "er weder bestanden noch fehlgeschlagen. Dafür braucht die Suite einen "
     "dritten Zustand „nicht messbar“ — grün stellen ist eine Lüge, rot lassen "
     "eine falsche Anschuldigung.",
     "Ein Round-Trip-Test gegen die Börse war am Wochenende rot, weil kein "
     "Geld/Brief anlag. Der erste Reparaturversuch meldete ihn als bestanden — "
     "ein grünes Feld ohne jede Messung dahinter."),

    ("gegenprobe", "Fehler verhindern",
     "Zu jedem neuen Test eine Gegenprobe",
     "Nach dem Schreiben den geprüften Code absichtlich beschädigen und "
     "nachsehen, ob der Test rot wird. Erst dann weiß man, dass er etwas prüft.",
     "Eine Prüfung blieb grün, obwohl eine Methode gelöscht war: Sie rief nur 5 "
     "von 17 Aliasen auf, und der Betroffene war nicht dabei. Aufgefallen ist "
     "das nur durch die Gegenprobe."),

    ("dict-zu-klasse-bool", "Fehler verhindern",
     "Beim Ersetzen eines Dictionary durch eine Klasse: kein __bool__",
     "Ein Dictionary mit Inhalt ist immer wahr. Gibt die neue Klasse ein "
     "__bool__ mit „wahr, wenn erfolgreich“, kehren sich alle Prüfungen der Form "
     "``if fehler:`` still um. Wer wissen will, ob es geklappt hat, fragt ein "
     "Feld — nicht das Objekt.",
     "Genau das ist beim Umbau eines Live-Orderpfads passiert: Das "
     "Fehler-Ergebnis war „falsch“, der Fehlerzweig wurde übersprungen, und der "
     "Code setzte eine Stop-Klammer auf eine Position, die es nicht gab. Zwölf "
     "von 35 Prüfpunkten eines Attrappen-Werkzeugs wurden rot — ohne das "
     "Werkzeug hätte es niemand vor dem nächsten echten Trade gemerkt."),

    ("import-am-kopf", "Fehler verhindern",
     "Code außerhalb des Django-Projekts nur SPÄT importieren",
     "Liegt ein Paket neben dem Django-Projekt (und nicht darin), steht es beim "
     "Laden der Apps noch nicht im Pfad. Ein Import am Dateikopf eines Moduls, "
     "das AppConfig.ready() lädt, killt den ganzen Server. Import in die "
     "Funktion ziehen — die Nachbarmodule machen es meist schon so.",
     "Genau so ist der Entwicklungsserver für zehn Minuten ausgefallen: ein "
     "sauberer Import am Dateikopf, „No module named depot“, und die "
     "Erreichbarkeitsprüfung davor war wertlos, weil sie den Pfad selbst gesetzt "
     "hatte. Was zählt, ist ``manage.py check`` ohne eigene sys.path-Tricks."),

    ("aufteilen", "Aufräumen",
     "Aufteilen mit Netz: Methodenliste vorher/nachher",
     "Beim Zerlegen einer großen Datei vor und nach dem Schnitt die Liste der "
     "Methoden/Funktionen vergleichen. Was verschwunden ist, muss bewusst "
     "verschoben worden sein.",
     "Beim Aufteilen eines 427-Zeilen-Moduls wurde eine Methode mitgelöscht, "
     "weil sie zwischen zwei ausgeschnittenen Blöcken lag. Kein bestehender "
     "Test sah es; der Fehler wäre erst beim Klick des Nutzers gekommen."),

    ("marker", "Aufräumen",
     "Begründung in den Code, nicht in die Ausnahmeliste",
     "Wenn ein Prüfwerkzeug eine absichtliche Stelle meldet, gehört die "
     "Begründung als Vermerk NEBEN die Stelle („geteilt gewollt: …“). Eine "
     "Ausnahmeliste im Werkzeug rät, was der Autor gemeint hat.",
     "Ein Prüfwerkzeug mit eigener Ausnahmeliste erklärte einmal 122 lebende "
     "Namen für tot und wollte 404 Dateien löschen, aus denen 53 Werkzeuge "
     "lesen."),

    ("duplikate", "Aufräumen",
     "Duplikate zusammenlegen — aber Signaturen prüfen",
     "Zeichengleiche Rümpfe sind ein Fund, keine Anweisung. Zwei Kopien können "
     "verschiedene Signaturen und Aufrufer haben; beim Zusammenlegen jeden "
     "Aufrufer einmal fahren.",
     "Vier Werkzeuge trugen denselben Ablauf. Als der geprüfte Code umgebaut "
     "wurde, lief einer davon ins Leere — drei Tage lang eine Sicherung, die "
     "keine mehr war."),

    ("weiterleitung", "Aufräumen",
     "Nach dem Zusammenlegen ist die Weiterleitung kein neues Duplikat",
     "Wer 34 Kopien einer Funktion zusammenlegt, hinterlässt an 34 Stellen ein "
     "``return Gemeinsam.tun(x)``. Das Duplikat-Werkzeug meldet diese Zeilen "
     "prompt als neuen Fund — wer dem folgt, schreibt die Kopien zurück. Rümpfe, "
     "die nur weiterreichen, gehören ausgenommen.",
     "Genau so geschehen beim Zusammenlegen der deutschen Zahlformatierung: Der "
     "nächste Lauf zeigte 34 frische „Duplikate“, die in Wahrheit die Lösung "
     "waren."),

    ("fehlalarm", "Aufräumen",
     "Ein Werkzeug mit 95 % Fehlalarm verdeckt die echten Funde",
     "Beim ersten Lauf zählen die Treffer wenig — entscheidend ist, wie viele "
     "davon standhalten. Jeder Fehlalarm kostet Prüfzeit UND drängt die echten "
     "Fälle aus dem Blickfeld. Lieber die Regel schärfen als die Liste abarbeiten.",
     "Die Schleifen-Prüfung meldete 199 Fälle, davon 190 falsch: Der Iterator im "
     "Schleifenkopf läuft einmal, nicht je Durchlauf; ein Zugriff, der an der "
     "Schleifenvariablen hängt, liest je Durchlauf etwas anderes. Nach den "
     "Unterscheidungen blieben 9 — darunter die eine Datei, die neunmal gelesen "
     "wurde. Über alle Kriterien fielen so 1.257 Befunde auf 568."),

    ("generiert", "Aufräumen",
     "Generierte Ordner nie bearbeiten",
     "Ordner, die ein Werkzeug bei jedem Lauf neu schreibt, sehen aus wie "
     "Quellcode und tauchen in jeder Suche auf. Sie brauchen eine LIESMICH mit "
     "Verweis auf die echte Quelle.",
     "Eine Änderung landete im gespiegelten Arbeitsordner der Node-Tests. Der "
     "nächste Testlauf hätte sie kommentarlos gelöscht."),

    ("werkzeug-index", "Werkzeuge",
     "Prüfwerkzeuge: ein Durchlauf, dann nachschlagen",
     "Ein Werkzeug, das je Fundstelle alle Dateien erneut durchsucht, ist "
     "quadratisch und läuft in Zeitüberschreitungen. Erst alles einmal lesen und "
     "indizieren, dann nachschlagen.",
     "Die erste Fassung der Modulzustand-Prüfung brauchte über 120 Sekunden und "
     "brach ab — sie machte genau den Fehler, den sie anderswo meldet."),

    ("dateiuebergreifend", "Werkzeuge",
     "Prüfungen dateiübergreifend anlegen",
     "Wer nur innerhalb einer Datei sucht, findet die interessanten Fälle nicht: "
     "Der Zustand wird in Datei A angelegt, in B verändert und in C gelesen.",
     "Die erste Fassung suchte Mutationen nur in derselben Datei und ließ genau "
     "den Fall durch, für den sie gebaut worden war."),

    ("laufzeit-test", "Werkzeuge",
     "Ein Ladetest gegen eine DOM-Attrappe",
     "Quelltext-Prüfungen sehen nicht, ob ein Browser-Modul überhaupt "
     "durchläuft. Eine kleine DOM-Attrappe in Node (getElementById, fetch, "
     "localStorage) reicht, um „Seite tot“ von „Seite da“ zu unterscheiden.",
     "Genau dieser Test fand die beim Aufteilen mitgelöschte Methode — "
     "zwanzig Minuten, nachdem sie verschwunden war."),

    ("zahlen-quelle", "Messen",
     "Keine Zahl ohne Messung dahinter",
     "Jede angezeigte Kennzahl braucht eine nachvollziehbare Quelle. Zahlen aus "
     "einer Erinnerung oder aus einem Text abgeschrieben sind der häufigste "
     "Grund für falsche Entscheidungen.",
     "Vier angezeigte Kennzahlen hatten keine Messung dahinter — eine "
     "beschrieb einen einzigen Tag, eine andere war aus bitgleichen Zeilen "
     "gerechnet."),

    ("keine-phantasie", "Messen",
     "Begründungen messen, nicht erfinden",
     "Wer eine Entscheidung mit einer Verhaltensbehauptung begründet („das "
     "gewöhnt an …“), muss sie belegen können. Sonst ist es eine Rationalisierung "
     "für das, was man ohnehin tun wollte.",
     "Ein rot bleibender Test wurde mit einer erfundenen Begründung grün "
     "gestellt. Der Satz klang plausibel und hatte nichts hinter sich."),

    ("erst-lohnt-es-sich", "Messen",
     "Vor dem Umbau fragen, ob er sich lohnt",
     "Ein Befund sagt „hier stimmt etwas nicht“ — nicht „bau es um“. Zwischen "
     "beidem steht eine Messung: Geht das Wörterbuch an die Oberfläche? Ist das "
     "geteilte Argument ein Feld oder ein Zwischenergebnis? Bleibt die Datei "
     "nach dem Schnitt wirklich unter der Grenze?",
     "134 von 204 Befunden waren Anzeigeformate, die der Auftrag selbst "
     "ausnimmt. Ein Schnitt, der 46/198 versprach, ergab 49/204 — die Hälfte "
     "blieb über der Grenze, der ganze Umbau brachte nichts."),

    ("vererbung-statt-schnitt", "Aufräumen",
     "Große Klassen über Vererbung teilen, nicht mit dem Zeilenschnitt",
     "Wird die herausgelöste Hälfte zur BASISKLASSE, bleibt jeder Aufruf "
     "unverändert — statische Methoden vererben sich mit. Ein Zeilenschnitt "
     "durch eine Klasse trennt dagegen nur ihren Kopf ab, und die Aufrufer "
     "suchen sie an der alten Adresse.",
     "Vier Dateien so geteilt, ohne dass ein Aufrufer mitwandern musste. Beim "
     "fünften Versuch — Zeilenschnitt statt Vererbung — landete die exportierte "
     "Klasse in der neuen Datei, während die Seite sie von der alten holte."),

    ("laedt-heisst-nicht-laeuft", "Fehler verhindern",
     "„Lädt ohne Fehler“ ist nicht „funktioniert“",
     "Ein Modul kann sauber laden und beim ERSTEN echten Aufruf werfen — etwa "
     "wenn eine Import-Zeile beim Aufteilen in der falschen Hälfte landete. "
     "Prüfungen müssen die Funktionen RUFEN, nicht nur zählen.",
     "Nach einem Schnitt lud alles, aber die Tabelle blieb leer: „esc is not "
     "defined“, geworfen erst beim Bauen der ersten Zelle. Seitdem baut die "
     "Prüfung alle 24 Zellfunktionen mit einer echten Zeile."),

    ("module-brechen-ganz", "Fehler verhindern",
     "Ein Modul, das beim Laden wirft, reißt die ganze Seite mit",
     "Der Browser verwirft es komplett — samt aller Namen, die es auf `window` "
     "legen wollte, teils auch die der Nachbardateien. Sechs Ursachen: fehlendes "
     "`super()`, Selbstbezug per Klassenname, doppelter Export, geteilter "
     "Modulzustand, Zugriff auf ein Seiten-Global auf Modulebene, und ein `let`, "
     "das über die Schnittgrenze geschrieben wird (Importe sind read-only).",
     "Alle sechs an einem Tag. Einmal waren acht window-Namen auf einen Schlag "
     "weg, darunter welche aus ganz anderen Dateien — wegen einer zweiten "
     "`export`-Zeile."),

    # ------------------------------------------------------------------
    # Aus dem 3DTools-Frontend-Durchgang (16.08.2026): 13 stille Ausfaelle in
    # einem Tag, alle in Browser-Code. Werkzeuge dazu: jswaisen,
    # jsregistrierung, jsfaenger, jssyntax, jsbefunde, jsfunktionen.
    # ------------------------------------------------------------------

    # ---- aus dem Fixer-Durchgang (16.08.2026) ------------------------------
    ("fixer-und-pruefer", "Werkzeuge",
     "Fixer und Prüfer müssen dieselbe Bedingung messen",
     "Bevor ein Fix-Werkzeug schreibt: nachsehen, unter welcher Bedingung der "
     "Prüfer meldet — und genau die übernehmen. Weicht der Fixer ab, arbeitet "
     "er an der Befundliste vorbei, in beide Richtungen.",
     "Ein Vermerk-Fixer setzte 75 Vermerke; die Befundzahl sank um EINEN. Er "
     "erkannte Anzeigeformate nach derselben 70-%-Regel, die der Prüfer schon "
     "als Ausnahme führte — 75 Dateiänderungen ohne Wirkung. Umgekehrt hielt "
     "eine Zusatzbedingung „mindestens zwei Leser“ den Klassen-Fixer von genau "
     "den Stellen fern, die gemeldet waren."),

    ("zwei-zaehlungen", "Messen",
     "Widersprechen sich zwei Zählungen, hat die genauere recht",
     "Dieselbe Größe zweimal unabhängig zählen und die Ergebnisse vergleichen. "
     "Wer nur eine Zahl hat, hält sie für richtig.",
     "„Wie viele Funktionen lesen dieses Dictionary?“ ergab 62 von 68 mit "
     "höchstens einem Leser (nur eigenes Modul), dann 1 von 68 (reiner "
     "Namensabgleich: 272 „Leser“ für eine Funktion namens kennzahlen), dann 51 "
     "von 68 (eigenes Modul plus echte Importeure). Erst als Prüfwerk und Fixer "
     "sich widersprachen, fiel der letzte Fehler auf: nach Funktionsnamen "
     "geschlüsselt statt nach Datei UND Name — und ``kennzahlen`` gibt es in "
     "fünf Werkzeugen."),

    ("sammelgrund", "Werkzeuge",
     "Ein Grund, der 35-mal gleich lautet, ist kein Grund",
     "Wenn ein Werkzeug für jede Fundstelle denselben Satz ausgibt, ist die "
     "Diagnose die eigentliche Arbeit — nicht der Befund.",
     "„Keine Trennlinie ohne Falle“ stand unter allen 35 zu großen JS-Dateien. "
     "Aufgeschlüsselt: 16 davon haben gar keine Trennlinie, weil sie je EINE "
     "Klasse sind (Vererbung statt Zeilennummer), 17 scheitern am Zirkel, 9 an "
     "einem read-only Import. Erst diese Aufteilung sagte, was zu tun ist."),

    ("neue-datei-alte-datei", "Fehler verhindern",
     "Die erzeugte Datei darf nie die Ausgangsdatei sein",
     "Jedes Werkzeug, das eine zweite Datei anlegt, prüft vor dem Schreiben, "
     "ob der Zielname schon vergeben ist — besonders vom Original selbst.",
     "``grid_daten.py`` mit einer Funktion ``datensatz`` ergab die Klasse "
     "``GridDaten`` in ``grid_daten.py``. Der Begleiter hätte das Original "
     "überschrieben und den ganzen Modulinhalt verloren; aufgefallen in der "
     "Vorschau, eine Minute vor dem ersten Schreibzugriff."),

    ("skript-kein-relativimport", "Fehler verhindern",
     "Skripte vertragen keinen relativen Import",
     "Vor dem Einfügen eines Imports ablesen, wie die Datei es hält: Hat sie "
     "einen ``__main__``-Block und sonst nur flache Importe, muss der neue auch "
     "flach sein.",
     "Vier Werkzeug-Skripte bekamen ein ``from .xyz_daten import …`` und "
     "starteten nicht mehr: „attempted relative import with no known parent "
     "package“. ``ast.parse`` sah nichts — die Zeile ist syntaktisch tadellos "
     "und scheitert erst beim Ausführen."),

    ("methoden-ohne-import", "Messen",
     "Methodenaufrufe tauchen in keiner Importliste auf",
     "Wer Aufrufer über Importe sucht, findet keine Methode: ``obj.tun()`` "
     "braucht den Namen nirgends importiert. Für eindeutige Methodennamen "
     "deshalb alle Attributaufrufe mitzählen.",
     "Eine Methode ``datensatz()`` mit zwei echten Aufrufern wurde als „null "
     "Leser“ gezählt und ihr Befund weggefiltert. Nach der Korrektur kamen drei "
     "Befunde zurück, die schon als erledigt galten."),

    ("schleifen-im-eigenen-werkzeug", "Werkzeuge",
     "Das eigene Werkzeug macht denselben Fehler, den es meldet",
     "Nach dem Bauen eines Prüf- oder Fix-Werkzeugs die Laufzeit messen und bei "
     "Auffälligkeiten profilen statt zu raten.",
     "Ein Fixer brauchte 73 Sekunden für einen Knopfdruck. Die erste Vermutung "
     "(Vorlagen je Datei neu durchsucht) senkte sie auf 71,5 — ``cProfile`` "
     "zeigte 177.246 Regex-Läufe: eine Textsuche JE NAME statt eines "
     "Mengenschnitts. Danach 5,5 Sekunden. Ein zweiter Fixer lag bei 154 "
     "Sekunden, aus demselben Grund an anderer Stelle."),

    ("beleg-auf-totem-code", "Messen",
     "Ein Beleg auf toten Code ist kein Beleg",
     "Wenn ein Werkzeug seine Begründung mit einer Fundstelle belegt, gehören "
     "Backup- und Archivdateien aus dem Suchraum — am Verzeichnis UND am "
     "Dateinamen.",
     "Ein automatisch gesetzter Vermerk begründete „geht an die Oberfläche“ mit "
     "``backup_dax_handel_vor_modulen.html``. Der Ausschluss griff nur auf "
     "Ordnernamen, nicht auf Dateinamen."),

    ("null-ist-verdaechtig", "Messen",
     "Ein Kriterium, das plötzlich auf null fällt, ist ein Alarmzeichen",
     "Sinkt eine Befundgruppe nach einer Regeländerung auf null, erst die "
     "Zählung an Einzelfällen gegenprüfen — nicht den Erfolg verbuchen. Die "
     "schärfste Frage dafür: <b>Findet die Prüfung noch den Fall, für den sie "
     "gebaut wurde?</b> Den kennt man, und er muss rot werden.",
     "Zweimal belegt. (1) Nach einer Verschärfung meldete Kriterium 11 null "
     "Befunde — ein Zählfehler; nach der Korrektur drei echte Fälle. Die "
     "Gegenprobe war übrigens auch erst falsch: ein ``grep`` zählte "
     "gleichnamige Funktionen anderer Dateien mit. (2) Das Werkzeug "
     "``getattr-namen`` meldete null, weil sein Maßstab zu weit war (jede "
     "Zeichenkette galt als Beleg). Es hätte seinen eigenen Anlassfall nicht "
     "gefunden: ``orb_nacht`` steht als Zeichenkette in der Prüfung, die ihn "
     "dokumentiert. Enger gefasst: 2 Verdachtsfälle statt 0 — und der "
     "Anlassfall wird wieder erkannt."),

    ("register-ohne-netz", "Fehler verhindern",
     "Ein Funktionsregister hat kein Netz — direkt importieren",
     "`fn.name = …` in einem Modul und `fn.name()` in einem anderen: Fehlt die "
     "Anmeldung (Modul nie importiert, Name geändert, Datei weggefallen), "
     "merkt es niemand. Wo möglich, direkt importieren; wo das Register "
     "bleibt, die Anmeldungen prüfen (Werkzeug `jsregistrierung`).",
     "Vier Namen wurden gerufen, aber nie angemeldet: die Fotoanalyse brach "
     "vor der Hautfarbe ab, der Ausricht-Assistent und der Textur-Reiter "
     "waren ohne Wirkung, und die Lichtsteuerung der Szene schaltete nicht "
     "mehr um. Kein einziger Eintrag in einem Log."),

    ("fragezeichen-punkt", "Fehler verhindern",
     "`obj.methode?.()` verschluckt eine fehlende Funktion vollständig",
     "Der Aufruf mit `?.` prüft nur, ob die Funktion existiert — fehlt sie, "
     "passiert NICHTS und es gibt keine Ausnahme. Für optionale Rückrufe ist "
     "das richtig, für Pflichtaufrufe eine Falle. Bei Pflichtaufrufen ohne "
     "`?.` schreiben, damit ein Fehler entsteht.",
     "`fn.syncLightVisibility?.()` war nie angemeldet. Nach jedem Wechsel des "
     "Lichttyps leuchteten die abgeschalteten Lichter weiter — ohne Meldung."),

    ("mjs-pruefen", "Werkzeuge",
     "`node --check datei.js` prüft als CommonJS — ES-Module braucht `.mjs`",
     "Eine kaputte `import`-Zeile geht in der Prüfung als `.js` durch. Die "
     "Datei vor der Prüfung nach `.mjs` kopieren (Werkzeug `jssyntax`), sonst "
     "ist das grüne Ergebnis wertlos.",
     "Ein Umsteller fügte eine Import-Zeile MITTEN in einen mehrzeiligen "
     "Import ein — drei Dateien unlesbar, drei Seiten weiß. `node --check` auf "
     "der `.js`-Datei war grün, dieselbe Datei als `.mjs` sofort rot."),

    ("import-einfuegen", "Fehler verhindern",
     "Eine Import-Zeile automatisch einfügen: nur hinter einer ABGESCHLOSSENEN "
     "Import-Anweisung",
     "„Letzte Zeile, die mit `import` beginnt\" ist bei mehrzeiligen Importen "
     "die erste — die neue Zeile landet mitten drin. Und „Zeile endet mit `;` "
     "und enthält ` from `\" trifft auch Meldungstexte. Also: Zeile muss mit "
     "`import` beginnen, Ende über die Klammertiefe suchen.",
     "Beide Varianten sind an einem Tag passiert. Die zweite fügte den Import "
     "hinter `console.log('… config from loaded character:', …);` ein, also "
     "mitten in eine Methode."),

    ("onclick-und-module", "Fehler verhindern",
     "`onclick=\"…\"` findet nichts, wenn der Code ein ES-Modul ist",
     "Ein Attribut-Handler sucht den Namen global; Module legen keinen an. "
     "Statt Namen auf `window` zu legen: EIN Zuhörer auf dem Container und "
     "`data-aktion`/`data-id` an den Knöpfen. Das gilt automatisch auch für "
     "Zeilen, die erst zur Laufzeit entstehen.",
     "Beim Auslagern von 1.060 Zeilen Inline-JavaScript aus vier Vorlagen "
     "waren 39 solcher Attribute betroffen — jedes ein toter Knopf, sobald der "
     "Code als Modul lädt."),

    ("schnellweg-vollstaendig", "Fehler verhindern",
     "Ein Schnellweg muss ALLE Schritte des langen Wegs übernehmen",
     "Wer für den häufigen Fall eine Abkürzung baut (nur Punkte statt ganzes "
     "Netz), muss jeden Schritt des vollständigen Wegs durchgehen und "
     "übernehmen — nicht nur die offensichtlichen.",
     "Der schnelle Netz-Nachlader ließ `alignBodyToSMPLX` weg, das der lange "
     "Weg nach dem Umrechnen anwendet. Der Körper wäre beim ersten "
     "Reglerziehen neben das Vergleichsmodell gesprungen. Aufgefallen beim "
     "Lesen des langen Wegs, nicht im Test."),

    ("unnoetige-nutzlast", "Messen",
     "Was der Client wegwirft, muss der Server nicht senden",
     "Vor dem Optimieren einer Antwort messen, welche Felder der Aufrufer "
     "überhaupt liest. Ein Feld, das nur beim ERSTEN Aufbau gebraucht wird "
     "(Topologie, UVs), gehört hinter einen Parameter.",
     "Der Netz-Endpunkt schickte bei JEDER Reglerbewegung 5,24 MB, davon 2,97 "
     "MB Dreiecke und UVs — die der Aufrufer verwarf, weil sich durch Morphs "
     "nur die Punktlagen ändern. Mit `nur_punkte=1`: 2,26 MB, 57 % weniger."),

    ("spezifitaet", "Fehler verhindern",
     "Eine CSS-Klasse ersetzt keinen Inline-Stil eins zu eins",
     "Ein Inline-Stil schlägt jede Regel; eine Klasse (0,0,1,0) verliert gegen "
     "`.karte h3` (0,0,1,1) und sogar eine doppelte Klasse (0,0,2,0) gegen "
     "`.zeile input[type=color]` (0,0,2,1). Beim Umstellen den Klassennamen "
     "mehrfach in den Selektor schreiben — nicht `!important`, das blockiert "
     "jede spätere Anpassung.",
     "Beim Ersetzen von 772 Inline-Stilen wurden Abschnittstitel grau statt "
     "rot und Farbfelder 28×22 statt 40×24 Pixel. Beides fiel NUR auf, weil "
     "vorher und nachher die berechneten Stile gemessen wurden — auf dem "
     "Bildschirm hätte man es überblättert."),

    ("vorher-messen", "Messen",
     "Vor einem mechanischen Umbau den Ist-Zustand messen, nicht nur danach",
     "Bei Änderungen, die das Aussehen oder Verhalten treffen könnten: vorher "
     "einen Zustand erfassen (berechnete Stile, Antwortgrößen, Zählwerte), "
     "danach denselben — und beides vergleichen. Ein Screenshot-Vergleich "
     "reicht nicht, kleine Verschiebungen sieht niemand.",
     "12.400 berechnete Eigenschaften über sechs Seiten verglichen; zwei echte "
     "Regressionen gefunden, die restlichen Abweichungen waren Live-Werte einer "
     "Auslastungsanzeige. Ohne die Vorher-Messung wäre beides unentdeckt "
     "geblieben."),

]


def gruppen():
    """[(Gruppenname, [Lehre, …])] in der Reihenfolge von LEHREN."""
    aus, index = [], {}
    for slug, gruppe, titel, tun, fall in LEHREN:
        if gruppe not in index:
            index[gruppe] = []
            aus.append((gruppe, index[gruppe]))
        index[gruppe].append({"slug": slug, "titel": titel, "tun": tun, "fall": fall})
    return aus
