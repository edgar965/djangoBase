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
    // FIXER: Vorschau schaltet „Anwenden" frei - nie umgekehrt.
    document.querySelectorAll('.sk2-fix-vorschau').forEach(b =>
      b.addEventListener('click', () => this.fixVorschau(b.dataset.fixer)));
    document.querySelectorAll('.sk2-fix-anwenden').forEach(b =>
      b.addEventListener('click', () => this.fixAnwenden(b.dataset.fixer)));

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

  /** Alle Knöpfe sperren oder freigeben - AUSSER den „Anwenden"-Knöpfen.
   *
   * Die dürfen nur eine Vorschau freischalten. Ein pauschales
   * ``.sk2-btn { disabled = false }`` nach jedem Prüflauf hätte sie alle
   * geöffnet - und damit genau die Sicherung ausgehebelt, für die sie da ist
   * (beim Bau bemerkt, 16.08.2026). */
  _knoepfe(an) {
    document.querySelectorAll('.sk2-btn').forEach(b => {
      if (b.classList.contains('sk2-fix-anwenden')) {
        if (!an) b.disabled = true;      // sperren ja, freigeben nein
        return;
      }
      b.disabled = !an;
    });
  }

  /** Umgekehrte Lesart von ``_knoepfe`` - „läuft gerade" statt „ist frei". */
  _sperren(an) {
    this.laeuft = an;
    this._knoepfe(!an);
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

  /* ── Fixer ────────────────────────────────────────────────────────────
     Ein Fixer SCHREIBT. Deshalb zwei getrennte Schritte, und „Anwenden" ist
     gesperrt, bis die Vorschau gelaufen ist: Wer nicht gesehen hat, welche
     Dateien es trifft, soll den Knopf nicht drücken können (16.08.2026). */
  async fixVorschau(slug) {
    if (this.laeuft) return;
    this._sperren(true);
    this._anhaengen(`… Vorschau ${slug}`, true);
    try {
      const r = await fetch(`?fix_vorschau=${encodeURIComponent(slug)}`,
                            {headers: {'X-Requested-With': 'fetch'}});
      const d = await r.json();
      this._anhaengen(this._bericht(d));
      // Freischalten nur, wenn es überhaupt etwas zu tun gibt.
      const knopf = document.querySelector(`.sk2-fix-anwenden[data-fixer="${slug}"]`);
      const machbar = d.ok && (d.zeilen || []).some(z => z.machbar === 'ja');
      if (knopf) {
        knopf.disabled = !machbar;
        knopf.title = machbar
          ? 'Schreibt die oben gezeigten Dateien — Sicherung wird angelegt'
          : 'Nichts zu tun';
      }
    } catch (e) {
      this._anhaengen(`Vorschau ${slug} fehlgeschlagen: ${e}`);
    } finally {
      this._sperren(false);
    }
  }

  async fixAnwenden(slug) {
    if (this.laeuft) return;
    this._sperren(true);
    this._anhaengen(`… ${slug} wird angewandt`, true);
    try {
      const daten = new FormData();
      daten.append('fixer', slug);
      // AUS DEM COOKIE, nicht aus einem Formularfeld: Diese Seite hat kein
      // <form>, also auch kein verstecktes csrfmiddlewaretoken. Ohne Token
      // antwortet Django mit einer HTML-Fehlerseite, und der Aufrufer bekommt
      // „Unexpected token '<'" - eine Meldung, die nach kaputtem JavaScript
      // aussieht und in Wahrheit CSRF heißt (16.08.2026).
      const marke = this._csrf();
      if (marke) daten.append('csrfmiddlewaretoken', marke);
      const r = await fetch('', {method: 'POST', body: daten,
                                 headers: {'X-CSRFToken': marke}});
      const d = await r.json();
      this._anhaengen(this._fixBericht(d));
    } catch (e) {
      this._anhaengen(`Anwenden ${slug} fehlgeschlagen: ${e}`);
    } finally {
      this._sperren(false);
    }
  }

  /** Das CSRF-Token dieser Sitzung - aus dem Formularfeld oder dem Cookie. */
  _csrf() {
    const feld = document.querySelector('[name=csrfmiddlewaretoken]');
    if (feld) return feld.value;
    const keks = document.cookie.split('; ').find(c => c.startsWith('csrftoken='));
    return keks ? decodeURIComponent(keks.split('=')[1]) : '';
  }

  /** Was ein Fixer getan hat - geschrieben, zurückgespielt, übersprungen. */
  _fixBericht(d) {
    const strich = '='.repeat(72);
    const aus = [strich, `## ${d.titel || d.slug} — ANGEWANDT`, strich];
    if (!d.ok) {
      aus.push(`FEHLGESCHLAGEN: ${d.fehler || 'unbekannt'}`, '');
      return aus.join('\n');
    }
    aus.push(`${(d.geschrieben || []).length} Dateien geschrieben, `
             + `${(d.zurueckgespielt || []).length} zurückgespielt, `
             + `${(d.uebersprungen || []).length} übersprungen   [${d.dauer} s]`, '');
    for (const g of d.geschrieben || []) aus.push(`  GESCHRIEBEN   ${g.datei}`);
    // Zurückgespielt heißt: Das Netz hat einen Fehler gefunden. Das ist die
    // wichtigste Zeile des Berichts - sie nennt, was NICHT ging und warum.
    for (const z of d.zurueckgespielt || []) aus.push(`  ZURÜCK        ${z.datei}  ${z.grund}`);
    for (const u of d.uebersprungen || []) aus.push(`  übersprungen  ${u.datei}  ${u.grund}`);
    if (d.geschrieben && d.geschrieben.length) {
      aus.push('', `Sicherung: ${d.geschrieben[0].sicherung}`);
    }
    aus.push('');
    return aus.join('\n');
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
