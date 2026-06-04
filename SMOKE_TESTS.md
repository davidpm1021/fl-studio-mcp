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

# Sprint 5 Smoke Tests

Manual test cases for the 6 Sprint 5 tools (Theory T2 composition). All placement
tools use the Piano Roll Scripting bridge (piano roll open + ComposeWithLLM
armed). The pyscript changed this sprint (new `humanize`/`quantize` actions), so
re-run ComposeWithLLM once before testing those two. The device script did NOT
change this sprint. Pure logic is covered by `tests/test_theory.py` (97 unit
tests).

---

## Pure helper

### `fl_get_diatonic_chords`

- [ ] `fl_get_diatonic_chords("C", "major")` → 7 chords: I/ii/iii/IV/V/vi/vii° with correct qualities (maj, min, min, maj, maj, min, dim).
- [ ] `fl_get_diatonic_chords("C", "major", sevenths=True)` → Imaj7, ii7, iii7, IVmaj7, V7, vi7, viiø7.
- [ ] `fl_get_diatonic_chords("C", "bogus")` → `INVALID_ARGS`.

## Placement (piano roll open + armed)

### `fl_place_progression_voiced`

- [ ] `fl_place_progression_voiced(["I","IV","V","I"], key="C")` → four chords placed with smooth voicings (later chords stay close to the previous; pitch classes preserved). Read back with `fl_get_piano_roll_state` and confirm voices move minimally vs close position.

### `fl_harmonize_melody`

- [ ] `fl_harmonize_melody([{"midi":72,"time":0,"duration":1},{"midi":74,"time":1,"duration":1},{"midi":76,"time":2,"duration":1}], key="C")` → a chord under each melody note, each chord containing the melody note's pitch class.

### `fl_generate_bassline`

- [ ] `fl_generate_bassline(["I","IV","V","I"], key="C", style="root")` → one low root note per chord.
- [ ] `style="walking"` → four notes per chord; `style="octaves"`/`"fifths"` → two notes per chord.
- [ ] `style="bogus"` → `INVALID_ARGS`.

### `fl_humanize_notes` (re-arm pyscript first)

- [ ] Place a chord/notes, `fl_humanize_notes(timing_amount=0.05, velocity_amount=0.1)` → note times/velocities shift slightly (read back; times no longer perfectly aligned).
- [ ] `timing_amount=-1` → `INVALID_ARGS`.

### `fl_quantize_notes` (re-arm pyscript first)

- [ ] Humanize some notes, then `fl_quantize_notes(grid=0.25, strength=1.0)` → note start times snap back to the 1/16 grid.
- [ ] `strength=0.5` → notes move halfway to the grid.
- [ ] `grid=0` → `INVALID_ARGS`; `strength=2` → `INVALID_ARGS`.

---

# Sprint 4 Smoke Tests

Manual test cases for the 12 Sprint 4 tools (Tier 3 arrangement). Most use the
MIDI bridge; `fl_get_piano_roll_markers` and `fl_get_timeline_selection` use the
Piano Roll Scripting bridge (piano roll open + ComposeWithLLM armed). Both FL
scripts changed this sprint — redeploy and reload (restart FL for the device
script; re-run ComposeWithLLM once for the pyscript).

---

## Arrangement (MIDI bridge)

### `fl_add_marker`

- [ ] `fl_add_marker(1, "Intro")` → `{"success": true, "name": "Intro", "time_ticks": 0}`; an "Intro" marker appears at bar 1 in the playlist.
- [ ] `fl_add_marker(5, "Chorus")` → marker at bar 5 (time_ticks = 4 * beats_per_bar * PPQ).
- [ ] `fl_add_marker(0, "x")` → `{"success": false, "error_code": "INVALID_ARGS"}`.

### `fl_jump_to_marker`

- [ ] With a couple of markers placed, `fl_jump_to_marker(1)` then `fl_jump_to_marker(-1)` → playhead moves between markers.

### `fl_get_selection`

- [ ] Make a timeline selection in the playlist, `fl_get_selection()` → `has_selection: true` with start/end ticks, bars, and B:S:T hints.
- [ ] With no selection, `has_selection` is false.

### `fl_set_selection` (experimental)

- [ ] `fl_set_selection(1, 5)` → returns start/end ticks; verify in FL whether the timeline selection updates (this uses the live-selection API; behavior to be confirmed).
- [ ] `fl_set_selection(5, 2)` → `{"success": false, "error_code": "INVALID_ARGS"}` (end <= start).

### `fl_get_piano_roll_markers` (Piano Roll Scripting)

- [ ] With a piano roll open that has a time-signature or scale marker, `fl_get_piano_roll_markers()` → `{"success": true, "count": n, "markers": [{index, name, time_ticks, time, mode, ...}]}`; time-sig markers include tsnum/tsden, scale markers include scale_root/scale_helper.
- [ ] Empty piano roll → `count: 0, markers: []`.

### `fl_get_timeline_selection` (Piano Roll Scripting)

- [ ] Select a time range in the piano roll, `fl_get_timeline_selection()` → `has_selection: true` with start/end ticks and beats.
- [ ] No selection → `has_selection: false` (FL returns start -1).

---

## Playlist (MIDI bridge)

### `fl_get_playlist_state`

- [ ] `fl_get_playlist_state()` → `{"success": true, "track_count": n, "tracks": [{index, name, color, rgb, muted, solo, selected}, ...]}` with indices starting at 1.

### `fl_set_playlist_track_name`

- [ ] `fl_set_playlist_track_name(1, "Drums")` → `{"success": true, "index": 1, "name": "Drums"}`; track 1 renamed in FL.
- [ ] `fl_set_playlist_track_name(0, "x")` → `INVALID_ARGS`.

### `fl_set_playlist_track_color`

- [ ] `fl_set_playlist_track_color(1, 255, 0, 0)` → track 1 turns red; returns color + rgb.
- [ ] component > 255 → `INVALID_ARGS`.

### `fl_mute_playlist_track` / `fl_solo_playlist_track`

- [ ] `fl_mute_playlist_track(1, 1)` → muted true; `fl_mute_playlist_track(1, 0)` → muted false; `(1, -1)` toggles.
- [ ] `fl_solo_playlist_track(1, 1)` → solo true; `(1, 0)` clears.

### `fl_select_playlist_track`

- [ ] `fl_select_playlist_track(2, exclusive=True)` → only track 2 selected (others deselected).
- [ ] `fl_select_playlist_track(3)` (non-exclusive) → toggles track 3 selection.

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
