/**
 * Die Tafel für Referenzen, Definition und Umbenennen (Stufe 2).
 *
 * Ein Klick auf den Knopf in einer Befund-Zeile setzt die Stelle (Datei, Zeile,
 * Spalte aus `data-id` der Zeile). Jede Anfrage geht als JSON an
 * `referenzen/`; Umbenennen erst als Vorschau, dann — nach dem Bestätigen —
 * mit `bestaetigt: true`. Ein Klick allein schreibt keine Datei.
 *
 * Fehler kommen auf die Tafel, nie nur in die Konsole (Lehre `jsstumm`).
 */
export class ReferenzenPanel {
    constructor(panel, token) {
        this.panel = panel;
        this.token = token;
        this.url = location.pathname.replace(/\/?$/, '/') + 'referenzen/';
        this.stelle = null;
        this.vorschauFuer = '';
        this.liste = panel.querySelector('#ls-ref-liste');
        this.meldung = panel.querySelector('#ls-ref-meldung');
        this.name = panel.querySelector('#ls-ref-name');
        this.umbenennenKnopf = panel.querySelector('[data-ref=umbenennen]');
    }

    binden() {
        document.querySelectorAll('table.ls-tabelle tbody tr').forEach((tr) => {
            const knopf = tr.querySelector('.ls-ref');
            if (knopf) knopf.addEventListener('click', () => this.setzen(tr.dataset.id));
        });
        this.panel.querySelectorAll('[data-ref]').forEach((knopf) =>
            knopf.addEventListener('click', () => this.aktion(knopf.dataset.ref)));
        this.name.addEventListener('input', () => {
            // Ein anderer Name als der der Vorschau: erst wieder ansehen.
            this.umbenennenKnopf.disabled = this.name.value.trim() !== this.vorschauFuer;
        });
    }

    setzen(id) {
        const [datei, zeile, spalte] = (id || '').split('|');
        if (!datei) return;
        this.stelle = {datei, zeile: parseInt(zeile, 10), spalte: parseInt(spalte, 10)};
        this.panel.hidden = false;
        this.panel.querySelector('#ls-ref-stelle').textContent = `${datei}:${zeile}:${spalte}`;
        this.liste.innerHTML = '';
        this.melden('');
        this.vorschauFuer = '';
        this.umbenennenKnopf.disabled = true;
        this.panel.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    }

    async aktion(art) {
        if (!this.stelle) { this.melden('Erst eine Zeile in der Tabelle wählen.', 'fehler'); return; }
        const koerper = {aktion: art, ...this.stelle};
        if (art === 'vorschau' || art === 'umbenennen') {
            koerper.name = this.name.value.trim();
            if (!koerper.name) { this.melden('Neuen Namen eintragen.', 'fehler'); return; }
        }
        if (art === 'umbenennen') {
            const n = this.liste.children.length;
            if (!window.confirm(`${n} Stellen umbenennen in „${koerper.name}“?\n`
                + 'Die Dateien werden geschrieben — mit Sicherung und Kompilier-Netz.')) return;
            koerper.bestaetigt = true;
        }
        this.melden('Frage den Server …');
        let d;
        try {
            const r = await fetch(this.url, {
                method: 'POST', headers: {'Content-Type': 'application/json',
                                          'X-CSRFToken': this.token},
                body: JSON.stringify(koerper),
            });
            d = await r.json();
            if (!r.ok || d.fehler) { this.melden(d.fehler || `Fehler ${r.status}`, 'fehler'); return; }
        } catch (fehler) {
            this.melden('Abruf fehlgeschlagen: ' + fehler.message, 'fehler');
            return;
        }
        if (d.stellen) this.zeigeStellen(d.stellen, art);
        else if (d.vorschau) this.zeigeVorschau(d.vorschau, koerper.name);
        else if (d.bericht) this.zeigeBericht(d.bericht);
    }

    zeigeStellen(stellen, art) {
        this.liste.innerHTML = stellen.map((s) =>
            `<li><code>${esc(s.datei)}:${s.zeile}:${s.spalte}</code></li>`).join('');
        this.melden(stellen.length
            ? `${stellen.length} ${art === 'definition' ? 'Definition(en)' : 'Stellen'}`
            : 'nichts gefunden', 'ok');
    }

    zeigeVorschau(vorschau, name) {
        this.liste.innerHTML = vorschau.map((v) =>
            `<li><code>${esc(v.datei)}:${v.zeile}</code> `
            + `<span class="ls-alt">${esc(v.alt)}</span> → <span class="ls-neu">${esc(v.neu)}</span>`
            + ` <code>${esc(v.zeile_text)}</code></li>`).join('');
        this.vorschauFuer = name;
        this.umbenennenKnopf.disabled = vorschau.length === 0;
        this.melden(vorschau.length
            ? `${vorschau.length} Stellen würden zu „${name}“ — unten bestätigen`
            : 'Der Server hat nichts zum Umbenennen gefunden.', vorschau.length ? 'ok' : 'fehler');
    }

    zeigeBericht(b) {
        const fehler = (b.fehler || []).map((f) => `<li class="ls-alt">${esc(f)}</li>`).join('');
        this.liste.innerHTML = fehler;
        this.melden(`${b.stellen} Stellen in ${b.dateien} Dateien geschrieben`
            + (b.sicherung ? ` — Sicherung: ${b.sicherung}` : '')
            + (b.fehler && b.fehler.length ? ` — ${b.fehler.length} Datei(en) unverändert gelassen` : ''),
            b.fehler && b.fehler.length ? 'fehler' : 'ok');
        this.umbenennenKnopf.disabled = true;
        this.vorschauFuer = '';
    }

    melden(text, art = '') {
        this.meldung.textContent = text;
        this.meldung.className = 'ls-meldung' + (art ? ' ls-' + art : '');
    }
}

function esc(text) {
    return String(text ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}
