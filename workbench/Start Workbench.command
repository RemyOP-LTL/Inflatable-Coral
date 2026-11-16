#!/bin/bash
# Double-click to run the workbench from this folder (no install). Close the window to stop it.
cd "$(dirname "$0")" || exit 1
python3 workbench.py
