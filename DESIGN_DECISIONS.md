# Design Decisions

## ADR-001: File-Based IPC Over Sockets

**Context:** The system has two processes in different languages (Python and Swift) that need to exchange structured data (reply candidates and user selections). Options: Unix sockets, named pipes, HTTP server, shared file.

**Decision:** Use a shared JSON file (`replies.json`) as the IPC mechanism. Python writes reply candidates; Swift reads them. Swift writes user selections back; Python reads them.

**Consequences:**
- Zero additional dependencies. Both languages have native JSON serialization.
- No socket lifecycle management (bind, listen, accept, reconnect).
- No protocol versioning needed — the JSON schema is the protocol.
- Race condition possible: both sides read and write the same file without locking. Mitigated in Swift by pausing the poll timer during writes (0.3s window). Not mitigated in Python.
- Polling required on both sides (1s in Swift, tight loop in Python).

## ADR-002: Local LLM Over Cloud API

**Context:** Reply generation requires an LLM. Options: OpenAI/Anthropic cloud API, local model via Ollama.

**Decision:** Use Ollama with Llama 3.1 8B running locally.

**Consequences:**
- No message content leaves the device. Privacy is absolute for a tool reading the user's full iMessage history.
- No API key management, no billing, no rate limits.
- Requires ~8 GB RAM for the model. Not viable on low-memory machines.
- Inference speed depends on local hardware (CPU/GPU). Generation times observed at ~6.5 seconds on test hardware.
- Model output is not reproducible across runs (no temperature pinning).

## ADR-003: Personality and Mood System in Config File

**Context:** The LLM system prompt needs to encode the user's communication style and generate replies in different emotional tones. Options: hardcode prompts in Python, store in a database, store in a JSON config file editable via UI.

**Decision:** Store personality (`name`, `personalDescription`) and mood definitions (`moods` dict) in `config.json`. The SwiftUI app provides a GUI editor. `model.py` reads the file on each generation cycle.

**Consequences:**
- Users customize tone without editing code.
- Moods are dynamically sized (1-5, enforced by UI).
- The LLM prompt length scales with the number of moods and description verbosity.
- No schema validation on `config.json`. Malformed JSON crashes `model.py`.
- Dual storage: SwiftUI writes both `config.json` and `UserDefaults`. `model.py` only reads the file.

## ADR-004: AppleScript for Message Sending

**Context:** The selected reply needs to be sent through iMessage. Options: AppleScript automation of Messages.app, private macOS frameworks, third-party libraries.

**Decision:** Use `send_imessage.applescript` invoked via `osascript` from `model.py`.

**Consequences:**
- AppleScript is the only documented, supported interface for programmatically sending iMessages on macOS.
- No additional dependencies or entitlements beyond what Messages.app requires.
- Invocation via `os.system` with string interpolation is fragile — messages containing double quotes, backslashes, or shell metacharacters will break the command or produce unexpected behavior.
- No error reporting: `osascript` failures are silent from `model.py`'s perspective.
- Requires Messages.app to be running and signed into an iMessage account.

## ADR-005: sqlite3 CLI Over Python sqlite3 Module

**Context:** `model.py` needs to read the most recent message from `~/Library/Messages/chat.db`. Options: Python `sqlite3` module, `sqlite3` CLI via subprocess.

**Decision:** Use `subprocess.run(['sqlite3', path, query])` to execute SQL queries.

**Consequences:**
- Avoids file locking conflicts. The Messages process holds `chat.db` open with WAL mode. The Python `sqlite3` module may fail to acquire a read lock or see stale data. The CLI tool handles this more gracefully.
- Subprocess overhead per query (~10ms) is negligible relative to LLM inference time (~6s).
- Requires `sqlite3` to be on the PATH. Addressed by the Swift process launcher prepending homebrew and conda bin paths to the environment.
- SQL injection is not a risk because no user input is interpolated into queries — they are hardcoded `SELECT` statements.

## ADR-006: SwiftUI Process Management for Python Engine

**Context:** The Python engine (`model.py`) needs to run alongside the SwiftUI app. Options: user launches Python manually, app launches it as a child process, launchd daemon.

**Decision:** `ContentView` launches `model.py` as a `Process` on `onAppear` and terminates it on `onDisappear`. The process auto-restarts on unexpected termination (1-second delay).

**Consequences:**
- Single launch point — user opens the app and everything starts.
- Auto-restart provides resilience against transient Python crashes.
- Process lifecycle is tied to the SwiftUI view lifecycle, not the app lifecycle. Navigating away from `ContentView` stops the engine.
- Python path resolution is heuristic: tries miniconda3, system python, homebrew python in order. Fails silently if none found.
- stdout/stderr are captured via `Pipe` and logged to Xcode console, providing visibility into the Python engine's state.

## ADR-007: Retry Logic for LLM Output Validation

**Context:** The LLM is instructed to return a JSON object with specific mood keys, but it may return incorrect keys, extra keys, or malformed output.

**Decision:** `gen_replies` validates that the sorted keys of the LLM output exactly match the sorted mood keys from `config.json`. On mismatch, retries up to 5 times. After 5 failures, returns a fallback dict with empty strings for each mood.

**Consequences:**
- Strict key matching ensures the UI always receives the expected mood categories.
- 5 retries at ~6s each means a worst case of ~30s for a single generation cycle.
- The fallback produces empty reply cards — the user sees the moods but with no text, which is a clear signal that generation failed.
- No partial acceptance: if the LLM returns 2 of 3 moods correctly, the entire response is rejected.

## ADR-008: Phone Number Filtering with Include/Exclude Modes

**Context:** The user may want the AI to respond only to specific contacts, or to exclude certain contacts.

**Decision:** `config.json` contains `phoneListMode` (Include or Exclude) and `phoneNumbers` (array of strings). `model.py` checks incoming message sender against this filter before generating replies.

**Consequences:**
- Include mode: only listed numbers trigger generation. Useful for testing with specific contacts.
- Exclude mode: all numbers except listed ones trigger generation. Useful for blocking bots or group chats.
- Phone numbers are compared as exact strings. No normalization is applied. `+14085551234` and `(408) 555-1234` are treated as different numbers.
- Empty phone list with Exclude mode means all numbers are processed. Empty list with Include mode means no numbers are processed.
