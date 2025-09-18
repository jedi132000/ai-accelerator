# AI Personality Assistant (Streamlit)

A Streamlit app for interactive chat with multiple AI personalities powered by OpenAI models. Switch personas, preview response styles, export conversations, and select your preferred model—all in one UI.

## Features

- **Personality Selection:** Choose from Professional, Creative, Technical, Friendly, or Custom personas.
- **Dynamic System Prompts:** Each personality uses a unique system prompt for tailored responses.
- **Visual Indicators:** Current personality is always shown in the chat header.
- **Personality Descriptions & Previews:** Sidebar shows what each persona is good for and example responses.
- **Mid-Conversation Switching:** Change personality at any time; system messages indicate switches.
- **Export Options:** Download chat history as TXT, JSON, or CSV with metadata (timestamp, message count, session info).
- **OpenAI Model Selection:** Pick from multiple models (e.g., GPT-3.5, GPT-4) via a pulldown menu.
- **Secrets Management:** API keys stored securely in `.streamlit/secrets.toml` (ignored by git).

## Setup

1. **Clone the repo:**
   ```sh
   git clone <repo-url>
   cd streamlit2
   ```
2. **Install dependencies:**
   ```sh
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Add your OpenAI API key:**
   Create `.streamlit/secrets.toml`:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
4. **Run the app:**
   ```sh
   streamlit run app.py
   # or
   .venv/bin/python -m streamlit run app.py
   ```

## Usage

- Select a personality and model in the sidebar.
- Type your message and interact with the AI.
- Switch personalities mid-conversation as needed.
- Download your chat history in your preferred format.

## Security
- Your OpenAI API key is never tracked by git (see `.gitignore`).

## License
MIT
