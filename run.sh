#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# ── .env check ──────────────────────────────────────────────
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "  ┌──────────────────────────────────────────────────────────┐"
  echo "  │  .env created from template.                             │"
  echo "  │  Open .env and add your API keys, then run again.        │"
  echo "  └──────────────────────────────────────────────────────────┘"
  echo ""
  exit 1
fi

# ── Virtual env ─────────────────────────────────────────────
if [ ! -d venv ]; then
  echo "→ Creating virtual environment…"
  python3 -m venv venv
fi

source venv/bin/activate

# ── Dependencies ────────────────────────────────────────────
echo "→ Installing dependencies…"
pip install -r requirements.txt -q

# ── Launch ──────────────────────────────────────────────────
echo ""
echo "  ┌─────────────────────────────────────────────────┐"
echo "  │  PulseHire  ⚡  http://localhost:8501            │"
echo "  └─────────────────────────────────────────────────┘"
echo ""
streamlit run app.py --server.port 8501 --server.headless true
