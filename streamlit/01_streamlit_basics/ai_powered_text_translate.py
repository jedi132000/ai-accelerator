import os
import streamlit as st
from openai import OpenAI
import logging
from streamlit.runtime.secrets import StreamlitSecretNotFoundError
from solutions import (
    translate,
    detect_language,
    get_language_candidates,
    translate_long_text,
    batch_translate,
)
import csv
import io
import json
import streamlit.components.v1 as components

# Load OpenAI API key robustly
openai_key = os.environ.get("OPENAI_API_KEY")
if not openai_key:
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY")
    except StreamlitSecretNotFoundError:
        openai_key = None

if not openai_key:
    st.error("OpenAI API key not found. Set `OPENAI_API_KEY` as env var or in `.streamlit/secrets.toml` (local only).")
    st.stop()

# Initialize OpenAI client
client = OpenAI(api_key=openai_key)


# Small ISO mapping (same as translate_app)
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
    "yo": "Yoruba",
}

# Mapping UI codes to standardized ISO 639-1 codes (where applicable)
LANG_CODE_MAP = {
    'auto': 'auto',
    'en': 'en',
    'es': 'es',
    'fr': 'fr',
    'de': 'de',
    'zh-cn': 'zh',
    'zh-tw': 'zh',
    'ja': 'ja',
    'ko': 'ko',
    'ru': 'ru',
    'pt': 'pt',
    'it': 'it',
    'nl': 'nl',
    'ar': 'ar',
    'hi': 'hi',
    
}


def two_stage_translate_and_process(task_prompt_template: str, user_text: str, target_lang: str, source_lang: str | None, do_reverse: bool = False):
    """Two-stage flow:
    1) Detect source language (unless provided)
    2) Translate to target_lang using solutions.translate
    3) Insert translated text into task prompt template and call gpt_process-like flow
    """
    # Stage 1: detection
    detected = source_lang if source_lang and source_lang != 'auto' else (detect_language(user_text) or 'und')

    # Heuristic: short English-looking phrases like "My name is <Name>" can be mis-detected
    # If detected as not-en but text contains common English words and is short, prefer 'en'
    try:
        if detected != 'en' and len(user_text.split()) <= 6:
            english_indicators = ['my', 'name', 'is', 'i', 'am', 'the', 'hello']
            lowered = user_text.lower()
            score = sum(1 for w in english_indicators if w in lowered)
            if score >= 1:
                detected = 'en'
    except Exception:
        pass

    # Stage 2: translation (use solutions.translate which prefers OpenAI then fallback)
    try:
        target_iso = LANG_CODE_MAP.get(target_lang, target_lang)
        src_iso = None if (source_lang == 'auto' or source_lang is None) else LANG_CODE_MAP.get(source_lang, source_lang)
        translated, detected_used = translate(user_text, target_iso, source_lang=src_iso)
    except Exception as e:
        logging.exception("Translation step failed")
        st.error("Translation service error.")
        return None

    if not translated:
        st.error("Translation failed. Ensure API key is configured or fallback translator is available.")
        return None

    # Build system prompt for translation tasks. Include cultural/context guidance.
    # Instruct the model to separate cultural notes using an explicit delimiter so we can parse them reliably
    delimiter = '\n---CULTURAL_NOTES---\n'
    cultural_note = (
        f"When relevant, provide brief cultural context or register notes (formality, idioms, cultural references)."
        f" ALWAYS append the cultural notes separated from the main response using the exact delimiter: {delimiter}"
    )
    system_prompt = (
        task_prompt_template.format(target_lang=target_lang, source_lang=detected_used)
        + "\n\n" + cultural_note
    )

    # Call OpenAI directly for task processing on the translated text
    try:
        with st.spinner("Calling LLM for translated task..."):
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": translated}
                ],
                temperature=0.7,
                max_tokens=400,
            )
    except Exception as e:
        logging.exception("LLM call failed")
        st.error(f"LLM API error: {e}")
        return None

    # extract content
    choices = getattr(response, 'choices', None) or (response.get('choices') if isinstance(response, dict) else None)
    if not choices:
        st.warning("No response from model.")
        return None
    first = choices[0]
    content = None
    if isinstance(first, dict):
        message = first.get('message') or {}
        content = message.get('content') if isinstance(message, dict) else None
        content = content or first.get('text')
    else:
        message = getattr(first, 'message', None)
        if message is not None:
            content = getattr(message, 'content', None)
        content = content or getattr(first, 'text', None)

    # Split assistant response into main result and cultural notes if present.
    assistant_text = (content or '').strip()
    cultural_notes = None
    # Use a delimiter to let the model separate cultural notes if it included them
    delimiter = '\n---CULTURAL_NOTES---\n'
    if delimiter in assistant_text:
        main_part, notes_part = assistant_text.split(delimiter, 1)
        assistant_text = main_part.strip()
        cultural_notes = notes_part.strip()

    # Append to conversation history in session state with optional cultural notes
    entry = {
        'user': user_text,
        'source': detected_used,
        'translated': translated,
        'assistant': assistant_text,
        'cultural_notes': cultural_notes,
    }

    # Optionally perform a reverse translation back to the detected/source language
    if do_reverse:
        try:
            back_target = LANG_CODE_MAP.get(detected_used, detected_used)
            back_src = LANG_CODE_MAP.get(target_lang, target_lang)
            back_translated, _ = translate(translated, back_target, source_lang=back_src)
            entry['reverse_translation'] = back_translated
        except Exception:
            entry['reverse_translation'] = None

    history = st.session_state.get('chat_history', [])
    history.append(entry)
    st.session_state['chat_history'] = history

    return {
        'detected': detected_used,
        'translated': translated,
        'result': (content or '').strip()
    }


