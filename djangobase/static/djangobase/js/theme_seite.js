// Einstellungen -> Theme (theme.html, views/theme_seite.py, Definition theme_stil.py). Füllt die Felder mit den
// Werten des aktiven Themes (Vorgaben des Projekts, darüber die eigenen Angaben), zeigt jede Änderung sofort an
// der ganzen Seite — als Variablen am <body>, der Stilblock des Servers wird dafür entfernt — und schickt beim
// Speichern die Arbeitskopie ALLER Themes. Umschalten: die Knöpfe tragen .theme-pick (base_app.html setzt
// body[data-theme]); danach gelten die Werte des neuen Themes.
import { TabellenBreiten } from '/static/djangobase/js/tabellen_breiten.js';

const lesen = (id) => JSON.parse(document.getElementById(id).textContent);
// Seitenleiste und Kopfleiste sind die echten — dort zeigt die Markierung beim Darüberfahren hin.
const SHELL = { menue: '.sidebar .nav-link', menue_abschnitt: '.sidebar .nav-abschnitt', seitenname: '.topbar-title' };
// Feste Spalten der Rollentabellen (px, data-key der Kopfzellen); „Schrift“ bekommt den Rest, mindestens 220 px.
const SPALTEN = { nr: 56, art: 190, groesse: 120, farbe: 90, gewicht: 130, kursiv: 76, weg: 44 };

function rgb(hex) {
    const h = hex.replace('#', '');
    return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)).join(', ');
}

