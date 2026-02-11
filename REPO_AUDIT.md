# Repository Audit

## 1. Purpose

Event-driven iMessage reply assistant for macOS. Monitors the local iMessage SQLite database for incoming messages, generates multiple mood-categorized reply candidates using a local LLM (Llama 3.1 8B via Ollama), and presents them in a native SwiftUI interface. The user selects a reply (or edits it), and the app sends it through Messages.app via AppleScript.

## 2. Entry Points

| Entry Point | Language | Role |
|---|---|---|
| `iMessageAI/iMessageAIApp.swift` | Swift | `@main` app entry. Launches `ContentView` in a `WindowGroup`. |
| `iMessageAI/ContentView.swift` | Swift | Full UI + process orchestration. Manages config, polls `replies.json`, starts/stops `model.py`, sends replies via AppleScript. |
| `model.py` | Python | Daemon process. Polls `chat.db`, constructs personality-aware prompts from `config.json`, calls Ollama, writes structured JSON to `replies.json`. |
| `send_imessage.applescript` | AppleScript | Sends a message to a phone number via Messages.app. Invoked by `osascript` from the Python engine. |

## 3. Dependency Surface

### Runtime

| Dependency | Type | Source |
|---|---|---|
| Ollama server | External service | Must be running locally with `llama3.1:8b` pulled |
| `ollama` Python package | pip | Python client for Ollama API |
| `sqlite3` CLI | System binary | Used by `model.py` via `subprocess.run` to query `chat.db` |
| macOS Messages.app | System app | Required for AppleScript send |
| SwiftUI / AppKit | System framework | macOS UI framework |
| UserNotifications | System framework | Local notification delivery |

### Dev

| Dependency | Type |
|---|---|
| Xcode | IDE + Swift compiler |
| Python 3.x | Interpreter (miniconda3 or system) |

## 4. Configuration Surface

| Source | Format | Contents |
|---|---|---|
| `config.json` | JSON | User name, personal description, mood definitions (name + description), phone number filter mode (Include/Exclude), phone number list |
| `~/iMessageAI/config.json` | JSON | Runtime copy written by SwiftUI app to a fixed path; read by `model.py` |
| `~/iMessageAI/replies.json` | JSON | IPC buffer. Python writes reply candidates; Swift reads and displays. Swift writes user selection back; Python reads to determine send action. |
| `.env.example` | Env template | Empty; no environment variables currently required beyond system PATH |

The SwiftUI app resolves config/replies paths to `/Users/<user>/iMessageAI/` (hardcoded base). The Python engine reads `config.json` from its working directory (set by the Swift process launcher to the same path).

## 5. Data Flow

```
chat.db (SQLite, ~/Library/Messages/chat.db)
    │
    ▼ [sqlite3 CLI subprocess, polled in tight loop]
model.py
    │
    ├── reads config.json (personality, moods, phone filter)
    │
    ├── constructs system prompt with mood definitions
    │
    ├── calls ollama.chat(model="llama3.1:8b", format="json")
    │     └── retries up to 5 times if mood keys mismatch
    │
    ├── writes replies.json (mood→reply map + sender + message + time)
    │
    └── polls replies.json for user selection (Reply key)
            │
            ├── "Refresh" → regenerate
            ├── "Ignore"  → skip
            └── <mood>    → osascript send_imessage.applescript <number> "<text>"

SwiftUI ContentView
    │
    ├── onAppear: loadConfigIfExists(), startRepliesPolling(), startModelIfNeeded()
    │
    ├── Timer(1s): polls ~/iMessageAI/replies.json
    │     └── updates generatedReplies, lastSender, lastMessage, lastReply
    │
    ├── user taps Reply → writes selected mood to Reply key in replies.json
    │
    ├── user taps Refresh → writes "Refresh" to Reply key
    │
    ├── user taps Ignore → writes "Ignore" to Reply key
    │
    └── config edits → persistConfig() writes config.json + UserDefaults
```

## 6. Determinism Risks

| Risk | Severity | Detail |
|---|---|---|
| LLM output nondeterminism | High | Ollama inference produces different replies each run. Temperature is not set (uses model default). |
| Tight polling loop | Medium | `model.py` polls `chat.db` in a `while True` with no sleep. CPU-intensive. Uses `count % 1000000` as a print throttle, not a rate limiter. |
| Race condition on `replies.json` | Medium | Both Python and Swift read/write the same file. Swift pauses polling for 0.3s during writes, but no file locking. |
| Phone number parsing | Low | No normalization of phone numbers. `+14085551234` vs `(408) 555-1234` would not match. |
| `osascript` shell injection | Medium | `os.system('osascript send_imessage.applescript {} "{}"'.format(...))` does not sanitize message text. Quotes in messages break the command. |

## 7. Observability

- `model.py` prints bracketed status messages: `[INIT]`, `[WAITING]`, `[RUN]`, `[GENERATING]`, `[FINISH]`, `[WRITING]`
- SwiftUI app captures stdout/stderr from the Python process via `Pipe` and logs to console
- `#if DEBUG` guards on file I/O error prints in Swift
- No structured logging, no log levels, no metrics, no crash reporting

## 8. Test State

- **Zero tests.** No unit tests, no integration tests, no UI tests.
- No test targets in the Xcode project.
- No Python test files.

## 9. Reproducibility

| Factor | State |
|---|---|
| Python dependencies pinned | No. No `requirements.txt` or lockfile. |
| Swift dependencies pinned | No external Swift packages. System frameworks only. |
| Ollama model version | Specified as `llama3.1:8b` but model weights are not version-pinned. |
| Build steps documented | Partial. README lists `brew install ollama` and `ollama pull`. |
| Deterministic output | No. LLM inference is inherently stochastic. |

## 10. Security Surface

| Surface | Risk | Detail |
|---|---|---|
| `chat.db` access | High | Reads the user's full iMessage history. Requires Full Disk Access on macOS. |
| Shell injection | Medium | `os.system` with string formatting for AppleScript invocation. |
| Local-only LLM | Low | No message data leaves the device (Ollama runs locally). |
| No authentication | Low | App has no auth; access is physical-machine-scoped. |
| `config.json` on disk | Low | Personal description and phone numbers stored in plaintext. |

## 11. Improvement List

### P0 (Critical)

1. Fix shell injection in `model.py` AppleScript invocation — use `subprocess.run` with argument list instead of `os.system` with string interpolation.
2. Add `requirements.txt` with pinned `ollama` version.
3. Add sleep interval to `model.py` polling loop to prevent CPU saturation.

### P1 (Important)

4. Implement file locking or atomic swap protocol for `replies.json` IPC to prevent read/write races.
5. Add `--temperature` parameter to Ollama call for more consistent output.
6. Normalize phone numbers before comparison.
7. Remove `.DS_Store` files from tracking.
8. Remove Xcode user state files from tracking (`.xcuserstate`, `xcschememanagement.plist`).

### P2 (Nice to have)

9. Add unit tests for `gen_replies` JSON parsing logic.
10. Add SwiftUI preview tests or snapshot tests.
11. Add structured logging with levels in `model.py`.
12. Pin Ollama model version hash for reproducible inference.
