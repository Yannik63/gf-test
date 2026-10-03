# Desktop Companion V1

Local-first conversational companion core. This first version deliberately has no avatar or GUI.

## Includes
- SQLite conversation history
- Persistent long-term memory
- Relevant-memory retrieval
- Lightweight dynamic state
- Configurable OpenAI-compatible API
- Terminal interface

## Setup

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, add your API key, then run `python main.py`.

The architecture is intentionally small so a desktop UI, voice layer, proactive scheduler and richer memory system can be added without rewriting the core.
