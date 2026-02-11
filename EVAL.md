# Evaluation

## Correctness Definition

The system is correct when:

1. `model.py` successfully reads `config.json` and constructs a system prompt containing all mood definitions
2. The Ollama call returns a JSON object whose keys exactly match the mood keys in `config.json`
3. `replies.json` is written with the complete mood→reply map plus metadata fields (`sender`, `message`, `time`, `Reply`)
4. The SwiftUI app displays one card per mood with the generated reply text
5. User selection writes the correct mood name to the `Reply` key in `replies.json`
6. `model.py` reads the selection and invokes `send_imessage.applescript` with the correct phone number and reply text

## Verification Commands

### Config Parsing (Python)

```bash
cd ~/iMessageAI
python3 -c "
import json
with open('config.json') as f:
    c = json.load(f)
assert 'name' in c, 'missing name'
assert 'personalDescription' in c, 'missing personalDescription'
assert 'moods' in c and isinstance(c['moods'], dict), 'missing or invalid moods'
assert len(c['moods']) >= 1, 'need at least 1 mood'
assert 'phoneListMode' in c and c['phoneListMode'] in ('Include', 'Exclude'), 'invalid phoneListMode'
assert 'phoneNumbers' in c and isinstance(c['phoneNumbers'], list), 'invalid phoneNumbers'
print('CONFIG_OK')
"
```

**Pass:** prints `CONFIG_OK`
**Fail:** assertion error with field name

### LLM Reply Structure (Python, requires Ollama running)

```bash
cd ~/iMessageAI
python3 -c "
import json, ollama
with open('config.json') as f:
    c = json.load(f)
moods = c['moods']
prompt = 'You must return JSON with keys: ' + ', '.join(moods.keys())
out = ollama.chat(model='llama3.1:8b', format='json', messages=[
    {'role': 'system', 'content': prompt},
    {'role': 'user', 'content': 'Hello'}
])['message']['content']
parsed = json.loads(out)
assert sorted(parsed.keys()) == sorted(moods.keys()), f'key mismatch: {sorted(parsed.keys())} vs {sorted(moods.keys())}'
print('LLM_REPLY_OK')
"
```

**Pass:** prints `LLM_REPLY_OK`
**Fail:** key mismatch assertion or JSON parse error

### Replies JSON Structure

```bash
cd ~/iMessageAI
python3 -c "
import json
with open('replies.json') as f:
    r = json.load(f)
assert 'Reply' in r, 'missing Reply key'
assert 'sender' in r, 'missing sender key'
assert 'message' in r, 'missing message key'
assert 'time' in r, 'missing time key'
with open('config.json') as f:
    c = json.load(f)
for mood in c['moods']:
    assert mood in r, f'missing mood key: {mood}'
print('REPLIES_OK')
"
```

**Pass:** prints `REPLIES_OK`
**Fail:** missing key assertion

### Swift Build

```bash
cd iMessageAI
xcodebuild -project iMessageAI.xcodeproj -scheme iMessageAI -configuration Debug build 2>&1 | tail -5
```

**Pass:** `BUILD SUCCEEDED`
**Fail:** compiler errors

## Performance Expectations

| Metric | Target | Measured |
|---|---|---|
| Reply generation time | < 15s per cycle | ~6.5s (Apple Silicon, Llama 3.1 8B) |
| Config parse time | < 10ms | Negligible |
| UI poll interval | 1s | 1s (fixed timer) |
| Retry overhead | < 5 retries * 6.5s = 32.5s worst case | Rare; typically 0-1 retries |

## Pass/Fail Criteria

- **Pass:** All verification commands above print their respective `_OK` tokens. Swift project builds without errors.
- **Fail:** Any verification command produces an assertion error or the build fails.

Full end-to-end testing requires: macOS, Full Disk Access, Messages.app signed in, Ollama running with `llama3.1:8b`, and an actual incoming iMessage. This cannot be automated in CI.
