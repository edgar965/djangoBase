/* tests_nummer.js — die Spalte „Nr.": Zahl ändern verschiebt die Zeile.
   ==========================================================================
   Ansage 17.08.2026: „mach eine Spalte bei den tests mit Nummer […] Die enthält
   zahlen, aufsteigend, die man ändern kann, dann verschieben sich die tests in
   der Tabelle."

   ABLAUF
     1. Zahl eintippen, Feld verlassen (oder Enter).
     2. Die Seite schickt die Kennung, die neue Nummer UND die aktuelle
        Reihenfolge ihres Abschnitts an `/hilfe/tests/nummer/`.
     3. Der Server ordnet um, speichert die Plätze und antwortet mit der neuen
        Reihenfolge. Erst dann hängt die Seite die Zeilen um.

   Warum der Server die Reihenfolge bestimmt und nicht der Browser: Sonst gäbe
   es zwei Meinungen darüber, wo ein Test steht — und nach dem nächsten Neuladen
   gewinnt immer die des Servers. Umgehängt wird nur, was er bestätigt hat.

   INNERHALB DES ABSCHNITTS: Die Tabelle ist nach Bereich gegliedert; die
   Nummern laufen je Abschnitt ab 1. Eine Zeile aus ihrem Bereich
   herauszuschieben würde die Gliederung zerlegen, deshalb bleibt sie darin. */
(function () {
    var URL = (document.getElementById('ts-nummer-url') || {}).textContent;
    if (URL) { URL = JSON.parse(URL); }

    /** Die Datenzeilen des Abschnitts, in dem diese Zeile steht. */
    function abschnitt(tr) {
        var koerper = tr.parentNode;
        var zeilen = [].slice.call(koerper.rows);
        var i = zeilen.indexOf(tr);
        var anfang = 0, ende = zeilen.length;
        for (var a = i; a >= 0; a--) {
            if (zeilen[a].dataset.gruppe !== undefined) { anfang = a + 1; break; }
        }
        for (var b = i + 1; b < zeilen.length; b++) {
            if (zeilen[b].dataset.gruppe !== undefined) { ende = b; break; }
        }
        return zeilen.slice(anfang, ende).filter(function (r) {
            return r.querySelector('input.ts-nr');
        });
    }

    function kennung(tr) {
        var feld = tr.querySelector('input.ts-nr');
        return feld ? feld.dataset.testId : '';
    }

    /** Meldung direkt am Feld — dort wurde getippt. */
    function melden(feld, text, art) {
        var alt = feld.parentNode.querySelector('.ts-nr-meldung');
        if (alt) { alt.remove(); }
        if (!text) { return; }
        var span = document.createElement('span');
        span.className = 'ts-nr-meldung ' + (art || '');
        span.textContent = text;
        feld.parentNode.appendChild(span);
    }

    async function setzen(feld) {
        var tr = feld.closest('tr');
        var zeilen = abschnitt(tr);
        var vorher = feld.dataset.stand || feld.defaultValue;
        if (!URL) { melden(feld, 'Kein Endpunkt konfiguriert.', 'fehler'); return; }
        feld.disabled = true;
        try {
            var r = await fetch(URL, {
                method: 'POST',
                headers: {'Content-Type': 'application/json',
                          'X-CSRFToken': (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || ''},
                credentials: 'same-origin',
                body: JSON.stringify({
                    id: kennung(tr), nummer: parseInt(feld.value, 10),
                    gruppe: zeilen.map(kennung),
                }),
            });
            var d = null;
            var roh = await r.text();
            try { d = JSON.parse(roh); } catch (e) { /* Rohtext zeigen */ }
            if (r.ok && d && d.ok) {
                umhaengen(tr.parentNode, zeilen, d.reihe);
                melden(feld, '', '');
                return;
            }
            melden(feld, (d && d.error) || roh.slice(0, 160) || ('HTTP ' + r.status),
                   'fehler');
            feld.value = vorher;
        } catch (fehler) {
            melden(feld, 'Netzwerkfehler: ' + fehler.message, 'fehler');
            feld.value = vorher;
        } finally {
            feld.disabled = false;
        }
    }

    /** Zeilen in die vom Server bestätigte Reihenfolge bringen und neu zählen. */
    function umhaengen(koerper, zeilen, reihe) {
        var nachId = {};
        zeilen.forEach(function (tr) { nachId[kennung(tr)] = tr; });
        var anker = zeilen[zeilen.length - 1].nextSibling;
        reihe.forEach(function (id, i) {
            var tr = nachId[id];
            if (!tr) { return; }
            koerper.insertBefore(tr, anker);
            var feld = tr.querySelector('input.ts-nr');
            feld.value = i + 1;
            feld.dataset.stand = String(i + 1);
            var zelle = feld.closest('td');
            if (zelle) { zelle.dataset.sort = String(i + 1); }
        });
    }

    /** Nach dem Sortieren die Nummern neu durchzählen — sie zeigen die
     *  SICHTBARE Position.
     *
     *  Sonst behauptet die Spalte etwas anderes, als man sieht: Nach einem
     *  Umsortieren standen dort vier Einsen untereinander (gemessen
     *  18.08.2026), weil jede Zahl aus der Grundordnung ihres Bereichs stammte.
     *  Wer dann eine Zahl ändert, ordnet die ANGEZEIGTE Reihenfolge um — und
     *  genau die schickt `setzen()` auch an den Server. */
    function nachzaehlen(tabelle) {
        const koerper = tabelle.tBodies[0];
        if (!koerper) return;
        let platz = 0;
        [].slice.call(koerper.rows).forEach(function (tr) {
            if (tr.dataset.gruppe !== undefined) { platz = 0; return; }
            const feld = tr.querySelector('input.ts-nr');
            if (!feld) return;
            platz++;
            feld.value = platz;
            feld.dataset.stand = String(platz);
            const zelle = feld.closest('td');
            if (zelle) zelle.dataset.sort = String(platz);
        });
    }

    document.addEventListener('tabelle:sortiert', function (e) {
        if (e.target && e.target.tBodies) nachzaehlen(e.target);
    });

    // Delegiert am document: Die Zeilen werden umgehängt und beim Sortieren neu
    // angeordnet — ein Listener je Feld wäre danach am falschen Element.
    document.addEventListener('change', function (e) {
        var feld = e.target.closest ? e.target.closest('input.ts-nr') : null;
        if (feld) { setzen(feld); }
    });
    document.addEventListener('keydown', function (e) {
        var feld = e.target.closest ? e.target.closest('input.ts-nr') : null;
        if (feld && e.key === 'Enter') { e.preventDefault(); feld.blur(); }
    });
    // Ausgangsstand festhalten, damit ein Fehlschlag die alte Zahl zurückbringt.
    document.querySelectorAll('input.ts-nr').forEach(function (f) {
        f.dataset.stand = f.value;
    });
})();
