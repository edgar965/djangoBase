from .conf import conf


def djangobase(request):
    """Stellt Branding, Farben, Menue, Version und Layout-Optionen in
    jedem Template bereit. Die Layout-Keys (extra_css, extra_js_head,
    sidebar_template, theme_modes, theme_default, toast_stack) werden
    von djangobase/_shell.html + base_app.html konsumiert."""
    c = conf()
    return {"djangobase": {
        "titel": c["titel"],
        "untertitel": c["untertitel"],
        "logo_icon": c["logo_icon"],
        "farben": c["farben"],
        "menu": c["menu"],
        "version": c["version"],
        "extra_css": c["extra_css"],
        "extra_js_head": c["extra_js_head"],
        "sidebar_template": c["sidebar_template"] or "djangobase/_sidebar.html",
        "theme_modes": c["theme_modes"],
        "theme_default": c["theme_default"],
        "toast_stack": c["toast_stack"],
    }}
