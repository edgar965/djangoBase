/* tests_auswahl.js — Checkbox-Auswahl je Karte und „Ausgewählte ausführen".
   ==========================================================================
   Ansage 17.08.2026: „bei jedem test noch eine spalte mit Checkbox zum
   Auswählen, und in dem Header einen Button zum laufen der ausgewählten. Button
   für alle auswählen".

   EIN LAUF, NICHT N LÄUFE
   Die Auswahl geht als EIN POST an die Tests-Seite; der Server baut daraus ein
   einziges `manage.py test <ziel> <ziel> …`. Nacheinander je Fall zu starten
   hiesse, die Testdatenbank je Fall neu aufzubauen — bei zwanzig Haken waeren
   das zwanzig Minuten Aufbau fuer Sekunden Testzeit.

   WARUM EIN ECHTES FORMULAR UND KEIN fetch
   Das Ergebnis (stdout, Dauer, Bestanden/Fehlgeschlagen) rendert der Server auf
   derselben Seite. Ein abgeschicktes Formular bringt genau das; ein `fetch`
   muesste die Antwort selbst zusammenbauen — zweite Darstellung fuer dasselbe.

   JE KARTE EINE AUSWAHL: Die Knoepfe im Kopf wirken nur auf die Tabelle IHRER
   Karte. Sonst wuerde „Alle auswählen" in „Unit" die Faelle aus „Component"
   mitnehmen, und der Lauf faehrt Dinge, die niemand angehakt hat. */
(function () {
    function karte(el) { return el.closest('.ts-wahlkarte'); }
    function kaesten(k) { return [...k.querySelectorAll('input.ts-wahl')]; }
    function gewaehlt(k) { return kaesten(k).filter(function (c) { return c.checked; }); }

    /** Zähler und Zustand der Knöpfe an die Auswahl anpassen. */
    function auffrischen(k) {
        var n = gewaehlt(k).length;
        var run = k.querySelector('.ts-wahl-run');
        var alle = k.querySelector('.ts-wahl-alle');
        if (run) {
            run.disabled = n === 0;
            var zahl = run.querySelector('.ts-wahl-zahl');
            if (zahl) zahl.textContent = n;
        }
        if (alle) {
            var voll = n > 0 && n === kaesten(k).length;
            alle.dataset.an = voll ? '1' : '0';
            alle.innerHTML = voll
                ? '<i class="bi bi-square"></i> Auswahl aufheben'
                : '<i class="bi bi-check2-square"></i> Alle auswählen';
        }
    }

    document.addEventListener('change', function (e) {
        if (e.target.classList && e.target.classList.contains('ts-wahl')) {
            var k = karte(e.target);
            if (k) auffrischen(k);
        }
    });

    /** Die Zeilen EINES Bereichs: ab der Abschnittszeile bis zur nächsten.
     *
     *  Über die Nachbarschaft im DOM, nicht über `data-bereich` an der Zeile:
     *  Nach einem Umsortieren stehen die Gruppen woanders, und die Zeile
     *  zwischen zwei Abschnitten ist die, die sichtbar dazugehört. */
    function gruppenKaesten(kopf) {
        var aus = [];
        for (var tr = kopf.nextElementSibling; tr; tr = tr.nextElementSibling) {
            if (tr.dataset.gruppe !== undefined) break;
            var c = tr.querySelector('input.ts-wahl');
            if (c) aus.push(c);
        }
        return aus;
    }

    document.addEventListener('click', function (e) {
        var alle = e.target.closest ? e.target.closest('.ts-wahl-alle') : null;
        if (alle) {
            var k = karte(alle);
            var an = alle.dataset.an !== '1';
            kaesten(k).forEach(function (c) { c.checked = an; });
            auffrischen(k);
            return;
        }
        var run = e.target.closest ? e.target.closest('.ts-wahl-run') : null;
        if (run) { starten(karte(run)); return; }
        // --- Abschnittszeile eines Bereichs: an-/abhaken bzw. nur ihn fahren.
        var bWahl = e.target.closest ? e.target.closest('.ts-ber-wahl') : null;
        if (bWahl) {
            var kopf = bWahl.closest('tr');
            var kaest = gruppenKaesten(kopf);
            var einAn = kaest.some(function (c) { return !c.checked; });
            kaest.forEach(function (c) { c.checked = einAn; });
            auffrischen(karte(bWahl));
            return;
        }
        var bRun = e.target.closest ? e.target.closest('.ts-ber-run') : null;
        if (bRun) {
            var ids = gruppenKaesten(bRun.closest('tr'))
                .map(function (c) { return c.value; });
            if (ids.length) fahren(karte(bRun), ids);
        }
    });

    /** Auswahl als Formular abschicken — der Server fährt sie in einem Lauf.
     *
     *  AUSNAHME: Seiten mit eigenem Runner (`<body data-tests-auswahl="ereignis">`
     *  bzw. ein Vorfahre mit diesem Attribut) bekommen stattdessen ein
     *  CustomEvent `tests:auswahl-lauf` mit den Kennungen. Der assistant faehrt
     *  seine `/tests/…`-Seiten per Streaming-API und schreibt den Fortschritt in
     *  die Zeilen; ein Formular-POST wuerde die Seite neu laden und genau das
     *  wegwerfen. Die Auswahl-Bedienung bleibt dieselbe — nur das Ziel wechselt. */
    function starten(k) {
        fahren(k, gewaehlt(k).map(function (c) { return c.value; }));
    }

    function fahren(k, ids) {
        if (!ids || !ids.length) return;
        if (k.closest('[data-tests-auswahl="ereignis"]')) {
            k.dispatchEvent(new CustomEvent('tests:auswahl-lauf', {
                bubbles: true, detail: {ids: ids, karte: k},
            }));
            return;
        }
        var f = document.createElement('form');
        f.method = 'post';
        f.action = location.pathname + location.search;
        f.style.display = 'none';
        var csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
        feld(f, 'csrfmiddlewaretoken', csrf);
        ids.forEach(function (id) { feld(f, 'ids', id); });
        var seite = document.querySelector('.ts-page');
        feld(f, 'tab', (seite && seite.dataset.aktivTab) || '');
        document.body.appendChild(f);
        f.submit();
    }

    function feld(form, name, wert) {
        var i = document.createElement('input');
        i.type = 'hidden'; i.name = name; i.value = wert;
        form.appendChild(i);
    }

    // Startzustand (nach einem Reload sind die Haken weg, die Zähler müssen mit).
    document.querySelectorAll('.ts-wahlkarte').forEach(auffrischen);
})();
