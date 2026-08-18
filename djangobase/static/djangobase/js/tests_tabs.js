/* tests_tabs.js — Reiter umschalten und den Inhalt bei Bedarf nachladen.
   ==========================================================================
   Ansage 18.08.2026: „der aufbau der testseiten ist langsam".

   Gemessen VOR der Änderung: 2,92 MB HTML, 1.513 Tabellenzeilen, rund 0,6 s
   Aufbau — für sechs Reiter, von denen man einen sieht. Jetzt liefert der
   Server nur den aktiven; die übrigen sind leere Hüllen (`data-lazy`), deren
   Inhalt beim ersten Klick über `?tab=…&teil=1` kommt.

   WAS NACH DEM EINSETZEN PASSIEREN MUSS
   Die Tabellen-Module binden beim Laden EINMAL: Sortierung und Spaltenbreiten
   kennen den neuen Inhalt sonst nicht, die Bereichs-Abschnitte auch nicht. Sie
   werden deshalb nach jedem Nachladen erneut gebunden — und die
   Spaltenbreiten-Gruppe umfasst dann ALLE Tabellen der Seite, damit dieselbe
   Spalte überall gleich breit bleibt.

   OHNE JAVASCRIPT bleibt die Seite bedienbar: Jeder Reiter ist auch eine
   Adresse (`?tab=Unit`), und der Server rendert sie vollständig. Schlägt das
   Nachladen fehl, wird genau dorthin gewechselt statt eine leere Fläche zu
   zeigen. */
import { TabellenSortierung } from './tabellen_sortierung.js';
import { TabellenBreiten } from './tabellen_breiten.js';

class Reiter {
    constructor() {
        this.seite = document.querySelector('.ts-page');
        this.tabs = [...document.querySelectorAll('.ts-tab')];
        this.laeuft = new Set();          // Reiter, die gerade geladen werden
    }

    binden() {
        if (!this.seite) return this;
        this.tabs.forEach(t => t.addEventListener('click', () => this.zeigen(t.dataset.tab)));
        const start = this.seite.dataset.aktivTab
            || (this.tabs.length ? this.tabs[0].dataset.tab : '');
        if (start) this.zeigen(start, true);
        this.tabellenBinden();
        return this;
    }

    async zeigen(name, still) {
        this.tabs.forEach(t => t.classList.toggle('aktiv', t.dataset.tab === name));
        document.querySelectorAll('.ts-panel').forEach(p =>
            p.classList.toggle('aktiv', p.dataset.panel === name));
        const panel = document.querySelector('.ts-panel[data-panel="' + CSS.escape(name) + '"]');
        if (!panel || panel.dataset.lazy === undefined) return;
        if (this.laeuft.has(name)) return;
        this.laeuft.add(name);
        panel.innerHTML = '<p class="ts-empty">Lade …</p>';
        try {
            const url = location.pathname + '?tab=' + encodeURIComponent(name) + '&teil=1';
            const antwort = await fetch(url, {credentials: 'same-origin'});
            if (!antwort.ok) throw new Error('HTTP ' + antwort.status);
            panel.innerHTML = await antwort.text();
            delete panel.dataset.lazy;
            this.nachbereiten(panel);
        } catch (fehler) {
            // Kein leeres Panel stehen lassen: Der Reiter ist auch eine Adresse.
            console.error('[Tests] Reiter ' + name + ' nicht geladen', fehler);
            if (!still) location.href = location.pathname + '?tab=' + encodeURIComponent(name);
        } finally {
            this.laeuft.delete(name);
        }
    }

    /** Skripte auf frisch eingesetzten Inhalt anwenden.
     *
     *  REIHENFOLGE ZÄHLT (gemessen 18.08.2026): Zuerst müssen die Module ihre
     *  Vorlagen sichern — `tests_bereiche.js` merkt sich die Abschnittszeilen,
     *  bevor irgendjemand sie anfasst. Erst danach die Sortierung binden: Sie
     *  wendet eine gemerkte Sortierung sofort an und NIMMT DIE ABSCHNITTSZEILEN
     *  HERAUS. Andersherum waren sie weg, bevor sie jemand kannte — und kamen
     *  auch beim Zurücksortieren nicht wieder. */
    nachbereiten(panel) {
        document.dispatchEvent(new CustomEvent('tests:panel-geladen', {detail: {panel}}));
        this.tabellenBinden();
        // `<script>` aus innerHTML läuft NICHT — die UI-Tests brauchen ihres.
        panel.querySelectorAll('script').forEach(alt => {
            const neu = document.createElement('script');
            [...alt.attributes].forEach(a => neu.setAttribute(a.name, a.value));
            neu.textContent = alt.textContent;
            alt.replaceWith(neu);
        });
        // Nummern-Felder brauchen ihren Ausgangsstand (für den Fehlerfall).
        panel.querySelectorAll('input.ts-nr').forEach(f => { f.dataset.stand = f.value; });
    }

    tabellenBinden() {
        const tabellen = [...document.querySelectorAll('table[data-sort-key]')];
        if (tabellen.length) new TabellenBreiten(tabellen, 'hilfe-tests').binden();
        TabellenSortierung.binden();
    }
}

new Reiter().binden();
