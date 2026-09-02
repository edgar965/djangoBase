/**
 * Hilfe · Werkzeug Language Server — Lauf starten, Zustand abfragen, Tabelle filtern.
 *
 * Der Lauf geschieht im Server-Hintergrund (umbau/ls_lauf.py). Diese Klasse
 * schickt das Formular per fetch ab (Kopf X-Requested-With: fetch, dann kommt
 * JSON statt einer Umleitung), fragt danach alle zwei Sekunden `status/` ab
 * und lädt die Seite neu, sobald der Lauf nicht mehr `laeuft` sagt. Ohne
 * JavaScript funktioniert das Formular weiter als gewöhnlicher POST.
 *
 * Kein eigener Abruf für die Tabelle: Sie kommt aus dem GET, wie überall in
 * djangoBase — zwei Stellen, die dieselbe Tabelle bauen, laufen auseinander.
 */
export class LanguageServerSeite {
    constructor(wurzel) {
        this.wurzel = wurzel;
        this.form = wurzel.querySelector('#ls-form');
        this.status = wurzel.querySelector('#ls-status');
        this.token = this.form.querySelector('[name=csrfmiddlewaretoken]').value;
        this.statusUrl = location.pathname.replace(/\/?$/, '/') + 'status/';
        this._pollt = false;
    }

    binden() {
        this.form.querySelectorAll('[data-aktion]').forEach((knopf) =>
            knopf.addEventListener('click', () => this.starten(knopf.dataset.aktion)));
        ['#ls-suche', '#ls-filter-regel', '#ls-filter-stufe'].forEach((sel) => {
            const el = this.wurzel.querySelector(sel);
            if (el) el.addEventListener('input', () => this.filtern());
        });
        this.filtern();
        if (this.wurzel.dataset.laeuft === '1') this.pollen();
    }

    async starten(aktion) {
        const daten = new FormData(this.form);
        daten.set('aktion', aktion);
        this.melden('Lauf wird gestartet …');
        this.form.querySelectorAll('[data-aktion]').forEach((k) => { k.disabled = true; });
        try {
            const r = await fetch(location.pathname, {
                method: 'POST', body: daten,
                headers: {'X-Requested-With': 'fetch', 'X-CSRFToken': this.token},
            });
            if (!r.ok) { this.melden('Start fehlgeschlagen: HTTP ' + r.status, true); return; }
            const d = await r.json();
            if (!d.gestartet && d.zustand && d.zustand.status === 'laeuft') {
                this.melden('Es läuft schon ein Lauf — warte auf ihn …');
            }
            this.pollen();
        } catch (fehler) {
            this.melden('Start fehlgeschlagen: ' + fehler.message, true);
        }
    }

    async pollen() {
        if (this._pollt) return;
        this._pollt = true;
        for (;;) {
            let d;
            try {
                d = await fetch(this.statusUrl, {cache: 'no-store'}).then((r) => r.json());
            } catch (fehler) {
                this.melden('Status nicht abrufbar: ' + fehler.message, true);
                break;
            }
            if (d.status === 'laeuft') {
                this.melden(`läuft seit ${Math.round(d.sekunden)} s (${d.werkzeug || '…'}) …`);
                await new Promise((r) => setTimeout(r, 2000));
                continue;
            }
            this.melden(d.status === 'fehler'
                ? 'Lauf gescheitert: ' + (d.fehler || '?')
                : `fertig nach ${Math.round(d.sekunden)} s — Seite lädt neu`);
            // Neu laden: das Ergebnis liegt in der Ablage, der GET zeigt es.
            setTimeout(() => location.reload(), 600);
            break;
        }
        this._pollt = false;
    }

    melden(text, fehler = false) {
        if (!this.status) return;
        this.status.textContent = text;
        this.status.style.color = fehler ? '#e06060' : '';
    }

    /** Filterzeile: Text in Datei oder Meldung, Regel, Stufe — nur Sichtbarkeit. */
    filtern() {
        const suche = (this.wurzel.querySelector('#ls-suche')?.value || '').toLowerCase();
        const regel = this.wurzel.querySelector('#ls-filter-regel')?.value || '';
        const stufe = this.wurzel.querySelector('#ls-filter-stufe')?.value || '';
        const zeilen = [...this.wurzel.querySelectorAll('table.ls-tabelle tbody tr')];
        let sichtbar = 0;
        zeilen.forEach((tr) => {
            const text = tr.textContent.toLowerCase();
            const zellen = tr.children;
            const regelText = zellen[3] ? zellen[3].textContent.trim() : '';
            const passt = (!suche || text.includes(suche))
                && (!regel || regelText === regel)
                && (!stufe || tr.classList.contains(stufe));
            tr.hidden = !passt;
            if (passt) sichtbar += 1;
        });
        const zaehler = this.wurzel.querySelector('#ls-zaehler');
        if (zaehler) zaehler.textContent = zeilen.length
            ? `${sichtbar} von ${zeilen.length} Zeilen` : '';
    }
}
