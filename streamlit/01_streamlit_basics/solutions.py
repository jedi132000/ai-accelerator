import os
from langdetect import detect, LangDetectException
from langdetect import detect_langs
from deep_translator import GoogleTranslator
from typing import Tuple, Optional, List, Dict
import difflib
import re
import io
from typing import List, Dict

# Try to import OpenAI client if available and API key is set
openai_key = os.environ.get("OPENAI_API_KEY")
openai_client = None
if openai_key:
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=openai_key)
    except Exception:
        openai_client = None


def detect_language(text: str) -> Optional[str]:
    """Detect the language code for the given text using langdetect."""
    # For very short inputs, prefer OpenAI-based detection if client available
    try:
        words = len(text.split())
    except Exception:
        words = 0

    if openai_client and words <= 6:
        # Try OpenAI-based short text detector
        try:
            code = detect_via_openai(text)
            if code:
                return code
        except Exception:
            pass

    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return None


def detect_via_openai(text: str) -> Optional[str]:
    """Use OpenAI to detect language for short text. Returns a 2-letter ISO code or None.
    This function relies on openai_client being initialized.
    """
    if not openai_client:
        return None
    try:
        prompt = (
            "Return only the 2-letter ISO 639-1 language code for the following text."
            " If you cannot determine, return 'und'.\n\nText:\n" + text
        )
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4,
        )
        choices = getattr(response, "choices", None) or response.get("choices")
        if not choices:
            return None
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message", {})
            code = message.get("content") if isinstance(message, dict) else None
        else:
            message = getattr(first, "message", None)
            code = getattr(message, "content", None)
        if not code:
            return None
        return code.strip().lower()
    except Exception:
        return None


def get_language_candidates(text: str, top_n: int = 3):
    """Return a list of (lang_code, probability) tuples for the input text using langdetect.detect_langs.
    Falls back to [] on error."""
    try:
        preds = detect_langs(text)
        # detect_langs returns objects like LangProb('en', 0.99)
        out = [(p.lang, p.prob) for p in preds[:top_n]]
        return out
    except Exception:
        return []


def translate_via_openai(text: str, target_lang: str, source_lang: Optional[str] = None) -> Optional[str]:
    """Translate text using OpenAI Chat Completions (if available).
    Returns translated text or None if OpenAI client isn't configured.
    """
    if not openai_client:
        return None
    try:
        # If source language is provided, instruct the model about it to improve fidelity
        src_hint = f" The source language is {source_lang}." if source_lang and source_lang != 'auto' else ""
        system = f"You are a helpful translator. Translate the user's text into {target_lang} and preserve meaning.{src_hint} Only return the translated text without extra commentary."
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text}
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        # Extract content
        choices = getattr(response, "choices", None) or response.get("choices")
        if not choices:
            return None
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message", {})
            return message.get("content") if isinstance(message, dict) else None
        else:
            message = getattr(first, "message", None)
            return getattr(message, "content", None)
    except Exception:
        return None


def translate_via_google(text: str, target_lang: str, source_lang: Optional[str] = None) -> Optional[str]:
    """Translate text using deep-translator's GoogleTranslator as a fallback."""
    try:
        # deep-translator accepts source='auto' or an ISO code like 'en'
        src = 'auto' if not source_lang or source_lang == 'auto' else source_lang
        translated = GoogleTranslator(source=src, target=target_lang).translate(text)
        return translated
    except Exception:
        return None


