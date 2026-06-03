# Sprint 1 Smoke Tests

Manual test cases for the 9 Sprint 1 tools. These require FL Studio running with
the FLStudioMCP MIDI controller enabled (and, for `fl_get_time_signature`, the
`ComposeWithLLM.pyscript` installed and the piano roll open).

**Setup**

- [ ] FL Studio 20.7+ running.
- [ ] FLStudioMCP controller enabled in MIDI Settings (MIDI bridge tools).
- [ ] `ComposeWithLLM.pyscript` installed in the Piano roll scripts folder.
- [ ] Virtual MIDI port configured (loopMIDI on Windows / IAC on macOS).
- [ ] `fl_connection_status` reports connected.

---

## General (MIDI bridge)

### `fl_set_tempo`

- [ ] `fl_set_tempo(140)` → `{"success": true, "new_tempo": 140}`; FL Studio tempo display reads 140 BPM.
- [ ] `fl_set_tempo(128.5)` → tempo display reads 128.5 BPM (fractional BPM preserved).
- [ ] `fl_set_tempo(5)` → `{"success": false, "error_code": "INVALID_ARGS"}` (below range; no MIDI sent).
- [ ] `fl_set_tempo(2000)` → `{"success": false, "error_code": "INVALID_ARGS"}` (above range).

### `fl_get_tempo`

- [ ] Set tempo to 140, then `fl_get_tempo()` → `{"success": true, "tempo": 140.0}`.
- [ ] Set a fractional tempo (e.g. 128.5), then `fl_get_tempo()` → matches.

### `fl_undo`

- [ ] Make a change (e.g. set tempo to 150), call `fl_undo()` → `{"success": true, "position_hint": "<n>/<m>"}`; the change is reverted.

### `fl_redo`

- [ ] After the undo above, call `fl_redo()` → `{"success": true, "position_hint": "..."}`; the change is reapplied.

### `fl_save_project`

- [ ] On a previously-saved project, `fl_save_project()` → `{"success": true}`; title bar loses the unsaved-change indicator.
- [ ] On a never-saved project, expect a Save As dialog to appear in FL Studio (documented caveat; not detectable from the API).

### `fl_get_project_info`

- [ ] `fl_get_project_info()` returns `success: true` with `tempo` matching the project, a `fl_studio_version` like "20.8.4", an integer `api_version`, a boolean `modified`, and an integer `ppq` (typically 96).
- [ ] `title` and `path` are `null` (documented limitation).
- [ ] After an edit, `modified` is `true`; after `fl_save_project`, `modified` is `false`.

---

## Time signature (Piano Roll Scripting)

### `fl_get_time_signature`

- [ ] Open a project at 4/4 with the piano roll open. Call the tool → `{"success": true, "numerator": 4, "denominator": 4}`.
- [ ] Change the project to 3/4 (Options > Project general settings > Time settings). Call the tool → `{"success": true, "numerator": 3, "denominator": 4}`.
- [ ] Close the piano roll. Call the tool → `{"success": false, "error_code": "FL_PIANO_ROLL_CLOSED"}` (or a clear error).

---

## UI / Windows (MIDI bridge)

### `fl_focus_window`

- [ ] `fl_focus_window("mixer")` → `{"success": true, "focused_window": "mixer"}`; mixer comes to front.
- [ ] Repeat for `channel_rack`, `playlist`, `piano_roll`, `browser`.
- [ ] `fl_focus_window("nonsense")` → `{"success": false, "error_code": "INVALID_ARGS"}` (no MIDI sent).

### `fl_get_window_state`

- [ ] Focus the piano roll, then `fl_get_window_state()` → `focused == "piano_roll"`, `visible` lists currently open windows, `focused_caption` is a non-empty string.

---

# Sprint 3 Smoke Tests

Manual test cases for the 7 Sprint 3 tools (Theory T1). The two `fl_get_*`
helpers are pure (no FL Studio needed). The `fl_place_*` and
`fl_transpose_selection` tools require the **piano roll open** and the
**ComposeWithLLM script armed once this session** (Piano Roll → Tools →
Scripting → ComposeWithLLM). The pyscript changed this sprint (new `transpose`
action), so re-run ComposeWithLLM from the menu once before testing.

Pure-function logic is also covered by `tests/test_theory.py` (83 unit tests,
run with `pytest`).

---

## Pure helpers (no FL Studio)

### `fl_get_chord_notes`

- [ ] `fl_get_chord_notes("C", "maj7")` → `{"success": true, "notes": [60,64,67,71], "note_names": ["C4","E4","G4","B4"]}`.
- [ ] `fl_get_chord_notes("A", "min", voicing="first")` → first-inversion notes.
- [ ] `fl_get_chord_notes("C", "bogus")` → `{"success": false, "error_code": "INVALID_ARGS"}`.

### `fl_get_scale_notes`

- [ ] `fl_get_scale_notes("A", "minor")` → `[69,71,72,74,76,77,79]`.
- [ ] `fl_get_scale_notes("D", "dorian")` → `[62,64,65,67,69,71,72]`.

---

## Placement (Piano Roll Scripting; piano roll open + script armed)

### `fl_place_chord`

- [ ] With piano roll open at bar 1, `fl_place_chord("C", "maj7")` → a Cmaj7 chord (C4 E4 G4 B4) appears at bar 1, one bar long.
- [ ] `fl_place_chord("G", "7", position_bars=2, voicing="drop2")` → G7 drop-2 voicing at bar 2.
- [ ] `fl_place_chord("C", position_bars=0)` → `{"success": false, "error_code": "INVALID_ARGS"}` (1-indexed).

### `fl_place_progression`

