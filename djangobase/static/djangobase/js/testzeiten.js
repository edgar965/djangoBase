/* testzeiten.js — die Laufzeit-Zellen einer Testcase-Zeile, für ALLE Runner.
   ==========================================================================
   Die Tabelle hat EINE Spaltendefinition (`testtabelle.Testtabelle.SPALTEN`).
   Wer Zeilen im Browser baut oder nach einem Lauf fortschreibt, muss sie genau
   so treffen — sonst rutschen Werte in die falsche Spalte, und niemand sieht es
   sofort. Deshalb steht die Zuordnung hier einmal und wird importiert:

       import { SPALTE, sekunden, zeitenSchreiben } from './testzeiten.js';

   Zwei Nutzer: die Browser-/UI-Tests (`tests_ui.js`, Zeilen entstehen aus der
   testcases.js) und Projektseiten mit eigenem AJAX-Runner (assistant:
   /tests/<bereich>/<art>/). Vorher trug jeder seine eigene Formatierung — als
   die Checkbox-Spalte dazukam, hatte die UI-Tabelle plötzlich sieben Zellen
   unter neun Überschriften. */

/** Spaltenpositionen — identisch zu `Testtabelle.SPALTEN`. */
export const SPALTE = {
    wahl: 0, nummer: 1, kategorie: 2, bereich: 3, name: 4, ziel: 5,
    letzte: 6, schnitt: 7, trend: 8, laeufe: 9, run: 10,
};

/** Unter einer Sekunde immer Millisekunden (Ansage 17.08.2026) — dieselbe
 *  Regel wie serverseitig in `zeitformat.dauer_text`. */
export function sekunden(w) {
    if (w === null || w === undefined) return "—";
    if (w < 1) return Math.round(w * 1000) + " ms";
    return Number(w).toFixed(2).replace(".", ",") + " s";
}

/** „17.08.2026 17:02:32" → „17.08. 17:02" (wie `Testtabelle._kurze_zeit`). */
export function kurzeZeit(z) {
    const t = String(z || "").split(" ");
    return t.length === 2 ? t[0].slice(0, 6) + " " + t[1].slice(0, 5) : z;
}

export function esc(s) {
    const d = document.createElement("div");
    d.textContent = s === null || s === undefined ? "" : s;
    return d.innerHTML;
}

/** Eine Zelle setzen: Rohwert zum Sortieren, Text zum Lesen. */
export function setzeZeit(td, wert) {
    if (!td) return;
    if (wert === null || wert === undefined) {
        td.removeAttribute("data-sort");
        td.innerHTML = '<span class="ts-nie">—</span>';
        return;
    }
    td.dataset.sort = wert;
    td.textContent = sekunden(wert);
}

/** Laufzeit-Spalten einer Zeile aus der Historie füllen (letzte · Ø · Läufe). */
export function zeitenSchreiben(tr, laeufe) {
    if (!tr) return;
    const zellen = tr.children;
    const reihe = laeufe || [];
    const letzte = reihe.length ? reihe[0].dauer : null;
    const mittel = reihe.length
        ? reihe.reduce((s, x) => s + x.dauer, 0) / reihe.length : null;
    setzeZeit(zellen[SPALTE.letzte], letzte);
    setzeZeit(zellen[SPALTE.schnitt], mittel);
    const zelle = zellen[SPALTE.laeufe];
    if (!zelle) return;
    zelle.dataset.sort = reihe.length;
    zelle.innerHTML = reihe.length
        ? reihe.map(l => '<span class="ts-lauf" title="' + esc(l.zeit) + '">'
              + esc(kurzeZeit(l.zeit)) + " · " + sekunden(l.dauer) + "</span>").join(" ")
        : '<span class="ts-nie">noch nie gelaufen</span>';
}

/** Status in der Namensspalte („läuft …", ✓, ✗) — der Platz dafür wird
 *  serverseitig im Knopf-Modus gerendert (`<span class="ts-status">`). */
export function statusSetzen(tr, text, klasse) {
    if (!tr) return;
    const zelle = tr.children[SPALTE.name];
    if (!zelle) return;
    let feld = zelle.querySelector("[data-status]");
    if (!feld) {
        feld = document.createElement("span");
        feld.className = "ts-status";
        feld.dataset.status = "";
        zelle.appendChild(feld);
    }
    feld.className = "ts-status " + (klasse || "");
    feld.textContent = text || "";
}
