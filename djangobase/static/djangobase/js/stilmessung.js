/**
 * Berechnete Stile aller Elemente mit `style="…"` erfassen — vor und nach dem
 * Umbau auf CSS-Klassen.
 *
 * WOZU: Eine CSS-Klasse hat eine NIEDRIGERE Spezifität als ein Inline-Stil.
 * Wo vorher `style="flex:1"` jede Regel überstimmt hat, kann nach dem Umbau
 * eine andere Regel gewinnen — die Seite sieht dann anders aus, ohne dass es
 * im Code auffällt. Deshalb wird jedes betroffene Element zweimal gemessen und
 * verglichen.
 *
 * Elemente werden über ihren Positionspfad im Baum identifiziert
 * (`3/1/0/12`) — stabil, solange der Umbau nur Attribute ändert.
 *
 * Aufruf in der Konsole (oder über Chrome-MCP):
 *     JSON.stringify(stilMessung())
 */
function stilMessung() {
    const pfad = (element) => {
        const teile = [];
        let knoten = element;
        while (knoten && knoten.parentElement) {
            teile.unshift([...knoten.parentElement.children].indexOf(knoten));
            knoten = knoten.parentElement;
        }
        return teile.join('/');
    };

    const messwerte = {};
    for (const element of document.querySelectorAll('[style], [data-stil]')) {
        // Welche Eigenschaften standen im Inline-Stil? Nur die zählen.
        const inline = element.getAttribute('style') || '';
        const namen = inline.split(';')
            .map(teil => teil.split(':')[0].trim())
            .filter(Boolean);
        const gemerkt = element.dataset.stil
            ? element.dataset.stil.split(',') : [];
        const alle = [...new Set([...namen, ...gemerkt])];
        if (!alle.length) continue;
        const berechnet = getComputedStyle(element);
        const werte = {};
        for (const name of alle) werte[name] = berechnet.getPropertyValue(name);
        messwerte[pfad(element)] = werte;
    }
    return messwerte;
}
