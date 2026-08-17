/* tests_bereiche.js — die Abschnittszeilen je Bereich am Leben halten.
   ==========================================================================
   Der Server rendert in jede Testcase-Tabelle vor jedem neuen Bereich eine
   Zeile mit Namen, Anzahl und den zwei Knöpfen („Auswählen", „Bereich
   ausführen"). Sortiert der Nutzer nach einer anderen Spalte, stimmt diese
   Gliederung nicht mehr — die Sortierung nimmt die Zeilen deshalb heraus
   (`tabellen_sortierung.js`) und meldet `tabelle:sortiert`.

   Hier steht die Antwort darauf:

     * nach der Spalte „Bereich" sortiert  -> Abschnittszeilen an den
       Wechselstellen wieder einsetzen, Zähler und Trennlinien neu
     * nach irgendetwas anderem sortiert  -> keine Abschnittszeilen, weil die
       Bereiche dann über die ganze Tabelle verstreut sind. Eine Zeile
       „Musik 12", unter der drei Mail-Tests stehen, wäre schlicht falsch.

   Die Zeilen werden NICHT neu gebaut, sondern beim Laden als Vorlage gemerkt.
   So gibt es weiterhin genau EINE Stelle, die ihr Aussehen bestimmt: den
   Server (`Testtabelle._gruppenzeile`). */

/** Index der Bereichsspalte einer Tabelle (-1, wenn es keine gibt). */
function bereichsSpalte(tabelle) {
    const kopf = tabelle.tHead && tabelle.tHead.rows.length
        ? tabelle.tHead.rows[tabelle.tHead.rows.length - 1] : null;
    if (!kopf) return -1;
    return [...kopf.cells].findIndex(th => th.dataset.key === 'bereich');
}

/** Bereichs-Slug einer Datenzeile — aus dem Attribut oder der Zelle. */
function slugVon(tr, spalte) {
    if (tr.dataset.bereich) return tr.dataset.bereich;
    const zelle = tr.cells[spalte];
    const marke = zelle && zelle.querySelector('[data-bereich]');
    return marke ? marke.dataset.bereich : '';
}

class Bereichsgliederung {
    constructor(tabelle) {
        this.tabelle = tabelle;
        this.spalte = bereichsSpalte(tabelle);
        this.vorlagen = new Map();
        [...tabelle.tBodies[0].rows].forEach(tr => {
            if (tr.dataset.gruppe !== undefined) {
                this.vorlagen.set(tr.dataset.bereich || '', tr.cloneNode(true));
            }
        });
    }

    binden() {
        if (this.spalte < 0 || !this.vorlagen.size) return this;
        this.tabelle.addEventListener('tabelle:sortiert', e => {
            this.setzen(e.detail && e.detail.idx === this.spalte);
        });
        // Startzustand: Eine gemerkte Sortierung ist beim Binden schon
        // angewandt worden, bevor dieser Listener stand.
        const idx = this.tabelle.dataset.sortIdx;
        if (idx !== undefined) this.setzen(parseInt(idx, 10) === this.spalte);
        return this;
    }

    /** Abschnittszeilen setzen (an) oder weglassen (aus) + Trennlinien. */
    setzen(an) {
        const koerper = this.tabelle.tBodies[0];
        [...koerper.rows].forEach(tr => {
            if (tr.dataset.gruppe !== undefined) tr.remove();
            else tr.classList.remove('ts-schnitt');
        });
        if (!an) return;
        const zeilen = [...koerper.rows];
        let vorher = null, kopf = null, zahl = 0;
        zeilen.forEach(tr => {
            const slug = slugVon(tr, this.spalte);
            if (slug !== vorher) {
                if (kopf) this._zahl(kopf, zahl);
                const vorlage = this.vorlagen.get(slug);
                if (vorlage) {
                    kopf = vorlage.cloneNode(true);
                    koerper.insertBefore(kopf, tr);
                    zahl = 0;
                } else {
                    kopf = null;
                    if (vorher !== null) tr.classList.add('ts-schnitt');
                }
                vorher = slug;
            }
            zahl++;
        });
        if (kopf) this._zahl(kopf, zahl);
    }

    _zahl(kopf, n) {
        const feld = kopf.querySelector('.ts-count');
        if (feld) feld.textContent = n;
    }
}

document.querySelectorAll('table[data-sort-key]').forEach(t => {
    if (t.tBodies.length) new Bereichsgliederung(t).binden();
});
