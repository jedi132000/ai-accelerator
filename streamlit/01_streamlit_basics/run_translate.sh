#!/usr/bin/env bash
# Simple launcher for the translate app
set -euo pipefail

# Activate venv if present
if [ -f ../.venv/bin/activate ]; then
  # shellcheck source=/dev/null
  . ../.venv/bin/activate
fi

# Accept optional filename argument, default to translate_app.py
APP=${1:-translate_app.py}

echo "Launching Streamlit app: $APP"
streamlit run "$APP"
