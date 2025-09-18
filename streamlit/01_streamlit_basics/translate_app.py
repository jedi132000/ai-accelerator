import streamlit as st
from solutions import translate, detect_language

# Minimal ISO code -> pretty name mapping (expandable)
# Expanded ISO code mapping (not exhaustive) - keys are ISO codes used by translators
LANG_MAP = {
    "auto": "Auto-detect",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "pt": "Portuguese",
    "it": "Italian",
    "nl": "Dutch",
    "ar": "Arabic",
    "hi": "Hindi",
    "bn": "Bengali",
}

st.set_page_config(page_title="Translate App")

st.title("🌐 Bidirectional Translator")

with st.sidebar:
    st.header("⚙️ Settings")
    # target language list
    source = st.selectbox("Source language:", list(LANG_MAP.keys()), index=0, format_func=lambda k: LANG_MAP[k])
    target = st.selectbox("Target language:", [k for k in LANG_MAP.keys() if k != source], index=1 if source == 'auto' else 0, format_func=lambda k: LANG_MAP[k])
    # swap button
    if st.button("🔁 Swap Languages"):
        source, target = target, source
        # Rerun with swapped values (Streamlit preserves widget state but we'll set session state)
        st.experimental_set_query_params(source=source, target=target)
        st.experimental_rerun()
    direction = st.selectbox("Direction:", ["Auto -> Target", "Target -> Auto"])

col1, col2 = st.columns(2)

with col1:
    st.subheader("✏️ Input")
    input_text = st.text_area("Enter text to translate:")

with col2:
    st.subheader("📝 Output")
    output_box = st.empty()

if st.button("Translate ▶️"):
    if not input_text:
        st.warning("Please enter text to translate.")
    else:
        if direction == "Auto -> Target":
            # Use selected source if not 'auto', otherwise let solutions.detect_language decide
            src_for_call = None if source == 'auto' else source
            translated, detected = translate(input_text, target if target != "auto" else "en", source_lang=src_for_call)
            st.write(f"Detected/assumed source language: {LANG_MAP.get(detected, detected)} ({detected})")
            if translated:
                output_box.text_area("Translated Text", translated, height=200)
            else:
                st.error("Translation failed. Ensure an API key is configured for OpenAI or that fallback translator is available.")
        else:
            # Target -> Auto: treat input as `source` and translate to selected target
            src_for_call = source if source != 'auto' else None
            translated, detected = translate(input_text, target if target != 'auto' else 'en', source_lang=src_for_call)
            st.write(f"Assumed source language: {LANG_MAP.get(source, source)} ({source})")
            if translated:
                output_box.text_area("Translated Text", translated, height=200)
            else:
                st.error("Translation failed. Ensure an API key is configured for OpenAI or that fallback translator is available.")
