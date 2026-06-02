"""UI / window management tools for FL Studio.

Uses the MIDI Controller Scripting context to focus FL Studio windows and read
which windows are focused/visible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

# Valid window names accepted by the tools below. Maps to FL Studio's
# midi.widMixer/widChannelRack/widPlaylist/widPianoRoll/widBrowser indices,
# which are resolved on the FL Studio side.
VALID_WINDOWS = ("mixer", "channel_rack", "playlist", "piano_roll", "browser")


def register_ui_tools(mcp: FastMCP) -> None:
    """Register UI / window tools with the MCP server."""
    from fl_studio_mcp.utils.connection import get_connection

    @mcp.tool()
    def fl_focus_window(window: str) -> dict:
        """Focus an FL Studio window.

        Args:
            window: One of "mixer", "channel_rack", "playlist", "piano_roll",
                    "browser".
        """
        if window not in VALID_WINDOWS:
            return {
                "success": False,
                "error": f"Invalid window '{window}'. Valid: {', '.join(VALID_WINDOWS)}",
                "error_code": "INVALID_ARGS",
            }

        conn = get_connection()
        try:
            result = conn.send_command("ui.focusWindow", {"window": window})
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}

        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "error_code": "API_ERROR",
            }

        return {"success": True, "focused_window": window}

    @mcp.tool()
    def fl_get_window_state() -> dict:
        """Get which FL Studio windows are focused and visible.

        Returns the focused window name, the list of visible windows, and the
        caption of the currently focused form.
        """
        conn = get_connection()
        try:
            result = conn.send_command("ui.getWindowState")
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
            "focused": result.get("focused"),
            "visible": result.get("visible", []),
            "focused_caption": result.get("focused_caption", ""),
        }
