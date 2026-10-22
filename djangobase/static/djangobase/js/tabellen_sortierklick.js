/* Sortierklick - entscheidet, ob ein Klick eine Tabelle sortiert, und nach welcher Spalte.
   ==========================================================================
   Herausgelöst aus tabellen_sortierung.js am 16.10.2026 (die Datei lag über
   300 Zeilen), als der Sortierpfeil ein eigener Knopf wurde. Kein Import von
   TabellenSortierung - die Richtung ist umgekehrt, sonst entstünde ein Ring.

   DER KNOPF (Ansage Edgar 16.10.2026: „ich klicke auf die Spalte und der Text
   wird ausgewählt … mach klaren Sortierbutton, mit Klickfeld, am besten in
   anderer Hintergrundfarbe"): Seit 16.08.2026 ist die Beschriftung markierbar,
   und eine bestehende Textmarkierung hält jeden Klick auf die Kopfzelle zurück
   (Markieren geht vor Sortieren, siehe ``_markiert``). Der Knopf ``.tsort-pfeil``
   sortiert IMMER und hebt eine Markierung dabei auf; ein Klick auf die
   Beschriftung verhält sich wie bisher. */

export class Sortierklick {

  /** Die Kopfzelle, nach der dieser Klick sortieren soll - oder ``null``. */
  static ziel(e) {
    const ziel = e.target;
    if (!ziel || !ziel.closest) return null;
    if (ziel.closest('table.sortable thead th .tsort-pfeil')) {
      const sel = window.getSelection && window.getSelection();
      if (sel && String(sel).length) sel.removeAllRanges();
    } else if (Sortierklick._markiert()) {
      return null;
    }
    if (ziel.closest('.tb-griff')) return null;      // Breiten-Ziehen
    const th = ziel.closest('table.sortable thead th');
    if (!th || th.dataset.sortAus !== undefined) return null;
    // `data-sort-aus` AN DER TABELLE: Die Zeilenfolge bedeutet etwas
    // (BWA-Gliederung, Steuer-Kennzahlen, Tage eines Stundenzettels).
    // Solche Tabellen tragen `sortable` normalerweise gar nicht erst;
    // steht es doch da, gilt die ausdrueckliche Marke.
    if (th.closest('table').dataset.sortAus !== undefined) return null;
    // NUR die unterste Kopfzeile sortiert. Tabellen mit einer GRUPPEN-Zeile
    // darüber (Walk-Forward: „Ergebnis beim Suchen" spannt mehrere Spalten)
    // haben dort th-Elemente mit colspan - deren Index in der Zeile ist
    // nicht der Spaltenindex, ein Klick hätte nach der falschen Spalte
    // sortiert (Befund beim Umbau 11.08.2026).
    if (th.parentNode !== Sortierklick.kopfzeile(th.closest('table'))) return null;
    return th;
  }

  /** Ist gerade Tabellentext markiert? Dann gehört der Klick dem Markieren.
   *
   *  Der Schutz ist dafuer da, dass ein Doppelklick auf Tabellentext die
   *  Auswahl nicht sofort wieder wegsortiert - ABER NICHT AUS EINEM
   *  EINGABEFELD HERAUS (25.08.2026). Steht der Cursor in einem Feld der
   *  Tabelle - die Werkzeugliste hat deren zwei je Zeile, die
   *  Kriteriums-Nummer und das Argument -, dann meldet ``getSelection()`` je
   *  nach Browser die Auswahl IM FELD. Der naechste Klick auf eine
   *  Spaltenueberschrift lief damit ins ``return``, und die Sortierung wirkte
   *  kaputt: gemeldet als "bei einer Aenderung der Nummern funktioniert der
   *  Sortier-Button nicht mehr". Eine Auswahl innerhalb eines Feldes gehoert
   *  zum Bearbeiten, nicht zum Lesen. */
  static _markiert() {
    const aktiv = document.activeElement;
    const imFeld = aktiv && /^(INPUT|TEXTAREA|SELECT)$/.test(aktiv.tagName);
    const sel = window.getSelection && window.getSelection();
    return !imFeld && !!sel && String(sel).length > 0;
  }

  /** Die Zeile mit den ECHTEN Spaltenköpfen: die UNTERSTE des <thead>.
   *
   *  Darüber können Gruppen-Zeilen stehen (th mit colspan). Nur die unterste
   *  Zeile hat je Spalte genau eine Zelle - nur dort stimmt der Index. */
  static kopfzeile(tabelle) {
    const k = tabelle && tabelle.tHead;
    return (k && k.rows.length) ? k.rows[k.rows.length - 1] : null;
  }
}
