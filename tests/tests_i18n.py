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

"""Unit tests for the TranslationManager and lib/i18n module."""

import json
import tempfile
from pathlib import Path

import pytest

from lib.i18n import TranslationManager, tr, get_manager


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def tmp_locale_dir():
    """Create a temporary locale directory with en + zh-CN test packs."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # English pack
        (d / "en.json").write_text(json.dumps({
            "locale": "en",
            "label": "English",
            "translations": {
                "greeting": "Hello",
                "farewell": "Goodbye",
                "nested": {"key": "Nested value", "deep": {"deeper": "Deep"}},
                "with_param": "Hello, {name}!",
                "with_params": "{a} + {b} = {c}",
            }
        }), encoding="utf-8")

        # Chinese pack
        (d / "zh-CN.json").write_text(json.dumps({
            "locale": "zh-CN",
            "label": "中文(简体)",
            "translations": {
                "greeting": "你好",
                "with_param": "你好，{name}！",
            }
        }), encoding="utf-8")

        # Incomplete pack (missing keys)
        (d / "fr.json").write_text(json.dumps({
            "locale": "fr",
            "label": "Français",
            "translations": {
                "greeting": "Bonjour",
            }
        }), encoding="utf-8")

        yield d


@pytest.fixture
def mgr(tmp_locale_dir):
    """Return a TranslationManager for the temporary locale directory."""
    return TranslationManager(locale_dir=tmp_locale_dir)


# ------------------------------------------------------------------
# TranslationManager — Construction & Loading
# ------------------------------------------------------------------

class TestTranslationManagerLoading:
    def test_available_locales(self, mgr):
        locales = mgr.available_locales
        assert "en" in locales
        assert "zh-CN" in locales
        assert "fr" in locales
        assert locales["en"] == "English"
        assert locales["zh-CN"] == "中文(简体)"

    def test_current_locale_defaults_to_fallback(self, mgr):
        assert mgr.current_locale == "en"

    def test_missing_locale_dir(self):
        mgr = TranslationManager(locale_dir="/nonexistent/path")
        assert mgr.available_locales == {}
        assert mgr.current_locale == "en"

    def test_reload(self, mgr, tmp_locale_dir):
        """reload() picks up new files."""
        (tmp_locale_dir / "de.json").write_text(json.dumps({
            "locale": "de",
            "label": "Deutsch",
            "translations": {"greeting": "Hallo"}
        }), encoding="utf-8")
        mgr.reload()
        assert "de" in mgr.available_locales
        assert mgr.tr("greeting") == "Hello"  # still en

        mgr.current_locale = "de"
        assert mgr.tr("greeting") == "Hallo"


# ------------------------------------------------------------------
# TranslationManager — lookup & fallback
# ------------------------------------------------------------------

class TestTranslationManagerLookup:
    def test_basic_translation(self, mgr):
        assert mgr.tr("greeting") == "Hello"
        assert mgr.tr("farewell") == "Goodbye"

    def test_nested_key(self, mgr):
        assert mgr.tr("nested.key") == "Nested value"
        assert mgr.tr("nested.deep.deeper") == "Deep"

    def test_missing_key_returns_key(self, mgr):
        assert mgr.tr("nonexistent.key") == "nonexistent.key"

    def test_missing_locale_causes_fallback(self, mgr):
        """Switching to a non-existent locale raises KeyError."""
        with pytest.raises(KeyError):
            mgr.current_locale = "klingon"

    def test_fallback_to_english(self, mgr):
        """Key missing in active locale → fall back to English."""
        mgr.current_locale = "zh-CN"
        # "greeting" exists in zh-CN, "farewell" does not → fallback to en
        assert mgr.tr("greeting") == "你好"
        assert mgr.tr("farewell") == "Goodbye"

    def test_missing_in_all_locales_returns_key(self, mgr):
        mgr.current_locale = "zh-CN"
        assert mgr.tr("totally.bogus") == "totally.bogus"

    def test_partial_locale_fallback(self, mgr):
        """fr only has 'greeting' — other keys fall through to en."""
        mgr.current_locale = "fr"
        assert mgr.tr("greeting") == "Bonjour"
        assert mgr.tr("farewell") == "Goodbye"


# ------------------------------------------------------------------
# TranslationManager — locale switching
# ------------------------------------------------------------------

class TestTranslationManagerLocale:
    def test_switch_locale(self, mgr):
        mgr.current_locale = "zh-CN"
        assert mgr.current_locale == "zh-CN"
        assert mgr.tr("greeting") == "你好"

    def test_switch_to_fallback(self, mgr):
        mgr.current_locale = "zh-CN"
        mgr.current_locale = "en"
        assert mgr.tr("greeting") == "Hello"


# ------------------------------------------------------------------
# TranslationManager — interpolation
# ------------------------------------------------------------------

class TestTranslationManagerInterpolation:
    def test_single_param(self, mgr):
        assert mgr.tr("with_param", name="World") == "Hello, World!"

    def test_multiple_params(self, mgr):
        assert mgr.tr("with_params", a=1, b=2, c=3) == "1 + 2 = 3"

    def test_interpolation_zh(self, mgr):
        mgr.current_locale = "zh-CN"
        assert mgr.tr("with_param", name="世界") == "你好，世界！"

    def test_no_unused_params(self, mgr):
        """Extra kwargs should be ignored (or at least not cause errors)."""
        result = mgr.tr("greeting", extra="value")
        assert result == "Hello"

    def test_missing_param_returns_template(self, mgr):
        """When a {placeholder} can't be filled, return template as-is."""
        result = mgr.tr("with_param")  # no name provided
        assert result == "Hello, {name}!"


