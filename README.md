# ⚡ PulseHire

AI-powered job search for data science, ML engineering, and AI specialist roles at early-to-mid stage healthcare startups. Filters for LLMs, agentic AI, and clinical NLP positions. Built with Streamlit + Claude AI.

![Python](https://img.shields.io/badge/Python-3.10+-purple) ![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-red) ![Claude](https://img.shields.io/badge/Claude-Opus-blueviolet)

---

## Features

- Searches Google Jobs, Greenhouse, and Lever boards across 6 query variants targeting healthcare AI startups
- Claude AI classifies every listing — filters out non-AI roles and big-corp results automatically
- **PhD tab** — instantly separate jobs that require/prefer a PhD from those that don't
- Filter chips: REMOTE · SEED · SERIES A · NLP/LLM · IMAGING AI · $200K+ · NO PhD
- Synthwave UI with animated orbs, Orbitron font, and purple glow aesthetic

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/pulsehire.git
cd pulsehire
```

### 2. Add API keys

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
SERPER_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

| Key | Where to get it | Cost |
|-----|----------------|------|
| `SERPER_API_KEY` | [serper.dev](https://serper.dev) | Free (2,500 searches/month) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Pay per use |

### 3. Run

```bash
bash run.sh
```

Opens at **http://localhost:8501**

---

## Deploy to Streamlit Cloud (free)

1. Push this repo to GitHub (do **not** commit `.env`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → pick your repo → `app.py`
3. In the app dashboard: **⋮ → Settings → Secrets**, paste:

```toml
SERPER_API_KEY = "your_key_here"
ANTHROPIC_API_KEY = "your_key_here"
```

---

## Project Structure

```
pulsehire/
├── app.py               # Streamlit UI
├── backend/
│   ├── scraper.py       # Job search (Serper API + ATS boards)
│   └── classifier.py    # Claude AI filtering & skill extraction
├── .env.example         # API key template
├── requirements.txt
└── run.sh               # One-command startup
```

---

## How it works

1. **Scraper** fires 6 search queries against Google Jobs (via Serper) and searches Greenhouse/Lever ATS boards directly
2. **Classifier** batches raw results through Claude, which filters for AI relevance + healthcare domain + startup stage, then extracts skills, PhD requirements, and company stage
3. **UI** displays filtered jobs with tab/chip filtering and direct links to apply
