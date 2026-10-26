#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
command -v ffmpeg
command -v ffprobe
command -v node
.venv/bin/python doctor.py
