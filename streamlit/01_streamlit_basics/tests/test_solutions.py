import importlib
import types
import os
import sys

import pytest

# Ensure the package dir (one level up) is on sys.path so 'solutions' can be imported
tests_dir = os.path.dirname(__file__)
pkg_dir = os.path.abspath(os.path.join(tests_dir, '..'))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)


def test_translate_fallback(monkeypatch):
    # Ensure openai client is None to force fallback
    sol = importlib.import_module('solutions')
    monkeypatch.setattr(sol, 'openai_client', None)

    # Mock google translator
    def fake_google(text, target):
        return f"[GOOGLE {target}] {text}"

    monkeypatch.setattr(sol, 'translate_via_google', lambda t, lang, src=None: fake_google(t, lang))

    translated, detected = sol.translate("Hello world", "es")
    assert translated is not None
    assert "[GOOGLE es]" in translated


def test_translate_openai(monkeypatch):
    sol = importlib.import_module('solutions')

    class FakeChoice:
        def __init__(self, content):
            self.message = types.SimpleNamespace(content=content)

    class FakeResponse:
        def __init__(self, text):
            self.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content=text))]

    # Fake openai client that returns a predictable structure
    class FakeClient:
        class chat:
            @staticmethod
            def completions_create(model, messages, temperature, max_tokens):
                return FakeResponse("Hola mundo")

        chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **k: FakeResponse("Hola mundo")))

    monkeypatch.setattr(sol, 'openai_client', FakeClient())
    # Ensure google fallback isn't called
    monkeypatch.setattr(sol, 'translate_via_google', lambda t, lang, src=None: None)

    translated, detected = sol.translate("Hello world", "es")
    assert translated is not None
    assert "Hola mundo" in translated
