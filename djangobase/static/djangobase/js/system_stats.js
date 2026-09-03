/* SystemStatsLeiste - GPU-/CPU-Auslastung als Pill-Leiste.
   ==========================================================================
   Geteiltes ES-Modul (eine Klasse pro Datei). Vorbild: CamTrack
   (app/templates/app/_system_stats.html + modules/system_stats.js).

   WARUM auf dem Optimierungs-Tab: Eine Grid-Optimierung läuft Minuten. Ohne
   Anzeige sieht man nicht, ob die Karte rechnet oder ob der Lauf im
   Vorbereitungsteil hängt (Python = CPU, ein Kern). Genau diese Unterscheidung
   hat am 27.07.2026 den Unterschied zwischen „Batch zu klein" (GPU bei 0,6 %)
   und „Zeilenbau" (CPU) sichtbar gemacht.

       import { SystemStatsLeiste } from '/static/djangobase/js/system_stats.js';
       SystemStatsLeiste.binden('opt-sysstats');      // <div id="opt-sysstats">

   DER PFAD IM BEISPIEL IST KEIN SCHMUCK (12.08.2026): Er stand hier nach dem
   Umzug noch auf dem alten Ort '/static/dashboard/…'. ShortLongX' Pruefung
   „ui-alle-seiten" folgt Modul-Importen rekursiv und liest dabei AUCH die
   Import-Zeilen aus Kommentaren - vier Seiten meldeten daraufhin eine fehlende
   Skriptdatei, die niemand mehr laedt. Ein falscher Beispielpfad in einer
   geteilten Datei ist teurer als anderswo: Er wird kopiert.
   ========================================================================== */

import { Basiswurzel } from '/static/djangobase/js/basiswurzel.js';

export class SystemStatsLeiste {
  /** Wohin gefragt wird. Anpassbar, weil JEDES Projekt ``djangobase.urls``
   *  unter einem eigenen Praefix einbindet:
   *
   *      shortlongx   path("hilfe/", include("djangobase.urls"))  -> /hilfe/api/system-stats/
   *      assistant    path("", ...)                               -> /api/system-stats/
   *
   *  Vor dem Umzug nach djangoBase (12.08.2026) stand hier die feste Adresse
   *  '/api/system-stats/' - die haette in jedem anderen Projekt einen 404
   *  geliefert, und die Leiste waere still leer geblieben.
   *
   *      SystemStatsLeiste.URL = '/meinpfad/api/system-stats/';   // vor .starten()
   */
  //  Seit 27.08.2026 steht hier keine feste Adresse mehr: Der Praefix
  //  kommt aus dem Grundgeruest (`Basiswurzel`). Ein Projekt, das die
  //  Zeile oben vergisst, bekommt damit trotzdem die richtige.
  static URL = Basiswurzel.weg('api/system-stats/');

  static WARN = 75;
  static GEFAHR = 90;
  static _timer = null;
  static _sichtbarkeit = null;
  static _ziel = null;
  static _takt = 2000;            // Ruhe-Takt; während eines Laufs schneller

  /** Das Aussehen der Leiste - vom Modul selbst mitgebracht.

     WARUM HIER (Ansage 07.08.2026, dreimal gemeldet): Das CSS stand als
     `extra_css`-Block INLINE in dax_handel.html. Jede weitere Seite, die
     `binden()` aufrief, bekam damit die Pills ohne jede Formatierung - auf
     /handelssysteme/best-technik/ stand die Leiste als nackter Fließtext da,
     ohne Rahmen und ohne Balken. Ein Modul, das sein Markup erzeugt, muss auch
     sein Aussehen mitbringen; sonst hängt es davon ab, ob jemand daran gedacht
     hat, das CSS in sein Template zu kopieren. */
  static CSS = `
.sysstats { display:inline-flex; gap:.3rem; flex-wrap:wrap; align-items:center }
.ss-pill { display:inline-flex; align-items:center; gap:.3rem; padding:.25rem .55rem;
  background:rgba(var(--fg-rgb, 224,232,240),.07); border:1px solid rgba(var(--fg-rgb, 224,232,240),.18);
  border-radius:999px; font-size:.78rem; color:rgba(var(--fg-rgb, 224,232,240),.85); line-height:1 }
/* Muss sein: die Klasse oben setzt display:inline-flex und schlaegt damit die
   Browser-Vorgabe fuer [hidden] - ohne diese Zeile bliebe eine ausgeblendete
   Pill (_gpuPillsZeigen) sichtbar. */
.ss-pill[hidden] { display:none }
.ss-pill .ss-icon i { font-size:.85rem; color:var(--accent) }
.ss-pill .ss-label { font-size:.6rem; text-transform:uppercase; letter-spacing:.04em;
  color:rgba(var(--fg-rgb, 224,232,240),.5); font-weight:700 }
.ss-pill .ss-bar { width:36px; height:5px; border-radius:3px;
  background:rgba(var(--fg-rgb, 224,232,240),.12); overflow:hidden }
.ss-pill .ss-fill { display:block; height:100%; width:0%; background:var(--accent);
  transition:width .4s, background .4s }
.ss-pill.ss-warn .ss-fill { background:#f59e0b }
.ss-pill.ss-danger .ss-fill { background:#f87171 }
.ss-pill .ss-num { font-variant-numeric:tabular-nums; color:rgba(var(--fg-rgb, 224,232,240),.95);
  font-weight:600; min-width:2.6em; text-align:right }
`;

