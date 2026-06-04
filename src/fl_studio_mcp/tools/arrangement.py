"""Arrangement tools for FL Studio.

Markers and timeline selection in the arrangement (song) view. Most tools use
the JSON+MIDI bridge (MIDI Controller Scripting context). The piano-roll marker
and timeline-selection reads use the Piano Roll Scripting bridge instead,
because that data is only exposed through ``flpianoroll.score``.

Bars are 1-indexed (bar 1 = start). ``beats_per_bar`` defaults to 4 (4/4);
tick conversion uses the project PPQ, resolved on the FL Studio side.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_arrangement_tools(mcp: FastMCP) -> None:
    """Register arrangement tools with the MCP server."""
    from fl_studio_mcp.tools.piano_roll import (
        _get_response_file,
        _write_request,
    )
    from fl_studio_mcp.utils.connection import get_connection
    from fl_studio_mcp.utils.fl_trigger import get_trigger, trigger_fl_studio

    @mcp.tool()
    def fl_add_marker(
        position_bars: float,
        name: str = "",
        beats_per_bar: float = 4.0,
    ) -> dict:
        """Add a time marker to the arrangement at the given bar.

        Args:
            position_bars: Bar to place the marker at (1 = start of song).
            name: Marker name (empty for an unnamed marker).
            beats_per_bar: Quarter notes per bar (4 for 4/4, 3 for 3/4).
        """
        if position_bars < 1:
            return {
                "success": False,
                "error": "position_bars is 1-indexed and must be >= 1",
                "error_code": "INVALID_ARGS",
            }
        conn = get_connection()
        try:
            result = conn.send_command(
                "arrangement.addMarker",
                {
                    "position_bars": position_bars,
                    "name": name,
                    "beats_per_bar": beats_per_bar,
                },
            )
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}

        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "error_code": "API_ERROR",
            }

        return {
            "success": True,
            "name": result.get("name"),
            "position_bars": position_bars,
            "time_ticks": result.get("time_ticks"),
        }

    @mcp.tool()
    def fl_get_selection(beats_per_bar: float = 4.0) -> dict:
        """Get the current timeline selection in the arrangement.

        Returns the selection start/end in ticks and as B:S:T hint strings, plus
        whether a non-empty selection exists. ``beats_per_bar`` is used only to
        compute the convenience ``start_bars``/``end_bars`` values.

        Args:
            beats_per_bar: Quarter notes per bar (for the bar conversion).
        """
        conn = get_connection()
        try:
            result = conn.send_command(
                "arrangement.getSelection", {"beats_per_bar": beats_per_bar}
            )
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}

        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "error_code": "API_ERROR",
            }

        has_selection = result.get("has_selection")
        out = {
            "success": True,
            "has_selection": has_selection,
            "start_ticks": result.get("start_ticks"),
            "end_ticks": result.get("end_ticks"),
        }
        # When nothing is selected FL reports a start of -1; the derived bars and
        # B:S:T hints are meaningless in that case, so omit them.
        if has_selection:
            out["start_bars"] = result.get("start_bars")
            out["end_bars"] = result.get("end_bars")
            out["start_hint"] = result.get("start_hint")
            out["end_hint"] = result.get("end_hint")
        else:
            out["start_bars"] = None
            out["end_bars"] = None
            out["start_hint"] = None
            out["end_hint"] = None
        return out

    @mcp.tool()
    def fl_set_selection(
        start_bars: float,
        end_bars: float,
        beats_per_bar: float = 4.0,
    ) -> dict:
        """Set the arrangement timeline selection to a bar range.

        Note: this uses FL Studio's live-selection API, which is not fully
        documented; verify the result in FL Studio. Bars are 1-indexed.

        Args:
            start_bars: Selection start bar (1 = start of song).
            end_bars: Selection end bar (must be > start_bars).
            beats_per_bar: Quarter notes per bar.
        """
        if start_bars < 1:
            return {
                "success": False,
                "error": "start_bars is 1-indexed and must be >= 1",
                "error_code": "INVALID_ARGS",
            }
        if end_bars <= start_bars:
            return {
                "success": False,
                "error": "end_bars must be greater than start_bars",
                "error_code": "INVALID_ARGS",
            }
        conn = get_connection()
        try:
            result = conn.send_command(
                "arrangement.setSelection",
                {
                    "start_bars": start_bars,
                    "end_bars": end_bars,
                    "beats_per_bar": beats_per_bar,
                },
            )
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}

        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "error_code": "API_ERROR",
            }

        return {
            "success": True,
            "start_ticks": result.get("start_ticks"),
            "end_ticks": result.get("end_ticks"),
        }

    @mcp.tool()
    def fl_jump_to_marker(delta: int = 1, select: bool = False) -> dict:
        """Jump to a nearby marker, relative to the current one.

        Args:
            delta: Relative marker index (1 = next, -1 = previous).
            select: Whether to select the region up to the marker.
        """
        conn = get_connection()
        try:
            result = conn.send_command(
                "arrangement.jumpToMarker", {"delta": delta, "select": select}
            )
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}

        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "error_code": "API_ERROR",
            }

        return {"success": True, "delta": delta, "select": select}

    # --- Piano Roll Scripting reads (markers + timeline selection) ----------

    def _piano_roll_request(action: str) -> dict:
        """Run a Piano Roll Scripting request and return the parsed response."""
        try:
            get_connection().send_command(
                "ui.focusWindow", {"window": "piano_roll"}, timeout=2.0
            )
        except Exception:
            pass

        trigger = get_trigger()
        if not trigger.is_supported:
            return {
                "success": False,
                "error": f"Auto-trigger not supported on {trigger.platform}; "
                f"cannot reach the Piano Roll Scripting context.",
                "error_code": "NOT_SUPPORTED",
            }

        response_file = _get_response_file()
        if response_file.exists():
            try:
                response_file.unlink()
            except OSError:
                pass

        _write_request({"action": action})
        trigger_fl_studio()

        if not response_file.exists():
            return {
                "success": False,
                "error": "No response from the piano roll script. Make sure the "
                "piano roll is open in FL Studio.",
                "error_code": "FL_PIANO_ROLL_CLOSED",
            }
        try:
            with open(response_file) as f:
                return {"success": True, "data": json.load(f)}
        except (json.JSONDecodeError, OSError) as e:
            return {
                "success": False,
                "error": f"Could not read piano roll response: {e}",
                "error_code": "API_ERROR",
            }

    @mcp.tool()
    def fl_get_piano_roll_markers() -> dict:
        """List markers in the currently open piano roll.

        Uses the Piano Roll Scripting context (piano roll must be open). Returns
        each marker's time (ticks and quarter notes), name, and mode, plus
        time-signature or scale data for those marker types. This reads piano
        roll markers (time signature, scale, pattern length), which are distinct
        from arrangement/playlist markers.
        """
        res = _piano_roll_request("get_markers")
        if not res.get("success"):
            return res
        data = res["data"]
        if "markers" not in data:
            return {
                "success": False,
                "error": "No marker data in response. The piano roll may be "
                "closed.",
                "error_code": "FL_PIANO_ROLL_CLOSED",
            }
        return {
            "success": True,
            "count": data.get("markerCount"),
            "markers": data["markers"],
        }

    @mcp.tool()
    def fl_get_timeline_selection() -> dict:
        """Get the selected time range in the currently open piano roll.

        Uses the Piano Roll Scripting context (piano roll must be open). Returns
        the selection start/end in ticks and quarter notes; ``has_selection`` is
        False when no range is selected (FL returns a start of -1).
        """
        res = _piano_roll_request("get_timeline_selection")
        if not res.get("success"):
            return res
        data = res["data"]
        if "selection_start_ticks" not in data:
            return {
                "success": False,
                "error": "No timeline selection data in response. The piano "
                "roll may be closed.",
                "error_code": "FL_PIANO_ROLL_CLOSED",
            }
        start = data.get("selection_start_ticks")
        end = data.get("selection_end_ticks")
        # FL signals "no selection" inconsistently (start -1, or end -1 with
        # start 0), so require both endpoints non-negative and end > start.
        has_selection = (
            start is not None and end is not None and start >= 0 and end > start
        )
        return {
            "success": True,
            "has_selection": has_selection,
            "start_ticks": start,
            "end_ticks": end,
            "start_beats": data.get("selection_start_beats") if has_selection else None,
            "end_beats": data.get("selection_end_beats") if has_selection else None,
        }
