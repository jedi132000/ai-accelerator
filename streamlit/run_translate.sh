#!/usr/bin/env bash
# Lightweight launcher for the translation Streamlit app
set -euo pipefail

# Activate virtualenv in repo root .venv
if [ -f .venv/bin/activate ]; then
  # shellcheck source=/dev/null
  . .venv/bin/activate
elif [ -f ../.venv/bin/activate ]; then
  . ../.venv/bin/activate
else
  echo "No .venv found in project root. Activate your Python environment manually."
fi

echo "Starting Streamlit app: 01_streamlit_basics/ai_powered_text_translate.py"
streamlit run 01_streamlit_basics/ai_powered_text_translate.py
