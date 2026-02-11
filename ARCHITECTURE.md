# Architecture

## Component Diagram

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────┐
│  chat.db     │────▶│   model.py       │────▶│  replies.json │
│  (SQLite)    │     │  (Python daemon)  │     │  (IPC buffer) │
│  iMessage DB │     │  - DB polling     │     └───────┬───────┘
└──────────────┘     │  - System prompt  │             │
                     │  - LLM inference  │             ▼
                     │  - JSON parsing   │     ┌───────────────┐
                     └──────────────────┘     │  SwiftUI App  │
                                              │  - Reply list  │
                     ┌──────────────────┐     │  - Config UI   │
                     │  config.json     │     │  - Send action │
                     │  - Name          │     └───────┬───────┘
                     │  - Personality   │             │
                     │  - Mood system   │             ▼
                     │  - Phone filter  │     ┌───────────────┐
                     └──────────────────┘     │  AppleScript   │
                                              │  send_imessage │
                                              └───────────────┘
```

## Execution Flow

### Startup

1. `iMessageAIApp.swift` creates a `WindowGroup` containing `ContentView`
2. `ContentView.onAppear`:
   - `loadConfigIfExists()` — reads `~/iMessageAI/config.json` into UI state
   - `startRepliesPolling()` — starts a 1-second `Timer` that reads `~/iMessageAI/replies.json`
   - `startModelIfNeeded()` — resolves a Python interpreter path, launches `model.py` as a `Process` with stdout/stderr pipes

### Message Detection

1. `model.py` enters `while True` loop
2. Each iteration: `subprocess.run(['sqlite3', path, 'SELECT text FROM message ORDER BY date DESC LIMIT 1;'])`
3. Retrieves sender via `SELECT id FROM handle WHERE ROWID=(SELECT handle_id FROM message ORDER BY date DESC LIMIT 1;)`
4. Checks phone number against config filter (Include/Exclude mode)
5. If new message detected (text or sender changed): proceeds to generation

### Reply Generation

1. `model.py` reads `config.json` for personality, name, and mood definitions
2. Constructs a system prompt embedding all mood names and descriptions
3. Calls `ollama.chat(model="llama3.1:8b", format="json", messages=[system, user])`
4. Parses response as JSON. Validates that output keys match mood keys exactly.
5. Retries up to 5 times on key mismatch. Falls back to empty strings after 5 failures.
6. Writes result to `replies.json` with structure: `{<mood>: <reply>, ..., "Reply": "", "sender": ..., "message": ..., "time": ...}`

### User Interaction

1. SwiftUI `Timer` reads `replies.json` every second
2. UI displays mood-keyed replies as selectable cards
3. User can:
   - **Select** a reply (tap card) — highlights it
   - **Edit** a reply — inline text editor, persisted back to `replies.json`
   - **Reply** — writes selected mood to `Reply` key in `replies.json`
   - **Refresh** — writes `"Refresh"` to `Reply` key, triggering regeneration
   - **Ignore** — writes `"Ignore"` to `Reply` key, skipping this message

### Message Send

1. `model.py` detects `Reply` key is no longer empty
2. If `Reply == "Refresh"`: loops back to generation
3. If `Reply == "Ignore"`: logs skip, resumes polling
4. Otherwise: executes `osascript send_imessage.applescript <number> "<text>"`
5. `send_imessage.applescript` tells Messages.app to send the message via iMessage service

## Contracts Between Components

### model.py ↔ config.json

- `model.py` reads: `name`, `personalDescription`, `moods` (dict of name→description), `phoneListMode`, `phoneNumbers`
- Schema not validated; missing keys produce `KeyError`

### model.py ↔ replies.json (write)

- Writes a flat JSON object: each mood name as key with reply text as value
- Special keys: `Reply` (empty string = awaiting selection), `sender`, `message`, `time`

### SwiftUI ↔ replies.json (read/write)

- Reads all top-level keys. Mood keys extracted by exclusion (not `sender`, `message`, `Reply`, `reply`, `time`, `replies`)
- Writes `Reply` key to signal user action
- Writes `reply` key with selected text (lowercase, for back-compat)
- Atomic write via temp file + `FileManager.replaceItemAt`

### SwiftUI ↔ config.json (read/write)

- Reads on launch: `loadConfigIfExists()`
- Writes on every config change: `persistConfig()` — encodes via `JSONEncoder` with `.prettyPrinted` and `.sortedKeys`
- Also writes to `UserDefaults` as a secondary store

### SwiftUI ↔ model.py (process)

- Launched via `Process` with `/bin/zsh -lc "python -u model.py"`
- Working directory set to `~/iMessageAI/`
- Environment: `PYTHONUNBUFFERED=1`, PATH prepended with conda and homebrew paths
- Termination handler: auto-restarts after 1-second delay if `shouldKeepModelRunning` is true
- Stopped on `ContentView.onDisappear`

## Failure Modes

| Failure | Effect | Recovery |
|---|---|---|
| Ollama not running | `model.py` crashes with connection error | Start Ollama server manually |
| `chat.db` not accessible | `sqlite3` returns empty string; polling loop spins | Grant Full Disk Access |
| `model.py` not found at expected path | Swift logs error, no replies generated | Ensure `~/iMessageAI/model.py` exists |
| Python not found | `Process` launch fails | Install Python via conda or homebrew |
| LLM returns malformed JSON | 5 retries, then fallback with empty reply strings | User sees empty reply cards |
| `replies.json` write race | Possible corrupted read on either side | Restart app |
| Messages.app not running | AppleScript fails silently | Open Messages.app |
| Quote in message text | `os.system` shell command breaks | No recovery; message not sent |

## Observability

- **Python stdout:** bracketed status tags (`[INIT]`, `[WAITING]`, `[RUN]`, `[GENERATING]`, `[FINISH]`, `[WRITING]`) with inline metadata (sender number, generation time)
- **Swift console:** Python stdout/stderr piped through `Pipe.fileHandleForReading.readabilityHandler`
- **Debug guards:** `#if DEBUG` on file I/O error prints in Swift
- **No metrics, no structured logging, no crash reporting**
