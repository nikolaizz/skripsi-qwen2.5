import os
import re
from typing import Optional, Tuple

try:
    from argostranslate import translate as argos_translate
except ImportError as exc:  # pragma: no cover - dependency hint
    argos_translate = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


SRC_LANG_CODE = os.getenv("ARGOS_SRC_LANG", "en")
TGT_LANG_CODE = os.getenv("ARGOS_TGT_LANG", "id")

_translation_cache = None
_warned_unavailable = False
_REPLACEMENT_PATTERNS = [
    (re.compile(r"\borang (cacat visual|cacat penglihatan)\b", re.IGNORECASE), "tunanetra"),
    (re.compile(r"\bspaced\b", re.IGNORECASE), "berjarak"),
    (re.compile(r"\bwell-cahaya\b", re.IGNORECASE), "terang"),
    (re.compile(r"\bdaerah\b", re.IGNORECASE), "area"),
    (re.compile(r"\bsebagai\b", re.IGNORECASE), "karena"),
    (re.compile(r"\bbaik\s*[- ]?\s*ditandai\b", re.IGNORECASE), "terlihat dengan jelas"),
    (re.compile(r"\bpengaturan\b", re.IGNORECASE), "latar"),
    (re.compile(r"^Gambar\b", re.IGNORECASE), "Di depan"),
    (re.compile(r"\bmenunjukkan\b", re.IGNORECASE), "terlihat"),
    (re.compile(r"\bbahaya langsung\b", re.IGNORECASE), "bahaya secara langsung"),
    (re.compile(r"\buneven\b", re.IGNORECASE), "tidak rata"),
    (re.compile(r"\badegan\b", re.IGNORECASE), "situasi"),
    (re.compile(r"\bbaik-menyala\b", re.IGNORECASE), "terang"),
    (re.compile(r"\blantai dipoles\b", re.IGNORECASE), "lantai mengkilap"),
    (re.compile(r"\bpaved\b", re.IGNORECASE), "pavling"),
    (re.compile(r"\bkondisi miskin\b", re.IGNORECASE), "kondisi buruk"),
    (re.compile(r"\blangkah-langkah\b", re.IGNORECASE), "tangga"),
    (re.compile(r"\bitem\b", re.IGNORECASE), "benda"),
    (re.compile(r"\bjelas ditandai\b", re.IGNORECASE), "terlihat dengan jelas"),
    (re.compile(r"\blantainya miring\b", re.IGNORECASE), "lantainya keramik"),
]

def _get_translation() -> Optional[object]:
    """
    Lazy-load dan cache pasangan bahasa Argos Translate.
    Return objek Translation atau None jika tidak tersedia.
    """
    global _translation_cache

    if _translation_cache is not None:
        return _translation_cache

    if argos_translate is None:
        return None

    try:
        installed_languages = argos_translate.get_installed_languages()
    except Exception:
        return None

    from_lang = next((lang for lang in installed_languages if lang.code == SRC_LANG_CODE), None)
    to_lang = next((lang for lang in installed_languages if lang.code == TGT_LANG_CODE), None)
    if not from_lang or not to_lang:
        return None

    try:
        translation = from_lang.get_translation(to_lang)
    except Exception:
        return None

    _translation_cache = translation
    return translation


def translate_text_to_indonesian(text: str, fallback_original: bool = True) -> Tuple[str, bool]:
    """
    Terjemahkan teks bahasa Inggris ke bahasa Indonesia.

    Return tuple (hasil_terjemahan, status_berhasil).
    Jika status False dan fallback_original True, teks asli dikembalikan.
    """
    global _warned_unavailable

    if not text:
        return text, False

    translation = _get_translation()
    if translation is None:
        if not _warned_unavailable:
            if _IMPORT_ERROR:
                print("[WARN] argostranslate belum terpasang. Install dengan `pip install argostranslate`.")
            else:
                print(
                    "[WARN] Pair bahasa Argos Translate (en -> id) belum tersedia.\n"
                    "       Instal paketnya dengan `argos-translate --from-lang en --to-lang id download` "
                    "dan `install`, kemudian jalankan ulang."
                )
            _warned_unavailable = True
        if fallback_original:
            return text, False
        raise RuntimeError("Argos Translate pair en->id tidak tersedia.")

    try:
        translated = translation.translate(text).strip()
    except Exception as exc:
        print(f"[ERROR] Gagal menerjemahkan dengan Argos Translate: {exc}")
        if fallback_original:
            return text, False
        raise

    if not translated:
        return text if fallback_original else "", False

    fixed_text = _apply_post_translation_fixes(translated)
    return fixed_text, True


def _apply_post_translation_fixes(text: str) -> str:
    """
    Post-processing sederhana untuk memperhalus istilah terjemahan.
    """
    def _match_case(src: str, repl: str) -> str:
        if src.isupper():
            return repl.upper()
        if src.istitle():
            return repl.capitalize()
        return repl

    result = text
    for pattern, replacement in _REPLACEMENT_PATTERNS:
        result = pattern.sub(lambda m: _match_case(m.group(0), replacement), result)
    return result


def persist_translated_text(txt_path: Optional[str], translated_text: str) -> bool:
    """
    Simpan hasil terjemahan ke file output asli (outputs/*.txt).
    Return True jika berhasil menulis ulang.
    """
    if not txt_path:
        return False

    if not translated_text:
        return False

    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(translated_text)
    except Exception as exc:
        print(f"[WARN] Gagal menulis ulang file output: {exc}")
        return False

    print(f"[PIPELINE] File output diperbarui dengan teks terjemahan: {txt_path}")
    return True

