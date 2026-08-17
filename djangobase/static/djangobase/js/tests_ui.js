/* tests_ui.js — die Browser-/UI-Tests der Seite Hilfe → Tests.
   ==========================================================================
   Baut die Zeilen der UI-Test-Tabelle (die Faelle stehen in der `testcases.js`
   des Projekts, nicht im Server), faehrt einen Fall im Iframe und meldet seine
   Laufzeit an `/hilfe/tests/dauer/` — damit auch die Browser-Tests ihre letzten
   vier Laeufe zeigen.

   Kopfzeile und Spalten kommen aus `Testtabelle.SPALTEN`; hier werden nur die
   `<tr>` gefuellt — NEUN Zellen, in dieser Reihenfolge:
       Auswahl · Nr. · Kategorie · Bereich · Name · Ziel · letzte · Ø ·
       Trend · letzte 4 Läufe · Run
   Die Laufzeit-Zellen schreibt `testzeiten.js`, damit die Darstellung dieselbe
   ist wie in den serverseitig gebauten Tabellen.

   Konfiguration steht im DOM (`#ts-ui-config`), nicht in Template-Variablen —
   sonst muesste diese Datei wieder ins Template zurueck. */

/* Die eigene Versions-Query WEITERREICHEN. Ein `import` ohne sie holt das
   Nachbarmodul aus dem Browser-Cache — gemessen am 17.08.2026: die
   Einstiegsdatei war neu, das importierte Modul alt, und der Fehler sah aus
   wie ein Fehler in der Darstellung. `import.meta.url` traegt die Query, mit
   der diese Datei geladen wurde. */
const { zeitenSchreiben, esc } =
    await import("./testzeiten.js" + new URL(import.meta.url).search);

