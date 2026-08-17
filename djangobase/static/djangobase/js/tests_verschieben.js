/* tests_verschieben.js — die Combo-Boxen „Bereich" und „Verschieben".
   ==========================================================================
   Auswahl einer anderen Kategorie ODER eines anderen Bereichs schickt POST an
   `/hilfe/tests/verschieben/`; der Server haengt die Testdatei in den Ordner der
   Zielkategorie um (siehe `testverschieben.py`).

   WARUM DIE SEITE DANACH NEU LAEDT
   Nach dem Umzug heisst der Fall anders (die Test-ID enthaelt die Kategorie),
   er steht in einem anderen Reiter, und die Zaehler oben stimmen nicht mehr.
   Eine Zeile an die richtige Stelle zu schieben waere Kosmetik mit vier
   Nebenwirkungen; ein Neuladen zeigt den echten Zustand.

   KEIN STILLES SCHEITERN: Geht es nicht (Ziel belegt, Datei liegt nicht in einem
   `tests/<art>/`-Ordner), steht der Grund WOERTLICH neben der Box und die
   Auswahl springt zurueck. */
(function () {
    var URL_VERSCHIEBEN = (document.getElementById('ts-verschieben-url') || {})
        .textContent;
    if (URL_VERSCHIEBEN) { URL_VERSCHIEBEN = JSON.parse(URL_VERSCHIEBEN); }

    function csrf() {
        return (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
    }

    /** Meldung direkt an der Box — sie ist der Ort, an dem geklickt wurde. */
    function melden(box, text, art) {
        var alt = box.parentNode.querySelector('.ts-kat-meldung');
        if (alt) { alt.remove(); }
        var span = document.createElement('span');
        span.className = 'ts-kat-meldung ' + (art || '');
        span.textContent = text;
        box.parentNode.appendChild(span);
        return span;
    }

    /** Kategorie- ODER Bereichs-Box: dieselbe Mechanik, anderes Ziel.
     *  `select.ts-kat` traegt die alte Art in `data-art`, `select.ts-ber` den
     *  alten Bereich in `data-bereich`. Was gemeint ist, sagt `was` dem Server
     *  (Ansage 17.08.2026: „der Bereich und die Kategorie können bei jedem test
     *  in der Tabelle per Combo Box geändert werden"). */
    async function verschieben(box) {
        var ziel = box.value;
        var istBereich = box.classList.contains('ts-ber');
        var vorher = istBereich ? box.dataset.bereich : box.dataset.art;
        if (!URL_VERSCHIEBEN) {
            melden(box, 'Kein Endpunkt konfiguriert.', 'fehler');
            box.value = vorher;
            return;
        }
        box.disabled = true;
        melden(box, 'verschiebe …', 'laeuft');
        try {
            var r = await fetch(URL_VERSCHIEBEN, {
                method: 'POST',
                headers: {'Content-Type': 'application/json',
                          'X-CSRFToken': csrf()},
                credentials: 'same-origin',
                body: JSON.stringify({
                    id: box.dataset.testId, ziel: ziel,
                    was: istBereich ? 'bereich' : 'kategorie',
                }),
            });
            var roh = await r.text();
            var d = null;
            try { d = JSON.parse(roh); } catch (e) { /* kein JSON: Rohtext zeigen */ }
            if (r.ok && d && d.ok) {
                melden(box, d.meldung || 'verschoben', 'gut');
                setTimeout(function () { location.reload(); }, 900);
                return;
            }
            // Die Meldung des Servers WOERTLICH — ein rotes „Fehler" ohne Grund
            // laesst den Nutzer genauso ratlos wie gar keine Anzeige.
            melden(box, (d && d.error) || roh.slice(0, 200)
                        || ('HTTP ' + r.status), 'fehler');
            box.value = vorher;
        } catch (fehler) {
            melden(box, 'Netzwerkfehler: ' + fehler.message, 'fehler');
            box.value = vorher;
        } finally {
            box.disabled = false;
        }
    }

    // Delegiert am document: Die Tabellen werden beim Sortieren neu gehaengt,
    // ein Listener je Box waere danach am falschen Element.
    document.addEventListener('change', function (e) {
        var box = e.target.closest
            ? e.target.closest('select.ts-kat, select.ts-ber') : null;
        if (box) { verschieben(box); }
    });
})();
