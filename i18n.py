"""
Internationalization module.
Provides t(key, **kwargs) with fallback to English when a key is missing
in the active language.
"""

import json
from pathlib import Path

_TRANSLATIONS_DIR = Path(__file__).parent / "translations"
_SUPPORTED = {"en", "es"}
_DEFAULT = "en"
_active = _DEFAULT
_cache: dict[str, dict] = {}


def _load(lang: str) -> dict:
    if lang not in _cache:
        path = _TRANSLATIONS_DIR / f"{lang}.json"
        _cache[lang] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _cache[lang]


def setup_language(lang: str) -> None:
    """Set the active language. Call once at app startup."""
    global _active
    _active = lang if lang in _SUPPORTED else _DEFAULT


def t(key: str, **kwargs) -> str:
    """Return the translation for key in the active language, falling back to English."""
    val = _load(_active).get(key) or _load(_DEFAULT).get(key) or key
    return val.format(**kwargs) if kwargs else val