st.title("💬 LLM  Text Processor + Translation")

input_text = st.text_area("Enter text to process or translate:")

# Initialize session state for conversation history
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

if 'last_detected' not in st.session_state:
    st.session_state['last_detected'] = None

with st.sidebar:
    st.header("🌍 Translation Settings")
    # show languages with friendly labels, default source to auto
    source = st.selectbox("Source language:", list(LANG_MAP.keys()), index=0, format_func=lambda k: LANG_MAP[k])
    # Make target list exclude 'auto' and be intuitive
    target_choices = [k for k in LANG_MAP.keys() if k != 'auto']
    # if user accidentally picks same code for source/target, still allow but show warning later
    target = st.selectbox("Target language:", target_choices, index=target_choices.index('en') if 'en' in target_choices else 0, format_func=lambda k: LANG_MAP[k])
    st.divider()
    st.write("🧠 Model and task settings")
    model_choice = st.selectbox("Model:", ["gpt-3.5-turbo", "gpt-4"], index=1)
    show_cultural = st.checkbox("📝 Provide cultural context (show inline)", value=False, help="When checked, display cultural notes inline with results; otherwise keep them separate and hide by default.")
    bidirectional = st.checkbox("🔁 Bidirectional translation (also translate back to source)", value=False)

    # If source is auto and we have input, show top language candidates with buttons
    if source == 'auto' and input_text:
        try:
            candidates = get_language_candidates(input_text, top_n=4)
            if candidates:
                st.markdown("**Detection candidates:**")
                for lang_code, prob in candidates:
                    label = f"{LANG_MAP.get(lang_code, lang_code)} ({lang_code}) — {prob:.2f}"
                    if st.button(f"Use {label}"):
                        # set the source in session state and rerun
                        st.session_state['override_source'] = lang_code
                        st.experimental_rerun()
        except Exception:
            pass

task_option = st.selectbox("Task:", ["Summarize", "Analyze Sentiment", "Improve Writing"])

# Document & batch translation controls
st.markdown("### 📄 Document and batch translation")
uploaded_file = st.file_uploader("Upload a text file (.txt) for document translation", type=['txt'])
csv_file = st.file_uploader("Or upload a CSV for batch translation (one text per row, first column)", type=['csv'])
glossary_file = st.file_uploader("Optional: upload glossary as JSON (term->replacement)", type=['json'])
do_pron = st.checkbox("Generate pronunciation guides (may use OpenAI)", value=False)
compute_confidence = st.checkbox("Compute translation confidence for batch items", value=True)