  /** CSS einmal je Seite einhängen (mehrfaches binden() bleibt wirkungslos). */
  static _stilSetzen() {
    if (document.getElementById('sysstats-css')) return;
    const s = document.createElement('style');
    s.id = 'sysstats-css';
    s.textContent = this.CSS;
    document.head.appendChild(s);
  }

  /** Leiste in ein Element rendern und periodisch aktualisieren. */
  static binden(zielId) {
    const el = document.getElementById(zielId);
    if (!el || el.dataset.sysstats === '1') return;
    el.dataset.sysstats = '1';
    this._stilSetzen();
    this._ziel = el;
    el.className = 'sysstats';
    // Aufbau, Reihenfolge und Icons wie in CamTrack (_system_stats.html):
    // GPU · VRAM · Temp · CPU · RAM · Net. Temp und Net tragen keinen Balken,
    // weil sie keine Prozent-Groesse sind.
    const PILLS = [
      {k: 'gpu',  label: 'GPU',  icon: 'bi-gpu-card',          bar: true,  tip: 'GPU-Auslastung'},
      {k: 'vram', label: 'VRAM', icon: 'bi-memory',            bar: true,  tip: 'GPU-Speicher'},
      {k: 'temp', label: 'Temp', icon: 'bi-thermometer-half',  bar: false, tip: 'GPU-Temperatur'},
      {k: 'cpu',  label: 'CPU',  icon: 'bi-cpu-fill',          bar: true,  tip: 'CPU-Auslastung'},
      {k: 'ram',  label: 'RAM',  icon: 'bi-hdd-stack',         bar: true,  tip: 'RAM-Auslastung'},
      {k: 'net',  label: 'Net',  icon: 'bi-arrow-down-up',     bar: false, tip: 'Netzwerk-Belastung (Mbit/s, Down/Up aller Interfaces)'},
    ];
    el.innerHTML = PILLS.map(p => `
      <span class="ss-pill" data-k="${p.k}" title="${p.tip}">
        <span class="ss-icon"><i class="bi ${p.icon}"></i></span>
        <span class="ss-label">${p.label}</span>
        ${p.bar ? '<span class="ss-bar"><span class="ss-fill"></span></span>' : ''}
        <span class="ss-num">–</span>
      </span>`).join('');
    this.starten();
    return el;
  }

  /** Schneller takten, solange gerechnet wird (und danach wieder zurück). */
  static takt(ms) {
    if (ms === this._takt) return;
    this._takt = ms;
    this.starten();
  }

  static starten() {
    if (this._timer) clearInterval(this._timer);
    this._holen(true);                               // erster Abruf immer
    this._timer = setInterval(() => this._holen(), this._takt);
    if (!this._sichtbarkeit) {
      // WARUM DREI Ereignisse (28.07.2026): Chrome drosselt setInterval in nicht
      // sichtbaren Tabs auf einen Lauf je MINUTE und friert lange verdeckte Tabs
      // ganz ein. Ein Tab, der stundenlang offen liegt, zeigt dann einen Wert von
      // vor einer Minute - er sieht gültig aus, ist es aber nicht. Deshalb bei
      // jedem Zurückkommen sofort neu abrufen, und zwar auf allen Wegen, auf
      // denen ein Fenster wieder in den Vordergrund kommt.
      this._sichtbarkeit = () => { if (!document.hidden) this._holen(true); };
      document.addEventListener('visibilitychange', this._sichtbarkeit);
      window.addEventListener('focus', this._sichtbarkeit);
      window.addEventListener('pageshow', this._sichtbarkeit);
    }
  }

