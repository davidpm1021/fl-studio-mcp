"""Mixer control tools for FL Studio."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_mixer_tools(mcp: FastMCP) -> None:
    """Register mixer control tools with the MCP server."""
    from fl_studio_mcp.utils.connection import get_connection

    @mcp.tool()
    def fl_get_mixer_track_count() -> int:
        """Get the total number of mixer tracks available.

        FL Studio typically has 125 mixer tracks (0-124), where track 0 is the Master.
        """
        conn = get_connection()
        result = conn.send_command("mixer.getTrackCount")

        if not result.get("success", False) and "error" in result:
            return -1  # Return -1 to indicate error

        return result.get("count", 0)

    @mcp.tool()
    def fl_get_mixer_track_info(track: int) -> dict:
        """Get detailed information about a specific mixer track.

        Args:
            track: Mixer track index (0 = Master, 1-124 = insert tracks)
        """
        conn = get_connection()
        result = conn.send_command("mixer.getTrackInfo", {"track": track})

        if not result.get("success", False) and "error" in result:
            return {"error": result["error"]}

        return {
            "index": result.get("index", track),
            "name": result.get("name", ""),
            "volume": result.get("volume", 0),
            "volume_db": result.get("volume_db", 0),
            "pan": result.get("pan", 0),
            "stereo_separation": result.get("stereo_separation", 0),
            "is_muted": result.get("is_muted", False),
            "is_solo": result.get("is_solo", False),
            "is_armed": result.get("is_armed", False),
            "color": result.get("color", "0x0"),
        }

    @mcp.tool()
    def fl_get_all_mixer_tracks(include_empty: bool = False) -> list[dict]:
        """Get information about all mixer tracks.

        Args:
            include_empty: If False, only returns tracks with non-default names.
                          If True, returns all 125 tracks.
        """
        conn = get_connection()
        result = conn.send_command("mixer.getAllTracks", {"include_empty": include_empty})

        if not result.get("success", False) and "error" in result:
            return [{"error": result["error"]}]

        return result.get("tracks", [])

    @mcp.tool()
    def fl_set_track_volume(track: int, volume: float) -> str:
        """Set the volume of a mixer track.

        Args:
            track: Mixer track index (0 = Master)
            volume: Volume level from 0.0 (silence) to 1.0 (0dB).
                   Default FL Studio volume is 0.8 (~-5.2dB).
                   Values above 1.0 may cause clipping.
        """
        if not 0.0 <= volume <= 1.25:
            return "Error: Volume should be between 0.0 and 1.25"

        conn = get_connection()
        result = conn.send_command("mixer.setTrackVolume", {
            "track": track,
            "volume": volume,
        })

        if not result.get("success", False) and "error" in result:
            return f"Error: {result['error']}"

        new_vol = result.get("volume", 0)
        new_vol_db = result.get("volume_db", 0)
        return f"Track {track} volume set to {new_vol:.3f} ({new_vol_db:.1f} dB)"

    @mcp.tool()
    def fl_set_track_pan(track: int, pan: float) -> str:
        """Set the pan position of a mixer track.

        Args:
            track: Mixer track index (0 = Master)
            pan: Pan position from -1.0 (full left) to 1.0 (full right).
                 0.0 is center.
        """
        if not -1.0 <= pan <= 1.0:
            return "Error: Pan must be between -1.0 (left) and 1.0 (right)"

        conn = get_connection()
        result = conn.send_command("mixer.setTrackPan", {
            "track": track,
            "pan": pan,
        })

        if not result.get("success", False) and "error" in result:
            return f"Error: {result['error']}"

        new_pan = result.get("pan", 0)
        if new_pan < -0.01:
            direction = f"{abs(new_pan) * 100:.0f}% left"
        elif new_pan > 0.01:
            direction = f"{new_pan * 100:.0f}% right"
        else:
            direction = "center"

        return f"Track {track} pan set to {direction}"

    @mcp.tool()
    def fl_mute_track(track: int, muted: bool | None = None) -> str:
        """Mute or unmute a mixer track.

        Args:
            track: Mixer track index
            muted: True to mute, False to unmute, None to toggle
        """
        conn = get_connection()
        result = conn.send_command("mixer.muteTrack", {
            "track": track,
            "muted": muted,
        })

        if not result.get("success", False) and "error" in result:
            return f"Error: {result['error']}"

        is_muted = result.get("is_muted", False)
        track_name = result.get("track_name", f"Track {track}")
        return f"{track_name} {'muted' if is_muted else 'unmuted'}"

    @mcp.tool()
    def fl_solo_track(track: int, solo: bool | None = None, mode: int = 3) -> str:
        """Solo or unsolo a mixer track.

        Args:
            track: Mixer track index
            solo: True to solo, False to unsolo, None to toggle
            mode: Solo mode:
                  1 = Solo with source tracks
                  2 = Solo with send tracks
                  3 = Solo with both source and send tracks (default)
                  4 = Solo track only
        """
        conn = get_connection()
        result = conn.send_command("mixer.soloTrack", {
            "track": track,
            "solo": solo,
            "mode": mode,
        })

        if not result.get("success", False) and "error" in result:
            return f"Error: {result['error']}"

        is_solo = result.get("is_solo", False)
        track_name = result.get("track_name", f"Track {track}")
        return f"{track_name} {'soloed' if is_solo else 'unsoloed'}"

    @mcp.tool()
    def fl_arm_track(track: int) -> str:
        """Toggle the recording arm state of a mixer track.

        Armed tracks will record audio when recording is enabled.

        Args:
            track: Mixer track index
        """
        conn = get_connection()
        result = conn.send_command("mixer.armTrack", {"track": track})

        if not result.get("success", False) and "error" in result:
            return f"Error: {result['error']}"

        is_armed = result.get("is_armed", False)
        track_name = result.get("track_name", f"Track {track}")
        return f"{track_name} recording {'armed' if is_armed else 'disarmed'}"

    @mcp.tool()
    def fl_set_track_name(track: int, name: str) -> str:
        """Set the name of a mixer track.

        Args:
            track: Mixer track index
            name: New name for the track. Empty string resets to default.
        """
        conn = get_connection()
        result = conn.send_command("mixer.setTrackName", {
            "track": track,
            "name": name,
        })

        if not result.get("success", False) and "error" in result:
            return f"Error: {result['error']}"

        return f"Track {track} renamed to '{name}'"

    @mcp.tool()
    def fl_set_track_color(track: int, red: int, green: int, blue: int) -> str:
        """Set the color of a mixer track.

        Args:
            track: Mixer track index
            red: Red component (0-255)
            green: Green component (0-255)
            blue: Blue component (0-255)
        """
        conn = get_connection()
        result = conn.send_command("mixer.setTrackColor", {
            "track": track,
            "r": red,
            "g": green,
            "b": blue,
        })

        if not result.get("success", False) and "error" in result:
            return f"Error: {result['error']}"

        return f"Track {track} color set to RGB({red}, {green}, {blue})"

    @mcp.tool()
    def fl_set_stereo_separation(track: int, separation: float) -> str:
        """Set the stereo separation of a mixer track.

        Args:
            track: Mixer track index
            separation: Stereo separation from -1.0 (merged/mono) to 1.0 (full separation).
                       0.0 is default.
        """
        if not -1.0 <= separation <= 1.0:
            return "Error: Separation must be between -1.0 and 1.0"

        conn = get_connection()
        result = conn.send_command("mixer.setStereoSep", {
            "track": track,
            "separation": separation,
        })

        if not result.get("success", False) and "error" in result:
            return f"Error: {result['error']}"

        return f"Track {track} stereo separation set to {separation}"

    # --- Tier 4 extensions: selection, EQ, sends -----------------------------

    def _api_err(result: dict) -> dict:
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "error_code": "API_ERROR",
        }

    def _bad(msg: str) -> dict:
        return {"success": False, "error": msg, "error_code": "INVALID_ARGS"}

    @mcp.tool()
    def fl_get_selected_mixer_track() -> dict:
        """Get the currently selected mixer track (index and name)."""
        conn = get_connection()
        try:
            result = conn.send_command("mixer.getSelected")
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _api_err(result)
        return {"success": True, "index": result.get("index"), "name": result.get("name")}

    @mcp.tool()
    def fl_select_mixer_track(track: int) -> dict:
        """Exclusively select a mixer track by index.

        Args:
            track: Mixer track index (0 = master).
        """
        if track < 0:
            return _bad("track must be >= 0")
        conn = get_connection()
        try:
            result = conn.send_command("mixer.selectTrack", {"track": track})
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _api_err(result)
        return {"success": True, "index": result.get("index"), "name": result.get("name")}

    @mcp.tool()
    def fl_get_mixer_eq(track: int) -> dict:
        """Get the built-in EQ settings for a mixer track.

        Returns each band's gain (normalized and dB), frequency (normalized and
        Hz), and bandwidth (normalized). FL Studio's built-in EQ has 3 bands.

        Args:
            track: Mixer track index.
        """
        if track < 0:
            return _bad("track must be >= 0")
        conn = get_connection()
        try:
            result = conn.send_command("mixer.getEq", {"track": track})
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _api_err(result)
        return {"success": True, "track": track, "bands": result.get("bands", [])}

    @mcp.tool()
    def fl_set_mixer_eq_band(
        track: int,
        band: int,
        gain: float | None = None,
        frequency: float | None = None,
        bandwidth: float | None = None,
    ) -> dict:
        """Set one or more parameters of a mixer EQ band (normalized 0.0-1.0).

        Only the provided parameters are changed. All values are normalized
        0.0-1.0 (gain 0.5 = 0 dB).

        Args:
            track: Mixer track index.
            band: EQ band index (0, 1, or 2).
            gain: New gain, 0.0-1.0 (optional).
            frequency: New frequency, 0.0-1.0 (optional).
            bandwidth: New bandwidth, 0.0-1.0 (optional).
        """
        if track < 0 or band < 0:
            return _bad("track and band must be >= 0")
        for pname, val in (("gain", gain), ("frequency", frequency), ("bandwidth", bandwidth)):
            if val is not None and not 0.0 <= val <= 1.0:
                return _bad(f"{pname} must be between 0.0 and 1.0")
        if gain is None and frequency is None and bandwidth is None:
            return _bad("provide at least one of gain/frequency/bandwidth")
        conn = get_connection()
        try:
            result = conn.send_command("mixer.setEqBand", {
                "track": track, "band": band,
                "gain": gain, "frequency": frequency, "bandwidth": bandwidth,
            })
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _api_err(result)
        return {"success": True, "track": track, "band": band, "eq": result.get("eq")}

    @mcp.tool()
    def fl_get_mixer_sends(track: int) -> dict:
        """List the mixer sends (routes) from a track and their levels.

        Returns the destination tracks this track is routed to, with each send
        level (0.0-1.0; 0.8 is unity).

        Args:
            track: Source mixer track index.
        """
        if track < 0:
            return _bad("track must be >= 0")
        conn = get_connection()
        try:
            result = conn.send_command("mixer.getSends", {"track": track})
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _api_err(result)
        return {"success": True, "track": track, "sends": result.get("sends", [])}

    @mcp.tool()
    def fl_set_mixer_send(from_track: int, to_track: int, level: float = 0.8) -> dict:
        """Route one mixer track to another and set the send level.

        Creates the route if needed, then sets its level.

        Args:
            from_track: Source mixer track index.
            to_track: Destination mixer track index.
            level: Send level, 0.0-1.0 (0.8 = unity gain, the default).
        """
        if from_track < 0 or to_track < 0:
            return _bad("track indices must be >= 0")
        if not 0.0 <= level <= 1.0:
            return _bad("level must be between 0.0 and 1.0")
        conn = get_connection()
        try:
            result = conn.send_command("mixer.setSend", {
                "from_track": from_track, "to_track": to_track, "level": level,
            })
        except RuntimeError as e:
            return {"success": False, "error": str(e), "error_code": "FL_NOT_RUNNING"}
        if not result.get("success", False):
            return _api_err(result)
        return {
            "success": True,
            "from_track": from_track,
            "to_track": to_track,
            "level": result.get("level", level),
        }
