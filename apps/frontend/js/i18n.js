/**
 * Internationalisation (i18n) helper for the frontend.
 *
 * Translations are embedded into the page by the Jinja2 template via:
 *
 *   <script>window.__i18n = {{ i18n_dict() | tojson | safe }};</script>
 *
 * Usage:
 *   const t = window.__i18n.tr;
 *   label = t("frontend.table.header_pos");
 *   label = t("frontend.fuel.surplus", { laps: surplus });
 *
 * When a key is missing, the key itself is returned as a fallback.
 */
(function () {
    "use strict";

    var translations = window.__i18n || {};

    /**
     * Look up a dot-separated translation key and return the localised value.
     *
     * @param {string} key  Dot-separated key, e.g. "frontend.table.header_pos"
     * @param {object} [params]  Optional format parameters for {placeholder} substitution.
     * @returns {string}  Translated string, or the key if not found.
     */
    function tr(key, params) {
        var value = translations[key];
        if (value === undefined || value === null) {
            // Fall back to the key itself
            return key;
        }
        if (params) {
            return value.replace(/\{(\w+)\}/g, function (_, name) {
                return params[name] !== undefined ? String(params[name]) : "{" + name + "}";
            });
        }
        return value;
    }

    // Expose the helper globally
    window.__i18n = window.__i18n || {};
    window.__i18n.tr = tr;
})();
