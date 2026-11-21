/* Knopf „mehr“ der Handy-Karten (21.11.2026, opt-in; css/tabellen_handy.css, tabellen_handy.py).
 *
 * Bis 768 px hängt das Modul an jede Zeile einer Tabelle ``db-handy``, die Zellen der Rolle ``mehr`` hat, eine
 * Zelle mit dem Knopf „mehr“; Tippen klappt diese Zellen auf und zu (``tr.db-handy-offen``). Über 768 px nimmt es
 * die Knopfzellen wieder heraus — dort zählen Spaltenbreiten und -reihenfolge die Zellen, und eine Zelle ohne
 * Kopf darf da nicht stehen. Seiten, die ihre Tabellen per ``innerHTML`` neu schreiben, bekommen die Knöpfe
 * über den MutationObserver zurück (einmal je Bild, nicht je Änderung). Aufgeklappt bleibt eine Zeile über das
 * Neuschreiben hinweg, wenn sie ein ``data-id`` trägt (``_tabelle.html``: ``id`` der Zeile).
 *
 *     import { TabellenHandy } from '…/djangobase/js/tabellen_handy.js';
 *     new TabellenHandy(document.getElementById('meine-flaeche')).binden();
 *
 * Seit 21.11.2026 auch das Sortieren ohne Tabellenkopf (``HandySortierung``).
 */
import { HandySortierung } from './tabellen_handy_sortierung.js';

export class TabellenHandy {
    static BREITE = '(max-width: 768px)';

    constructor(wurzel = document.body) {
        this.wurzel = wurzel;
        this.medien = window.matchMedia(TabellenHandy.BREITE);
        this.geplant = false;
        this.offen = new Set(); // data-id aufgeklappter Zeilen
        this.sortierung = new HandySortierung();
    }

    binden() {
        if (!this.wurzel) return this;
        this.wurzel.addEventListener('click', (e) => {
            const knopf = e.target.closest('.db-handy-mehr');
            if (knopf) this.umschalten(knopf);
        });
        this.medien.addEventListener('change', () => this.anpassen());
        new MutationObserver(() => this.planen()).observe(this.wurzel, { childList: true, subtree: true });
        this.anpassen();
        return this;
    }

    planen() {
        if (this.geplant) return;
        this.geplant = true;
        requestAnimationFrame(() => {
            this.geplant = false;
            this.anpassen();
        });
    }

    anpassen() {
        const handy = this.medien.matches;
        for (const zeile of this.wurzel.querySelectorAll('table.db-handy > tbody > tr')) {
            const knopf = zeile.querySelector(':scope > td.db-handy-knopf');
            if (!handy) {
                knopf?.remove();
            } else if (!knopf && zeile.querySelector(':scope > td[data-handy="mehr"]')) {
                const zelle = TabellenHandy.knopfZelle();
                zeile.append(zelle);
                if (zeile.dataset.id && this.offen.has(zeile.dataset.id)) this.zeigen(zeile, true);
            }
        }
        // ohne sichtbaren Kopf: nach dem Titel sortieren, Auswahl „Sortieren“ (tabellen_handy_sortierung.js)
        if (handy) this.wurzel.querySelectorAll('table.db-handy').forEach((t) => this.sortierung.anpassen(t));
    }

    umschalten(knopf) {
        const zeile = knopf.closest('tr');
        const offen = !zeile.classList.contains('db-handy-offen');
        this.zeigen(zeile, offen);
        if (!zeile.dataset.id) return;
        if (offen) this.offen.add(zeile.dataset.id);
        else this.offen.delete(zeile.dataset.id);
    }

    zeigen(zeile, offen) {
        zeile.classList.toggle('db-handy-offen', offen);
        const knopf = zeile.querySelector('.db-handy-mehr');
        if (!knopf) return;
        knopf.textContent = offen ? 'weniger' : 'mehr';
        knopf.setAttribute('aria-expanded', String(offen));
    }

    static knopfZelle() {
        const zelle = document.createElement('td');
        zelle.className = 'db-handy-knopf';
        zelle.innerHTML = '<button type="button" class="db-handy-mehr" aria-expanded="false">mehr</button>';
        return zelle;
    }
}
