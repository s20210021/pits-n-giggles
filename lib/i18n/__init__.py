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

"""Internationalisation (i18n) support for Pits n' Giggles.

Usage::

    from lib.i18n import tr, get_manager, set_locale

    # Get a one-shot translation (uses the module-level singleton).
    label = tr("frontend.table.header_pos")

    # Set the active locale.
    set_locale("zh-CN")

    # Access the manager directly for advanced use.
    mgr = get_manager()
    mgr.reload()
"""

import logging
from pathlib import Path
from typing import Optional

from .manager import TranslationManager

# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_manager: Optional[TranslationManager] = None
_logger_configured: bool = False


def _ensure_manager(logger: Optional[logging.Logger] = None) -> TranslationManager:
    """Return the module-level TranslationManager singleton, creating it
    on first call."""
    global _manager, _logger_configured  # noqa: PLW0603
    if _manager is None:
        _manager = TranslationManager(logger=logger)
        if not _logger_configured and not _manager.available_locales:
            # Try once more from the project root (dev mode)
            import sys
            from pathlib import Path

            # Walk up looking for the locales directory
            cwd = Path.cwd()
            for parent in [cwd, *cwd.parents]:
                candidate = parent / "locales"
                if candidate.is_dir():
                    _manager = TranslationManager(locale_dir=candidate, logger=logger)
                    break

        _logger_configured = True
    return _manager


def tr(key: str, **kwargs) -> str:
    """Look up a translation key in the active locale.

    Convenience function that delegates to the module-level
    :class:`TranslationManager` singleton.

    Args:
        key: Dot-separated translation key, e.g. ``"frontend.table.header_pos"``.
        **kwargs: Optional format parameters for ``str.format()`` interpolation.

    Returns:
        The translated string, or the English fallback, or the key itself.
    """
    return _ensure_manager().tr(key, **kwargs)


def get_manager() -> TranslationManager:
    """Return the module-level :class:`TranslationManager` singleton."""
    return _ensure_manager()


def set_locale(locale_code: str) -> None:
    """Convenience function to switch the active locale.

    Args:
        locale_code: A locale code present in the loaded language packs.

    Raises:
        KeyError: If *locale_code* is not loaded.
    """
    get_manager().current_locale = locale_code


def reload() -> None:
    """Re-scan the locales directory for updated or new language packs."""
    get_manager().reload()
