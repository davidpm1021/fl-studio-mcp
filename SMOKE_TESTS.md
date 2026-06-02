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

## Open questions to verify during smoke testing

- [ ] Confirm `fl_get_tempo` returns the BPM as the first token of the formatted string across FL Studio versions.
- [ ] Confirm `fl_get_project_info.song_length_bars` parses sensibly (the formatted `REC_SongLength` string shape is unconfirmed; `song_length_raw` is included as a fallback).
- [ ] Confirm the `fl_get_time_signature` pre-flight focus + keystroke trigger is reliable when focus starts elsewhere.
