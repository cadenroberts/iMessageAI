# iMessageAI

macOS application that monitors iMessage for incoming texts, generates mood-categorized reply candidates using a local LLM, and sends the selected reply through Messages.app.

## What It Does

- Polls the macOS iMessage SQLite database (`~/Library/Messages/chat.db`) for new incoming messages
- Constructs a personality-aware system prompt from user-defined moods in `config.json`
- Calls a local Llama 3.1 8B model via Ollama to generate one reply per mood
- Displays reply candidates in a native SwiftUI interface with edit, refresh, and ignore controls
- Sends the selected reply through Messages.app via AppleScript automation
- Filters conversations by phone number (include or exclude list)

## Architecture

```
           ┌───────────────────────────────┐
           │┌──────────────┐  ┌───────────┐│
           ├┼▶ config.json ├─┬┼▶ SwiftUI  ├┘
           │└──────────────┘ │└───────────┘
┌─────────┐│┌───────────────┐│┌───────────┐┌────────────────┐
│ chat.db ├┴┼▶ replies.json ├┴┼▶ model.py ├┼▶ send_imessage │
└─────────┘ └───────────────┘ └───────────┘└────────────────┘

```

**Staged execution:**

1. SwiftUI app launches and starts `model.py` as a child process
2. `model.py` polls `chat.db` via `sqlite3` CLI for the most recent message
3. When a new message arrives from an allowed phone number, `model.py` reads `config.json` and constructs a personality prompt with all mood definitions
4. Ollama generates a JSON response with one reply per mood (retries up to 5 times on key mismatch)
5. `model.py` writes the reply map to `replies.json`
6. SwiftUI app polls `replies.json` every second, displays candidates
7. User selects, edits, refreshes, or ignores. Selection writes back to `replies.json`
8. `model.py` reads the selection and invokes `send_imessage.applescript` via `osascript`

## Design Tradeoffs

- **File-based IPC** over sockets: zero-dependency cross-language communication. Both Python and Swift have native JSON support. File watching is simpler than socket lifecycle management. Tradeoff: no locking, potential race conditions.
- **Local LLM** over cloud API: no message data leaves the device, zero network latency variance, no API cost. Tradeoff: requires Ollama installed with sufficient hardware.
- **Personality/mood system in JSON** over hardcoded prompts: behavior tuning separated from code. Users modify `config.json` instead of editing prompt strings. Tradeoff: no schema validation.
- **AppleScript for send** over direct API: only supported programmatic interface to Messages.app on macOS. Tradeoff: fragile string interpolation, no error reporting.
- **`sqlite3` CLI** over Python sqlite3 module: avoids file locking conflicts with the Messages process that holds the database open. Tradeoff: subprocess overhead per query.

## Evaluation

Correctness is defined as:

1. `model.py` parses `config.json` and produces a valid system prompt containing all mood names
2. Ollama returns a JSON object whose keys exactly match the mood names in `config.json`
3. `replies.json` contains all mood keys plus `sender`, `message`, `time`, and `Reply` fields
4. The SwiftUI app displays all mood-keyed replies and writes the user selection back correctly

See [EVAL.md](EVAL.md) for measurable criteria and commands.

## Demo

Prerequisites: macOS, Ollama installed with `llama3.1:8b` pulled, Python 3 with `ollama` package, Xcode.

```bash
# Install dependencies
brew install ollama
ollama pull llama3.1:8b
pip install ollama

# Clone and build
git clone git@github.com:cadenroberts/iMessageAI.git
cd iMessageAI
open iMessageAI.xcodeproj
# Build and run from Xcode (Cmd+R)
```

The app starts `model.py` automatically. Configure your name, personality description, and moods in the UI. Incoming iMessages trigger reply generation.

See [DEMO.md](DEMO.md) for detailed walkthrough and expected outputs.

## Repository Layout

```
iMessageAI/
├── model.py                          Python daemon: DB polling + LLM inference + IPC
├── send_imessage.applescript         AppleScript: sends message via Messages.app
├── config.json                       Personality and mood configuration template
├── iMessageAI/
│   ├── iMessageAIApp.swift           SwiftUI @main entry point
│   └── ContentView.swift             Full UI + process orchestration (~1140 lines)
├── iMessageAI.xcodeproj/             Xcode project configuration
├── iMessageAI.app                    Pre-built macOS application bundle
├── iMessageAI/Assets.xcassets/       App icons and asset catalog
├── scripts/
│   └── demo.sh                       Reproducible verification script
├── .github/workflows/
│   └── ci.yml                        CI workflow
├── ARCHITECTURE.md                   Component and flow documentation
├── DESIGN_DECISIONS.md               ADR-style decision records
├── EVAL.md                           Correctness criteria and commands
├── DEMO.md                           Demo walkthrough
├── REPO_AUDIT.md                     Technical audit
└── PATCHSET_SUMMARY.md               Change log for this overhaul
```

## Limitations

- Requires macOS with Full Disk Access granted to the terminal or Xcode (for `chat.db` read)
- Requires Ollama running locally with sufficient RAM for Llama 3.1 8B (~8 GB)
- No file locking on `replies.json` — concurrent read/write from Python and Swift can race
- AppleScript send uses string interpolation without escaping — messages containing quotes will fail
- `model.py` polling loop has no sleep interval — high CPU usage when idle
- No phone number normalization — format must match exactly between config and `chat.db`
- No tests