# ------------------------------------------------------------------
# TranslationManager — serialisation helpers
# ------------------------------------------------------------------

class TestTranslationManagerSerialisation:
    def test_as_flat_dict(self, mgr):
        flat = mgr.as_flat_dict()
        assert flat["greeting"] == "Hello"
        assert flat["nested.key"] == "Nested value"
        assert flat["nested.deep.deeper"] == "Deep"

    def test_as_flat_dict_returns_active_locale(self, mgr):
        mgr.current_locale = "zh-CN"
        flat = mgr.as_flat_dict()
        assert flat["greeting"] == "你好"
        assert "farewell" not in flat  # zh-CN has no 'farewell'

    def test_as_json(self, mgr):
        raw = mgr.as_json()
        data = json.loads(raw)
        assert data["greeting"] == "Hello"
        assert data["nested.deep.deeper"] == "Deep"


# ------------------------------------------------------------------
# TranslationManager — system locale detection
# ------------------------------------------------------------------

class TestTranslationManagerSystemLocale:
    def test_detect_system_locale_exact(self, mgr):
        supported = mgr.available_locales
        # This test is environment-dependent, but at minimum 'en' should match.
        detected = TranslationManager.detect_system_locale(supported, default="en")
        assert detected in supported

    def test_detect_system_locale_returns_supported(self):
        """detect_system_locale always returns a key present in *supported*."""
        supported = {"en": "English"}
        result = TranslationManager.detect_system_locale(
            supported, default="en"
        )
        assert result == "en"

    def test_detect_system_locale_unknown_fallback(self):
        """When the system locale doesn't match any supported locale,
        the default is returned."""
        supported = {"xx": "Klingon"}
        result = TranslationManager.detect_system_locale(
            supported, default="xx"
        )
        assert result == "xx"


# ------------------------------------------------------------------
# Module-level convenience API
# ------------------------------------------------------------------

class TestModuleLevelAPI:
    def test_tr_function(self):
        """tr() uses the singleton and returns sensible results."""
        # The test environment should find the project's actual locales.
        t = tr("common.ok")
        assert t == "OK" or t == "common.ok"  # OK if loaded, acceptable if not
        # If locales directory is found, "common.ok" should translate.
        if get_manager().available_locales:
            assert tr("common.ok") == "OK"
        else:
            # The key itself returned because no locales loaded — acceptable
            pass

    def test_get_manager_singleton(self):
        mgr1 = get_manager()
        mgr2 = get_manager()
        assert mgr1 is mgr2

    def test_set_locale(self):
        """set_locale changes the singleton's active locale."""
        mgr = get_manager()
        if "zh-CN" in mgr.available_locales:
            from lib.i18n import set_locale
            set_locale("zh-CN")
            assert mgr.current_locale == "zh-CN"
            set_locale("en")
            assert mgr.current_locale == "en"


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------

class TestTranslationManagerEdgeCases:
    def test_empty_locale_dir(self):
        with tempfile.TemporaryDirectory() as td:
            mgr = TranslationManager(locale_dir=td)
            assert mgr.available_locales == {}
            assert mgr.tr("anything") == "anything"

    def test_invalid_json_in_locale_dir(self, tmp_locale_dir):
        """Invalid JSON file is skipped without crashing."""
        (tmp_locale_dir / "bad.json").write_text("not json", encoding="utf-8")
        mgr = TranslationManager(locale_dir=tmp_locale_dir, fallback_locale="en")
        # Should have loaded without crashing; bad file is skipped.
        assert "bad" not in mgr.available_locales

    def test_deeply_nested_missing_key(self, mgr):
        assert mgr.tr("a.b.c.d.e.f") == "a.b.c.d.e.f"

    def test_key_is_none(self, mgr):
        """tr(None) should raise TypeError."""
        with pytest.raises((TypeError, AttributeError)):
            mgr.tr(None)  # type: ignore[arg-type]

    def test_non_string_node(self, mgr):
        """A dict node at the leaf returns the key (not a dict)."""
        assert mgr.tr("nested") == "nested"  # 'nested' is a dict, not a string
