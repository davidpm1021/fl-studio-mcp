"""General project tools for FL Studio.

Covers undo/redo, saving, composite project info (MIDI Controller Scripting
context), and time signature reads (Piano Roll Scripting context).

Most tools here use the JSON+MIDI bridge. ``fl_get_time_signature`` is the one
exception: the project time signature is only exposed via ``flpianoroll.score``
inside the Piano Roll Scripting context, so it uses the JSON+keystroke bridge
(see ``scripts/ComposeWithLLM.pyscript``).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_general_tools(mcp: FastMCP) -> None:
    """Register general project tools with the MCP server."""
    from fl_studio_mcp.utils.connection import get_connection
    from fl_studio_mcp.utils.fl_trigger import get_trigger, trigger_fl_studio

    # Piano roll bridge helpers (reused for the time signature read).
    from fl_studio_mcp.tools.piano_roll import (
        _get_response_file,
        _write_request,
    )

    @mcp.tool()
    def fl_undo() -> dict:
        """Undo the last action in FL Studio.

        Note: FL Studio's ``undoUp()`` moves backwards through the undo history
        (what users think of as "undo"), despite the "up" in the name.

        Returns a position hint like "3/10" (position/total in undo history).
        """
        conn = get_connection()
        try:
            result = conn.send_command("general.undo")
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}

        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "error_code": "API_ERROR",
            }

        return {"success": True, "position_hint": result.get("position_hint")}

    @mcp.tool()
    def fl_redo() -> dict:
        """Redo the next action in FL Studio.

        Uses ``undoDown()`` to move forward through the undo history.

        Returns a position hint like "4/10" (position/total in undo history).
        """
        conn = get_connection()
        try:
            result = conn.send_command("general.redo")
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}

        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "error_code": "API_ERROR",
            }

        return {"success": True, "position_hint": result.get("position_hint")}

    @mcp.tool()
    def fl_save_project() -> dict:
        """Save the current FL Studio project to its existing file.

        Caveat: if the project has never been saved, FL Studio may pop a Save As
        dialog requiring user interaction. This cannot be detected from the API.
        """
        conn = get_connection()
        try:
            result = conn.send_command("general.save")
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}

        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "error_code": "API_ERROR",
            }

        return {"success": True}

    @mcp.tool()
    def fl_get_project_info() -> dict:
        """Get composite information about the current FL Studio project.

        Combines tempo, song length, FL Studio version, API version, modified
        flag, and PPQ. The project title and .flp path are not exposed by any
        API function and are always returned as None.
        """
        conn = get_connection()
        try:
            result = conn.send_command("general.getProjectInfo")
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
            "tempo": result.get("tempo"),
            "song_length_bars": result.get("song_length_bars"),
            "fl_studio_version": result.get("fl_studio_version"),
            "api_version": result.get("api_version"),
            "modified": result.get("modified"),
            "ppq": result.get("ppq"),
            "title": None,
            "path": None,
        }

    @mcp.tool()
    def fl_get_time_signature() -> dict:
        """Get the project's overall time signature (numerator/denominator).

        Uses the Piano Roll Scripting context: the piano roll must be open in
        FL Studio. This tool pre-flights by focusing the piano roll window, then
        triggers ``ComposeWithLLM.pyscript`` to read ``flpianoroll.score.tsnum``
        and ``tsden``.

        Returns the project-level time signature, NOT time signature markers in
        the playlist (those are not exposed by the API).
        """
        # Pre-flight: try to focus the piano roll via the MIDI bridge so the
        # Piano Roll Scripting context has something to read. Non-fatal if the
        # MIDI bridge isn't connected; the keystroke trigger may still work.
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

        # Clear any stale response before triggering.
        response_file = _get_response_file()
        if response_file.exists():
            try:
                response_file.unlink()
            except OSError:
                pass

        _write_request({"action": "get_time_signature"})
        trigger_fl_studio()  # blocks ~2s to let FL Studio process

        if not response_file.exists():
            return {
                "success": False,
                "error": "No response from the piano roll script. Make sure the "
                "piano roll is open in FL Studio.",
                "error_code": "FL_PIANO_ROLL_CLOSED",
            }

        try:
            with open(response_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return {
                "success": False,
                "error": f"Could not read piano roll response: {e}",
                "error_code": "API_ERROR",
            }

        if "numerator" in data and "denominator" in data:
            return {
                "success": True,
                "numerator": data["numerator"],
                "denominator": data["denominator"],
            }

        return {
            "success": False,
            "error": "Time signature not present in response. The piano roll may "
            "be closed or no channel is selected.",
            "error_code": "FL_PIANO_ROLL_CLOSED",
        }
