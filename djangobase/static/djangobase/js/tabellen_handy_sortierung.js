/* Sortieren der Handy-Karten (21.11.2026, StayNestor-Heizung; Edgar: „die sortierung der Thermostate ist gaga auf
 * dem Handy, die soll immer nach Ziffer sortiert werden beim Start", „wie sortiere ich die anders auf dem Handy??").
 *
 * Bis 768 px ist der Tabellenkopf der Karten aus (css/tabellen_handy.css) — also auch das Sortieren per Klick, und
 * es galt die Reihenfolge vom Server oder eine am Rechner gemerkte. Darum hier: beim Start nach dem Titel der Karte
 * (Spalte mit ``data-handy="titel"``), aufsteigend, Ziffern als Zahl („9 Bad" vor „10 Bad", wie
 * ``TabellenSortierung._anwenden``); darüber eine Auswahl „Sortieren“ mit allen sortierbaren Spalten und ein Knopf
 * ↑/↓. Die Wahl gilt je Tabellenschlüssel, solange die Seite offen ist, und wird auch nach dem Neuschreiben einer
 * Tabelle wieder angewandt. Gemerkt wird nichts — die Sortierung am Rechner bleibt, wie sie ist.
 */
export class HandySortierung {
    constructor() {
        this.wahl = new Map();   // data-sort-key → {idx, auf}
    }

    /** Auswahl einfügen (einmal je Tabelle) und sortieren, wenn die Tabelle anders steht als gewählt. */
    anpassen(tabelle) {
        const kopf = tabelle.tHead?.rows[tabelle.tHead.rows.length - 1];
        const sortierer = window.TabellenSortierung;
        if (!kopf || !sortierer || tabelle.dataset.sortAus !== undefined) return;
        const w = this.gewaehlt(tabelle);
        if (!this.auswahlDa(tabelle)) tabelle.before(this.auswahl(tabelle, kopf, w));
        const richtung = w.auf ? 'asc' : 'desc';
        // nur wenn nötig: _anwenden hängt die Zeilen um, das löst den MutationObserver erneut aus
        if (tabelle.dataset.sortIdx !== String(w.idx) || tabelle.dataset.sortDir !== richtung) {
            sortierer._anwenden(tabelle, w.idx, w.auf);
        }
    }

    gewaehlt(tabelle) {
        const schluessel = tabelle.dataset.sortKey || '';
        if (!this.wahl.has(schluessel)) {
            const titel = tabelle.tBodies[0]?.querySelector(':scope > tr > td[data-handy="titel"]');
            this.wahl.set(schluessel, { idx: titel ? titel.cellIndex : 0, auf: true });
        }
        return this.wahl.get(schluessel);
    }

    auswahlDa(tabelle) {
        return tabelle.previousElementSibling?.classList.contains('db-handy-sortwahl');
    }

    auswahl(tabelle, kopf, w) {
        const leiste = document.createElement('div');
        leiste.className = 'db-handy-sortwahl';
        const liste = document.createElement('select');
        liste.setAttribute('aria-label', 'Sortieren nach');
        [...kopf.cells].forEach((th, i) => {
            const text = th.textContent.replace(/[⇅↕▲▼↑↓]/g, '').trim();
            if (!text || th.dataset.sortAus !== undefined) return;
            liste.add(new Option(text, String(i), false, i === w.idx));
        });
        const knopf = document.createElement('button');
        knopf.type = 'button';
        knopf.textContent = w.auf ? '↑' : '↓';
        knopf.title = 'Richtung umkehren';
        const anwenden = () => {
            const neu = { idx: Number(liste.value), auf: knopf.textContent === '↑' };
            this.wahl.set(tabelle.dataset.sortKey || '', neu);
            window.TabellenSortierung._anwenden(tabelle, neu.idx, neu.auf);
        };
        liste.addEventListener('change', anwenden);
        knopf.addEventListener('click', () => {
            knopf.textContent = knopf.textContent === '↑' ? '↓' : '↑';
            anwenden();
        });
        const beschriftung = document.createElement('label');
        beschriftung.append('Sortieren ', liste);
        leiste.append(beschriftung, knopf);
        return leiste;
    }
}