  static stoppen() { if (this._timer) { clearInterval(this._timer); this._timer = null; } }

  static async _holen(erzwingen) {
    // KEINE Hintergrund-Pause mehr. Sie sparte nichts (der Server cacht die Werte
    // ohnehin 1 s), sorgte aber dafuer, dass nach dem Zurueckwechseln von einem
    // anderen Tab kurz ein VERALTETER Wert stand - und der sah aus wie ein Messfehler
    // (28.07.2026: Leiste zeigte 39 %, waehrend die Karte real bei 100 % lief).
    if (!this._ziel) return;
    let d;
    try {
      d = await (await fetch(SystemStatsLeiste.URL, {cache: 'no-store'})).json();
    } catch (e) {
      // NICHT stumm zurueckkehren. Vorher blieb bei jedem fehlgeschlagenen Abruf
      // (z.B. Server-Neustart) der LETZTE Wert stehen - dauerhaft und ohne Hinweis.
      // Der Nutzer sah 100 %, waehrend die Karte laengst bei 30 % lief, und hielt die
      // Messung fuer kaputt (28.07.2026). Jetzt sagt die Leiste, dass sie nichts weiss.
      this._ausfall();
      return;
    }
    if (!d || !d.ok) { this._ausfall(); return; }
    // Alter des vorherigen Standes: war der Tab gedrosselt oder eingefroren, lag
    // zwischen zwei Abrufen viel mehr als der Takt. Das gehoert sichtbar gemacht -
    // ein stehender Wert sieht sonst aus wie eine ruhige Maschine (28.07.2026).
    this._luecke = this._stand ? (Date.now() - this._stand) : 0;
    this._stand = Date.now();
    this._zeitTip = new Date().toLocaleTimeString('de-DE');
    const g = d.gpu;
    // Ohne Grafikkarte stünden hier drei Pills mit „keine / – / –“ - auf einem
    // Server (NoiseSpy, 03.09.2026) ist das die Hälfte der Leiste, und keine
    // davon sagt etwas. Sie verschwinden, sobald der erste Abruf zeigt, dass
    // nvidia-smi nichts liefert; auf Maschinen MIT Karte ändert sich nichts.
    this._gpuPillsZeigen(Boolean(g));
    this._setzen('gpu', g ? g.util : null, g ? g.util + ' %' : 'keine',
      g ? `${g.name} – Auslastung ${g.util} %` : 'Keine NVIDIA-GPU erkannt (nvidia-smi nicht verfügbar)');
    const vram = g && g.mem_total ? Math.round(100 * g.mem_used / g.mem_total) : null;
    this._setzen('vram', vram, g ? (g.mem_used / 1024).toFixed(1) + ' GB' : '–',
      g ? `${g.mem_used} von ${g.mem_total} MB belegt` : '');
    this._setzen('temp', null, g ? g.temp + ' °C' : '–', g ? 'GPU-Temperatur' : '');
    this._setzen('cpu', d.cpu_percent, d.cpu_percent != null ? d.cpu_percent + ' %' : '–',
      d.kerne ? `Auslastung über alle ${d.kerne} logischen Kerne` : 'CPU-Auslastung');
    this._setzen('ram', d.ram_percent, d.ram_percent != null ? d.ram_percent + ' %' : '–',
      'Arbeitsspeicher belegt');
    // Netzwerk: Down/Up in Mbit/s, wie in CamTrack als ein Wertepaar ohne Balken
    const dn = d.net_recv_mbps, up = d.net_sent_mbps;
    this._setzen('net', null,
      (dn == null && up == null) ? '–' : `${this._mbit(dn)} ↓ ${this._mbit(up)} ↑`,
      'Netzwerk-Belastung (Mbit/s, Down/Up aller Interfaces)');
    this._setzenDisks(d.disks || []);
  }

  /** Mbit/s knapp: unter 10 mit einer Nachkommastelle, darüber gerundet. */
  static _mbit(v) {
    const n = Number(v);
    if (!isFinite(n)) return '0';
    return n < 10 ? n.toFixed(1).replace('.', ',') : String(Math.round(n));
  }

