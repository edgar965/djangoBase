/**
 * BefundTafel — die gespeicherten Befunde eines Prüfwerkzeugs anzeigen.
 *
 * WAS SIE ANDERS MACHT ALS DER TEXTBLOCK DARÜBER
 * ==============================================
 * Der Werkzeug-Kasten zeigt, was der laufende Aufruf gerade schreibt. Diese
 * Tafel zeigt, was in der Ablage der CLI steht — und das hat drei Folgen, die
 * den Umbau überhaupt erst lohnen:
 *
 *   1. **Sie kostet keinen Lauf.** Im kostenlosen Plan sind es drei je Stunde.
 *      Die Befunde beim Öffnen der Seite zu sehen, darf davon nichts abziehen.
 *   2. **Sie überlebt den Serverneustart.** Das Lauf-Register liegt im
 *      Arbeitsspeicher; nach einem Neustart war die Seite leer, obwohl die
 *      Befunde auf der Platte lagen.
 *   3. **Sie ist sortier- und filterbar**, weil jeder Befund als Datensatz
 *      kommt und nicht als Zeile in einem Block.
 *
 * ABGERUFEN WIRD MIT DEM SLUG DES WERKZEUGS, nie mit einem Pfad: Welches
 * Verzeichnis gelesen wird, entscheidet die Server-Konfiguration.
 */
import { Serverabruf } from './serverabruf.js';
import { BefundKarte } from './review_befund_karte.js';

/** Reihenfolge der Filterknöpfe — schwerwiegend zuerst. */
const GRADE = [
    { wert: '', name: 'alle' },
    { wert: 'critical', name: 'kritisch' },
    { wert: 'major', name: 'schwer' },
    { wert: 'minor', name: 'klein' },
];

export class BefundTafel {

    constructor(el) {
        this.el = el;
        this.adresse = el.dataset.adresse;
        this.laeufe = [];
        this.lauf = null;
        this.grad = '';
        /* Zählt die Abrufe. Siehe `laden()` — ohne ihn kann eine langsame
           alte Antwort eine frische überschreiben. */
        this.abruf = 0;
        this.kopf = el.querySelector('.rb-leiste');
        this.liste = el.querySelector('.rb-liste');
        this.meldung = el.querySelector('.rb-meldung');
    }

    /**
     * Beim Seitenaufbau und nach jedem fertigen Lauf.
     *
     * ÜBERHOLTE ANTWORTEN WERDEN VERWORFEN (Befund CodeRabbit, 31.08.2026):
     * Diese Methode läuft mindestens zweimal — einmal beim Aufbau, einmal
     * wenn ein Lauf endet. Kommt die erste, langsame Antwort NACH der
     * zweiten an, überschrieb sie den frischen Stand mit dem alten: Die
     * Seite hätte die eben gefundenen Befunde wieder verloren, ohne dass
     * etwas darauf hindeutet.
     *
     * Ein Zähler genügt, ein AbortController wäre hier zu viel: Die Antwort
     * ist klein, sie soll nur nicht mehr gezeichnet werden.
     */
    async laden() {
        const meiner = ++this.abruf;
        this._melden('lädt …');
        try {
            const daten = await Serverabruf.json(this.adresse);
            if (meiner !== this.abruf) return;          // überholt
            this.laeufe = daten.laeufe || [];
            this.lauf = this.laeufe[0] || null;
            this._zeichnen(daten);
        } catch (e) {
            /* Ein Fehler beim LESEN der Ablage ist kein Grund, die Seite
               stumm zu lassen — sonst sieht „nichts gefunden" aus wie
               „nichts da". Auch hier gilt der Zähler: Der Fehler eines
               überholten Abrufs darf die Meldung des neueren nicht
               verdrängen. */
            if (meiner !== this.abruf) return;
            this._melden('Befunde nicht lesbar: ' + e.message, true);
        }
    }

    // -------------------------------------------------------------- Zeichnen

    _zeichnen(daten) {
        this.kopf.replaceChildren();
        this.liste.replaceChildren();
        if (!this.lauf) {
            this._melden(daten.hinweis || 'Noch kein Lauf gespeichert.');
            return;
        }
        this._melden('');
        this.kopf.append(this._laufwahl(), this._zusammenfassung(), ...this._filterknoepfe());
        if (!daten.belegt) this.kopf.append(this._warnung(daten));
        this._listeZeichnen();
    }

