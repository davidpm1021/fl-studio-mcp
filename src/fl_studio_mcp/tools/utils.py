"""Utility tools for FL Studio.

Small conversions and version/PPQ queries. The note-name and bars/seconds
conversions are pure (the bars/seconds ones need the current tempo, which is
read from FL when not supplied). Version and PPQ reuse the existing
``general.getProjectInfo`` MIDI-bridge command rather than adding new handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_utils_tools(mcp: FastMCP) -> None:
    """Register utility tools with the MCP server."""
    from fl_studio_mcp.tools.theory import (
        midi_to_note_name,
        note_name_to_midi,
    )
    from fl_studio_mcp.utils.connection import get_connection

    def _project_info() -> dict:
        return get_connection().send_command("general.getProjectInfo")

    def _api_error(info: dict) -> dict:
        return {
            "success": False,
            "error": info.get("error", "Unknown error"),
            "error_code": "API_ERROR",
        }

    @mcp.tool()
    def fl_note_name_to_midi(name: str) -> dict:
        """Convert a note name (e.g. "C4", "F#3", "Bb5") to a MIDI number.

        C4 = 60 (middle C). If no octave is given, octave 4 is assumed.
        """
        try:
            midi = note_name_to_midi(name)
        except ValueError as e:
            return {"success": False, "error": str(e), "error_code": "INVALID_ARGS"}
        return {"success": True, "name": name, "midi": midi}

    @mcp.tool()
    def fl_midi_to_note_name(midi: int) -> dict:
        """Convert a MIDI note number to a note name (C4 = 60)."""
        if not 0 <= midi <= 127:
            return {
                "success": False,
                "error": "midi must be between 0 and 127",
                "error_code": "INVALID_ARGS",
            }
        return {"success": True, "midi": midi, "name": midi_to_note_name(midi)}

    @mcp.tool()
    def fl_bars_to_seconds(
        bars: float, beats_per_bar: float = 4.0, bpm: float | None = None
    ) -> dict:
        """Convert a number of bars to seconds at a given tempo.

        Args:
            bars: Number of bars.
            beats_per_bar: Quarter notes per bar (4 for 4/4).
            bpm: Tempo. If omitted, the current project tempo is used.
        """
        if bpm is None:
            try:
                bpm = _project_info().get("tempo")
            except RuntimeError as e:
                return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
            if not bpm:
                return {
                    "success": False,
                    "error": "could not read project tempo; pass bpm explicitly",
                    "error_code": "API_ERROR",
                }
        if bpm <= 0:
            return {"success": False, "error": "bpm must be > 0", "error_code": "INVALID_ARGS"}
        seconds = bars * beats_per_bar * 60.0 / bpm
        return {"success": True, "bars": bars, "bpm": bpm, "seconds": seconds}

    @mcp.tool()
    def fl_seconds_to_bars(
        seconds: float, beats_per_bar: float = 4.0, bpm: float | None = None
    ) -> dict:
        """Convert seconds to a number of bars at a given tempo.

        Args:
            seconds: Duration in seconds.
            beats_per_bar: Quarter notes per bar (4 for 4/4).
            bpm: Tempo. If omitted, the current project tempo is used.
        """
        if bpm is None:
            try:
                bpm = _project_info().get("tempo")
            except RuntimeError as e:
                return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
            if not bpm:
                return {
                    "success": False,
                    "error": "could not read project tempo; pass bpm explicitly",
                    "error_code": "API_ERROR",
                }
        if bpm <= 0:
            return {"success": False, "error": "bpm must be > 0", "error_code": "INVALID_ARGS"}
        bars = seconds * bpm / 60.0 / beats_per_bar
        return {"success": True, "seconds": seconds, "bpm": bpm, "bars": bars}

    @mcp.tool()
    def fl_get_ppq() -> dict:
        """Get the project's PPQ (pulses/ticks per quarter note)."""
        try:
            info = _project_info()
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not info.get("success", False):
            return _api_error(info)
        return {"success": True, "ppq": info.get("ppq")}

    @mcp.tool()
    def fl_get_fl_version() -> dict:
        """Get the FL Studio version string (e.g. "21.0.3")."""
        try:
            info = _project_info()
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not info.get("success", False):
            return _api_error(info)
        return {"success": True, "fl_studio_version": info.get("fl_studio_version")}

    @mcp.tool()
    def fl_get_api_version() -> dict:
        """Get the FL Studio MIDI scripting API version (integer)."""
        try:
            info = _project_info()
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not info.get("success", False):
            return _api_error(info)
        return {"success": True, "api_version": info.get("api_version")}
