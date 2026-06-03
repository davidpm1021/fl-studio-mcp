"""Pattern management tools for FL Studio.

Operations on existing patterns: listing, selecting, and editing name/color,
plus reading the active pattern and pattern length. All use the JSON+MIDI
bridge (MIDI Controller Scripting context).

Note: FL Studio's API cannot *create* new patterns programmatically, and
patterns are 1-indexed. ``patternCount()`` counts patterns that differ from the
default empty state; these are not guaranteed to be contiguous.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_patterns_tools(mcp: FastMCP) -> None:
    """Register pattern management tools with the MCP server."""
    from fl_studio_mcp.utils.connection import get_connection

    @mcp.tool()
    def fl_list_patterns() -> dict:
        """List the project's patterns with name, color, length, and selection.

        Returns patterns by 1-based index. ``length_beats`` is the pattern
        length in beats. ``color`` is an FL Studio color int (also given as
        ``rgb``). ``count`` is FL Studio's count of patterns modified from the
        default empty state; ``active`` is the currently active pattern index.

        The list covers indices 1..max(count, active), so the active pattern
        always appears even on a fresh project. Patterns modified at
        non-contiguous indices beyond that range may not appear (an FL Studio
        API limitation).
        """
        conn = get_connection()
        try:
            result = conn.send_command("patterns.list")
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
            "count": result.get("count"),
            "active": result.get("active"),
            "patterns": result.get("patterns", []),
        }

    @mcp.tool()
    def fl_get_current_pattern() -> dict:
        """Get the currently active pattern (index and name).

        The active pattern is where notes and step sequencing are applied.
        """
        conn = get_connection()
        try:
            result = conn.send_command("patterns.getCurrent")
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
            "index": result.get("index"),
            "name": result.get("name"),
        }

    @mcp.tool()
    def fl_select_pattern(index: int) -> dict:
        """Select (and jump to) the pattern at the given 1-based index.

        Warning: FL Studio will *create* a pattern if one does not already exist
        at ``index``. Avoid selecting unusually high indices.

        Args:
            index: 1-based pattern index.
        """
        if index < 1:
            return {
                "success": False,
                "error": "index must be >= 1 (patterns are 1-indexed)",
                "error_code": "INVALID_ARGS",
            }

        conn = get_connection()
        try:
            result = conn.send_command("patterns.select", {"index": index})
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
            "index": result.get("index"),
            "name": result.get("name"),
        }

    @mcp.tool()
    def fl_set_pattern_name(index: int, name: str) -> dict:
        """Rename the pattern at the given 1-based index.

        Args:
            index: 1-based pattern index.
            name: New name. An empty string resets the pattern to its default
                  name.
        """
        if index < 1:
            return {
                "success": False,
                "error": "index must be >= 1 (patterns are 1-indexed)",
                "error_code": "INVALID_ARGS",
            }

        conn = get_connection()
        try:
            result = conn.send_command(
                "patterns.setName", {"index": index, "name": name}
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
            "index": result.get("index"),
            "name": result.get("name"),
        }

    @mcp.tool()
    def fl_set_pattern_color(index: int, red: int, green: int, blue: int) -> dict:
        """Set the color of the pattern at the given 1-based index.

        Args:
            index: 1-based pattern index.
            red: Red component, 0-255.
            green: Green component, 0-255.
            blue: Blue component, 0-255.
        """
        if index < 1:
            return {
                "success": False,
                "error": "index must be >= 1 (patterns are 1-indexed)",
                "error_code": "INVALID_ARGS",
            }
        for name, val in (("red", red), ("green", green), ("blue", blue)):
            if not 0 <= val <= 255:
                return {
                    "success": False,
                    "error": f"{name} must be between 0 and 255",
                    "error_code": "INVALID_ARGS",
                }

        conn = get_connection()
        try:
            result = conn.send_command(
                "patterns.setColor",
                {"index": index, "red": red, "green": green, "blue": blue},
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
            "index": result.get("index"),
            "color": result.get("color"),
            "rgb": result.get("rgb"),
        }

    @mcp.tool()
    def fl_get_pattern_length(index: int) -> dict:
        """Get the length (in beats) of the pattern at the given 1-based index.

        Args:
            index: 1-based pattern index.
        """
        if index < 1:
            return {
                "success": False,
                "error": "index must be >= 1 (patterns are 1-indexed)",
                "error_code": "INVALID_ARGS",
            }

        conn = get_connection()
        try:
            result = conn.send_command("patterns.getLength", {"index": index})
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
            "index": result.get("index"),
            "length_beats": result.get("length_beats"),
        }
