/**
 * djangoBase SidebarResizer — verschiebbarer Balken zwischen Sidebar und
 * Inhalt. Die Breite wird clientseitig in localStorage gespeichert
 * (kein Server-Endpunkt noetig).
 *
 * Element: #db-sidebar-resizer  (eigener Selektor, damit fremde Resizer
 * — z. B. der des Assistant — nicht beeinflusst werden).
 * Konfiguration via data-min / data-max / data-default (px).
 */
(function () {
    var el = document.getElementById('db-sidebar-resizer');
    if (!el) return;

    var KEY = el.dataset.key || 'djangobase.sidebarWidth';
    var MIN = parseInt(el.dataset.min, 10) || 140;
    var MAX = parseInt(el.dataset.max, 10) || 600;
    var DEFAULT = parseInt(el.dataset.default, 10) || 250;
    // data-extra-vars="--ct-sidebar-width,--my-other-var" — zusaetzliche
    // CSS-Variablen die parallel zu --sidebar-width gesetzt werden, fuer
    // Projekte deren bestehende CSS auf eigene Variablen-Namen reagiert.
    var EXTRA_VARS = (el.dataset.extraVars || '').split(',')
        .map(function (s) { return s.trim(); }).filter(Boolean);

    function clamp(w) { return Math.max(MIN, Math.min(MAX, w)); }

    function setWidth(w) {
        w = clamp(w);
        var root = document.documentElement;
        root.style.setProperty('--sidebar-width', w + 'px');
        EXTRA_VARS.forEach(function (v) { root.style.setProperty(v, w + 'px'); });
        return w;
    }

    function save(w) {
        try { localStorage.setItem(KEY, String(w)); } catch (e) { /* ignore */ }
    }

    // Startbreite: gespeicherter Wert oder Default.
    var current = DEFAULT;
    try {
        var stored = parseInt(localStorage.getItem(KEY), 10);
        if (stored) current = clamp(stored);
    } catch (e) { /* ignore */ }
    setWidth(current);

    el.addEventListener('mousedown', function (e) {
        // Aus eingeklapptem Zustand heraus ziehen = aufklappen (auch persistieren).
        if (document.body.classList.contains('sidebar-collapsed')) {
            document.body.classList.remove('sidebar-collapsed');
            try { localStorage.setItem('djangobase.sidebarCollapsed', '0'); } catch (err) {}
        }
        var startX = e.clientX;
        var startW = current;
        el.classList.add('dragging');
        document.body.classList.add('resizing-sidebar');

        function onMove(ev) { current = setWidth(startW + (ev.clientX - startX)); }
        function onUp() {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
            el.classList.remove('dragging');
            document.body.classList.remove('resizing-sidebar');
            save(current);
        }
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
        e.preventDefault();
    });

    // Doppelklick = auf Standardbreite zuruecksetzen.
    el.addEventListener('dblclick', function () {
        current = setWidth(DEFAULT);
        save(current);
    });
})();
