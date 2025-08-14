# Kai Project – DESIGN\_NOTES.md

## Vision & Emotional Intent

Kai isn’t just another app. It should feel like a safe, emotionally warm space—less like tech, more like a cozy garden you visit when the world feels overwhelming.

* Tone: Uplifting, non-corporate, and emotionally intelligent.
* Visual Influence: Township, Animal Crossing, Pinterest.
* Moodboard Keywords: Light, soulful, gentle motion, handwritten vibes, sunlit edges, responsive expression.

## Kai's Visual Identity

* Primary Visual Symbol: Animated Samoyed (Kai) with subtle mood-shifting animations based on emotional tone
* Style Keywords: Soft shadows, rounded corners, breathable white space, cute without being infantilizing
* Kai vs. Eden:

  * Kai = emotional resonance, warmth, sunlight
  * Eden = reflective, grounded, tree-of-life archetype

## UI/UX Design Themes

* "Feel > Feature" — prioritize emotional response over tech flashiness
* Microinteractions matter: typing dots, breathing animations, light haptics (eventually)
* Avoid sterile or transactional layouts—this is not a chatbot interface

## Notes for Future Designers

You’re not designing a UI—you’re designing a feeling.

* Avoid corporate UX tropes or overly masculine interfaces
* Do study emotionally intelligent design: meditation apps, affirmations, visual journaling
* Every color, motion, sound should be selected like you're giving life to something new. You're designing with the users in mind, not as an afterthought

## File Structure Alignment

The following reflects the current project hierarchy relevant to frontend/UX design:

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

## Suggested Experiments

* Animated petting/sleep cycle for Samoyed icon
* Sunlight shifting UI gradient
* Mood-sensitive avatar blinking/eye direction
* Unlockable emotional “stamps” or journaling frames

---

This design doc will evolve. Let future artists dream even further.
