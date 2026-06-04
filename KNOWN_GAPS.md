# Known Gaps

Tools and capabilities that were planned but cannot be implemented against the
FL Studio scripting API, plus capabilities discovered during planning that are
deferred to later sprints. Verified against the local `fl-studio-api-stubs`
package (v37.0.1) installed in `.venv`.

## Dropped in Sprint 1 (verified impossible)

### `fl_set_time_signature`

**Status:** Impossible — no setter in any scripting context.

The project time signature is only exposed through the Piano Roll Scripting
context as `flpianoroll.score.tsnum` and `flpianoroll.score.tsden`. Both are
**read-only** properties (confirmed in `flpianoroll/__score.py`: each is a bare
`@property` with no setter).

Note: the `Marker` class (`flpianoroll/__marker.py`) *does* expose settable
`tsnum`/`tsden`, but those set the time signature of an individual **time
signature marker** in the piano roll, not the project's overall time signature.
The API does not expose reading or placing playlist time signature markers, so
this is not a usable workaround for setting the project time signature.

`fl_get_time_signature` (read) is implemented and ships in Sprint 1.

### `fl_save_project_as(path)`

**Status:** Impossible — no programmatic path argument.

`transport.globalTransport(midi.FPT_SaveNew, 1)` triggers FL Studio's "Save As"
dialog, which requires user interaction. `globalTransport` takes a `command` and
an opaque `value`; there is no parameter for a destination file path. There is
no other API surface for saving to a specified path.

`fl_save_project` (save to the current file via `FPT_Save`) is implemented and
ships in Sprint 1.

## Deferred in Sprint 2

### `fl_set_loop_region(start_bars, end_bars)` / `fl_clear_loop_region()`

**Status:** No clean API — deferred (revisit in Sprint 4, arrangement).

There is no MIDI Controller Scripting function to set the song's loop/time
selection region by bar range. `transport.setLoopMode()` only *toggles* between
pattern and song loop mode (it takes no arguments and sets no region), and
`transport.getLoopMode()` only reads that mode. The `FPT_Loop` (15) and
`FPT_LoopRecord` (113) global-transport commands are likewise toggles, not
region setters.

The closest candidate is `arrangement.liveSelection(time, stop)` plus
`arrangement.liveSelectionStart()`, but these manage the **performance-mode live
selection** (absolute ticks, one endpoint at a time) and are explicitly flagged
"HELP WANTED / ???" in the stubs — not a reliable bars-based loop-region setter.
Deferred to the Sprint 4 arrangement work, where the selection/markers APIs are
tackled as a group.

### `fl_get_undo_history` — step names not available

**Status:** Partially implemented (position only).

`fl_get_undo_history` ships in Sprint 2, but the API exposes only the **position
and counts** within the undo history (`getUndoLevelHint`, `getUndoHistoryLast`,
`getUndoHistoryPos`, `getUndoHistoryCount`). There is no function that returns
the **text/description** of individual undo steps, so the tool cannot return a
named list of history entries — only where you are in the history.

## Dropped/deferred in Sprint 4

### `fl_add_pattern_to_playlist` / `fl_remove_playlist_clip`

**Status:** Impossible — no clip placement API.

The `playlist` module exposes track properties (`trackCount`, `getTrackName`,
`setTrackName`, `getTrackColor`/`setTrackColor`, `muteTrack`, `soloTrack`,
`selectTrack`, etc.) and performance/live-block helpers, but **no function to
add or remove a pattern/audio clip on the playlist timeline**. There is no
`addClip`/`placeClip`/`deleteClip` surface in any module. Playlist track
editing tools ship in Sprint 4; clip placement does not.

### `fl_list_markers` (arrangement)

**Status:** Not reliable — no marker count in the arrangement context.

`arrangement` exposes `getMarkerName(index)`, `jumpToMarker(delta, select)`, and
`addAutoTimeMarker(time, name)`, but there is **no `markerCount`** and no
marker-time getter, so arrangement markers cannot be reliably enumerated
(probing indices is ambiguous because unnamed markers return `""`).
`fl_add_marker` and `fl_jump_to_marker` ship in Sprint 4.

Note: **piano roll** markers *can* be listed — `flpianoroll.score.markerCount`
plus `getMarker(i)` exist — so `fl_get_piano_roll_markers` is provided instead
(piano roll markers are time-signature/scale/pattern-length markers, distinct
from arrangement markers).

### `fl_remove_marker` (arrangement)

**Status:** Impossible — no remove API. The arrangement markers module has no
delete function.

### `fl_clear_selection` (arrangement)

**Status:** No API. The `arrangement` module has selection *getters*
(`selectionStart`/`selectionEnd`) and the live-selection *setter*
(`liveSelection`), but nothing to clear a selection. `fl_set_selection`
(experimental, via `liveSelection`) ships; clearing does not.

## Other hard API limits (from the spec, not attempted)

| Capability | Reality |
| --- | --- |
| Read project title or `.flp` path | No getter exists. `fl_get_project_info` returns `title`/`path` as `None`. |
| Read playlist time signature markers | Not exposed by the API; only the project-level time signature is readable. |
| Load new VST/AU plugins | Not in the API. |
| Create new patterns programmatically | Not in the API. Workaround: scaffold the project with empty patterns. |
| Audio rendering to wav/mp3 | GUI-only, not scriptable. |
| Granular automation curve editing | Limited API support. |

## Bonus Piano Roll Scripting capabilities (deferred, not in Sprint 1)

Discovered during planning. Verified to exist in the stubs but intentionally
left out to keep Sprint 1 focused. Candidates for later sprints.

| Capability | Source | Notes |
| --- | --- | --- |
| `fl_get_snap_scale` | `flpianoroll.score.snap_root_note`, `snap_scale_helper` | Snap-to-scale root + 12-char scale pattern. Sprint 6 (Theory analysis). |
| Granular note access | `flpianoroll.score.getNote(i)` | Extends `fl_get_piano_roll_state`. |
| Piano roll markers | `flpianoroll.score.getMarker(i)` | Sprint 4 (arrangement). |
| Timeline selection | `flpianoroll.score.getTimelineSelection()` | Sprint 4. |
| Selective clear | `flpianoroll.score.clear(all=False)` / `clearNotes` / `clearMarkers` | Refines the existing clear tool. |
