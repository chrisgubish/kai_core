# Kai Project – ARCHITECTURE\_NOTES.md

## Overview

This document outlines the structural and architectural decisions made during the early phases of Kai Technologies' development. It’s intended to guide future contributors, especially backend and systems engineers, in understanding the design rationale and evolution path.

## Core Principles

* Maintainable modularity
* Scalable backend-first development
* No reliance on third-party APIs for core logic (long-term resilience)
* MVP stability and emotional integrity come first

## Current Directory Structure

```
kai-core/
├── backend/
│   ├── api/                  # interaction endpoints (LLM routing, user data, etc.)
│   ├── memory/               # memory modules (e.g., eden_memory.py)
│   ├── processing/           # tone adapters, embeddings, summaries
│   ├── persona_api.py        # thin controller layer for persona selection
│   ├── emotion_weights.py    # custom tuning matrix (placeholder logic)
│   └── tone_adapter.py       # emotional tone interpreter
├── frontend/
│   ├── assets/               # future image/audio assets
│   ├── themes/               # visual palettes, Kai Skies, light/dark
│   ├── chatapp.js
│   ├── styleapp.css
│   └── frontend.html
├── tests/                    # basic self-tests and scripts
├── models/                   # LLM weights or references (eventual vector DB plug-in)
├── llama.cpp/               # optional integration with local model runner
├── eden_env/                # environment/infra files (venv-like logic)
├── .git/                    # version control
├── .venv/                   # Python virtual environment
├── venv/                    # redundant - will be pruned
├── .env                     # secrets placeholder (NEVER push real creds)
├── dreamlog.py              # Eden’s nightly log generator
├── eden_emotion_profile.yaml
├── eden_inference0.py       # legacy inference trial (to be deprecated)
├── eden_monologue.py        # solo Eden reflection tool
├── eden_persona.py          # deprecated, now kai_persona.py takes over
├── kai_persona.py           # current persona selector logic
├── scheduler.py             # for Kai’s eventual background tasks (dreams, reminders)
├── DESIGN_NOTES.md
├── ARCHITECTURE_NOTES.md
├── README.md
├── requirements.txt         # for backend environment setup
```

## Future Goals

* Containerization (Docker) for portable deployment
* Replace in-memory store with persistent vector DB (like Chroma or Weaviate)
* Internal admin CLI for rapid tuning
* Biometric or emotion-based adaptive threading (Kai Mirror support)

## Dependencies

* Python >= 3.10
* FastAPI (or Flask, modular fallback)
* LLAMA.cpp (for local LLM experimentation)
* Frontend: Vanilla JS + CSS for now; Tailwind or React optional in later builds

## Memory Notes

* `eden_memory.py` now lives in `backend/memory/` and is aliased as `memory.py`
* Uses in-process dict store for rapid prototyping
* Can be swapped with vector index with no upstream changes

## Security Cautions

* Avoid reliance on external APIs for sentiment/emotion unless self-hosted
* All local modules must pass audit once pre-MVP testing is complete

---

Let this doc evolve as Kai grows. Keep things transparent and resilient.
