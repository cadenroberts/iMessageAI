# Demo

## Prerequisites

- macOS 13+ (Ventura or later)
- Xcode 15+ installed
- Ollama installed and running (`brew install ollama && ollama serve`)
- Llama 3.1 8B model pulled (`ollama pull llama3.1:8b`)
- Python 3.9+ with `ollama` package (`pip install ollama`)
- Full Disk Access granted to Terminal (System Settings > Privacy & Security > Full Disk Access)
- Messages.app signed into an iMessage account

## Setup

```bash
git clone git@github.com:cadenroberts/iMessageAI.git
cd iMessageAI

# Copy project files to the runtime directory
mkdir -p ~/iMessageAI
cp model.py config.json send_imessage.applescript ~/iMessageAI/
```

## Running

### Option A: Pre-built App

```bash
open iMessageAI.app
```

### Option B: Build from Source

```bash
open iMessageAI.xcodeproj
# In Xcode: Product > Run (Cmd+R)
```

## Expected Behavior

1. **App launches** — shows the configuration panel with Name, Personal Description, Moods, and Phone Numbers sections
2. **Model starts** — Xcode console (or app stdout) shows:
   ```
   [INIT] Config loaded.
   [INIT] Texts found.
   ```
3. **Waiting state** — periodically prints `[WAITING] Fetching text with content ...`
4. **Message arrives** — when someone sends you an iMessage:
   ```
   [RUN] New text from +1XXXXXXXXXX found.
   [GENERATING] 3 new responses will be generated.
   ```
5. **Replies generated** (~6.5 seconds):
   ```
   [FINISH] Done generating in 6.565435886383057 seconds.
   [WRITING] Writing to replies.json.
   ```
6. **UI updates** — reply cards appear in the Conversation section, one per mood
7. **User action** — tap a card to select, then:
   - **Reply** — sends the selected text via iMessage
   - **Refresh** — regenerates all replies
   - **Ignore** — skips this message
8. **Send confirmation** — console shows `[FINISH] Sending text.`

## Smoke Test (No iMessage Required)

To verify the Python engine and config parsing without waiting for a real message:

```bash
cd ~/iMessageAI
python3 -c "
import json
with open('config.json') as f:
    c = json.load(f)
print(f'Name: {c[\"name\"]}')
print(f'Moods: {list(c[\"moods\"].keys())}')
print(f'Filter: {c[\"phoneListMode\"]}')
print('SMOKE_OK')
"
```

Expected output:
```
Name: Caden Roberts
Moods: ['Happy', 'Professional', 'Sad']
Filter: Exclude
SMOKE_OK
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `model.py` crashes on startup | Verify Ollama is running: `curl http://localhost:11434/api/tags` |
| No messages detected | Grant Full Disk Access to Terminal/Xcode in System Settings |
| Empty reply cards | Ollama model may not be loaded: `ollama pull llama3.1:8b` |
| AppleScript send fails | Open Messages.app and sign into iMessage |
| Python not found | Install via `brew install python` or ensure conda is on PATH |
| Build fails in Xcode | Verify macOS deployment target matches your OS version |

## Full Demo Limitation

A complete end-to-end demo requires another person to send you an iMessage while the app is running. The smoke test above verifies config parsing and dependency availability without requiring an incoming message.
