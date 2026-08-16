/* Skills2 - Werkzeuge starten, Bericht ins Textfeld schreiben, Lehren abhaken.
   ==========================================================================
   Drei Aufgaben, eine Klasse:

   1. „Prüfen" (je Zeile), „Auswahl prüfen" und „Alle prüfen". Die Läufe gehen
      NACHEINANDER, nicht gleichzeitig: Jedes Werkzeug liest den ganzen
      Quellbaum: parallel würden sie sich gegenseitig ausbremsen und die
      Zeitangaben in der Tabelle wertlos machen.
   2. Der Bericht landet im Textfeld - je Werkzeug mit Überschrift, mit Datei
      und Zeile je Fundstelle. Das ist das eigentliche Ziel: Der Text lässt sich
      in eine Sitzung kopieren, und dort kann direkt daran gearbeitet werden.
   3. Die Haken der Lehren liegen im localStorage. Anfangszustand ist AN: Die
      Liste ist zum Abarbeiten da, nicht zum Ankreuzen.

   Kein Zustand auf Modulebene (das ist die erste Lehre der Seite): Alles hängt
   an der Instanz. */

const SPEICHER = 'djangobase.skills2.lehren';
/** Mehr Zeilen als das macht den Bericht unlesbar - und das wird GESAGT. */
const MAX_ZEILEN = 300;

export class Skills2 {
  constructor() {
    this.laeuft = false;
    this.laeufe = 0;
  }

  binden() {
    document.querySelectorAll('[data-werkzeug]').forEach(b =>
      b.addEventListener('click', () => this.stapel([b.dataset.werkzeug])));
    const stapel = document.getElementById('sk2-stapel');
    if (stapel) stapel.addEventListener('click', () => this.stapel(this._gewaehlt()));
    const alle = document.getElementById('sk2-alle-pruefen');
    if (alle) alle.addEventListener('click', () => this.stapel(this._alleSlugs()));
    const kopf = document.getElementById('sk2-alle');
    if (kopf) kopf.addEventListener('change', () => {
      document.querySelectorAll('.sk2-wahl').forEach(c => { c.checked = kopf.checked; });
      this._wahlZaehlen();
    });
    document.querySelectorAll('.sk2-wahl').forEach(c =>
      c.addEventListener('change', () => this._wahlZaehlen()));
    const leeren = document.getElementById('sk2-leeren');
    if (leeren) leeren.addEventListener('click', () => this.leeren());
    const kopieren = document.getElementById('sk2-kopieren');
    if (kopieren) kopieren.addEventListener('click', () => this.kopieren());
    this._wahlZaehlen();
    this.lehrenLaden();
    document.querySelectorAll('[data-lehre]').forEach(c =>
      c.addEventListener('change', () => this.lehrenSpeichern()));
    return this;
  }

  // ---- Auswahl ----------------------------------------------------------
  _gewaehlt() {
    return [...document.querySelectorAll('.sk2-wahl')].filter(c => c.checked)
      .map(c => c.value);
  }

  _alleSlugs() {
    return [...document.querySelectorAll('.sk2-wahl')].map(c => c.value);
  }

  _wahlZaehlen() {
    const n = this._gewaehlt().length;
    const z = document.getElementById('sk2-wahl-zaehler');
    if (z) z.textContent = n === 1 ? '1 ausgewählt' : `${n} ausgewählt`;
  }

  // ---- Läufe ------------------------------------------------------------
  async stapel(slugs) {
    if (this.laeuft || !slugs.length) return;
    this.laeuft = true;
    this._knoepfe(false);
    for (const slug of slugs) {
      await this.pruefen(slug);
    }
    this._knoepfe(true);
    this.laeuft = false;
  }

  _knoepfe(an) {
    document.querySelectorAll('.sk2-btn').forEach(b => { b.disabled = !an; });
  }

  async pruefen(slug) {
    const knopf = document.querySelector(`[data-werkzeug="${slug}"]`);
    const vorher = knopf ? knopf.textContent : '';
    if (knopf) knopf.textContent = 'läuft …';
    this._anhaengen(`… ${slug} läuft`, true);
    let d = null;
    try {
      const r = await fetch('?werkzeug=' + encodeURIComponent(slug));
      d = await r.json();
    } catch (e) {
      d = {ok: false, slug, fehler: (e && e.message) || String(e)};
    }
    this._letzteZeileWeg();
    this._anhaengen(this._bericht(d));
    if (knopf) knopf.textContent = vorher || 'Prüfen';
    this.laeufe += 1;
    this._ausgabeZaehler();
  }

