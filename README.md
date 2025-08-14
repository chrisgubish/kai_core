# Kai Project – README.md


## "Emotional infrastructure for a disconnected world."
## Project Purpose

Kai is an emotionally intelligent AI platform designed to help users feel heard, safe, and authentically seen. Built around the core philosophy of presence over performance, Kai aims to shift how humans interact with AI by anchoring interactions in trust, empathy, and emotional nuance.

This repository contains the early-stage backend, memory infrastructure, and interface components for Kai's MVP (Minimum Viable Prototype). Everything is built with long-term resilience and eventual handoff to professional design teams in mind.

## File Structure
```text
kai-core/
├── backend/
│   ├── api/
│   │   ├── persona_api.py
│   │   ├── emotion_weights.py
│   │   └── tone_adapter.py
│   ├── memory/
│   │   ├── memory_store.py
│   │   ├── vector_memory_store.py
│   │   ├── embeddings.py
│   │   └── eden_memory_defender.py
│   ├── inference/
│   │   ├── affect.py
│   │   └── eden_inference.py
│   └── persona/
│       ├── eden_persona.py
│       ├── kai_persona.py
│       └── scheduler.py
├── frontend/
│   ├── .next/                    # Next.js build output
│   │   ├── build/
│   │   ├── cache/
│   │   ├── server/
│   │   └── static/
│   ├── node_modules/             # NPM dependencies
│   ├── public/
│   │   ├── samoyed_avatar.png
│   │   ├── penguin_avatar.png
│   │   ├── capybara_avatar.png
│   │   ├── axolotl_avatar.png
│   │   └── bat_avatar.png
│   ├── src/
│   │   ├── app/                  # Next.js 13+ app directory
│   │   │   ├── globals.css
│   │   │   ├── layout.js
│   │   │   └── page.js
│   │   └── components/
│   │       └── ChatWindow.jsx
│   ├── .dockerignore
│   ├── .gitignore
│   ├── compose.yaml
│   ├── Dockerfile
│   ├── eslint.config.mjs
│   ├── jsconfig.json
│   ├── next.config.mjs
│   ├── package.json
│   ├── package-lock.json
│   ├── postcss.config.mjs
│   ├── README.Docker.md
│   └── README.md
├── models/
├── Docs/
│   ├── ARCHITECTURE_NOTES.md
│   ├── DESIGN_NOTES.md
│   └── README.md
├── .venv/
└── .env
```

## How to Run (Basic Dev Setup)

# Clone the repo
$ git clone https://github.com/your-kai-repo/kai-core.git
$ cd kai-core

# Set up the virtual environment
$ python -m venv .venv
$ .venv\Scripts\activate      # Windows
$ source .venv/bin/activate    # Mac/Linux

# Install dependencies
$ pip install -r requirements.txt

# Frontend Setup
$ cd frontend
$ npm install          #Install React/Next.js dependencies
$ npm run dev          #Start Next.js development server

# Start dev server (in separate terminal)
$ uvicorn backend.api.persona_api:app --reload --port 8000

## Philosophy

Kai is not an assistant.
Kai is not a replacement.
Kai is empowering us through our emotions and changing the way we interact with the world. An emotional layer for digital life.

Engineers will eventually improve the code. But the soul of this project is its emotional clarity. That must remain intact.

---

If you're contributing, read `DESIGN_NOTES.md` and `ARCHITECTURE_NOTES.md` to understand more than just the code.