- [ ] `fl_place_progression(["I","vi","IV","V"], key="C")` → four chords (C, Am, F, G), one per bar, starting at bar 1.
- [ ] `fl_place_progression(name="jazz_ii_v_i", key="C")` → Dm7, G7, Cmaj7.
- [ ] `fl_place_progression(["C","Am7","F","G"])` → chord-symbol progression places correctly.

### `fl_place_scale`

- [ ] `fl_place_scale("C", "major")` → ascending C major run (8 notes incl. top C5) starting at bar 1.
- [ ] `fl_place_scale("C", "major", octaves=2, direction="updown")` → two-octave up-then-down run.

### `fl_place_arpeggio`

- [ ] `fl_place_arpeggio("A", "min7", pattern="up", octaves=2)` → ascending Am7 arpeggio over two octaves.
- [ ] `fl_place_arpeggio("C", pattern="updown")` → up-then-down arpeggio.

### `fl_transpose_selection`

- [ ] Place a chord, select some notes in FL, `fl_transpose_selection(semitones=12)` → selected notes move up an octave (response notes_transposed = number selected, scope "selected").
- [ ] With nothing selected, `fl_transpose_selection(interval="up_octave")` → all notes move up an octave (scope "all").
- [ ] `fl_transpose_selection(interval="down_fifth")` → notes move down 7 semitones.
- [ ] `fl_transpose_selection()` (no args) → `{"success": false, "error_code": "INVALID_ARGS"}`.

---

# Sprint 2 Smoke Tests

Manual test cases for the 9 Sprint 2 tools (Tier 2 workflow primitives). All use
the MIDI bridge; same setup as Sprint 1. Deploy the updated
`device_FLStudioMCP.py` and **reload it in FL Studio** (a full restart is the
most reliable way to clear FL's in-memory script cache) before testing.

---

## Transport (MIDI bridge)

### `fl_get_song_position`

- [ ] Stop playback at the start. `fl_get_song_position("bars")` → `{"success": true, "mode": "bars", "bars": 1, "steps": 1, "ticks": 0, "hint": "1:1:0"}` (or FL's equivalent at position zero).
- [ ] Move the playhead a few bars in, call again → `bars`/`steps`/`ticks` reflect the new position and `hint` matches FL's transport hint.
- [ ] `fl_get_song_position("seconds")` → `{"success": true, "mode": "seconds", "seconds": <int>}`.
- [ ] `fl_get_song_position("ms")` and `("absticks")` → return `ms` / `absticks` integers.
- [ ] `fl_get_song_position("nonsense")` → `{"success": false, "error_code": "INVALID_ARGS"}` (no MIDI sent).

---

## General (MIDI bridge)

### `fl_is_project_modified`

- [ ] On a freshly-saved project, `fl_is_project_modified()` → `{"success": true, "modified": false, "changed_flag": 0}`.
- [ ] Make an edit (e.g. `fl_set_tempo(135)`), call again → `modified: true`, `changed_flag` is 1 (or 2 after an autosave).

### `fl_get_undo_history`

- [ ] Make a couple of undoable changes, then `fl_get_undo_history()` → `{"success": true, "position_hint": "<n>/<m>", "current_pos": <int>, "history_length": <int>, "total_count": <int>}`.
- [ ] Call `fl_undo()` once, then `fl_get_undo_history()` → `current_pos` / `position_hint` reflect the moved position.

---

## Patterns (MIDI bridge)

### `fl_list_patterns`

- [ ] On a project with a few patterns, `fl_list_patterns()` → `{"success": true, "count": <int>, "active": <int>, "patterns": [{index, name, color, rgb, length_beats, selected}, ...]}` with indices starting at 1.
- [ ] On a fresh project (no pattern modified yet), the list still includes the active pattern. Note: `count` is FL's count of *modified* patterns (0 on a fresh project); the list iterates 1..max(count, active), so the active pattern always appears.

### `fl_get_current_pattern`

- [ ] Select a pattern in FL, `fl_get_current_pattern()` → `{"success": true, "index": <selected>, "name": "<name>"}`.

### `fl_select_pattern`

- [ ] `fl_select_pattern(2)` → `{"success": true, "index": 2, "name": "..."}`; pattern 2 becomes active in FL.
- [ ] `fl_select_pattern(0)` → `{"success": false, "error_code": "INVALID_ARGS"}` (1-indexed; no MIDI sent).

### `fl_set_pattern_name`

- [ ] `fl_set_pattern_name(1, "Verse")` → `{"success": true, "index": 1, "name": "Verse"}`; the pattern is renamed in FL.
- [ ] `fl_set_pattern_name(1, "")` → name resets to FL's default.

### `fl_set_pattern_color`

- [ ] `fl_set_pattern_color(1, 255, 128, 0)` → `{"success": true, "index": 1, "color": <int>, "rgb": [255, 128, 0]}`; the pattern turns orange in FL.
- [ ] `fl_set_pattern_color(1, 300, 0, 0)` → `{"success": false, "error_code": "INVALID_ARGS"}` (component out of range).

### `fl_get_pattern_length`

- [ ] `fl_get_pattern_length(1)` → `{"success": true, "index": 1, "length_beats": <int>}` matching the pattern's length in beats.

---

## Open questions to verify during smoke testing

- [ ] Confirm `fl_get_tempo` returns the BPM as the first token of the formatted string across FL Studio versions.
- [ ] Confirm `fl_get_project_info.song_length_bars` parses sensibly (the formatted `REC_SongLength` string shape is unconfirmed; `song_length_raw` is included as a fallback).
- [ ] Confirm the `fl_get_time_signature` pre-flight focus + keystroke trigger is reliable when focus starts elsewhere.