if st.button("Process / Translate ▶️"):
    if not input_text:
        st.warning("Please enter some text.")
    else:
        if task_option == "Summarize":
            template = "You are a translator-assistant. Summarize the following text translated from {source_lang} into {target_lang}. Provide a concise summary."
        elif task_option == "Analyze Sentiment":
            template = "You are a translator-assistant. Translate from {source_lang} to {target_lang} and provide a brief sentiment analysis."
        else:
            template = "You are a translator-assistant. Translate from {source_lang} to {target_lang} and improve the writing to be clearer and more professional."

        out = two_stage_translate_and_process(template, input_text, target if target != 'auto' else 'en', source, do_reverse=bidirectional)
        if out:
            st.subheader("🔎 Detected Language")
            st.write(out['detected'])
            st.subheader("🈸 Translated Text")
            st.write(out['translated'])
            st.subheader("🤖 LLM Result")
            # If the result includes an inline cultural notes separator, split it for display
            res_text = out['result']
            if '\n---CULTURAL_NOTES---\n' in res_text:
                main, notes = res_text.split('\n---CULTURAL_NOTES---\n', 1)
                st.write(main.strip())
                if show_cultural:
                    st.markdown("**Cultural notes:**")
                    st.write(notes.strip())
            else:
                st.write(res_text)

            # update last detected
            st.session_state['last_detected'] = out['detected']

        # Handle document upload translation
        if uploaded_file:
            text = uploaded_file.read().decode('utf-8')
            glossary = None
            if glossary_file:
                try:
                    glossary = json.load(glossary_file)
                except Exception:
                    st.warning('Failed to load glossary JSON; continuing without it.')
            with st.spinner('Translating document...'):
                long_trans, detected = translate_long_text(text, target if target != 'auto' else 'en', source, glossary)
            if long_trans:
                st.subheader('📄 Document translation')
                st.write(long_trans)

        # Handle CSV batch translation
        if csv_file:
            try:
                content = csv_file.read().decode('utf-8')
                reader = csv.reader(io.StringIO(content))
                rows = [r for r in reader if r]
                texts = [r[0] for r in rows]
            except Exception:
                st.error('Failed to read CSV file. Ensure it is UTF-8 and first column contains text.')
                texts = []

            glossary = None
            if glossary_file:
                try:
                    glossary = json.load(glossary_file)
                except Exception:
                    st.warning('Failed to load glossary JSON; continuing without it.')

            if texts:
                with st.spinner('Running batch translation...'):
                    results = batch_translate(texts, target if target != 'auto' else 'en', source, glossary, do_pron)
                st.subheader('🧾 Batch results')
                # present results in a readable format and include confidence/pronunciation
                for r in results:
                    st.markdown(f"**Original:** {r.get('original')}  ")
                    st.markdown(f"- Detected: `{r.get('detected')}`  ")
                    st.markdown(f"- Translated: {r.get('translated')}  ")
                    if compute_confidence:
                        st.markdown(f"- Confidence: **{r.get('confidence', 0):.2%}**  ")
                    if r.get('pronunciation'):
                        st.info(f"Pronunciation: {r.get('pronunciation')}")
                    st.write('---')
                st.download_button('Download batch results (JSON)', data=json.dumps(results, ensure_ascii=False, indent=2), file_name='batch_results.json', mime='application/json')

# Conversation history UI
st.markdown("---")
st.subheader("🕘 Conversation History")
if st.session_state.get('chat_history'):
    # Export / download button
    export_json = json.dumps(st.session_state['chat_history'], ensure_ascii=False, indent=2)
    st.download_button("Export conversation (JSON)", data=export_json, file_name="conversation.json", mime="application/json")

    # Display entries with copy buttons
    for i, msg in enumerate(reversed(st.session_state['chat_history'])):
        st.write(f"**User ({msg['source']}):** {msg['user']}")
        st.write(f"**Translated:** {msg['translated']}")
        st.write(f"**Assistant:** {msg['assistant']}")
        if msg.get('cultural_notes'):
            if show_cultural:
                st.markdown("**Cultural notes:**")
                st.write(msg.get('cultural_notes'))
            else:
                st.info("Cultural notes available (toggle 'Show cultural notes inline' to view).")

        # Small copy buttons
        # prepare javascript for copying assistant text
        copy_id = f"copy-assistant-{i}"
        assistant_text = (msg.get('assistant') or '')
        components.html(f"""
        <div>
          <button onclick="navigator.clipboard.writeText({json.dumps(assistant_text)})">Copy assistant</button>
        </div>
        """, height=40)

        st.write("---")
else:
    st.write("No conversation history yet. Process some text to start.")

if st.sidebar.button("Clear History"):
    st.session_state['chat_history'] = []
    st.session_state['last_detected'] = None
    st.experimental_rerun()
