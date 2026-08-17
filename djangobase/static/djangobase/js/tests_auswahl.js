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
        if (run) { starten(karte(run)); }
    });

    /** Auswahl als Formular abschicken — der Server fährt sie in einem Lauf. */
    function starten(k) {
        var ids = gewaehlt(k).map(function (c) { return c.value; });
        if (!ids.length) return;
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
