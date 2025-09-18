import sys
import os
import importlib
import types

import pytest


def make_dummy_response(text: str):
    # mimic the structure used in the app extraction logic
    return {'choices': [{'message': {'content': text}}]}


@pytest.fixture(autouse=True)
def insert_app_path(monkeypatch):
    # ensure the app package path is importable (parent directory: 01_streamlit_basics)
    here = os.path.dirname(__file__)
    app_dir = os.path.abspath(os.path.join(here, '..'))
    sys.path.insert(0, app_dir)
    # ensure OpenAI client in module init won't fail
    monkeypatch.setenv('OPENAI_API_KEY', 'testkey')
    yield


def test_history_append_and_cultural_notes(monkeypatch):
    # Import the module freshly
    mod = importlib.import_module('ai_powered_text_translate')
    importlib.reload(mod)

    # Monkeypatch solutions.translate and detect_language
    def fake_detect(text):
        return 'es'

    def fake_translate(text, target, source_lang=None):
        return ("Texto traducido", 'es')

    monkeypatch.setattr('ai_powered_text_translate.detect_language', fake_detect)
    monkeypatch.setattr('ai_powered_text_translate.translate', fake_translate)

    # Monkeypatch the OpenAI client call to return a response with cultural notes delimiter
    dummy_text = "Processed summary text.\n---CULTURAL_NOTES---\nNote: informal register preferred in Spanish."

    class DummyClient:
        class chat:
            class completions:
                @staticmethod
                def create(*args, **kwargs):
                    return make_dummy_response(dummy_text)

    # Inject dummy client into module
    monkeypatch.setattr(mod, 'client', DummyClient())

    # Ensure session state keys exist
    if 'chat_history' in mod.st.session_state:
        mod.st.session_state['chat_history'] = []

    # Call the processing function
    out = mod.two_stage_translate_and_process("Task: translate from {source_lang} to {target_lang}.", "Hola mundo", 'en', 'auto')

    assert out is not None
    assert out['detected'] == 'es'
    assert 'translated' in out
    assert out['result'].startswith('Processed summary text.')

    # Verify history updated
    hist = mod.st.session_state.get('chat_history', [])
    assert len(hist) == 1
    entry = hist[0]
    assert entry['user'] == 'Hola mundo'
    assert entry['source'] == 'es'
    assert entry['translated'] == 'Texto traducido'
    assert entry['assistant'].startswith('Processed summary text.')
    assert 'cultural_notes' in entry and entry['cultural_notes'] is not None
    assert 'informal register' in entry['cultural_notes']
