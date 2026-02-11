# Patchset Summary

## Baseline Snapshot

- **Branch:** main
- **HEAD commit:** 8e4b426badec78bb43d715f6692464cded1f3d67
- **Tracked files:** 31
- **Primary entry points:**
  - `model.py` — Python daemon that polls macOS `chat.db` for new iMessages, generates mood-based replies via Ollama (Llama 3.1 8B), writes candidates to `replies.json`
  - `iMessageAI/iMessageAIApp.swift` — SwiftUI app entry (`@main`), launches `ContentView`
  - `iMessageAI/ContentView.swift` — Full SwiftUI interface: config editing, mood management, reply selection, Python process lifecycle, AppleScript send
  - `send_imessage.applescript` — AppleScript that sends a message through Messages.app
- **How it runs:** User launches the SwiftUI app (Xcode build or pre-built `iMessageAI.app`). The app starts `model.py` as a child process. `model.py` polls `~/Library/Messages/chat.db` via `sqlite3` CLI, calls Ollama for reply generation, writes `replies.json`. The SwiftUI app polls `replies.json` at 1-second intervals, displays mood-categorized reply candidates, and sends the selected reply via `send_imessage.applescript` through `osascript`.
- **Build:** Xcode project (`iMessageAI.xcodeproj`) targeting macOS. Python engine requires `ollama` pip package and a running Ollama server with `llama3.1:8b` model pulled.
- **Tests:** None.
