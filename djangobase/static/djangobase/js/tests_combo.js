/* tests_combo.js — die Auswahllisten erst beim Aufklappen füllen.
   ==========================================================================
   Ansage 18.08.2026: „der aufbau der testseiten ist langsam".

   Gemessen wurde, bevor etwas geändert wurde: Die Seite wog 4,4 MB, und über
   die Hälfte davon waren `<option>`-Elemente — rund 2.750 Zeilen mit je zwei
   Auswahlfeldern (Kategorie: 6 Einträge, Bereich: 15) ergeben etwa 58.000
   Optionen. Benutzt wird davon eine, wenn überhaupt.

   Deshalb rendert der Server nur noch die AKTUELLE Option je Feld. Die
   vollständige Liste steht EINMAL im DOM (als JSON), und dieses Modul füllt
   das Feld, das gerade aufgeklappt wird.

   Warum `mousedown`/`focus` und nicht `click`: Der Browser baut die Liste auf,
   bevor `click` feuert — bei `mousedown` sind die Einträge rechtzeitig da.
   Tastaturbedienung (Tab, dann Pfeiltaste) fängt `focus` ab. */
(function () {
    const speicher = {};

    /** Die Liste zu einem Feld — einmal geparst, dann gemerkt. */
    function liste(name) {
        if (speicher[name] !== undefined) return speicher[name];
        const feld = document.getElementById(name);
        let daten = [];
        try {
            daten = feld ? JSON.parse(feld.textContent) : [];
        } catch (e) {
            // Kein stilles Weiter: Ohne Liste bliebe die Box bei einem Eintrag
            // stehen, und niemand wüsste warum.
            console.error('[Tests] Auswahlliste ' + name + ' unlesbar', e);
        }
        speicher[name] = daten;
        return daten;
    }

    function fuellen(box) {
        if (!box.classList.contains('ts-lazy')) return;
        const eintraege = liste(box.dataset.liste);
        if (!eintraege.length) return;
        const gewaehlt = box.value;
        box.textContent = '';
        eintraege.forEach(function (e) {
            const o = document.createElement('option');
            o.value = e.wert;
            o.textContent = e.name;
            if (e.wert === gewaehlt) o.selected = true;
            box.appendChild(o);
        });
        // Steht der aktuelle Wert nicht in der Liste (abgeleiteter Bereich,
        // nicht verschiebbare Kategorie), gehört er trotzdem hinein — sonst
        // springt die Anzeige beim Aufklappen auf einen fremden Wert.
        if (box.value !== gewaehlt) {
            const o = document.createElement('option');
            o.value = gewaehlt;
            o.textContent = gewaehlt;
            o.selected = true;
            box.insertBefore(o, box.firstChild);
        }
        box.classList.remove('ts-lazy');
    }

    ['mousedown', 'focus', 'keydown'].forEach(function (art) {
        document.addEventListener(art, function (e) {
            const box = e.target.closest ? e.target.closest('select.ts-lazy') : null;
            if (box) fuellen(box);
        }, true);
    });
})();