def translate(text: str, target_lang: str, source_lang: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Translate text to `target_lang`.

    source_lang: optional ISO code or 'auto' to auto-detect. Returns (translated_text_or_None, detected_source_language).
    """
    detected = source_lang if source_lang and source_lang != 'auto' else (detect_language(text) or "und")

    # Try OpenAI first
    if openai_client:
        out = translate_via_openai(text, target_lang, source_lang)
        if out:
            return out.strip(), detected

    # Fallback to GoogleTranslator
    out = translate_via_google(text, target_lang, source_lang)
    if out:
        return out.strip(), detected

    return None, detected


if __name__ == "__main__":
    # quick CLI test
    sample = "Hello, how are you?"
    print("Detected:", detect_language(sample))
    print("Translate to es:", translate(sample, "es"))


def apply_glossary(text: str, glossary: Dict[str, str]) -> str:
    """Apply glossary replacements to text. Glossary is a dict of term -> replacement.
    Matches are case-insensitive and replace whole words.
    """
    if not glossary:
        return text

    def replace(match):
        word = match.group(0)
        repl = glossary.get(word.lower()) or glossary.get(word)
        return repl if repl is not None else word

    # Build a regex that matches any glossary term as a whole word
    terms = sorted([re.escape(t) for t in glossary.keys()], key=len, reverse=True)
    if not terms:
        return text
    pattern = r"\b(" + "|".join(terms) + r")\b"
    return re.sub(pattern, replace, text, flags=re.IGNORECASE)


def chunk_text(text: str, max_chars: int = 3000) -> List[str]:
    """Naive chunking by paragraphs and then by character count."""
    paragraphs = text.split('\n\n')
    chunks: List[str] = []
    current = ''
    for p in paragraphs:
        if not current:
            current = p
        elif len(current) + 2 + len(p) <= max_chars:
            current += '\n\n' + p
        else:
            chunks.append(current)
            current = p
    if current:
        chunks.append(current)
    # fallback: ensure no chunk > max_chars (split by char)
    final: List[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            final.append(c)
        else:
            for i in range(0, len(c), max_chars):
                final.append(c[i:i+max_chars])
    return final


def translate_long_text(text: str, target_lang: str, source_lang: Optional[str] = None, glossary: Optional[Dict[str, str]] = None) -> Tuple[Optional[str], str]:
    """Translate long text by chunking and reassembling. Returns (translated_text, detected_source).
    Applies glossary replacements before translating chunks.
    """
    detected = source_lang if source_lang and source_lang != 'auto' else (detect_language(text) or 'und')
    chunks = chunk_text(text)
    translated_chunks: List[str] = []
    for c in chunks:
        c_pre = apply_glossary(c, glossary) if glossary else c
        out, detected_used = translate(c_pre, target_lang, source_lang)
        if out is None:
            return None, detected_used
        translated_chunks.append(out)
    return '\n\n'.join(translated_chunks), detected


def translation_confidence(original: str, translated: str, back_translated: Optional[str] = None) -> float:
    """Return a confidence score in [0,1] for the translation.
    If back_translated is provided, compute similarity between original and back_translated.
    Otherwise, use ratio between original and translated (less reliable).
    """
    try:
        if back_translated:
            ref = original
            cmp = back_translated
        else:
            ref = original
            cmp = translated
        seq = difflib.SequenceMatcher(None, ref, cmp)
        return float(seq.ratio())
    except Exception:
        return 0.0


def generate_pronunciation(text: str, target_lang: str) -> Optional[str]:
    """Generate a pronunciation guide using OpenAI if available; otherwise return None."""
    if not openai_client:
        return None
    try:
        prompt = (
            f"Provide a short pronunciation guide (simple phonetic or IPA) for the following text in {target_lang}. "
            "Return only the pronunciation on one line.\n\nText:\n" + text
        )
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=60,
        )
        choices = getattr(response, "choices", None) or response.get("choices")
        if not choices:
            return None
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message", {})
            code = message.get("content") if isinstance(message, dict) else None
        else:
            message = getattr(first, "message", None)
            code = getattr(message, "content", None)
        return code.strip() if code else None
    except Exception:
        return None


def batch_translate(texts: List[str], target_lang: str, source_lang: Optional[str] = None, glossary: Optional[Dict[str, str]] = None, do_pronunciation: bool = False) -> List[Dict]:
    """Translate a list of texts and return list of result dicts with translation, confidence, pronunciation, reverse, etc."""
    results: List[Dict] = []
    for t in texts:
        t_pre = apply_glossary(t, glossary) if glossary else t
        translated, detected = translate(t_pre, target_lang, source_lang)
        back = None
        conf = 0.0
        pron = None
        if translated:
            # attempt back translation
            try:
                back, _ = translate(translated, source_lang if source_lang and source_lang != 'auto' else detected, target_lang)
            except Exception:
                back = None
            conf = translation_confidence(t, translated, back)
            if do_pronunciation:
                pron = generate_pronunciation(translated, target_lang)

        results.append({
            'original': t,
            'detected': detected,
            'translated': translated,
            'back_translation': back,
            'confidence': conf,
            'pronunciation': pron,
        })
    return results
