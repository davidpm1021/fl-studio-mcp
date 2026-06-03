"""Playlist tools for FL Studio.

Read and edit playlist track properties (name, color, mute, solo, selection)
via the JSON+MIDI bridge. Playlist tracks are 1-indexed and ``trackCount``
includes empty tracks.

Note: FL Studio's API has no function to place or remove pattern clips in the
playlist, so those operations are not provided (see KNOWN_GAPS).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_playlist_tools(mcp: FastMCP) -> None:
    """Register playlist tools with the MCP server."""
    from fl_studio_mcp.utils.connection import get_connection

    def _err(result: dict) -> dict:
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "error_code": "API_ERROR",
        }

    @mcp.tool()
    def fl_get_playlist_state() -> dict:
        """List playlist tracks with name, color, mute, solo, and selection.

        Tracks are 1-indexed; the list includes empty tracks (FL Studio always
        reports a fixed number of playlist tracks).
        """
        conn = get_connection()
        try:
            result = conn.send_command("playlist.getState")
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _err(result)
        return {
            "success": True,
            "track_count": result.get("track_count"),
            "tracks": result.get("tracks", []),
        }

    @mcp.tool()
    def fl_set_playlist_track_name(index: int, name: str) -> dict:
        """Rename a playlist track (1-indexed).

        Args:
            index: 1-based track index.
            name: New name. An empty string resets it to "Track n".
        """
        if index < 1:
            return {
                "success": False,
                "error": "index must be >= 1 (playlist tracks are 1-indexed)",
                "error_code": "INVALID_ARGS",
            }
        conn = get_connection()
        try:
            result = conn.send_command(
                "playlist.setTrackName", {"index": index, "name": name}
            )
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _err(result)
        return {
            "success": True,
            "index": result.get("index"),
            "name": result.get("name"),
        }

    @mcp.tool()
    def fl_set_playlist_track_color(
        index: int, red: int, green: int, blue: int
    ) -> dict:
        """Set a playlist track's color (1-indexed).

        Args:
            index: 1-based track index.
            red: Red component, 0-255.
            green: Green component, 0-255.
            blue: Blue component, 0-255.
        """
        if index < 1:
            return {
                "success": False,
                "error": "index must be >= 1 (playlist tracks are 1-indexed)",
                "error_code": "INVALID_ARGS",
            }
        for cname, val in (("red", red), ("green", green), ("blue", blue)):
            if not 0 <= val <= 255:
                return {
                    "success": False,
                    "error": f"{cname} must be between 0 and 255",
                    "error_code": "INVALID_ARGS",
                }
        conn = get_connection()
        try:
            result = conn.send_command(
                "playlist.setTrackColor",
                {"index": index, "red": red, "green": green, "blue": blue},
            )
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _err(result)
        return {
            "success": True,
            "index": result.get("index"),
            "color": result.get("color"),
            "rgb": result.get("rgb"),
        }

    @mcp.tool()
    def fl_mute_playlist_track(index: int, value: int = -1) -> dict:
        """Mute, unmute, or toggle a playlist track (1-indexed).

        Args:
            index: 1-based track index.
            value: 1 = mute, 0 = unmute, -1 = toggle (default).
        """
        if index < 1:
            return {
                "success": False,
                "error": "index must be >= 1 (playlist tracks are 1-indexed)",
                "error_code": "INVALID_ARGS",
            }
        if value not in (-1, 0, 1):
            return {
                "success": False,
                "error": "value must be -1 (toggle), 0 (unmute), or 1 (mute)",
                "error_code": "INVALID_ARGS",
            }
        conn = get_connection()
        try:
            result = conn.send_command(
                "playlist.muteTrack", {"index": index, "value": value}
            )
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _err(result)
        return {
            "success": True,
            "index": result.get("index"),
            "muted": result.get("muted"),
        }

    @mcp.tool()
    def fl_solo_playlist_track(index: int, value: int = -1) -> dict:
        """Solo, unsolo, or toggle a playlist track (1-indexed).

        Args:
            index: 1-based track index.
            value: 1 = solo, 0 = unsolo, -1 = toggle (default).
        """
        if index < 1:
            return {
                "success": False,
                "error": "index must be >= 1 (playlist tracks are 1-indexed)",
                "error_code": "INVALID_ARGS",
            }
        if value not in (-1, 0, 1):
            return {
                "success": False,
                "error": "value must be -1 (toggle), 0 (unsolo), or 1 (solo)",
                "error_code": "INVALID_ARGS",
            }
        conn = get_connection()
        try:
            result = conn.send_command(
                "playlist.soloTrack", {"index": index, "value": value}
            )
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _err(result)
        return {
            "success": True,
            "index": result.get("index"),
            "solo": result.get("solo"),
        }

    @mcp.tool()
    def fl_select_playlist_track(index: int, exclusive: bool = False) -> dict:
        """Select a playlist track (1-indexed).

        Args:
            index: 1-based track index.
            exclusive: If True, deselect all other tracks first so only this
                       track ends up selected. If False, toggles this track's
                       selection.
        """
        if index < 1:
            return {
                "success": False,
                "error": "index must be >= 1 (playlist tracks are 1-indexed)",
                "error_code": "INVALID_ARGS",
            }
        conn = get_connection()
        try:
            result = conn.send_command(
                "playlist.selectTrack", {"index": index, "exclusive": exclusive}
            )
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _err(result)
        return {
            "success": True,
            "index": result.get("index"),
            "selected": result.get("selected"),
        }
