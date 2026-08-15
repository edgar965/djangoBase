/* TabellenBreiten - ziehbare, GEMERKTE Spaltenbreiten fuer klassische <table>-
   Elemente.
   ==========================================================================
   Entstanden in shortlongx (Ansage 05.08.2026, IB-Seite: Positionen, Offene und
   Ausgefuehrte Orders), am 11.08.2026 nach djangoBase gezogen, damit alle
   Projekte dieselbe Tabellen-Bedienung haben. Das Gegenstueck fuer die
   Sortierung ist ``tabellen_sortierung.js``; beide vertragen sich (der Griff
   faengt den Klick ab, der Pfeil sitzt links daneben).

   Das CSS dazu steht in ``css/tabellen.css`` - OHNE das ist der Griff
   unsichtbar und nicht greifbar.

   Hier bekommen BESTEHENDE Template-Tabellen Griffe an die Kopfzellen.

   EINE Instanz verwaltet eine GRUPPE von Tabellen mit gemeinsamem Speicher:
   Ziehen an einer Tabelle setzt die Spalte (gleicher data-key) LIVE in allen
   Tabellen der Gruppe - so bleiben „Offene" und „Ausgefuehrte Orders" deckungs-
   gleich (Ansage 05.08.2026). Spalten ohne data-key laufen ueber ihren Index.

   Verhalten:
   - Ohne gemerkte Breiten bleibt alles im Auto-Layout (wie bisher). Beim ERSTEN
     Ziehen wird der Ist-Zustand der Gruppe eingefroren (table-layout:fixed).
     WICHTIG dabei: th/td brauchen box-sizing:border-box (CSS der Seite), sonst
     springen die Breiten beim Einfrieren um das Zellen-Padding.
   - Breiten liegen in localStorage je Gruppen-Key + Spalten-Key und ueberleben F5.
   - Der Griff sitzt INNERHALB der Kopfzelle (right:0) - er darf nicht ueberstehen,
     weil table-layout:fixed Ueberstehendes kappt und der Griff unklickbar wuerde.
   - Griff faengt click/mousedown ab (Sortier-Klick bleibt getrennt); Doppelklick
     setzt die gemerkten Breiten der ganzen Gruppe zurueck. */
export class TabellenBreiten {
  /** Schmaler darf keine Spalte gezogen werden.
   *
   *  WARUM 70 UND NICHT 34 (Meldung 11.08.2026: „Pfeil viel zu gross"):
   *  Der Sortier-Pfeil ist 11 px breit und sitzt fest am rechten Rand der
   *  Kopfzelle. Bei den frueheren 34 px Mindestbreite nahm er ein DRITTEL der
   *  Spalte ein - er war nicht groesser geworden, die Spalte war zu schmal.
   *  Dazu blieb von der Ueberschrift nichts uebrig.
   *
   *  70 px ist Platz fuer ein kurzes Wort plus Pfeil. Wer eine Spalte wirklich
   *  wegdruecken will, hat dafuer den Doppelklick (setzt alle Breiten zurueck)
   *  bzw. blendet die Spalte in der jeweiligen Seite aus. */
  static MIN_PX = 70;

  /** ``vorgaben`` = {spaltenKey: px}: feste Start-Breiten. Mit Vorgaben wird die
   *  Gruppe SOFORT eingefroren - alle Tabellen zeigen dieselbe Spalte gleich
   *  breit, deckungsgleich ab dem ersten Rendern (Ansage 05.08.2026: „gleiche
   *  Spaltenbreiten für Offene und Ausgeführte"). Gespeicherte Breiten gewinnen. */
  constructor(tabellen, key, vorgaben) {
    const liste = Array.isArray(tabellen) ? tabellen : [tabellen];
    this.ts = liste.map(t => typeof t === 'string' ? document.getElementById(t) : t).filter(Boolean);
    this.key = 'tblBreiten:' + key;
    this.vorgaben = vorgaben || null;
  }

  /** Gemerkte Breiten - schon gespeicherte ZU SCHMALE werden angehoben.
   *
   *  Wer vor dem 11.08.2026 eine Spalte auf 34 px gezogen hat, haette diesen
   *  Zustand sonst fuer immer behalten: Die neue Mindestbreite greift nur beim
   *  Ziehen, nicht auf das, was schon im Browser steht. */
  _laden() {
    let b;
    try { b = JSON.parse(localStorage.getItem(this.key) || '{}'); } catch (e) { return {}; }
    for (const k of Object.keys(b)) {
      if (b[k] < TabellenBreiten.MIN_PX) b[k] = TabellenBreiten.MIN_PX;
    }
    return b;
  }

  _merken(sk, px) {
    const b = this._laden();
    b[sk] = Math.round(px);
    try { localStorage.setItem(this.key, JSON.stringify(b)); } catch (e) {}
  }

