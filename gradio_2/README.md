# Gradio DialoGPT Chat

A simple chatbot using Hugging Face's DialoGPT-small model and Gradio UI. Features conversation history, proper attention masking, and a clean messages-style interface.

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
# Create venv (if not exists)
python -m venv .venv

# Activate it
source .venv/bin/activate  # Unix/macOS
# or
.venv\Scripts\activate     # Windows

# Install requirements
pip install -r requirements.txt
```

## Running the App

Standard run (production mode):
```bash
python app.py
```

Development mode with auto-reload (needs Gradio CLI):
```bash
gradio app.py
```

The app will be available at http://127.0.0.1:7860 by default.

## Features

- Uses smaller DialoGPT-small model for faster downloads/startup
- Proper attention masking for better response quality
- Messages-style chat interface (OpenAI format)
- Persistent conversation history (until page reload)
- Temperature=0.7 for some response variety

## Development Notes

- The model weights (~500MB) download on first run
- Use `gr.Chatbot(type="messages")` format for modern chat UI
- Full attention masking implemented to avoid warnings
- Chat history stored in state includes model context