(function () {
    var CFG = JSON.parse(document.getElementById("ts-ui-config").textContent || "{}");
    var SEITEN = CFG.seiten || {};
    var HISTORIE = JSON.parse(document.getElementById("ts-ui-historie").textContent || "{}");
    var DAUER_URL = CFG.dauerUrl;
    var RUNNER_URL = CFG.runner, CASES_URL = CFG.cases;
    var listEl = document.querySelector('table[data-sort-key="tests-ui-browser"] tbody');
    var hintEl = document.getElementById("ts-ui-hint");
    var frame = document.getElementById("ts-ui-frame");
    var countEl = document.getElementById("ts-ui-count");
    var runnerText = "", casesText = "";

    function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

    // testcases.js + runner.js als Text holen (zum Injizieren ins Iframe) und
    // testcases.js zusätzlich hier laden, um die Liste aufzubauen.
    Promise.all([
        fetch(RUNNER_URL).then(function (r) { return r.text(); }),
        fetch(CASES_URL).then(function (r) { return r.text(); })
    ]).then(function (txt) {
        runnerText = txt[0]; casesText = txt[1];
        try { (0, eval)(casesText); } catch (e) {}      // definiert window.SPIN.testcases hier
        bauen();
    }).catch(function (e) { hintEl.textContent = "Konnte Test-Dateien nicht laden: " + e; });

    // Spaltenreihenfolge wie in `Testtabelle.SPALTEN`:
    // Name · Ziel · letzte · Ø · Trend · letzte 4 Läufe · Run
    function bauen() {
        var tc = (window.SPIN && window.SPIN.testcases) || {};
        var n = 0;
        listEl.innerHTML = "";
        Object.keys(tc).forEach(function (g) {
            var seite = SEITEN[g];
            (tc[g] || []).forEach(function (c) {
                n++;
                var kennung = "ui:" + g + "." + c.id;
                var tr = document.createElement("tr");
                // ELF Zellen, genau wie `Testtabelle.SPALTEN` (Auswahl, Nr.,
                // Kategorie, Bereich, Testcase, Ziel, letzte, Ø, Trend, Läufe,
                // Run). Fehlt eine, rutscht alles Folgende in die falsche
                // Spalte — und das faellt erst auf, wenn jemand die Zahlen
                // liest. Der Test `test_js_kennt_dieselben_spalten` haelt die
                // Zuordnung mit `SPALTEN` zusammen.
                tr.innerHTML =
                    '<td class="ts-wahl-zelle"><input type="checkbox" '
                    + 'class="ts-wahl" value="' + esc(kennung)
                    + '" aria-label="auswählen"></td>'
                    + '<td class="ts-nr-zelle">' + n + '</td>'
                    + '<td><span class="ts-kat-fest" title="Browser-Test aus der '
                    + 'testcases.js — nicht verschiebbar">UI</span></td>'
                    + '<td><span class="ts-bereich" data-bereich="ui">UI</span></td>'
                    + '<td><i class="bi bi-dot"></i> ' + esc(c.name)
                    + ' <span class="ts-ui-status" data-st></span></td>'
                    + '<td class="ts-ziel">' + esc(g + " · " + c.id) + "</td>"
                    + '<td class="num" data-letzte></td>'
                    + '<td class="num" data-schnitt></td>'
                    + '<td class="num"></td>'
                    + "<td data-laeufe></td>"
                    + '<td><button type="button" class="ts-run">'
                    + '<i class="bi bi-play-fill"></i> Run</button></td>';
                var btn = tr.querySelector("button");
                var st = tr.querySelector("[data-st]");
                if (!seite) { btn.disabled = true; btn.title = "Keine Seite für Gruppe " + g; }
                else btn.addEventListener("click", function () { runOne(g, c.id, kennung, seite, btn, st, tr); });
                zeitenSchreiben(tr, HISTORIE[kennung] || []);
                listEl.appendChild(tr);
            });
        });
        hintEl.style.display = "none";
        if (countEl) countEl.textContent = n;
    }

    /** Laufzeit an den Server melden — sonst hätten die Browser-Tests als
     *  einzige Liste keine Historie (Ansage 17.08.2026). Antwort ist die
     *  aktualisierte Reihe, die direkt in die Zeile geschrieben wird. */
    async function dauerMelden(kennung, sekundenWert, tr) {
        var csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
        try {
            var r = await fetch(DAUER_URL, {
                method: "POST",
                headers: {"Content-Type": "application/json", "X-CSRFToken": csrf},
                credentials: "same-origin",
                body: JSON.stringify({id: kennung, dauer: sekundenWert}),
            });
            var d = await r.json();
            if (d.ok) { HISTORIE[kennung] = d.laeufe; zeitenSchreiben(tr, d.laeufe); }
            else console.error("[UI-Test] Laufzeit nicht gespeichert:", d.error);
        } catch (e) {
            console.error("[UI-Test] Laufzeit nicht gespeichert:", e);
        }
    }

    async function runOne(group, id, kennung, seite, btn, st, tr) {
        btn.disabled = true;
        st.className = "ts-ui-status laeuft"; st.textContent = "läuft …";
        var t0 = performance.now();
        try {
            await new Promise(function (res, rej) {
                frame.onload = res; frame.onerror = rej; frame.src = seite;
            });
            await sleep(3500);                       // JS-/Karten-Init im Iframe
            var w = frame.contentWindow;
            if (String(w.location.pathname).indexOf("login") !== -1)
                throw new Error("nicht angemeldet (Iframe → Login)");
            w.eval(runnerText); w.eval(casesText);   // same-origin Injektion
            var r = await w.SPIN.runOne(group, id);
            st.className = "ts-ui-status " + (r.ok ? "ok" : "fail");
            st.textContent = r.ok ? "✓" : ("✗ " + (r.error || "Fehler"));
            // Die Laufzeit des Falls selbst, nicht die Wartezeit auf das
            // Iframe: `r.ms` kommt aus dem Runner. Fehlt es, bleibt die
            // gemessene Gesamtzeit.
            var sek = (typeof r.ms === "number" ? r.ms / 1000
                                                : (performance.now() - t0) / 1000);
            await dauerMelden(kennung, sek, tr);
        } catch (e) {
            st.className = "ts-ui-status fail";
            st.textContent = "✗ " + (e && e.message ? e.message : e);
        } finally { btn.disabled = false; }
    }

})();
