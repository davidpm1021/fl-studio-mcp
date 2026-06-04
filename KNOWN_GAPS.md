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
