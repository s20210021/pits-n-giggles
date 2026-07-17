# MIT License
#
# Copyright (c) [2026] [Ashwin Natarajan]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# -------------------------------------- IMPORTS -----------------------------------------------------------------------

import json
import locale
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# -------------------------------------- CLASSES -----------------------------------------------------------------------

_DEFAULT_LOG_PREFIX = "[i18n]"


class TranslationManager:
    """Translation manager for Pits n' Giggles.

    Loads JSON language packs from a locales directory and provides
    key-based translation lookups with {param} interpolation.

    Falls back to the English value when a key is missing in the
    active locale.  Falls back to the key itself when neither the
    active locale nor the fallback locale have it.
    """

    # Default locale directory relative to project root or packaged app base
    DEFAULT_LOCALE_DIR = "locales"

    def __init__(
        self,
        locale_dir: str | Path = DEFAULT_LOCALE_DIR,
        fallback_locale: str = "en",
        logger: Optional[logging.Logger] = None,
    ):
        """Initialise the translation manager.

        Args:
            locale_dir: Path to the directory containing ``{locale}.json`` files.
            fallback_locale: Locale code to fall back to when a key is missing.
            logger: Optional logger instance.
        """
        self._log = logger or logging.getLogger(__name__)
        self._log_prefix = _DEFAULT_LOG_PREFIX

        self._locale_dir = Path(locale_dir)
        self._fallback_locale = fallback_locale
        self._current_locale: str = fallback_locale
        self._translations: Dict[str, Dict[str, str]] = {}
        self._available: Dict[str, str] = {}  # locale_code → label

        self._load_all()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        """Scan the locale directory and load every ``*.json`` file."""
        self._translations.clear()
        self._available.clear()

        if not self._locale_dir.is_dir():
            self._log.warning(
                "%s Locale directory not found: %s",
                self._log_prefix,
                self._locale_dir,
            )
            return

        for path in sorted(self._locale_dir.glob("*.json")):
            locale_code = path.stem  # e.g. "en" → "en.json"
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                translations = data.get("translations", data)
                label = data.get("label", locale_code)
                self._translations[locale_code] = translations
                self._available[locale_code] = label
                self._log.info(
                    "%s Loaded locale '%s' (%s) — %d keys",
                    self._log_prefix,
                    locale_code,
                    label,
                    len(translations),
                )
            except Exception as exc:
                self._log.error(
                    "%s Failed to load locale file %s: %s",
                    self._log_prefix,
                    path,
                    exc,
                )

        if self._fallback_locale not in self._translations:
            self._log.warning(
                "%s Fallback locale '%s' not loaded — missing keys "
                "will appear as raw key names.",
                self._log_prefix,
                self._fallback_locale,
            )

    def reload(self) -> None:
        """Re-scan the locale directory.  Useful when language packs are
        updated at runtime (e.g. during development)."""
        old_locale = self._current_locale
        self._load_all()
        if old_locale not in self._translations:
            self._current_locale = self._fallback_locale

    # ------------------------------------------------------------------
    # Locale selection
    # ------------------------------------------------------------------

    @property
    def current_locale(self) -> str:
        """The active locale code (e.g. ``"en"``, ``"zh-CN"``)."""
        return self._current_locale

    @current_locale.setter
    def current_locale(self, locale_code: str) -> None:
        if locale_code not in self._translations:
            raise KeyError(
                f"Locale '{locale_code}' is not loaded. "
                f"Available: {list(self._translations)}"
            )
        self._current_locale = locale_code

    @property
    def available_locales(self) -> Dict[str, str]:
        """Mapping of locale codes to their display labels."""
        return dict(self._available)

    @classmethod
    def detect_system_locale(
        cls,
        supported: Dict[str, str],
        default: str = "en",
    ) -> str:
        """Detect the best-matching system locale from the supported set.

        Args:
            supported: ``{locale_code: label}`` mapping (e.g. from
                       :attr:`available_locales`).
            default: Fallback locale when detection fails.

        Returns:
            A locale code that is present in *supported*, or *default*.
        """
        try:
            sys_lc = locale.getlocale()[0]
        except Exception:
            sys_lc = None

        if not sys_lc:
            return default

        # Exact match
        if sys_lc in supported:
            return sys_lc

        # Language-only match (e.g. "zh" for "zh-CN")
        lang = sys_lc.split("_", 1)[0].lower()
        for code in supported:
            if code.split("-", 1)[0].lower() == lang:
                return code

        return default

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def tr(self, key: str, **kwargs: Any) -> str:
        """Look up *key* in the active locale.

        Args:
            key: Dot-separated translation key, e.g. ``"frontend.table.header_pos"``.
            **kwargs: Optional format parameters for ``str.format()`` interpolation.

        Returns:
            The translated string, or the English fallback, or the key itself
            if nothing is found.
        """
        # 1. Try the active locale.
        value = self._lookup(key, self._current_locale)
        if value is not None:
            return self._interpolate(value, kwargs)

        # 2. Try the fallback locale.
        if self._current_locale != self._fallback_locale:
            value = self._lookup(key, self._fallback_locale)
            if value is not None:
                return self._interpolate(value, kwargs)

        # 3. Give up — return the key.
        self._log.warning(
            "%s Missing translation key '%s' (locale=%s)",
            self._log_prefix,
            key,
            self._current_locale,
        )
        return key

    def _lookup(self, key: str, locale_code: str) -> Optional[str]:
        """Walk the dotted *key* in the *locale_code* translations dict."""
        translations = self._translations.get(locale_code)
        if translations is None:
            return None

        parts = key.split(".")
        current: Any = translations
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        if isinstance(current, str):
            return current
        return None

    @staticmethod
    def _interpolate(template: str, kwargs: Dict[str, Any]) -> str:
        """Apply ``str.format(**kwargs)`` safely."""
        if not kwargs:
            return template
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def as_flat_dict(self) -> Dict[str, str]:
        """Return all active-locale translations as a flat ``{key: value}`` dict.

        Useful for embedding into HTML/JavaScript or passing as a QML
        context property.
        """
        return self._flatten(self._current_locale)

    def as_json(self) -> str:
        """Return all active-locale translations as a JSON string."""
        return json.dumps(self.as_flat_dict(), ensure_ascii=False)

    def _flatten(self, locale_code: str, prefix: str = "") -> Dict[str, str]:
        """Recursively flatten the translations dict for *locale_code*."""
        translations = self._translations.get(locale_code)
        if translations is None:
            return {}

        result: Dict[str, str] = {}

        def _walk(node: Any, path: str) -> None:
            if isinstance(node, dict):
                for key, child in node.items():
                    _walk(child, f"{path}.{key}" if path else key)
            elif isinstance(node, str):
                result[path] = node

        _walk(translations, prefix)
        return result
