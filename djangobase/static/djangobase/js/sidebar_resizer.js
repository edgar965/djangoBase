/**
 * djangoBase SidebarResizer — verschiebbarer Balken zwischen Sidebar und
 * Inhalt.
 *
 * Element: #db-sidebar-resizer  (eigener Selektor, damit fremde Resizer
 * — z. B. der des Assistant — nicht beeinflusst werden).
 *
 * Persistenz (Reihenfolge):
 *   1. data-initial-width auf dem Element — vom Server gerendert (z. B.
 *      aus einer UserUiPref-Tabelle). Hat hoechste Prioritaet.
 *   2. localStorage — als Browser-lokaler Cache, ueberlebt Reload sofort
 *      ohne Server-Roundtrip.
 *   3. data-default — Fallback wenn nichts gespeichert.
 *
 * Server-Persistenz (optional, opt-in per data-attrs):
 *   data-save-url       — POST-Endpoint, der den Wert speichert
 *   data-save-field     — wenn gesetzt: Body = {<field>: {<key>: width}}
 *                          z. B. data-save-field="pane_widths"
 *                          und  data-save-key="sidebar"
 *                          -> {"pane_widths": {"sidebar": 280}}
 *   data-save-key       — wenn data-save-field LEER: Body = {<key>: width}
 *                          -> {"sidebar": 280}
 *   data-save-debounce  — Debounce ms (Default 350)
 *
 * Custom-Event (immer ausgeloest, unabhaengig von Server-Persistenz):
 *   db:sidebar-resized  bubbles=true, detail={width, key, persisted}
 *   Projekte koennen darauf hoeren um eigene Aktionen anzuhaengen
 *   (z. B. zusaetzliche Pane-Layouts neu rechnen).
 *
 * Konfiguration ueber data-attrs:
 *   data-key            localStorage-Key (Default "djangobase.sidebarWidth")
 *   data-min / data-max / data-default  Grenzen + Default in px
 *   data-extra-vars     "--ct-sidebar-width,--my-other" — zusaetzliche
 *                       CSS-Variablen die parallel zu --sidebar-width
 *                       gesetzt werden (komma-separiert)
 *   data-initial-width  Server-gelieferte Startbreite (siehe oben)
 */
(function () {
    var el = document.getElementById('db-sidebar-resizer');
    if (!el) return;

    var KEY = el.dataset.key || 'djangobase.sidebarWidth';
    var MIN = parseInt(el.dataset.min, 10) || 140;
    var MAX = parseInt(el.dataset.max, 10) || 600;
    var DEFAULT = parseInt(el.dataset.default, 10) || 250;
    var INITIAL = parseInt(el.dataset.initialWidth, 10) || 0;
    var EXTRA_VARS = (el.dataset.extraVars || '').split(',')
        .map(function (s) { return s.trim(); }).filter(Boolean);

    var SAVE_URL = el.dataset.saveUrl || '';
    var SAVE_FIELD = el.dataset.saveField || '';
    var SAVE_KEY = el.dataset.saveKey || 'sidebar';
    var SAVE_DEBOUNCE = parseInt(el.dataset.saveDebounce, 10) || 350;

    function clamp(w) { return Math.max(MIN, Math.min(MAX, w)); }

    function setWidth(w) {
        w = clamp(w);
        var root = document.documentElement;
        root.style.setProperty('--sidebar-width', w + 'px');
        EXTRA_VARS.forEach(function (v) { root.style.setProperty(v, w + 'px'); });
        return w;
    }

    function saveLocal(w) {
        try { localStorage.setItem(KEY, String(w)); } catch (e) { /* ignore */ }
    }

    function csrfCookie() {
        var match = document.cookie.split('; ').find(function (r) {
            return r.indexOf('csrftoken=') === 0;
        });
        return match ? decodeURIComponent(match.split('=')[1]) : '';
    }

    var saveTimer = null;
    function saveServer(w) {
        if (!SAVE_URL) return;
        clearTimeout(saveTimer);
        saveTimer = setTimeout(function () {
            var body;
            if (SAVE_FIELD) {
                body = {};
                body[SAVE_FIELD] = {};
                body[SAVE_FIELD][SAVE_KEY] = w;
            } else {
                body = {};
                body[SAVE_KEY] = w;
            }
            fetch(SAVE_URL, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfCookie(),
                },
                body: JSON.stringify(body),
            }).catch(function () { /* best-effort */ });
        }, SAVE_DEBOUNCE);
    }

    function emit(width, persisted) {
        try {
            el.dispatchEvent(new CustomEvent('db:sidebar-resized', {
                bubbles: true,
                detail: { width: width, key: SAVE_KEY, persisted: !!persisted },
            }));
        } catch (e) { /* ignore */ }
    }

    function persist(w) {
        saveLocal(w);
        saveServer(w);
        emit(w, true);
    }

    // Startbreite: server-rendered > localStorage > default
    var current;
    if (INITIAL) {
        current = clamp(INITIAL);
    } else {
        current = DEFAULT;
        try {
            var stored = parseInt(localStorage.getItem(KEY), 10);
            if (stored) current = clamp(stored);
        } catch (e) { /* ignore */ }
    }
    setWidth(current);

    el.addEventListener('mousedown', function (e) {
        // Aus eingeklapptem Zustand heraus ziehen = aufklappen.
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
            persist(current);
        }
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
        e.preventDefault();
    });

    // Doppelklick = auf Standardbreite zuruecksetzen.
    el.addEventListener('dblclick', function () {
        current = setWidth(DEFAULT);
        persist(current);
    });
})();
