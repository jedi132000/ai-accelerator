# Translation Chatbot (compact)

Quick start

1. Create and activate a Python venv (optional if you already have `.venv`):

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Set your OpenAI API key either as an environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

or place it in `01_streamlit_basics/.streamlit/secrets.toml` (local only) with:

```toml
[general]
OPENAI_API_KEY = "sk-..."
```

3. Run the app from repository root:

```bash
./run_translate.sh
```

Features
- Auto-detect source language
- Translate + run LLM tasks (summarize, sentiment, improve writing)
- Conversation history stored during session
- Toggle to show/hide cultural notes produced by the model

Rotate an exposed API key (recommended)
- Go to https://platform.openai.com/account/api-keys
- Revoke the compromised key and create a new one
- Update your environment variable or `secrets.toml` with the new key
# Streamlit Basics - Teaching Materials

This folder contains progressive examples to teach Streamlit fundamentals to experienced tech professionals.

## Teaching Sequence

1. **01_hello_world.py** - Basic app structure and script execution model
2. **02_session_state.py** - Understanding persistence across reruns
3. **03_chat_interface.py** - Building chat-style interfaces
4. **04_sidebar_widgets.py** - User controls and configuration
5. **05_complete_example.py** - Putting it all together

## Key Concepts to Emphasize

- **Script Execution Model**: Top-to-bottom execution on every interaction
- **Session State**: The persistence layer that survives reruns
- **Widget State**: How user inputs trigger reruns
- **Chat Components**: Modern interface patterns for AI applications

## Running the Examples

```bash
pip install streamlit
streamlit run 01_hello_world.py
```

Each example builds upon the previous one, introducing new concepts incrementally.

## OpenAI API Key / Secrets

The examples that call OpenAI require an API key. You can provide it in one of two ways:

- Add it to `.streamlit/secrets.toml` in this folder:

```
OPENAI_API_KEY = "your-real-key-here"
```

- Or set the environment variable before running Streamlit:

```bash
export OPENAI_API_KEY="your-real-key-here"
streamlit run 01_streamlit_basics/ai_powered_text.py
```

Never commit real API keys to the repository. Use CI or deployment secrets for production.