  /** Der Bericht eines Laufs als Klartext - so, dass man ihn weiterreichen kann. */
  _bericht(d) {
    const strich = '='.repeat(72);
    const kopf = [strich,
                  `## ${d.titel || d.slug}` + (d.kriterium ? `  (Kriterium ${d.kriterium})` : ''),
                  strich];
    if (!d.ok) {
      kopf.push(`FEHLGESCHLAGEN: ${d.fehler || 'unbekannt'}`, '');
      return kopf.join('\n');
    }
    kopf.push(`${d.zusammenfassung}   [${d.dauer} s]`);
    if (d.abhilfe) kopf.push(`Abhilfe: ${d.abhilfe}`);
    if (d.hinweis) kopf.push(`Hinweis: ${d.hinweis}`);
    kopf.push('');
    if (!d.zeilen.length) {
      kopf.push('Nichts gefunden.', '');
      return kopf.join('\n');
    }
    // Feste Spaltenbreiten: Der Text soll auch in einer Konsole lesbar sein.
    const breiten = d.spalten.map(s =>
      Math.min(46, Math.max(s.length,
        ...d.zeilen.slice(0, MAX_ZEILEN).map(z => String(z[s] ?? '').length))));
    const zeile = werte => werte.map((w, i) =>
      String(w ?? '').slice(0, breiten[i]).padEnd(breiten[i])).join('  ').trimEnd();
    kopf.push(zeile(d.spalten));
    kopf.push(breiten.map(b => '-'.repeat(b)).join('  '));
    for (const z of d.zeilen.slice(0, MAX_ZEILEN)) {
      kopf.push(zeile(d.spalten.map(s => z[s])));
    }
    if (d.zeilen.length > MAX_ZEILEN) {
      kopf.push(`… ${d.zeilen.length - MAX_ZEILEN} weitere Zeilen nicht ausgegeben `
                + `(Deckel ${MAX_ZEILEN}).`);
    }
    kopf.push('');
    return kopf.join('\n');
  }

  _feld() { return document.getElementById('sk2-ausgabe'); }

  _anhaengen(text, fluechtig) {
    const f = this._feld();
    if (!f) return;
    f.value += (f.value && !f.value.endsWith('\n') ? '\n' : '') + text + '\n';
    f.scrollTop = f.scrollHeight;
    if (fluechtig) this._fluechtig = text;
  }

  /** Die „… läuft"-Zeile wieder entfernen, sobald das Ergebnis da ist. */
  _letzteZeileWeg() {
    const f = this._feld();
    if (!f || !this._fluechtig) return;
    const marke = this._fluechtig + '\n';
    if (f.value.endsWith(marke)) f.value = f.value.slice(0, -marke.length);
    this._fluechtig = null;
  }

  leeren() {
    const f = this._feld();
    if (f) f.value = '';
    this.laeufe = 0;
    this._ausgabeZaehler();
  }

  async kopieren() {
    const f = this._feld();
    if (!f || !f.value) return;
    try {
      await navigator.clipboard.writeText(f.value);
    } catch (e) {
      // Ohne Berechtigung: markieren, damit Strg+C greift - besser als nichts
      // zu tun und den Nutzer raten zu lassen, ob es geklappt hat.
      f.focus();
      f.select();
    }
  }

  _ausgabeZaehler() {
    const z = document.getElementById('sk2-ausgabe-zaehler');
    if (z) z.textContent = this.laeufe ? `· ${this.laeufe} Lauf/Läufe im Feld` : '';
  }

  // ---- Lehren -----------------------------------------------------------
  lehrenLaden() {
    let ab = {};
    try { ab = JSON.parse(localStorage.getItem(SPEICHER) || '{}'); } catch (e) { ab = {}; }
    document.querySelectorAll('[data-lehre]').forEach(c => {
      // Voreinstellung AN: Nur was ausdrücklich abgehakt wurde, ist aus.
      c.checked = ab[c.dataset.lehre] !== false;
      c.closest('.sk2-lehre').classList.toggle('erledigt', !c.checked);
    });
    this._zaehlen();
  }

  lehrenSpeichern() {
    const ab = {};
    document.querySelectorAll('[data-lehre]').forEach(c => {
      ab[c.dataset.lehre] = c.checked;
      c.closest('.sk2-lehre').classList.toggle('erledigt', !c.checked);
    });
    try { localStorage.setItem(SPEICHER, JSON.stringify(ab)); } catch (e) { /* privat */ }
    this._zaehlen();
  }

  _zaehlen() {
    const alle = [...document.querySelectorAll('[data-lehre]')];
    const offen = alle.filter(c => c.checked).length;
    const z = document.getElementById('sk2-zaehler');
    if (z) z.textContent = `· ${offen} von ${alle.length} offen`;
  }
}
