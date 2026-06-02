# Claude Code: FL Studio MCP Extended, Sprint 1

I'm extending an MCP server for FL Studio. The full specification is in `fl-studio-mcp-extended-spec.md` in this project directory. Read it in full before starting work.

## This sprint

**Sprint 1: Primitives Tier 1 (critical blockers).** 9 tools across 3 modules + 1 piano roll script extension. Estimated 2-4 hours.

**Note on revised scope**: Original spec listed 11 tools. Two have been dropped after verifying against the FL Studio API:

- `fl_set_time_signature`: time signature is read-only in the FL Studio API (only `flpianoroll.score.tsnum` and `tsden`, both read-only). No setter exists.
- `fl_save_project_as(path)`: `globalTransport(FPT_SaveNew)` triggers FL Studio's save-as dialog requiring user interaction. No programmatic path argument is possible.

## Dual scripting context architecture

This sprint touches both FL Studio scripting contexts:

1. **MIDI Controller Scripting** (`device_FLStudioMCP.py`): handles 8 of 9 tools. JSON+MIDI dispatch pattern, existing in the base repo.
2. **Piano Roll Scripting** (`ComposeWithLLM.pyscript`): handles `fl_get_time_signature` only. Keystroke-trigger pattern, existing in the base repo.

The existing MCP already uses both. This sprint extends each with new operations.

**Prerequisite for `fl_get_time_signature`**: The piano roll must be open with a channel selected. The tool should pre-flight by calling `fl_focus_window("piano_roll")` internally before triggering the script, OR return a clear error if the piano roll isn't accessible.

## Tools to implement (Sprint 1, revised)

### `src/fl_studio_mcp/tools/transport.py` (extend existing file)

#### `fl_set_tempo(bpm: float) -> dict`

Set project tempo in BPM. Validates input range 10-1000.

**FL Studio API call**:

```python
import general
import midi

general.processRECEvent(
    midi.REC_Tempo,
    int(bpm * 1000),  # FL stores tempo as 1000x BPM
    midi.REC_Control | midi.REC_UpdateControl
)
```

**Returns**: `{"success": True, "new_tempo": bpm}` or `{"success": False, "error": "...", "error_code": "INVALID_ARGS"}`

#### `fl_get_tempo() -> dict`

Get current project tempo. Uses the string-formatted read because `getLinkedValue` returns a 0.0-1.0 normalized value, not raw BPM.

**FL Studio API call**:

```python
import device
import midi

tempo_str = device.getLinkedValueString(midi.REC_Tempo)
# tempo_str will be like "124.0 BPM" or "124 BPM"
bpm = float(tempo_str.split()[0])
```

**Returns**: `{"success": True, "tempo": 124.0}`

### `src/fl_studio_mcp/tools/general.py` (new file)

#### `fl_undo() -> dict`

**FL Studio API call**: `general.undoUp()`

**Note**: In FL Studio 21+, "up" in undo history actually moves backwards (visually appears as "down" in newer FL versions). The function name reflects internal data structure, not UI direction. Use `undoUp()` for what users think of as "undo".

**Returns**: `{"success": True, "position_hint": "3/10"}` where position_hint comes from `general.getUndoLevelHint()`

#### `fl_redo() -> dict`

**FL Studio API call**: `general.undoDown()`

**Returns**: `{"success": True, "position_hint": "4/10"}`

#### `fl_save_project() -> dict`

Save to current file path. Triggers FL Studio's normal save operation.

**FL Studio API call**:

```python
import transport
import midi

transport.globalTransport(midi.FPT_Save, 1)
```

**Caveat**: If the project has never been saved, this may trigger a Save As dialog. Cannot detect this from the API.

**Returns**: `{"success": True}` (no path returned by API)

#### `fl_get_project_info() -> dict`

Composite information from multiple API sources:

```python
import general
import device
import midi
import ui

tempo_str = device.getLinkedValueString(midi.REC_Tempo)
tempo = float(tempo_str.split()[0])

length_str = device.getLinkedValueString(midi.REC_SongLength)
# Parse as appropriate

fl_version = ui.getVersion()    # string like "21.0.3 [build 3517]"
api_version = general.getVersion()  # int
changed = general.getChangedFlag()  # 0=unchanged, 1=changed, 2=changed-since-autosave
ppq = general.getRecPPQ()
```

**Known limitations**: No API function returns the project title or file path. These are not accessible.

**Returns**:

```python
{
    "success": True,
    "tempo": 124.0,
    "song_length_bars": 32,
    "fl_studio_version": "21.0.3",
    "api_version": 33,
    "modified": True,
    "ppq": 96,
    "title": None,
    "path": None,
}
```

#### `fl_get_time_signature() -> dict`

**IMPORTANT**: This tool uses the **Piano Roll Scripting context**, NOT the MIDI Controller Scripting context. Implementation lives in two places:

1. **MCP-side wrapper** in `general.py`: triggers the piano roll script and reads response
2. **Piano Roll script handler** in `scripts/ComposeWithLLM.pyscript`: reads `flpianoroll.score.tsnum` and `tsden`

**MCP-side implementation pattern**:

- Write a JSON request like `{"op": "get_time_signature"}` to the queue file
- Call the existing `fl_trigger.py` mechanism to send Ctrl+Alt+Y keystroke
- Read response JSON
- Return result

**Piano Roll script handler addition** (in `ComposeWithLLM.pyscript`):

```python
# Inside the script's main dispatch:
if request["op"] == "get_time_signature":
    response = {
        "success": True,
        "numerator": flpianoroll.score.tsnum,
        "denominator": flpianoroll.score.tsden,
    }
    write_response(response)
```

**Verified API**: `flpianoroll.score.tsnum` and `flpianoroll.score.tsden` are read-only properties returning the project's overall time signature numerator and denominator. Both documented in the Piano Roll Scripting API stubs.

**Caveats**:

- Returns the project's overall time signature, NOT time signature markers in the playlist.
- Piano roll must be open in FL Studio. The tool should call `ui.setFocused(midi.widPianoRoll)` first or return a helpful error.

**Returns**: `{"success": True, "numerator": 4, "denominator": 4}` or `{"success": False, "error": "piano roll not accessible", "error_code": "FL_PIANO_ROLL_CLOSED"}`

### `src/fl_studio_mcp/tools/ui.py` (new file)

#### `fl_focus_window(window: str) -> dict`

**Valid window names**: `mixer`, `channel_rack`, `playlist`, `piano_roll`, `browser`

**FL Studio API call**:

```python
import ui
import midi

WINDOW_MAP = {
    "mixer": midi.widMixer,                # 0
    "channel_rack": midi.widChannelRack,   # 1
    "playlist": midi.widPlaylist,          # 2
    "piano_roll": midi.widPianoRoll,       # 3
    "browser": midi.widBrowser,            # 4
}

window_index = WINDOW_MAP[window]
ui.setFocused(window_index)
```

**Returns**: `{"success": True, "focused_window": "piano_roll"}`

#### `fl_get_window_state() -> dict`

**FL Studio API call**:

```python
import ui
import midi

windows = ["mixer", "channel_rack", "playlist", "piano_roll", "browser"]
indices = [midi.widMixer, midi.widChannelRack, midi.widPlaylist, midi.widPianoRoll, midi.widBrowser]

focused = None
visible = []
for name, idx in zip(windows, indices):
    if ui.getFocused(idx):
        focused = name
    if ui.getVisible(idx):
        visible.append(name)

focused_caption = ui.getFocusedFormCaption()
```

**Returns**: `{"success": True, "focused": "piano_roll", "visible": ["channel_rack", "piano_roll", "mixer"], "focused_caption": "Piano Roll - FL Keys"}`

## Architecture patterns to internalize

Three FL Studio API patterns to know upfront:

### Pattern 1: REC events are how you write to "global controls"

Tempo, master volume, master swing, and master pitch are all REC events, not dedicated functions:

```python
general.processRECEvent(
    midi.REC_<TARGET>,
    value_in_internal_units,  # often value * 1000
    midi.REC_Control | midi.REC_UpdateControl,
)
```

### Pattern 2: REC event READS use device module, NOT general

```python
normalized = device.getLinkedValue(midi.REC_Tempo)  # 0.0-1.0 normalized
text = device.getLinkedValueString(midi.REC_Tempo)  # "124 BPM" string
```

Parse the string for raw values.

### Pattern 3: Window constants live in the `midi` module

Always `import midi` for `widMixer`, `widChannelRack`, `widPlaylist`, `widPianoRoll`, `widBrowser`.

### Pattern 4: Piano Roll Scripting is a separate context

The `flpianoroll` module is only available inside Piano Roll scripts (triggered via Tools > Scripting menu or the existing keystroke trigger). It runs in its own sandbox and has access to:

- Read time signature (`tsnum`, `tsden`)
- Read snap-to-scale settings (`snap_root_note`, `snap_scale_helper`)
- Granular note and marker access
- Project PPQ