    _laufwahl() {
        const wahl = document.createElement('select');
        wahl.className = 'rv-select rb-laufwahl';
        wahl.setAttribute('aria-label', 'Welcher Lauf');
        for (const l of this.laeufe) {
            const o = document.createElement('option');
            o.value = l.id;
            /* Ein Lauf ohne `git.json` (die CLI räumt sie in älteren Läufen
               weg) hat keinen Commit. Das wird hingeschrieben statt mit einem
               leeren Feld überspielt. */
            o.textContent = `${l.zeitpunkt} · ${l.anzahl} Befunde`
                + (l.commit ? ` · ${l.commit}` : ' · älterer Lauf');
            wahl.append(o);
        }
        wahl.addEventListener('change', () => {
            this.lauf = this.laeufe.find(l => l.id === wahl.value) || this.lauf;
            this._kopfZahlen();
            this._listeZeichnen();
        });
        return wahl;
    }

    _zusammenfassung() {
        const s = document.createElement('span');
        s.className = 'rb-summe';
        this._summeSchreiben(s);
        return s;
    }

    _summeSchreiben(el) {
        const zaehler = {};
        for (const b of this.lauf.befunde) zaehler[b.grad] = (zaehler[b.grad] || 0) + 1;
        const teile = GRADE.slice(1)
            .filter(g => zaehler[g.wert])
            .map(g => `${zaehler[g.wert]} ${g.name}`);
        /* Grade, die die Liste oben nicht kennt, werden mitgezählt statt
           verschluckt — sonst stimmt die Summe nicht mit der Liste überein. */
        const bekannt = new Set(GRADE.map(g => g.wert));
        for (const [grad, n] of Object.entries(zaehler)) {
            if (!bekannt.has(grad)) teile.push(`${n} ${grad}`);
        }
        el.textContent = teile.length ? teile.join(' · ') : 'keine Befunde';
    }

    _kopfZahlen() {
        const summe = this.kopf.querySelector('.rb-summe');
        if (summe) this._summeSchreiben(summe);
    }

    _filterknoepfe() {
        return GRADE.map(g => {
            const k = document.createElement('button');
            k.type = 'button';
            k.className = 'rb-filter' + (g.wert === this.grad ? ' rb-an' : '');
            k.dataset.grad = g.wert;
            k.textContent = g.name;
            k.addEventListener('click', () => {
                this.grad = g.wert;
                this.kopf.querySelectorAll('.rb-filter').forEach(b =>
                    b.classList.toggle('rb-an', b.dataset.grad === this.grad));
                this._listeZeichnen();
            });
            return k;
        });
    }

    _warnung(daten) {
        const w = document.createElement('span');
        w.className = 'rb-warnung';
        w.textContent = 'Zuordnung nicht belegt — kein Lauf nennt sein Verzeichnis';
        w.title = `Ablage: ${daten.ablage || '?'} · Ordner: ${daten.ordner || '?'}`;
        return w;
    }

    _listeZeichnen() {
        this.liste.replaceChildren();
        const gezeigt = this.lauf.befunde.filter(b => !this.grad || b.grad === this.grad);
        if (!gezeigt.length) {
            const p = document.createElement('p');
            p.className = 'rv-fuss';
            p.textContent = this.lauf.befunde.length
                ? 'Kein Befund dieses Schweregrads.'
                : 'Dieser Lauf hat nichts gefunden.';
            this.liste.append(p);
            return;
        }
        for (const b of gezeigt) {
            const karte = new BefundKarte(b);
            if (karte.gueltig()) this.liste.append(karte.bauen());
        }
        if (this.lauf.uebersprungen) {
            /* Dateien, die der Leser nicht als Befund erkannt hat. Normal sind
               die Beidateien der CLI; eine steigende Zahl heißt Formatwechsel.
               Sie steht deshalb auf der Seite und nicht nur im Log. */
            const p = document.createElement('p');
            p.className = 'rv-fuss';
            p.textContent = `${this.lauf.uebersprungen} Datei(en) im Lauf-Ordner `
                + 'ergaben keinen Befund — vermutlich Beidateien der CLI.';
            this.liste.append(p);
        }
    }

    _melden(text, schlimm = false) {
        this.meldung.textContent = text || '';
        this.meldung.hidden = !text;
        this.meldung.classList.toggle('rb-fehler', !!schlimm);
    }

    /** Alle Tafeln der Seite anmelden — und auf fertige Läufe hören. */
    static starten() {
        const tafeln = [...document.querySelectorAll('.rb-tafel')].map(el => {
            const t = new BefundTafel(el);
            t.laden();
            return t;
        });
        /* Der Werkzeug-Kasten meldet das Ende eines Laufs; erst dann liegt in
           der Ablage etwas Neues. Ohne dieses Ereignis zeigte die Tafel bis
           zum nächsten Seitenaufruf den Stand von vorher — und der Nutzer
           hätte den frischen Befund für einen alten gehalten. */
        document.addEventListener('review-werkzeug-fertig', e => {
            const slug = e.detail && e.detail.slug;
            for (const t of tafeln) {
                if (!slug || t.el.dataset.slug === slug) t.laden();
            }
        });
        return tafeln;
    }
}