  /** Die Kopfzellen der UNTERSTEN <thead>-Zeile.
   *
   *  Nicht ``querySelectorAll('th')`` (Korrektur 11.08.2026): Tabellen mit einer
   *  GRUPPEN-Zeile darueber (Walk-Forward) lieferten damit auch die
   *  colspan-Zellen der Gruppenzeile. Die Spalten-Zuordnung verschob sich, und
   *  ``_summeSetzen`` zaehlte Breiten doppelt. Bei einzeiligem Kopf ist das
   *  Ergebnis unveraendert. */
  _ths(t) {
    const k = t && t.tHead;
    return (k && k.rows.length) ? [...k.rows[k.rows.length - 1].cells] : [];
  }

  _sk(th, i) { return th.dataset.key || ('i' + i); }

  /** Breite einer Spalte (per Key) in ALLEN Tabellen der Gruppe setzen. */
  _setzen(sk, px) {
    this.ts.forEach(t => {
      this._ths(t).forEach((th, i) => {
        if (this._sk(th, i) === sk) th.style.width = px + 'px';
      });
      this._summeSetzen(t);
      this._hochkantPruefen(t);
    });
  }

  /** Ueberschriften neu ausrichten, wenn sich die Spaltenbreite geaendert hat.
   *
   *  Wird die Spalte schmal, muss die Beschriftung hochkant; wird sie wieder
   *  breit, soll sie sich hinlegen. Die Entscheidung trifft
   *  ``TabellenSortierung.hochkant`` - die Kopplung laeuft ueber ein optionales
   *  globales Objekt, damit TabellenBreiten ohne die Sortierung benutzbar
   *  bleibt (nicht jede Tabelle ist sortierbar). */
  _hochkantPruefen(t) {
    const ts = window.TabellenSortierung;
    if (ts && typeof ts.hochkant === 'function') ts.hochkant(t);
  }

  /** Tabellenbreite = SUMME der Spaltenbreiten. Ohne das skaliert der Browser
   *  die px-Vorgaben proportional auf die Container-Breite (width:100 % der
   *  Seite) hoch - je Tabelle anders, und die Spalten waren wieder ungleich
   *  (gemessen 05.08.2026: 48 px Vorgabe wurde in einer Tabelle 100 px, in der
   *  anderen 48 px). Der .tbl-wrap scrollt, wenn die Summe breiter ist. */
  _summeSetzen(t) {
    let s = 0;
    this._ths(t).forEach(th => {
      s += parseFloat(th.style.width) || th.getBoundingClientRect().width;
    });
    t.style.width = Math.round(s) + 'px';
  }

  /** Ist-Breiten ALLER Spalten der Gruppe einfrieren - noetig, bevor eine einzelne
   *  Spalte gezielt geaendert werden kann (im Auto-Layout verteilt der Browser um).
   *
   *  WICHTIG (Fehler vom 06.08.2026): Frueher stieg die Methode aus, sobald die
   *  Tabelle schon ``table-layout:fixed`` war - und liess Spalten OHNE eigene Breite
   *  unangetastet. Das passiert bei jeder Tabelle mit DYNAMISCHEN Spalten (die
   *  Jahres-Spalten der Best-Technik-Kreuztabelle stehen in keiner Vorgabe-Liste):
   *  ``_summeSetzen`` mass ihre vom Browser verteilte Restbreite, setzte daraus die
   *  Tabellenbreite, woraufhin der Browser die Restbreite NEU verteilte - eine
   *  Rueckkopplung, die das Ziehen unbrauchbar machte und die letzte Spalte gar
   *  nicht mehr wachsen liess. Jetzt wird JEDE Spalte ohne feste Breite eingefroren. */
  _einfrieren() {
    this.ts.forEach(t => {
      const offen = this._ths(t).filter(th => !parseFloat(th.style.width));
      if (t.style.tableLayout === 'fixed' && !offen.length) return;
      // Mindestbreite wie in binden() (16.08.2026) - ohne sie friert hier eine
      // vom Browser auf ~12 px gequetschte Spalte dauerhaft ein.
      offen.forEach(th => {
        th.style.width = Math.max(TabellenBreiten.MIN_PX,
                                  th.getBoundingClientRect().width) + 'px';
      });
      t.style.tableLayout = 'fixed';
      this._summeSetzen(t);
    });
  }

  zuruecksetzen() {
    try { localStorage.removeItem(this.key); } catch (e) {}
    this.ts.forEach(t => {
      t.style.tableLayout = '';
      t.style.width = '';
      this._ths(t).forEach(th => { th.style.width = ''; });
    });
    if (this.vorgaben) this.binden();       // zurück auf die einheitlichen Vorgaben
  }

