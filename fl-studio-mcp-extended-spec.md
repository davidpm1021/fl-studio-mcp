# FL Studio MCP Extended: Specification (v2.1)

**Status**: Planning
**Author**: Dave
**Base**: Fork of [karl-andres/fl-studio-mcp](https://github.com/karl-andres/fl-studio-mcp)
**Last revised**: 2026-06-01 (added Piano Roll Scripting context findings)
**License**: MIT (inherited from base repo)

---

## Document conventions

| Marker         | Meaning                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------- |
| ✅ VERIFIED    | API call confirmed against [FL Studio API stubs](https://il-group.github.io/FL-Studio-API-Stubs/) |
| ⚠️ PROVISIONAL | Tool defined here but API call not yet verified. Claude Code must verify before implementing.     |
| ❌ IMPOSSIBLE  | Verified that the API does not support this. Tool removed from scope.                             |
| 🆕 BONUS       | Capability discovered during planning. Flagged for future sprints, not in immediate scope.        |

This spec was originally drafted without verifying each FL Studio API call. Sprint 1 has been verified across both scripting contexts (MIDI Controller and Piano Roll). Sprints 2-7 remain provisional and require Claude Code to verify each function call against the local `fl-studio-api-stubs` package before implementation.

---

## 1. Overview

FL Studio MCP Extended is a fork of `karl-andres/fl-studio-mcp` that expands the original ~36 tools across two layers:

- **Layer B (Primitives)**: FL Studio Python API coverage organized to match the module structure from [IL-Group/FL-Studio-API-Stubs](https://github.com/IL-Group/FL-Studio-API-Stubs).
- **Layer C (Theory Wrappers)**: Music-theory-aware abstractions built on top of primitives. Lives in a new `theory.py` module.

Goal: enable a workflow where Claude (in Claude Desktop) handles FL Studio mechanics, leaving the user focused on theory, listening, and creative decisions.

The MCP spans **two FL Studio scripting contexts** (MIDI Controller and Piano Roll), already established in the base repo and extended here.

---

## 2. Project metadata

| Property                    | Value                              |
| --------------------------- | ---------------------------------- |
| Suggested repo name         | `fl-studio-mcp-extended`           |
| Python                      | 3.10+ (project uses 3.12.x via uv) |
| Package manager             | uv                                 |
| MCP framework               | FastMCP                            |
| Total tool count (revised)  | ~65-70                             |
| Tools verified in this spec | 9 (Sprint 1)                       |
| Tools provisional           | ~56-61                             |
| FL Studio                   | 20.7+                              |
| OS support                  | Windows + macOS                    |
| Scripting contexts used     | MIDI Controller + Piano Roll       |

---

## 3. Architecture

### 3.1 Module organization

```
src/fl_studio_mcp/tools/
├── transport.py    # (extend) playback (NOT tempo - see general.py)
├── mixer.py        # (extend) tracks + eq + events + selection
├── channels.py     # (existing) channel rack
├── plugins.py      # (existing) plugin parameters
├── piano_roll.py   # (existing) piano roll operations
├── general.py      # (new) undo, save, FL state, TEMPO, TIME SIG (read)
├── patterns.py     # (new) pattern management
├── arrangement.py  # (new) markers, time queries
├── playlist.py     # (new) arrangement view
├── ui.py           # (new) window focus, navigation
├── utils.py        # (new) helpers
└── theory.py       # (new) Layer C wrappers
```

### 3.2 Naming conventions

- All tools use `fl_` prefix
- snake_case throughout
- Read operations: `fl_get_*`, `fl_list_*`, `fl_analyze_*`
- Write operations: `fl_set_*`, `fl_place_*`, `fl_apply_*`, `fl_add_*`, `fl_remove_*`

### 3.3 Communication patterns (dual scripting context)

The base repo already uses two FL Studio scripting contexts. This MCP extends both.

#### 3.3.1 MIDI Controller Scripting (primary)

Used for: transport, channels, mixer, plugins, general (most ops), patterns, arrangement, playlist, ui, utils

Flow:

1. MCP server writes a JSON command file
2. MCP sends a MIDI trigger note via loopMIDI
3. FL Studio controller script (`device_FLStudioMCP.py`) reads JSON, executes API call, writes response
4. MCP reads response

#### 3.3.2 Piano Roll Scripting (secondary)

Used for: piano roll note manipulation (existing), time signature reads, snap-to-scale reads (future), granular note access (future)

Flow:

1. MCP server writes a JSON command file
2. MCP triggers Ctrl+Alt+Y keystroke via `pynput`
3. FL Studio invokes `scripts/ComposeWithLLM.pyscript` which reads JSON, accesses `flpianoroll` module, writes response
4. MCP reads response

**Constraint**: The Piano Roll Scripting context only operates when the piano roll is open and focused. Tools using this context should pre-flight by ensuring the piano roll is accessible.

### 3.4 Error handling

Standardized structured response shape:

```python
{
    "success": bool,
    "data": <tool-specific payload>,
    "error": str | None,
    "error_code": str | None  # FL_NOT_RUNNING, INVALID_ARGS, API_TIMEOUT, API_ERROR, NOT_SUPPORTED, FL_PIANO_ROLL_CLOSED
}
```

Validate args before sending MIDI. Default timeout: 5 seconds. For dropped tools, do not register; do not stub with NOT_SUPPORTED.

### 3.5 Backwards compatibility

All ~36 existing tools from karl-andres/fl-studio-mcp are preserved with identical signatures.

### 3.6 Repository fork strategy

Single fork, no upstream PRs initially. Primitive additions could be PR'd later once stable.

---

## 4. FL Studio API patterns

Patterns discovered during Sprint 1 verification. Internalize before implementing any tool.

### 4.1 REC events: how to write to global controls

Tempo, master volume, master swing, and master pitch are NOT dedicated functions. They are "REC events" accessed via:

```python
import general
import midi

general.processRECEvent(
    midi.REC_<TARGET>,
    value_in_internal_units,
    midi.REC_Control | midi.REC_UpdateControl,
)
```

**Internal unit gotcha**: Tempo stores `BPM * 1000` (so 124 BPM = value 124000). Always check expected unit.

Documented REC events: https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/midi/__rec_events/

### 4.2 REC events: how to READ values

Two read APIs in the `device` module:

```python
normalized = device.getLinkedValue(midi.REC_Tempo)        # 0.0-1.0 normalized
formatted = device.getLinkedValueString(midi.REC_Tempo)   # "124 BPM" string
```

**Recommendation**: Use `getLinkedValueString` and parse. The normalized value is hard to convert back without knowing the parameter's range.

### 4.3 Constants live in the `midi` module

Window indices, REC event IDs, globalTransport commands, and other constants live in `midi`. The `ui` and `general` modules have functions that USE these constants but don't define them.

Example: `ui.setFocused(midi.widChannelRack)`, never `ui.widChannelRack`. Always `import midi`.

### 4.4 Save operations

`transport.globalTransport(midi.FPT_Save, 1)` saves the project. Works if a file has been saved before; pops a dialog otherwise.

`transport.globalTransport(midi.FPT_SaveNew, 1)` triggers the Save As dialog but takes no file path.

### 4.5 Piano Roll Scripting context for reads

The `flpianoroll.score` object exposes data not available in the MIDI Controller context:

- `tsnum`, `tsden`: project time signature (read-only)
- `PPQ`: ticks per quarter note (also in `general.getRecPPQ()`)
- `snap_root_note`: piano roll's snap-to-scale root
- `snap_scale_helper`: 12-char binary string showing scale pattern
- `noteCount`, `markerCount`: piano roll content sizes
- `getNote(i)`, `getMarker(i)`, `deleteNote(i)`, `deleteMarker(i)`: granular content access
- `getTimelineSelection()`: selected time range
- `getDefaultNoteProperties()`: draw tool's current style

Access pattern: invoke via the existing `ComposeWithLLM.pyscript` keystroke trigger, adding new operation handlers as needed.

### 4.6 Hard limits in the API (cannot fix at MCP layer)

| Wanted feature                       | Reality                                                       |
| ------------------------------------ | ------------------------------------------------------------- |
| Load new VST/AU plugins              | Not in API                                                    |
| Create new patterns programmatically | Not in API. Workaround: scaffold project with empty patterns. |
| **Set time signature**               | **Read-only** in Piano Roll Scripting. No setter.             |
| **Save As with file path**           | Save dialog requires user interaction                         |
| **Read project title or .flp path**  | No getter function exists                                     |
| Audio rendering to wav/mp3           | GUI-only, not scripting                                       |
| Granular automation curve editing    | Limited support                                               |

---

## 5. Sprint plan

Each sprint is one Claude Code session of 2-4 hours. Each ends with manual smoke testing.

| Sprint | Focus                                    | Tool count (revised) | Hours |
| ------ | ---------------------------------------- | -------------------- | ----- |
| 1      | Primitives Tier 1 (critical)             | 9 ✅ VERIFIED        | 2-4   |
| 2      | Primitives Tier 2 (workflow)             | ~10 ⚠️ PROVISIONAL   | 2-3   |
| 3      | Theory T1 (essentials)                   | ~7 ⚠️ PROVISIONAL    | 3-4   |
| 4      | Primitives Tier 3 (arrangement)          | ~12 ⚠️ PROVISIONAL   | 3-4   |
| 5      | Theory T2 (high-value composition)       | ~6 ⚠️ PROVISIONAL    | 3-4   |
| 6      | Primitives Tier 4 + Theory T4 (analysis) | ~15 ⚠️ PROVISIONAL   | 4-5   |
| 7      | Theory T3 (advanced jazz)                | ~6 ⚠️ PROVISIONAL    | 3-4   |

**Total**: ~65 new tools across primitives and theory wrappers.

Each sprint deliverable:

- Working tools registered with FastMCP
- Updated `device_FLStudioMCP.py` and/or `scripts/ComposeWithLLM.pyscript` with new dispatch handlers
- Unit tests for theory.py logic (pure functions)
- Manual smoke test results in `SMOKE_TESTS.md`
- `KNOWN_GAPS.md` updated with tools discovered impossible during the sprint
- Updated README tool tables

---

## 6. Tool specifications

### 6.1 transport.py (extend)

Sprint 1 transport additions deferred to Sprint 2; this sprint focuses on tempo (which lives in general.py per REC events pattern).

#### Sprint 2 additions ⚠️ provisional

| Tool                                       | Likely API                              |
| ------------------------------------------ | --------------------------------------- |
| `fl_get_song_position(mode='bars')`        | `transport.getSongPos(SONGLENGTH_BARS)` |
| `fl_set_loop_region(start_bars, end_bars)` | TBD                                     |
| `fl_clear_loop_region()`                   | TBD                                     |

### 6.2 general.py (new) ✅ Sprint 1 fully verified

#### Sprint 1 tools

| Tool                    | Args         | Verified API                                                                                                       | Context                  |
| ----------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| `fl_set_tempo`          | `bpm: float` | `general.processRECEvent(midi.REC_Tempo, bpm*1000, midi.REC_Control \| midi.REC_UpdateControl)`                    | MIDI Controller          |
| `fl_get_tempo`          | (none)       | Parse `device.getLinkedValueString(midi.REC_Tempo)`                                                                | MIDI Controller          |
| `fl_get_time_signature` | (none)       | `flpianoroll.score.tsnum`, `flpianoroll.score.tsden`                                                               | **Piano Roll Scripting** |
| `fl_undo`               | (none)       | `general.undoUp()`                                                                                                 | MIDI Controller          |
| `fl_redo`               | (none)       | `general.undoDown()`                                                                                               | MIDI Controller          |
| `fl_save_project`       | (none)       | `transport.globalTransport(midi.FPT_Save, 1)`                                                                      | MIDI Controller          |
| `fl_get_project_info`   | (none)       | Composite: REC_Tempo, REC_SongLength, ui.getVersion, general.getVersion, general.getChangedFlag, general.getRecPPQ | MIDI Controller          |

**Architectural note**: `fl_get_time_signature` is the only Sprint 1 tool requiring Piano Roll Scripting context. Implementation extends `scripts/ComposeWithLLM.pyscript` with a new `get_time_signature` operation. Prerequisite: piano roll must be open.

#### Sprint 2 additions ⚠️ provisional

| Tool                         | Likely API                                               |
| ---------------------------- | -------------------------------------------------------- |
| `fl_get_undo_history(count)` | `general.getUndoLevelHint` + `general.getUndoHistoryPos` |
| `fl_is_project_modified`     | `general.getChangedFlag()`                               |

#### Removed (impossible) ❌

| Tool                       | Reason                                                                  |
| -------------------------- | ----------------------------------------------------------------------- |
| `fl_save_project_as(path)` | `FPT_SaveNew` triggers dialog, no path arg                              |
| `fl_set_time_signature`    | `flpianoroll.score.tsnum/tsden` are read-only; no setter in any context |

### 6.3 patterns.py (new) ⚠️ Sprint 2 PROVISIONAL

Cannot create new patterns (hard API limit). Operations work on existing only.

| Tool                                 | Plausible source                                      |
| ------------------------------------ | ----------------------------------------------------- |
| `fl_list_patterns`                   | `patterns.patternCount`, `patterns.getPatternName(i)` |
| `fl_get_current_pattern`             | `patterns.patternNumber()`                            |
| `fl_select_pattern(index)`           | `patterns.jumpToPattern(index)`                       |
| `fl_set_pattern_name(index, name)`   | `patterns.setPatternName(index, name)`                |
| `fl_set_pattern_color(index, color)` | `patterns.setPatternColor(index, color)`              |
| `fl_get_pattern_length(index)`       | `patterns.getPatternLength(index)`                    |

### 6.4 arrangement.py (new) ⚠️ Sprint 4 PROVISIONAL

| Tool                                 | Plausible source        |
| ------------------------------------ | ----------------------- |
| `fl_add_marker(position_bars, name)` | `arrangement/markers`   |
| `fl_remove_marker(marker_id)`        | TBD                     |
| `fl_list_markers`                    | `arrangement/markers`   |
| `fl_get_selection`                   | `arrangement/selection` |
| `fl_set_selection(start, end)`       | `arrangement/selection` |
| `fl_clear_selection`                 | `arrangement/selection` |

### 6.5 playlist.py (new) ⚠️ Sprint 4 PROVISIONAL

| Tool                         | Plausible source                             |
| ---------------------------- | -------------------------------------------- |
| `fl_get_playlist_state`      | `playlist/performance` and `playlist/tracks` |
| `fl_add_pattern_to_playlist` | TBD                                          |
| `fl_remove_playlist_clip`    | TBD                                          |
| `fl_set_playlist_track_name` | `playlist/tracks`                            |

Note: playlist REC events documentation is an empty stub.

### 6.6 ui.py (new) ✅ Sprint 1 windows tools verified

#### Sprint 1 tools

| Tool                           | Verified API                                                                                         |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `fl_focus_window(window: str)` | `ui.setFocused(WINDOW_MAP[window])` with widMixer/widChannelRack/widPlaylist/widPianoRoll/widBrowser |
| `fl_get_window_state`          | `ui.getFocused(i)` and `ui.getVisible(i)` for window indices 0-4                                     |

#### Sprint 4+ tools ⚠️ provisional

| Tool                                 | Plausible source                 |
| ------------------------------------ | -------------------------------- |
| `fl_navigate_menu(path)`             | May not be directly possible     |
| `fl_show_hint(message, duration_ms)` | `ui/overlays` module             |
| `fl_show_window`, `fl_hide_window`   | `ui.showWindow`, `ui.hideWindow` |
| `fl_get_focused_caption`             | `ui.getFocusedFormCaption()`     |

### 6.7 mixer.py (extend) ⚠️ PROVISIONAL

| Tool                                               | Plausible source  |
| -------------------------------------------------- | ----------------- |
| `fl_get_selected_mixer_track`                      | `mixer/selection` |
| `fl_select_mixer_track(index)`                     | `mixer/selection` |
| `fl_get_mixer_eq(track)`                           | `mixer/eq`        |
| `fl_set_mixer_eq_band(track, band, freq, gain, q)` | `mixer/eq`        |
| `fl_get_mixer_sends(track)`                        | `mixer/tracks`    |
| `fl_set_mixer_send(from_track, to_track, level)`   | `mixer/tracks`    |

### 6.8 utils.py (new) ⚠️ Sprint 6 PROVISIONAL

| Tool                              | Notes                   |
| --------------------------------- | ----------------------- |
| `fl_bars_to_seconds(bars)`        | Pure helper using tempo |
| `fl_seconds_to_bars(seconds)`     | Pure helper using tempo |
| `fl_note_name_to_midi(name)`      | Pure helper             |
| `fl_midi_to_note_name(midi_note)` | Pure helper             |
| `fl_get_fl_version`               | `ui.getVersion()`       |
| `fl_get_api_version`              | `general.getVersion()`  |
| `fl_get_ppq`                      | `general.getRecPPQ()`   |

### 6.9 theory.py (new) ⚠️ Layer C PROVISIONAL

All Layer C tools are pure Python with FL Studio integration via existing primitives.

#### T1: Essentials (Sprint 3)

| Tool                                                                                       | Approach                                                    |
| ------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| `fl_place_chord(root, quality, position_bars, duration_bars, octave, voicing)`             | Compute notes, call existing `fl_send_chord`                |
| `fl_place_progression(progression OR roman, key, start_bars, chord_duration_bars, octave)` | Compute chord sequence, call `fl_send_chord` multiple times |
| `fl_place_scale(key, mode, octave, direction, rhythm, start_bars)`                         | Compute scale notes, call `fl_send_notes`                   |
| `fl_place_arpeggio(chord, pattern, octaves, note_duration, start_bars)`                    | Compute arpeggio sequence, call `fl_send_notes`             |
| `fl_transpose_selection(semitones OR interval)`                                            | Get state, modify, replace                                  |
| `fl_get_chord_notes(root, quality, octave, voicing)`                                       | Pure helper                                                 |
| `fl_get_scale_notes(key, mode, octave)`                                                    | Pure helper                                                 |

T2 (Sprint 5), T3 (Sprint 7), T4 (Sprint 6) tools: see original spec v1 for full list, all marked ⚠️ provisional.

### 6.10 Bonus Piano Roll Scripting capabilities 🆕

Discovered during planning but not in immediate scope. Add to relevant later sprints or as ad-hoc additions.

| Tool                              | Source                                                  | Sprint candidate                                    |
| --------------------------------- | ------------------------------------------------------- | --------------------------------------------------- |
| `fl_get_snap_scale`               | `flpianoroll.score.snap_root_note`, `snap_scale_helper` | Sprint 6 (Theory T4 analysis)                       |
| `fl_get_piano_roll_note(index)`   | `flpianoroll.score.getNote(i)`                          | Replaces/extends existing `fl_get_piano_roll_state` |
| `fl_get_piano_roll_marker(index)` | `flpianoroll.score.getMarker(i)`                        | Sprint 4 (arrangement)                              |
| `fl_get_timeline_selection`       | `flpianoroll.score.getTimelineSelection()`              | Sprint 4                                            |
| `fl_clear_piano_roll_selective`   | `flpianoroll.score.clear(all=False)`                    | Refines existing clear tool                         |

---

## 7. Implementation notes for Claude Code

### 7.1 FL Studio API reference

The `fl-studio-api-stubs` package is installed in the project's venv:

- Windows: `.venv\Lib\site-packages\<module>\__init__.pyi`
- macOS/Linux: `.venv/lib/python3.12/site-packages/<module>/__init__.pyi`

Online: https://il-group.github.io/FL-Studio-API-Stubs/

For each ⚠️ PROVISIONAL tool:

1. Grep the relevant module's stubs
2. Read the function docstring
3. Verify the signature
4. Implement only after verification

If an assumed function doesn't exist, mark as IMPOSSIBLE in `KNOWN_GAPS.md` and skip. Do not invent API calls.

### 7.2 Cross-context implementation guidance

#### MIDI Controller Scripting tools

- MCP wrapper in `src/fl_studio_mcp/tools/<module>.py`
- Dispatch handler in `fl_controller/device_FLStudioMCP.py`
- Uses JSON+MIDI bridge via `src/fl_studio_mcp/utils/connection.py`

#### Piano Roll Scripting tools

- MCP wrapper in `src/fl_studio_mcp/tools/<module>.py`
- Dispatch handler in `scripts/ComposeWithLLM.pyscript`
- Uses JSON+keystroke trigger via `src/fl_studio_mcp/utils/fl_trigger.py`
- **Requires piano roll open**; tools should pre-flight or error helpfully

### 7.3 Theory wrapper implementation

Theory wrappers are partly pure Python and partly FL Studio integration:

- **Pure helpers** (`fl_get_chord_notes`, `fl_get_scale_notes`, `fl_note_name_to_midi`): no FL Studio communication. Fully unit testable.
- **Placement tools** (`fl_place_chord`, `fl_place_progression`, etc.): compute notes pure, then call existing primitive piano roll tools.
- **Analysis tools** (`fl_analyze_*`): read piano roll state via `fl_get_piano_roll_state`, run pure analysis logic.

Reusing existing primitives keeps theory wrappers thin (~50-150 LOC each).

### 7.4 Music theory data

Define constants for chord qualities, scale modes, named progressions:

```python
# theory.py (excerpt)

CHORD_QUALITIES = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "dim7": [0, 3, 6, 9],
}

SCALE_MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
}

NAMED_PROGRESSIONS = {
    "fifties": ["I", "vi", "IV", "V"],
    "axis_of_awesome": ["I", "V", "vi", "IV"],
    "andalusian": ["i", "VII", "VI", "V"],
    "twelve_bar_blues": ["I", "I", "I", "I", "IV", "IV", "I", "I", "V", "IV", "I", "I"],
    "jazz_ii_v_i": ["ii7", "V7", "Imaj7"],
    "pachelbel": ["I", "V", "vi", "iii", "IV", "I", "IV", "V"],
}
```

### 7.5 Testing strategy

- **Unit tests** for `theory.py` pure functions. pytest. No FL Studio required.
- **Manual smoke tests** for FL Studio integration. Documented in `SMOKE_TESTS.md`.

### 7.6 Sprint workflow

1. Branch from main: `sprint-N-<focus>`
2. Verify each ⚠️ PROVISIONAL tool against local stubs
3. Implement in priority order
4. Update `KNOWN_GAPS.md` for any tools discovered impossible
5. Add to FastMCP tool registry
6. Extend `device_FLStudioMCP.py` and/or `ComposeWithLLM.pyscript` with new commands
7. Run unit tests (theory only)
8. Run manual smoke tests with FL Studio open
9. Update README tool tables
10. PR to main for review

---

## 8. Migration plan

### 8.1 Fork and rename

```powershell
# Fork karl-andres/fl-studio-mcp on GitHub
# Suggested name: fl-studio-mcp-extended
cd C:\Users\david\Documents
git clone https://github.com/<dave-github>/fl-studio-mcp-extended.git
cd fl-studio-mcp-extended

# Update pyproject.toml: name = "fl-studio-mcp-extended"
# Update README header
```

### 8.2 Update Claude Desktop config

```json
"fl-studio": {
  "command": "uv",
  "args": [
    "run",
    "--directory",
    "C:\\Users\\david\\Documents\\fl-studio-mcp-extended",
    "fl-studio-mcp"
  ]
}
```

Keep both servers configured during transition.

### 8.3 Existing project compatibility

All ~36 existing tools preserved with identical signatures.

### 8.4 Hand-off to Claude Code

```powershell
cd C:\Users\david\Documents\fl-studio-mcp-extended
claude
```

Paste the corresponding `sprint-N-claude-code-prompt.md` content.

---

## 9. Known gaps and future work

### 9.1 Hard limits discovered

| Item                                    | API status                                                      |
| --------------------------------------- | --------------------------------------------------------------- |
| Set time signature                      | Read-only in Piano Roll Scripting (`tsnum`/`tsden`). No setter. |
| Read time signature markers in playlist | Only project-level time sig accessible. Markers not in API.     |
| Save As with file path                  | Dialog-only                                                     |
| Project title and file path reads       | No getter functions                                             |
| Load VST/AU plugins                     | Not in API                                                      |
| Create new patterns                     | Not in API                                                      |
| Audio rendering                         | GUI-only                                                        |
| Granular automation curves              | Limited                                                         |

### 9.2 Future work (deferred)

- Edison audio scripting context (different from Piano Roll Scripting; audio analysis)
- Bonus Piano Roll Scripting tools (see section 6.10)
- Web UI for MCP debugging
- Multi-project support (FL Studio is single-project anyway)
- Linux support (FL Studio runs via Wine; scripting unsupported)

---

## 10. Glossary

| Term                                  | Meaning                                                                                                                |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Primitives (Layer B)**              | Tools wrapping FL Studio API functions.                                                                                |
| **Theory wrappers (Layer C)**         | Higher-level tools encoding musical concepts.                                                                          |
| **REC event**                         | FL Studio's automatable parameter. Read/written via `general.processRECEvent` and `device.getLinkedValue`.             |
| **PPQ**                               | Pulses Per Quarter note. FL Studio's tick resolution.                                                                  |
| **B:S:T**                             | Bars:Steps:Ticks. FL Studio's hierarchical time format.                                                                |
| **MIDI Controller Scripting context** | Primary scripting context. JSON+MIDI bridge. Runs in `device_FLStudioMCP.py`.                                          |
| **Piano Roll Scripting context**      | Secondary scripting context. JSON+keystroke bridge. Runs in `ComposeWithLLM.pyscript`. Access to `flpianoroll` module. |
| **Channel Rack**                      | FL Studio's instrument/sound list.                                                                                     |
| **Piano Roll**                        | FL Studio's note editor.                                                                                               |
| **Pattern**                           | A reusable musical unit. Placed in the Playlist.                                                                       |
| **Playlist**                          | FL Studio's arrangement view.                                                                                          |
| **Voicing**                           | The vertical arrangement of notes in a chord.                                                                          |
| **Voice leading**                     | Moving each note as little as possible between chords.                                                                 |
| **Aeolian**                           | Natural minor mode.                                                                                                    |

---

## 11. Open questions

1. **Tempo range bounds**: FL Studio's tempo range determines normalization for `getLinkedValue(REC_Tempo)`. Spec uses `getLinkedValueString` to avoid this. Validation bounds (10-1000 BPM) are plausible but unconfirmed.
2. **Pattern length auto-extend**: When sending notes past end of current pattern, does FL Studio auto-extend? Verify in Sprint 1 smoke tests.
3. **Naming conflict**: `fl_send_chord` (primitive, raw notes) vs `fl_place_chord` (theory wrapper, musical concept). Keep both with distinct semantics.
4. **MIDI note encoding**: Standard MIDI (C4 = 60) assumed. Verify in Sprint 1 smoke tests.
5. **Piano roll script reliability**: How does the keystroke trigger behave if focus is elsewhere? May need explicit window management before each Piano Roll Scripting call.

---

## Changelog

### v2.1 (2026-06-01)

- Added `fl_get_time_signature` to Sprint 1 via Piano Roll Scripting context (`flpianoroll.score.tsnum/tsden`)
- Sprint 1 count: 8 → 9 tools
- New section 4.5: Piano Roll Scripting context for reads
- New section 6.10: Bonus Piano Roll Scripting capabilities flagged for future sprints
- Section 9.1: Time signature now "read-only via Piano Roll Scripting" instead of fully impossible
- New error code: `FL_PIANO_ROLL_CLOSED`
- Dual-context architecture explicitly documented in section 3.3
- Glossary entries for both scripting contexts

### v2 (2026-06-01)

- Sprint 1 tools verified against FL Studio API stubs
- New Section 4: FL Studio API patterns (REC events, read patterns, constants, save operations, hard limits)
- Moved tempo from `transport.py` to `general.py`
- Dropped `fl_set_time_signature`, `fl_save_project_as` (later partially restored in v2.1 for get)
- Sprint 1 tool count: 11 → 8
- Added ✅/⚠️/❌ verification markers throughout
- Section 9 (Known gaps) expanded
- Section 11 (Open questions) updated

### v1 (2026-06-01, original)

- Initial draft with planning-level tool definitions
- No API verification performed
