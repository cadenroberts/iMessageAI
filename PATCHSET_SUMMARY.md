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

## Commits Made

### Clarifying (insertions only)

1. `0fb5d59` — Clarifying: add repository audit
2. `61a27dd` — Clarifying: add reproducible demo script
3. `6212a81` — Clarifying: add continuous integration workflow

### Cleaning (deletions only)

4. `ca031a3` — Cleaning: remove tracked noise, binary artifacts, and user state files

### Refactoring (mixed)

5. `137645f` — Refactoring: rebuild documentation and align structure

## Files Added

- `REPO_AUDIT.md` — Technical audit of repository
- `ARCHITECTURE.md` — Component diagram, execution flow, contracts, failure modes
- `DESIGN_DECISIONS.md` — 8 ADR-style decision records
- `EVAL.md` — Correctness definitions, verification commands, pass/fail criteria
- `DEMO.md` — Prerequisites, setup, expected behavior, troubleshooting
- `PATCHSET_SUMMARY.md` — This file
- `scripts/demo.sh` — Non-interactive verification script
- `.github/workflows/ci.yml` — CI workflow
- `.gitignore` — Ignore rules for build artifacts and runtime files
- `.env.example` — Environment variable template
- `sync.sh` — Commit and push helper

## Files Deleted

- `.DS_Store` — macOS Finder metadata (noise)
- `iMessageAI/.DS_Store` — nested Finder metadata
- `iMessageAI.mp4` — LFS-tracked demo video (binary)
- `imessageai.pdf` — PDF document (binary)
- `problemstatement.txt` — content absorbed into documentation
- `replies.json` — runtime artifact, not source
- `.gitattributes` — LFS filter configuration (no longer needed)
- `iMessageAI.xcodeproj/project.xcworkspace/xcuserdata/...` — Xcode user state
- `iMessageAI.xcodeproj/xcuserdata/...` — Xcode user scheme state

## Verification

```
=== iMessageAI Verification ===
Repo: /Users/croberts/resume/repos/iMessageAI

[CHECK] Required files...
  OK: model.py
  OK: send_imessage.applescript
  OK: config.json
  OK: iMessageAI/ContentView.swift
  OK: iMessageAI/iMessageAIApp.swift

[CHECK] config.json structure...
  Name: Caden Roberts
  Moods: ['Happy', 'Professional', 'Sad']
  Filter: Exclude
  CONFIG_OK

[CHECK] model.py syntax...
  SYNTAX_OK

[CHECK] Swift source syntax...
  OK: ContentView.swift
  OK: iMessageAIApp.swift
  SWIFT_SYNTAX_OK

[CHECK] AppleScript syntax...
  APPLESCRIPT_OK

[CHECK] Documentation...
  OK: README.md (121 lines)
  OK: ARCHITECTURE.md (131 lines)
  OK: DESIGN_DECISIONS.md (102 lines)
  OK: EVAL.md (107 lines)
  OK: DEMO.md (103 lines)
  OK: REPO_AUDIT.md (150 lines)
  OK: PATCHSET_SUMMARY.md (15 lines)

=== All checks passed ===
SMOKE_OK
```

## Remaining Improvements

### P0

- Fix shell injection in `model.py` AppleScript invocation
- Add `requirements.txt` with pinned `ollama` version
- Add sleep interval to `model.py` polling loop

### P1

- File locking on `replies.json`
- Temperature parameter for Ollama calls
- Phone number normalization

### P2

- Unit tests for `gen_replies`
- Structured logging in `model.py`
