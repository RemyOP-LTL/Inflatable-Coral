#!/bin/bash
# Double-click this file to start the frame tool in your browser (http://127.0.0.1:8790/).
# First time only: it makes a private folder (.venv) and installs the libraries it needs. This takes a minute or two.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "First-time setup: installing the libraries the tool needs (about a minute)..."
  python3 -m venv .venv || { echo "Could not set up Python. Please tell Claude what this window says."; read -p "Press Return to close"; exit 1; }
  .venv/bin/python -m pip install --quiet --upgrade pip
fi
.venv/bin/python -m pip install --quiet -r requirements.txt || { echo "Install failed. Please tell Claude what this window says."; read -p "Press Return to close"; exit 1; }
.venv/bin/python frame_app.py
read -p "The tool has stopped. Press Return to close."