  /** Keine Verbindung: Werte ausgrauen statt einen alten Stand vorzugaukeln. */
  static _ausfall() {
    if (!this._ziel) return;
    this._ziel.querySelectorAll('.ss-pill').forEach(p => {
      p.querySelector('.ss-num').textContent = '?';
      p.title = 'Keine Verbindung zum Server – der Wert ist unbekannt (nicht 0).';
      p.style.opacity = '.45';
      const f = p.querySelector('.ss-fill'); if (f) f.style.width = '0%';
    });
  }

  /** GPU-, VRAM- und Temp-Pill ein- oder ausblenden.
   *
   *  Ausgeblendet wird über `hidden`, nicht entfernt: Steckt später eine Karte
   *  in der Maschine (oder wird nvidia-smi nachinstalliert), sind die Pills beim
   *  nächsten Abruf wieder da, ohne dass die Leiste neu gebaut werden muss. */
  static _gpuPillsZeigen(zeigen) {
    if (!this._ziel) return;
    ['gpu', 'vram', 'temp'].forEach(k => {
      const pill = this._ziel.querySelector(`.ss-pill[data-k="${k}"]`);
      if (pill) pill.hidden = !zeigen;
    });
  }

  static _setzen(key, pct, text, tip) {
    const pill = this._ziel && this._ziel.querySelector(`.ss-pill[data-k="${key}"]`);
    if (!pill) return;
    const num = pill.querySelector('.ss-num'), fill = pill.querySelector('.ss-fill');
    pill.style.opacity = '';                      // nach einem Ausfall wieder normal
    num.textContent = text;
    // Zeitstempel IMMER in den Tooltip: so ist an jeder Zahl ablesbar, wie alt sie
    // ist - und ob die Leiste überhaupt noch nachlädt.
    if (tip) pill.title = tip + (this._zeitTip ? `\nStand ${this._zeitTip}` : '')
                             + (this._luecke > 3 * this._takt
                                ? `\nDavor ${Math.round(this._luecke / 1000)} s Pause – der Tab lag im Hintergrund `
                                  + `und wurde vom Browser gedrosselt.` : '');
    if (fill && pct != null) fill.style.width = Math.max(0, Math.min(100, pct)) + '%';
    pill.classList.toggle('ss-warn', pct != null && pct >= this.WARN && pct < this.GEFAHR);
    pill.classList.toggle('ss-danger', pct != null && pct >= this.GEFAHR);
  }

  /** Festplatten-Pills (Start-/System-Platte + Projekt-Platte). Dynamisch,
   *  weil die Zahl der Platten je Rechner variiert - eine Pill je Laufwerk,
   *  Balken = Belegung in Prozent, Zahl = belegt/gesamt in GB. */
  static _setzenDisks(disks) {
    if (!this._ziel) return;
    for (const dk of disks) {
      const label = this._diskLabel(dk.name) + (dk.letter ? ` (${dk.letter})` : '');
      const id = ('disk-' + String(dk.name).replace(/[^A-Za-z0-9]/g, '')) || 'disk';
      let pill = this._ziel.querySelector(`.ss-pill[data-k="${id}"]`);
      if (!pill) {
        pill = document.createElement('span');
        pill.className = 'ss-pill';
        pill.dataset.k = id;
        // Kein Balken: Disk-I/O ist eine Rate, keine 0-100-%-Groesse (wie Net).
        pill.innerHTML =
          '<span class="ss-icon"><i class="bi bi-hdd"></i></span>'
          + `<span class="ss-label">${label}</span>`
          + '<span class="ss-num">–</span>';
        this._ziel.appendChild(pill);
      }
      const num = pill.querySelector('.ss-num');
      pill.style.opacity = '';
      // Lesen ↓, Schreiben ↑ (MB/s) — Einheit im Tooltip.
      num.textContent = `${this._mbit(dk.read_mbps)}↓ ${this._mbit(dk.write_mbps)}↑`;
      pill.title = `${label} – Lesen ${dk.read_mbps} MB/s, `
        + `Schreiben ${dk.write_mbps} MB/s (physische Platte)`
        + (this._zeitTip ? `\nStand ${this._zeitTip}` : '');
    }
  }

  /** 'PhysicalDrive0' -> 'Disk 0'; sonst Rohname (Unix: 'sda', 'nvme0n1'). */
  static _diskLabel(name) {
    const m = /^PhysicalDrive(\d+)$/i.exec(String(name));
    return m ? 'Disk ' + m[1] : String(name);
  }
}