  binden() {
    const b = this._laden();
    const fest = Object.keys(b).length > 0 || !!this.vorgaben;
    this.ts.forEach(t => {
      if (!t.tHead) return;
      if (fest) t.style.tableLayout = 'fixed';
      const ths = this._ths(t);
      ths.forEach((th, i) => {
        const sk = this._sk(th, i);
        const px = b[sk] || (this.vorgaben && this.vorgaben[sk]) || 0;
        if (px) th.style.width = px + 'px';
        th.style.position = 'relative';
        // Griff an JEDER Spalte - auch der letzten (Ansage 05.08.2026): seit die
        // Tabelle exakt die Spalten-Summe breit ist, gibt es keine „Rest-Spalte".
        if (!th.querySelector('.tb-griff')) th.appendChild(this._griff(th, sk));
      });
      // Spalten OHNE Vorgabe/gemerkte Breite bekommen ihre Ist-Breite fest zugewiesen,
      // BEVOR die Tabellenbreite aus der Summe entsteht - sonst misst _summeSetzen eine
      // vom Browser verteilte Restbreite, die sich durch das Setzen sofort wieder
      // aendert (siehe _einfrieren).
      // MINDESTBREITE, nicht die blosse Ist-Breite (Fehler vom 16.08.2026):
      // Sobald die Spalten MIT Vorgabe den Container schon fuellen, verteilt der
      // Browser im fixed-Layout auf die restlichen fast nichts - gemessen ~12 px.
      // Diese ~12 px wurden hier FESTGESCHRIEBEN, und die Ueberschriften brachen
      // Buchstabe fuer Buchstabe um (Optimierungs-Ergebnistabelle: 25 Spalten,
      // davon 4 mit Vorgabe). MIN_PX gilt schon beim Ziehen und beim Laden -
      // hier fehlte es als Einzige.
      if (fest) {
        ths.filter(th => !parseFloat(th.style.width))
           .forEach(th => {
             const ist = th.getBoundingClientRect().width;
             th.style.width = Math.max(TabellenBreiten.MIN_PX, ist) + 'px';
           });
        this._summeSetzen(t);
      }
    });
    return this;
  }

  /** Der waagerecht scrollende Vorfahr einer Zelle (BtTabelle: ``.bt-scroll``,
   *  IB-Seite: ``.tbl-wrap``). Null, wenn die Tabelle gar nicht in einem scrollenden
   *  Kasten steckt - dann gibt es beim Ziehen auch nichts zu retten. */
  _scroller(el) {
    for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      const ox = getComputedStyle(n).overflowX;
      if (ox === 'auto' || ox === 'scroll') return n;
    }
    return null;
  }

  /** Griff fuer EINE Kopfzelle bauen (auch fuer nachruesten() nach Kopf-Neuaufbau). */
  _griff(th, sk) {
    const g = document.createElement('span');
    g.className = 'tb-griff';
    g.title = 'Spaltenbreite ziehen (wirkt auf alle Tabellen dieser Gruppe) · Doppelklick setzt alle Breiten zurück';
    g.addEventListener('click', e => e.stopPropagation());
    g.addEventListener('dblclick', e => { e.stopPropagation(); this.zuruecksetzen(); });
    g.addEventListener('mousedown', e => {
      e.preventDefault(); e.stopPropagation();
      this._einfrieren();
      document.body.classList.add('lg-zieht');
      const x0 = e.clientX, w0 = th.getBoundingClientRect().width;
      // WAAGERECHTE SCROLL-POSITION ueber das Ziehen retten (Meldung 07.08.2026):
      // Wird die Spalte schmaler, schrumpft die ganze Tabelle - das Scroll-Maximum
      // sinkt, und der Browser KAPPT scrollLeft auf den neuen Hoechstwert. Zieht man
      // danach wieder breiter, kommt der alte Wert nicht von selbst zurueck: Wer ganz
      // rechts stand, landete mitten in der Tabelle (gemessen: 397 -> 247 von 398).
      // Deshalb wird der Wunschwert festgehalten und nach jedem Setzen erneut gesetzt.
      const box = this._scroller(th);
      const sx = box ? box.scrollLeft : 0;
      const move = ev => {
        this._setzen(sk, Math.max(TabellenBreiten.MIN_PX, Math.round(w0 + ev.clientX - x0)));
        if (box) box.scrollLeft = sx;
      };
      const up = () => {
        document.removeEventListener('mousemove', move);
        document.removeEventListener('mouseup', up);
        document.body.classList.remove('lg-zieht');
        if (box) box.scrollLeft = sx;      // letzter Stand kann noch gekappt sein
        this._merken(sk, th.getBoundingClientRect().width);
      };
      document.addEventListener('mousemove', move);
      document.addEventListener('mouseup', up);
    });
    return g;
  }

  /** Fehlende Griffe nachruesten (nach innerHTML-Neuaufbau der Kopfzellen). */
  nachruesten() {
    this.ts.forEach(t => {
      this._ths(t).forEach((th, i) => {
        if (th.querySelector('.tb-griff')) return;
        th.style.position = 'relative';
        th.appendChild(this._griff(th, this._sk(th, i)));
      });
    });
  }
}