The existing `ComposeWithLLM.pyscript` is the piano roll script. Extending it with new operations is the way to access this context from MCP tools.

## Implementation pattern

Follow the existing architecture exactly. Before writing any new code, study how `transport.py` and `channels.py` currently work in this repo. Then study `scripts/ComposeWithLLM.pyscript` for the piano roll pattern.

### For MIDI controller scripting tools (8 of 9 tools)

- MCP-side wrapper: `@mcp.tool()` decorator, validate args, call connection layer with command name and args, return structured response
- FL Studio-side handler in `device_FLStudioMCP.py`: add new command name to dispatch, call verified FL Studio API, write JSON response, return MIDI ack

### For Piano Roll Scripting tools (fl_get_time_signature only)

- MCP-side wrapper: validate args, write request JSON, trigger keystroke via existing `fl_trigger.py`, read response JSON
- Piano Roll script-side handler in `scripts/ComposeWithLLM.pyscript`: extend dispatch to handle "get_time_signature" op, read `flpianoroll.score.tsnum/tsden`, write response

## Error handling

Standardized structured response shape (from spec section 3.4):

```python
{
    "success": bool,
    "data": <tool-specific payload>,
    "error": str | None,
    "error_code": str | None
}
```

Error codes: `FL_NOT_RUNNING`, `INVALID_ARGS`, `API_TIMEOUT`, `API_ERROR`, `NOT_SUPPORTED`, `FL_PIANO_ROLL_CLOSED` (new, for time signature tool).

For dropped tools (`fl_set_time_signature`, `fl_save_project_as`), do not register them. Don't add stub implementations that return `NOT_SUPPORTED`.

## Testing

1. **Unit tests**: Not required this sprint. These are thin wrappers over FL Studio API calls.

2. **Smoke tests**: Create `SMOKE_TESTS.md` in the project root with manual test cases for all 9 tools.

   Specifically for `fl_get_time_signature`:
   - [ ] Open project at 4/4. Call tool. Returns `{numerator: 4, denominator: 4}`.
   - [ ] Change project to 3/4 (Options > Project general settings > Time settings). Call tool. Returns `{numerator: 3, denominator: 4}`.
   - [ ] Close piano roll. Call tool. Returns helpful error.

## Deliverables

When the sprint is complete:

1. All 9 tools registered with FastMCP
2. `device_FLStudioMCP.py` dispatches 8 new commands (everything except time signature)
3. `scripts/ComposeWithLLM.pyscript` extended with `get_time_signature` op
4. README tool tables updated to include all 9 new tools, with notes on which use Piano Roll Scripting
5. `SMOKE_TESTS.md` created with test cases for all 9 tools
6. `KNOWN_GAPS.md` created documenting the two dropped tools (set_time_signature, save_as) with the API reasoning
7. Code committed to a feature branch: `sprint-1-tier1-primitives`
8. Pull request to `main` ready for review

## What NOT to do this sprint

- Do not implement `fl_set_time_signature` or `fl_save_project_as`. They are documented as impossible. Do not create stub implementations.
- Do not implement Tier 2, 3, or 4 primitives (later sprints)
- Do not implement any theory wrappers (later sprints)
- Do not implement the other Piano Roll Scripting bonus tools (`fl_get_snap_scale`, granular note access) discovered during planning. Flag them in `KNOWN_GAPS.md` as future opportunities and move on. Sprint 1 stays focused.
- Do not refactor existing tools unless strictly necessary for new ones to work
- Do not change existing tool signatures (backwards compatibility is required)

## If you discover the spec is wrong

If a verified API call above doesn't work as documented, or you find a way to do something documented as impossible, surface this. Don't silently work around it.

## Start

1. Read `fl-studio-mcp-extended-spec.md` in full, especially sections 3, 4, and 6.
2. Read `src/fl_studio_mcp/tools/transport.py` to understand the current MCP-side pattern.
3. Read `fl_controller/device_FLStudioMCP.py` to understand the MIDI Controller dispatch pattern.
4. Read `scripts/ComposeWithLLM.pyscript` to understand the Piano Roll Scripting dispatch pattern.
5. Read `src/fl_studio_mcp/utils/connection.py` and `src/fl_studio_mcp/utils/fl_trigger.py` to understand both communication bridges.
6. Grep the local `fl-studio-api-stubs` package in `.venv` to verify the function signatures I provided.
7. Implement.

When unsure, the local stubs are the authoritative reference. Read the `.pyi` files directly.
