# Kai Project – ARCHITECTURE\_NOTES.md

## Overview

This document outlines the structural and architectural decisions made during the early phases of Kai Technologies' development. It’s intended to guide future contributors, especially backend and systems engineers, in understanding the design rationale and evolution path.

## Core Principles

* Maintainable modularity
* Scalable backend-first development
* No reliance on third-party APIs for core logic (long-term resilience)
* MVP stability and emotional integrity come first

## Current Directory Structure

...
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
...

## Future Goals

* Containerization (Docker) for portable deployment
* Replace in-memory store with persistent vector DB (like Chroma or Weaviate)
* Internal admin CLI for rapid tuning
* Biometric or emotion-based adaptive threading (Kai Mirror support)

## Dependencies

**Backend:**
* Python >= 3.10
* FastAPI with uvicorn
* transformers, torch (for LLM inference)
* chromadb (for vector memory)

**Frontend:**
* Node.js >= 18.0
* Next.js 14+ with React 18+
* Tailwind CSS (utility classes only)
* React Mardkwon for message rendering

**Future Mobile:**
* React Native for iOS and Android apps

## Avatar System
* **5 Companion Designs:** Samoyed, Penguin, Capybara, Axolotl, Bat
* **Independent Selection:** Users choose visual design separa from personality (Kai/Eden)
* **Circular Avar Display:** 180px with soft shadows and gentle animations
* **Fallback System:** Defaults to penguin if avatar fails to load

**Future Implementations**
* **Customizable** customizable avatars using preset designs that users can unlock to modify and design their avatars. Gives users the ability to give their personal flair to the avatars to make it a true mirror/expression of themselves

## Memory Notes

* `eden_memory.py` now lives in `backend/memory/` and is aliased as `memory.py`
* Uses in-process dict store for rapid prototyping
* Can be swapped with vector index with no upstream changes

## Security Cautions

* Avoid reliance on external APIs for sentiment/emotion unless self-hosted
* All local modules must pass audit once pre-MVP testing is complete

---

Let this doc evolve as Kai grows. Keep things transparent and resilient.