// "#abc", "#aabbcc" oder "rgb(a, b, c)" -> "#aabbcc"; sonst "".
function hex(wert) {
    const w = String(wert || '').trim();
    if (/^#[0-9a-f]{6}$/i.test(w)) return w.toLowerCase();
    if (/^#[0-9a-f]{3}$/i.test(w)) return `#${[...w.slice(1)].map((z) => z + z).join('')}`.toLowerCase();
    const m = w.match(/^rgba?\((\d+)[,\s]+(\d+)[,\s]+(\d+)/i);
    return m ? `#${m.slice(1, 4).map((z) => Number(z).toString(16).padStart(2, '0')).join('')}` : '';
}

class ThemeSeite {
    constructor(wurzel) {
        this.wurzel = wurzel;
        this.formular = wurzel.querySelector('#dbt-theme-form');
        this.vorschau = wurzel.querySelector('.dbt-theme-vorschau-inhalt');
        this.status = wurzel.querySelector('[data-status]');
        this.alleFarben = wurzel.querySelector('[data-alle-farben]');
        this.def = lesen('dbt-theme-definition');
        this.vorgaben = lesen('dbt-theme-vorgaben');
        this.arbeit = lesen('dbt-theme-gespeichert');
        this.gesetzt = [];
        this.geaendert = false;
    }

    theme() {
        return document.body.getAttribute('data-theme') || '';
    }

    eigene() {
        const t = this.arbeit[this.theme()] || (this.arbeit[this.theme()] = {});
        t.farben = t.farben || {};
        t.schriften = t.schriften || {};
        return t;
    }

    // Wie ThemeStil.wirksam: Vorgaben, darüber die eigenen Angaben — je Farbe und je Attribut einer Rolle.
    wirksam() {
        const v = this.vorgaben[this.theme()] || {};
        const e = this.eigene();
        const schriften = {};
        [v.schriften || {}, e.schriften].forEach((quelle) => {
            Object.entries(quelle).forEach(([rolle, werte]) => { schriften[rolle] = { ...(schriften[rolle] || {}), ...werte }; });
        });
        return { farben: { ...(v.farben || {}), ...e.farben }, schriften };
    }

    // Wie ThemeStil.deklarationen — dieselben Variablen, damit die Vorschau zeigt, was gespeichert wird.
    deklarationen(w) {
        const d = this.def;
        const raus = [];
        Object.entries(w.farben).forEach(([k, farbe]) => {
            (d.farben[k] || []).forEach(([variable, form]) => raus.push([variable, form === 'rgb' ? rgb(farbe) : farbe]));
        });
        Object.entries(w.schriften).forEach(([rolle, s]) => {
            const p = `--dbt-s-${rolle}`;
            if (d.stapel[s.art]) {
                raus.push([`${p}-art`, d.stapel[s.art]]);
                if (rolle === 'alle') d.alle_art.forEach((v) => raus.push([v, d.stapel[s.art]]));
            }
            if (typeof s.groesse === 'number') raus.push([`${p}-groesse`, `${s.groesse}px`]);
            if (s.farbe) {
                raus.push([`${p}-farbe`, s.farbe]);
                if (rolle === 'alle') d.alle_farbe.forEach((v) => raus.push([v, s.farbe]));
            }
            if (d.gewichte[s.gewicht]) raus.push([`${p}-gewicht`, d.gewichte[s.gewicht]]);
            if (s.kursiv === true) raus.push([`${p}-stil`, 'italic']);
        });
        return raus;
    }

    anwenden() {
        const stil = document.body.style;
        this.gesetzt.forEach((name) => stil.removeProperty(name));
        this.gesetzt = [];
        this.deklarationen(this.wirksam()).forEach(([name, wert]) => { stil.setProperty(name, wert); this.gesetzt.push(name); });
    }

    // Element, an dem eine Rolle gemessen und markiert wird: Beispiel der Vorschau, sonst Seitenleiste/Kopfleiste.
    beispiele(rolle) {
        const vorschau = [...this.vorschau.querySelectorAll(`[data-rolle="${rolle}"]`)];
        return SHELL[rolle] ? [...vorschau, ...document.querySelectorAll(SHELL[rolle])] : vorschau;
    }

    gemessen(rolle) {
        const el = rolle === 'alle' ? document.body : this.beispiele(rolle)[0];
        return el ? getComputedStyle(el) : null;
    }

    fuellen() {
        const w = this.wirksam();
        const seite = getComputedStyle(document.body);
        this.alleFarben.value = (w.schriften.alle || {}).farbe || hex(seite.color) || '#000000';
        this.formular.querySelectorAll('[data-farbe]').forEach((feld) => {
            const k = feld.dataset.farbe;
            feld.value = w.farben[k] || hex(seite.getPropertyValue(this.def.farben[k][0][0])) || '#000000';
        });
        this.formular.querySelectorAll('[data-rolle][data-attr]').forEach((feld) => {
            const { rolle, attr } = feld.dataset;
            const s = w.schriften[rolle] || {};
            const ist = this.gemessen(rolle);
            if (attr === 'kursiv') feld.checked = s.kursiv === true;
            else if (attr === 'farbe') feld.value = s.farbe || (ist && hex(ist.color)) || '#000000';
            else if (attr === 'groesse') {
                feld.value = s.groesse ?? '';
                feld.placeholder = ist ? String(Math.round(parseFloat(ist.fontSize) * 10) / 10) : '';
            } else feld.value = s[attr] || '';
        });
        this.markieren();
    }

    // Was eine eigene Angabe hat, steht voll da und bekommt sein ×; der Rest ist Vorgabe des Themes.
    markieren() {
        const e = this.eigene();
        this.formular.querySelectorAll('[data-farbe]').forEach((f) => f.classList.toggle('vorgabe', !e.farben[f.dataset.farbe]));
        this.formular.querySelectorAll('[data-weg-farbe]').forEach((k) => { k.hidden = !e.farben[k.dataset.wegFarbe]; });
        this.formular.querySelectorAll('input[type="color"][data-rolle]').forEach((f) => {
            f.classList.toggle('vorgabe', !(e.schriften[f.dataset.rolle] || {}).farbe);
        });
        this.formular.querySelectorAll('[data-weg-rolle]').forEach((k) => { k.hidden = !(e.schriften[k.dataset.wegRolle] || {}).farbe; });
        this.formular.querySelectorAll('[data-weg-zeile]').forEach((k) => { k.hidden = !e.schriften[k.dataset.wegZeile]; });
        this.wurzel.querySelectorAll('.dbt-theme-wahlknopf').forEach((k) => k.classList.toggle('aktiv', k.dataset.theme === this.theme()));
        this.status.textContent = this.geaendert ? 'Nicht gespeichert' : '';
    }

    eingabe(feld) {
        const e = this.eigene();
        if (feld.dataset.farbe) {
            e.farben[feld.dataset.farbe] = feld.value;
        } else if (feld.dataset.rolle && feld.dataset.attr) {
            const { rolle, attr } = feld.dataset;
            const s = e.schriften[rolle] || (e.schriften[rolle] = {});
            const zahl = parseFloat(String(feld.value).replace(',', '.'));
            if (attr === 'kursiv') { if (feld.checked) s.kursiv = true; else delete s.kursiv; }
            else if (attr === 'groesse') { if (zahl >= 7 && zahl <= 40) s.groesse = zahl; else delete s.groesse; }
            else if (feld.value) s[attr] = feld.value;
            else delete s[attr];
            if (!Object.keys(s).length) delete e.schriften[rolle];
        } else return;
        this.geaendert = true;
        this.anwenden();
        this.markieren();
    }

    weg(knopf) {
        const e = this.eigene();
        const d = knopf.dataset;
        if (d.wegFarbe) delete e.farben[d.wegFarbe];
        if (d.wegZeile) delete e.schriften[d.wegZeile];
        if (d.wegRolle && e.schriften[d.wegRolle]) {
            delete e.schriften[d.wegRolle].farbe;
            if (!Object.keys(e.schriften[d.wegRolle]).length) delete e.schriften[d.wegRolle];
        }
        this.geaendert = true;
        this.anwenden();
        this.fuellen();
    }

    // „Alle Schriftfarben“: jede Rolle mit Farbe (Knopf hat keine) und die Schrift der Seitenleiste.
    alleSetzen(farbe) {
        const e = this.eigene();
        this.def.bereiche.forEach((b) => b.rollen.forEach((r) => {
            if (r.attribute.includes('farbe')) (e.schriften[r.rolle] = e.schriften[r.rolle] || {}).farbe = farbe;
        }));
        if (this.def.farben.leiste_text) e.farben.leiste_text = farbe;
        this.geaendert = true;
        this.anwenden();
        this.fuellen();
    }

    // Alle Rollentabellen als eine Gruppe: gleiche Spalten, gleiche Breite, Ziehen wirkt auf alle.
    spaltenBinden() {
        const tabellen = [...this.formular.querySelectorAll('table.dbt-theme-rollen')];
        if (!tabellen.length) return;
        const fest = Object.values(SPALTEN).reduce((summe, px) => summe + px, 0);
        const schrift = Math.max(220, tabellen[0].parentElement.clientWidth - fest - 2);
        new TabellenBreiten(tabellen, tabellen[0].dataset.sortKey, { ...SPALTEN, schrift }).binden();
    }

    zeigen(rolle, an) {
        this.beispiele(rolle).forEach((el) => el.classList.toggle('dbt-markiert', an));
    }

    verbinden() {
        // Ab hier gilt die Arbeitskopie: der Stilblock des Servers zeigte nur den gespeicherten Stand.
        const block = document.getElementById('dbt-theme-anpassung');
        if (block) block.remove();
        this.def.bereiche.forEach((b) => b.rollen.forEach((r) => {
            this.vorschau.querySelectorAll(`[data-rolle="${r.rolle}"]`).forEach((el) => { el.dataset.nr = r.nr; });
        }));
        ['input', 'change'].forEach((art) => this.formular.addEventListener(art, (ev) => this.eingabe(ev.target)));
        this.alleFarben.addEventListener('input', () => this.alleSetzen(this.alleFarben.value));
        this.spaltenBinden();
        this.formular.addEventListener('click', (ev) => {
            const knopf = ev.target.closest('[data-weg-farbe], [data-weg-rolle], [data-weg-zeile]');
            if (knopf) this.weg(knopf);
        });
        this.formular.querySelectorAll('[data-rolle-zeile]').forEach((zeile) => {
            zeile.addEventListener('mouseenter', () => { zeile.classList.add('markiert'); this.zeigen(zeile.dataset.rolleZeile, true); });
            zeile.addEventListener('mouseleave', () => { zeile.classList.remove('markiert'); this.zeigen(zeile.dataset.rolleZeile, false); });
        });
        this.wurzel.querySelector('[data-zuruecksetzen]').addEventListener('click', () => {
            this.arbeit[this.theme()] = {};
            this.geaendert = true;
            this.anwenden();
            this.fuellen();
        });
        // Nach base_app.html (setzt data-theme im selben Klick): erst dann gelten die Werte des neuen Themes.
        document.addEventListener('click', (ev) => {
            if (ev.target.closest('.theme-pick')) setTimeout(() => { this.anwenden(); this.fuellen(); }, 0);
        });
        this.formular.addEventListener('submit', () => {
            this.formular.querySelector('[data-daten]').value = JSON.stringify(this.arbeit);
            this.geaendert = false;
        });
        window.addEventListener('beforeunload', (ev) => { if (this.geaendert) ev.preventDefault(); });
        this.anwenden();
        this.fuellen();
    }
}

const wurzel = document.getElementById('dbt-theme');
if (wurzel) new ThemeSeite(wurzel).verbinden();
