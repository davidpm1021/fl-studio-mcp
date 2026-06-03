"""Music theory wrappers (Layer C) for FL Studio.

These tools encode musical concepts (chords, scales, progressions, arpeggios,
transposition) on top of the raw piano roll primitives. The pure helpers
(``get_chord_notes``, ``get_scale_notes`` and friends) do no FL Studio
communication and are fully unit-testable. The placement tools compute notes
with those helpers and reuse the existing Piano Roll Scripting bridge
(``add_notes`` / ``add_chord`` requests) to write them into the open piano roll.

Conventions:
- MIDI note numbers use C4 = 60 (middle C).
- "bars" are 1-indexed (bar 1 is the start of the song), matching FL Studio's
  ruler. ``beats_per_bar`` defaults to 4 (4/4); pass a different value for
  other time signatures (e.g. 3 for 3/4, 3 for 6/8 in quarter-note terms).
- Timing passed to the piano roll bridge is in quarter notes (beats).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


# =============================================================================
# Music theory data
# =============================================================================

# Pitch class for each natural note letter.
_LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

_NOTE_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Chord qualities as semitone offsets from the root.
CHORD_QUALITIES = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "7": [0, 4, 7, 10],
    "dim7": [0, 3, 6, 9],
    "m7b5": [0, 3, 6, 10],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "6": [0, 4, 7, 9],
    "min6": [0, 3, 7, 9],
    "9": [0, 4, 7, 10, 14],
    "maj9": [0, 4, 7, 11, 14],
    "min9": [0, 3, 7, 10, 14],
    "add9": [0, 4, 7, 14],
}

# Alternate spellings mapped to canonical quality keys.
_QUALITY_ALIASES = {
    "": "maj",
    "major": "maj",
    "M": "maj",
    "minor": "min",
    "m": "min",
    "-": "min",
    "dominant": "7",
    "dom7": "7",
    "dominant7": "7",
    "halfdim": "m7b5",
    "half_diminished": "m7b5",
    "min7b5": "m7b5",
    "m7flat5": "m7b5",
    "diminished": "dim",
    "augmented": "aug",
    "+": "aug",
    "major7": "maj7",
    "M7": "maj7",
    "maj7th": "maj7",
    "m7": "min7",
    "-7": "min7",
    "major9": "maj9",
    "m9": "min9",
    "m6": "min6",
    "6th": "6",
}

# Scale modes as semitone offsets from the tonic.
SCALE_MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
}

_MODE_ALIASES = {
    "ionian": "major",
    "aeolian": "minor",
    "natural_minor": "minor",
    "naturalminor": "minor",
}

# Named progressions as roman numerals (interpreted in a given key).
NAMED_PROGRESSIONS = {
    "fifties": ["I", "vi", "IV", "V"],
    "axis_of_awesome": ["I", "V", "vi", "IV"],
    "andalusian": ["i", "VII", "VI", "V"],
    "twelve_bar_blues": [
        "I", "I", "I", "I", "IV", "IV", "I", "I", "V", "IV", "I", "I",
    ],
    "jazz_ii_v_i": ["ii7", "V7", "Imaj7"],
    "pachelbel": ["I", "V", "vi", "iii", "IV", "I", "IV", "V"],
}

# Interval names to semitone counts (for transposition).
INTERVALS = {
    "unison": 0,
    "semitone": 1,
    "minor2": 1,
    "tone": 2,
    "whole": 2,
    "major2": 2,
    "minor3": 3,
    "major3": 4,
    "perfect4": 5,
    "fourth": 5,
    "tritone": 6,
    "perfect5": 7,
    "fifth": 7,
    "minor6": 8,
    "major6": 9,
    "minor7": 10,
    "major7": 11,
    "octave": 12,
}

# Major scale degrees, used as the reference frame for roman numerals.
_MAJOR_DEGREES = [0, 2, 4, 5, 7, 9, 11]
_ROMAN_DEGREES = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6}


# =============================================================================
# Pure helpers (no FL Studio communication; unit tested)
# =============================================================================


def parse_pitch_class(name: str) -> int:
    """Parse a note letter with optional accidentals into a pitch class (0-11).

    Accepts e.g. "C", "C#", "Db", "F##", "Bbb". Case-insensitive on the letter.
    """
    if not name:
        raise ValueError("empty note name")
    letter = name[0].upper()
    if letter not in _LETTER_PC:
        raise ValueError(f"invalid note letter: {name[0]!r}")
    pc = _LETTER_PC[letter]
    for ch in name[1:]:
        if ch in ("#", "♯"):
            pc += 1
        elif ch in ("b", "B", "♭"):
            pc -= 1
        else:
            raise ValueError(f"invalid accidental in note name: {name!r}")
    return pc % 12


def note_to_midi(name: str, octave: int) -> int:
    """Convert a note name (no octave) plus an octave number to a MIDI number.

    C4 = 60. Example: note_to_midi("C", 4) -> 60, note_to_midi("A", 4) -> 69.
    """
    pc = parse_pitch_class(name)
    midi = pc + (octave + 1) * 12
    if not 0 <= midi <= 127:
        raise ValueError(f"note {name}{octave} is out of MIDI range (0-127)")
    return midi


def midi_to_note_name(midi: int) -> str:
    """Convert a MIDI note number to a sharp-spelled note name (C4 = 60)."""
    return f"{_NOTE_NAMES_SHARP[midi % 12]}{midi // 12 - 1}"


def _canonical_quality(quality: str) -> str:
    """Resolve a chord quality string (with aliases) to a canonical key."""
    q = quality.strip()
    if q in CHORD_QUALITIES:
        return q
    if q in _QUALITY_ALIASES:
        return _QUALITY_ALIASES[q]
    lowered = q.lower()
    if lowered in CHORD_QUALITIES:
        return lowered
    if lowered in _QUALITY_ALIASES:
        return _QUALITY_ALIASES[lowered]
    raise ValueError(
        f"unknown chord quality: {quality!r}. Known: "
        f"{sorted(CHORD_QUALITIES)}"
    )


def _canonical_mode(mode: str) -> str:
    """Resolve a scale mode string (with aliases) to a canonical key."""
    m = mode.strip().lower()
    if m in SCALE_MODES:
        return m
    if m in _MODE_ALIASES:
        return _MODE_ALIASES[m]
    raise ValueError(
        f"unknown scale mode: {mode!r}. Known: {sorted(SCALE_MODES)}"
    )


def apply_voicing(notes: list[int], voicing: str) -> list[int]:
    """Apply a voicing transformation to a sorted list of MIDI notes.

    Supported voicings: "close" (default), "open", "drop2", "drop3", and the
    inversions "first"/"second"/"third".
    """
    v = (voicing or "close").strip().lower()
    s = sorted(notes)
    if v in ("close", "root", ""):
        return s
    if v in ("first", "inv1", "1"):
        if len(s) < 2:
            return s
        return sorted(s[1:] + [s[0] + 12])
    if v in ("second", "inv2", "2"):
        if len(s) < 3:
            return s
        return sorted(s[2:] + [n + 12 for n in s[:2]])
    if v in ("third", "inv3", "3"):
        if len(s) < 4:
            return s
        return sorted(s[3:] + [n + 12 for n in s[:3]])
    if v == "open":
        if len(s) < 3:
            return s
        spread = s[:]
        spread[1] += 12
        return sorted(spread)
    if v == "drop2":
        if len(s) < 2:
            return s
        s2 = s[:]
        s2[-2] -= 12
        return sorted(s2)
    if v == "drop3":
        if len(s) < 3:
            return s
        s3 = s[:]
        s3[-3] -= 12
        return sorted(s3)
    raise ValueError(
        f"unknown voicing: {voicing!r}. Known: close, open, drop2, drop3, "
        f"first, second, third"
    )


def get_chord_notes(
    root: str,
    quality: str = "maj",
    octave: int = 4,
    voicing: str = "close",
) -> list[int]:
    """Compute the MIDI notes of a chord.

    Args:
        root: Root note name, e.g. "C", "F#", "Bb".
        quality: Chord quality, e.g. "maj", "min7", "7", "dim7", "sus4".
        octave: Octave of the root (C4 = middle C = MIDI 60).
        voicing: Voicing transform (close/open/drop2/drop3/first/second/third).
    """
    canonical = _canonical_quality(quality)
    root_midi = note_to_midi(root, octave)
    notes = [root_midi + iv for iv in CHORD_QUALITIES[canonical]]
    return apply_voicing(notes, voicing)


def get_scale_notes(key: str, mode: str = "major", octave: int = 4) -> list[int]:
    """Compute one octave of a scale's MIDI notes (tonic up to the leading tone).

    Args:
        key: Tonic note name, e.g. "C", "G#", "Eb".
        mode: Scale mode (major/minor/dorian/.../locrian).
        octave: Octave of the tonic (C4 = MIDI 60).
    """
    canonical = _canonical_mode(mode)
    tonic = note_to_midi(key, octave)
    return [tonic + iv for iv in SCALE_MODES[canonical]]


def build_scale_sequence(
    key: str,
    mode: str = "major",
    octave: int = 4,
    octaves: int = 1,
    direction: str = "up",
) -> list[int]:
    """Build a playable scale run across one or more octaves.

    Includes the tonic at the top of the run. ``direction`` is "up", "down", or
    "updown" (ascend then descend without repeating the peak).
    """
    if octaves < 1:
        raise ValueError("octaves must be >= 1")
    canonical = _canonical_mode(mode)
    tonic = note_to_midi(key, octave)
    intervals = SCALE_MODES[canonical]

    ascending: list[int] = []
    for o in range(octaves):
        for iv in intervals:
            ascending.append(tonic + o * 12 + iv)
    ascending.append(tonic + octaves * 12)  # top tonic

    d = direction.strip().lower()
    if d in ("up", "ascending"):
        seq = ascending
    elif d in ("down", "descending"):
        seq = list(reversed(ascending))
    elif d in ("updown", "up_down", "both"):
        seq = ascending + list(reversed(ascending))[1:]
    else:
        raise ValueError(f"unknown direction: {direction!r}")
    return [n for n in seq if 0 <= n <= 127]


def parse_chord_symbol(symbol: str, octave: int = 4) -> tuple[int, str]:
    """Parse a chord symbol like "C", "Am7", "F#maj7" into (root_pc, quality).

    Returns the root pitch class (0-11) and the canonical quality key.
    """
    if not symbol:
        raise ValueError("empty chord symbol")
    i = 1
    while i < len(symbol) and symbol[i] in ("#", "b", "♯", "♭"):
        i += 1
    root_part = symbol[:i]
    quality_part = symbol[i:]
    root_pc = parse_pitch_class(root_part)
    quality = _canonical_quality(quality_part)
    return root_pc, quality


def parse_roman(symbol: str) -> tuple[int, str]:
    """Parse a roman-numeral chord symbol into (degree_offset, quality).

    ``degree_offset`` is the chromatic semitone offset of the chord root from
    the key tonic (already accounting for the diatonic degree and any leading
    accidental). Returns the canonical chord quality.

    Examples: "I" -> (0, "maj"), "vi" -> (9, "min"), "V7" -> (7, "7"),
    "bVII" -> (10, "maj"), "viio7" -> (11, "dim7").
    """
    s = symbol.strip()
    if not s:
        raise ValueError("empty roman numeral")

    accidental = 0
    while s and s[0] in ("#", "b", "♯", "♭"):
        accidental += 1 if s[0] in ("#", "♯") else -1
        s = s[1:]

    # Longest roman numeral first (vii before vi before v).
    roman = None
    for cand in ("vii", "iii", "vi", "iv", "ii", "v", "i"):
        if s.lower().startswith(cand):
            roman = cand
            break
    if roman is None:
        raise ValueError(f"invalid roman numeral: {symbol!r}")

    degree = _ROMAN_DEGREES[roman]
    is_upper = s[: len(roman)].isupper()
    suffix = s[len(roman):].strip()

    quality = _roman_quality(suffix, is_upper)
    offset = (_MAJOR_DEGREES[degree] + accidental) % 12
    return offset, quality


def _roman_quality(suffix: str, is_upper: bool) -> str:
    """Map a roman numeral's case + suffix to a canonical chord quality."""
    suf = suffix.replace("°", "dim").replace("ø", "m7b5")
    suf = suf.replace("o7", "dim7").replace("o", "dim") if suf in (
        "o", "o7"
    ) else suf
    low = suf.lower()

    if low in ("dim", "diminished"):
        return "dim"
    if low in ("dim7", "°7"):
        return "dim7"
    if low in ("m7b5", "halfdim", "ø", "ø7"):
        return "m7b5"
    if low in ("aug", "+"):
        return "aug"
    if low in ("maj7", "M7"):
        return "maj7"
    if low in ("sus2",):
        return "sus2"
    if low in ("sus4", "sus"):
        return "sus4"
    if low == "6":
        return "6" if is_upper else "min6"
    if low == "7":
        return "7" if is_upper else "min7"
    if low == "9":
        return "9" if is_upper else "min9"
    if low in ("", "triad"):
        return "maj" if is_upper else "min"
    # Fall back: treat suffix as an explicit quality if recognised.
    return _canonical_quality(suffix)


def progression_to_chords(
    progression: list[str],
    key: str | None = None,
    octave: int = 4,
    voicing: str = "close",
) -> list[list[int]]:
    """Resolve a progression to a list of chords (each a list of MIDI notes).

    Each item may be a roman numeral (requires ``key``) or a concrete chord
    symbol like "Am7". Items are detected per-element, so the two styles can be
    mixed.
    """
    chords: list[list[int]] = []
    key_pc = parse_pitch_class(key) if key else None

    for item in progression:
        token = item.strip()
        if _looks_like_roman(token) and key_pc is not None:
            offset, quality = parse_roman(token)
            root_pc = (key_pc + offset) % 12
        else:
            root_pc, quality = parse_chord_symbol(token, octave)
        root_midi = root_pc + (octave + 1) * 12
        notes = [root_midi + iv for iv in CHORD_QUALITIES[quality]]
        chords.append(apply_voicing(notes, voicing))
    return chords


def _looks_like_roman(token: str) -> bool:
    """Heuristic: does the token start like a roman numeral chord?"""
    s = token
    while s and s[0] in ("#", "b", "♯", "♭"):
        s = s[1:]
    for cand in ("vii", "iii", "vi", "iv", "ii", "v", "i"):
        if s.lower().startswith(cand):
            return True
    return False


def interval_to_semitones(interval: str) -> int:
    """Resolve an interval name (with optional direction) to signed semitones.

    Accepts e.g. "octave", "fifth", "up_octave", "down_fifth", "-fifth".
    """
    s = interval.strip().lower()
    sign = 1
    for prefix in ("up_", "up ", "+"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    for prefix in ("down_", "down ", "-"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            sign = -1
            break
    if s not in INTERVALS:
        raise ValueError(
            f"unknown interval: {interval!r}. Known: {sorted(INTERVALS)}"
        )
    return sign * INTERVALS[s]


def bars_to_beats(bars: float, beats_per_bar: float) -> float:
    """Convert a bar count to beats (quarter notes)."""
    return bars * beats_per_bar


# =============================================================================
# MCP tool registration
# =============================================================================


def register_theory_tools(mcp: FastMCP) -> None:
    """Register music theory (Layer C) tools with the MCP server."""
    from fl_studio_mcp.tools.piano_roll import (
        _get_trigger_info,
        _write_request,
    )

    def _names(notes: list[int]) -> list[str]:
        return [midi_to_note_name(n) for n in notes]

    @mcp.tool()
    def fl_get_chord_notes(
        root: str,
        quality: str = "maj",
        octave: int = 4,
        voicing: str = "close",
    ) -> dict:
        """Compute the notes of a chord without placing anything (pure helper).

        Args:
            root: Root note name, e.g. "C", "F#", "Bb".
            quality: Chord quality (maj, min, 7, maj7, min7, dim, dim7, aug,
                     m7b5, sus2, sus4, 6, min6, 9, maj9, min9, add9).
            octave: Octave of the root (C4 = middle C).
            voicing: close/open/drop2/drop3/first/second/third.
        """
        try:
            notes = get_chord_notes(root, quality, octave, voicing)
        except ValueError as e:
            return {"success": False, "error": str(e), "error_code": "INVALID_ARGS"}
        return {"success": True, "notes": notes, "note_names": _names(notes)}

    @mcp.tool()
    def fl_get_scale_notes(
        key: str,
        mode: str = "major",
        octave: int = 4,
    ) -> dict:
        """Compute one octave of a scale without placing anything (pure helper).

        Args:
            key: Tonic note name, e.g. "C", "G#", "Eb".
            mode: Scale mode (major, minor, harmonic_minor, melodic_minor,
                  dorian, phrygian, lydian, mixolydian, locrian).
            octave: Octave of the tonic (C4 = middle C).
        """
        try:
            notes = get_scale_notes(key, mode, octave)
        except ValueError as e:
            return {"success": False, "error": str(e), "error_code": "INVALID_ARGS"}
        return {"success": True, "notes": notes, "note_names": _names(notes)}

    @mcp.tool()
    def fl_place_chord(
        root: str,
        quality: str = "maj",
        position_bars: float = 1.0,
        duration_bars: float = 1.0,
        octave: int = 4,
        voicing: str = "close",
        beats_per_bar: float = 4.0,
        velocity: float = 0.8,
        auto_trigger: bool = True,
    ) -> dict:
        """Place a chord in the open FL Studio piano roll.

        Requires the piano roll open and the ComposeWithLLM script armed once
        this session. ``position_bars`` is 1-indexed (bar 1 = start).

        Args:
            root: Root note name.
            quality: Chord quality (see fl_get_chord_notes).
            position_bars: Bar to place the chord at (1 = start of song).
            duration_bars: Chord length in bars.
            octave: Octave of the root (C4 = middle C).
            voicing: close/open/drop2/drop3/first/second/third.
            beats_per_bar: Quarter notes per bar (4 for 4/4, 3 for 3/4).
            velocity: Note velocity 0.0-1.0.
            auto_trigger: Trigger FL Studio automatically.
        """
        if position_bars < 1:
            return {
                "success": False,
                "error": "position_bars is 1-indexed and must be >= 1",
                "error_code": "INVALID_ARGS",
            }
        try:
            notes = get_chord_notes(root, quality, octave, voicing)
        except ValueError as e:
            return {"success": False, "error": str(e), "error_code": "INVALID_ARGS"}

        time_beats = (position_bars - 1) * beats_per_bar
        duration_beats = duration_bars * beats_per_bar
        request = {
            "action": "add_chord",
            "time": time_beats,
            "duration": duration_beats,
            "notes": [{"midi": n, "velocity": velocity} for n in notes],
        }
        _write_request(request)
        trigger_info = _get_trigger_info(auto_trigger)
        return {
            "success": True,
            "notes": notes,
            "note_names": _names(notes),
            "time_beats": time_beats,
            "duration_beats": duration_beats,
            "message": f"Placed {root}{quality} ({', '.join(_names(notes))})."
            + trigger_info,
        }

    @mcp.tool()
    def fl_place_progression(
        progression: list[str] | None = None,
        name: str | None = None,
        key: str = "C",
        start_bars: float = 1.0,
        chord_duration_bars: float = 1.0,
        octave: int = 4,
        voicing: str = "close",
        beats_per_bar: float = 4.0,
        velocity: float = 0.8,
        auto_trigger: bool = True,
    ) -> dict:
        """Place a chord progression in the open FL Studio piano roll.

        Provide either ``progression`` (a list of roman numerals like
        ["I","vi","IV","V"] or chord symbols like ["C","Am7","F","G"]) or a
        ``name`` from the named-progression library (fifties, axis_of_awesome,
        andalusian, twelve_bar_blues, jazz_ii_v_i, pachelbel). Roman numerals
        are interpreted in ``key``.

        Args:
            progression: Explicit list of roman numerals or chord symbols.
            name: Named progression to use instead of ``progression``.
            key: Key for interpreting roman numerals.
            start_bars: Bar to start at (1 = start of song).
            chord_duration_bars: Length of each chord in bars.
            octave: Octave of the chord roots.
            voicing: Voicing for all chords.
            beats_per_bar: Quarter notes per bar.
            velocity: Note velocity 0.0-1.0.
            auto_trigger: Trigger FL Studio automatically.
        """
        if name:
            if name not in NAMED_PROGRESSIONS:
                return {
                    "success": False,
                    "error": f"unknown progression name: {name!r}. Known: "
                    f"{sorted(NAMED_PROGRESSIONS)}",
                    "error_code": "INVALID_ARGS",
                }
            symbols = NAMED_PROGRESSIONS[name]
        elif progression:
            symbols = progression
        else:
            return {
                "success": False,
                "error": "provide either 'progression' or 'name'",
                "error_code": "INVALID_ARGS",
            }
        if start_bars < 1:
            return {
                "success": False,
                "error": "start_bars is 1-indexed and must be >= 1",
                "error_code": "INVALID_ARGS",
            }

        try:
            chords = progression_to_chords(symbols, key, octave, voicing)
        except ValueError as e:
            return {"success": False, "error": str(e), "error_code": "INVALID_ARGS"}

        duration_beats = chord_duration_bars * beats_per_bar
        requests = []
        placed = []
        for i, notes in enumerate(chords):
            time_beats = (start_bars - 1) * beats_per_bar + i * duration_beats
            requests.append({
                "action": "add_chord",
                "time": time_beats,
                "duration": duration_beats,
                "notes": [{"midi": n, "velocity": velocity} for n in notes],
            })
            placed.append({
                "symbol": symbols[i],
                "notes": notes,
                "note_names": _names(notes),
                "time_beats": time_beats,
            })

        _write_request(requests)
        trigger_info = _get_trigger_info(auto_trigger)
        return {
            "success": True,
            "key": key,
            "chords": placed,
            "message": f"Placed {len(chords)} chords "
            f"({', '.join(symbols)})." + trigger_info,
        }

    @mcp.tool()
    def fl_place_scale(
        key: str,
        mode: str = "major",
        octave: int = 4,
        octaves: int = 1,
        direction: str = "up",
        note_duration_beats: float = 1.0,
        start_bars: float = 1.0,
        beats_per_bar: float = 4.0,
        velocity: float = 0.8,
        auto_trigger: bool = True,
    ) -> dict:
        """Place a scale run in the open FL Studio piano roll.

        Args:
            key: Tonic note name.
            mode: Scale mode (see fl_get_scale_notes).
            octave: Octave of the tonic.
            octaves: How many octaves to span.
            direction: up / down / updown.
            note_duration_beats: Length of each note in beats (quarter notes).
            start_bars: Bar to start at (1 = start of song).
            beats_per_bar: Quarter notes per bar.
            velocity: Note velocity 0.0-1.0.
            auto_trigger: Trigger FL Studio automatically.
        """
        if start_bars < 1:
            return {
                "success": False,
                "error": "start_bars is 1-indexed and must be >= 1",
                "error_code": "INVALID_ARGS",
            }
        try:
            seq = build_scale_sequence(key, mode, octave, octaves, direction)
        except ValueError as e:
            return {"success": False, "error": str(e), "error_code": "INVALID_ARGS"}

        start_beat = (start_bars - 1) * beats_per_bar
        notes = []
        for i, midi in enumerate(seq):
            notes.append({
                "midi": midi,
                "time": start_beat + i * note_duration_beats,
                "duration": note_duration_beats,
                "velocity": velocity,
            })
        _write_request({"action": "add_notes", "notes": notes})
        trigger_info = _get_trigger_info(auto_trigger)
        return {
            "success": True,
            "notes": seq,
            "note_names": _names(seq),
            "count": len(seq),
            "message": f"Placed {key} {mode} scale ({len(seq)} notes)."
            + trigger_info,
        }

    @mcp.tool()
    def fl_place_arpeggio(
        root: str,
        quality: str = "maj",
        pattern: str = "up",
        octave: int = 4,
        octaves: int = 1,
        note_duration_beats: float = 0.5,
        start_bars: float = 1.0,
        beats_per_bar: float = 4.0,
        velocity: float = 0.8,
        auto_trigger: bool = True,
    ) -> dict:
        """Place an arpeggio (broken chord) in the open FL Studio piano roll.

        Args:
            root: Root note name of the chord.
            quality: Chord quality (see fl_get_chord_notes).
            pattern: up / down / updown.
            octave: Octave of the root.
            octaves: How many octaves to span.
            note_duration_beats: Length of each note in beats.
            start_bars: Bar to start at (1 = start of song).
            beats_per_bar: Quarter notes per bar.
            velocity: Note velocity 0.0-1.0.
            auto_trigger: Trigger FL Studio automatically.
        """
        if start_bars < 1:
            return {
                "success": False,
                "error": "start_bars is 1-indexed and must be >= 1",
                "error_code": "INVALID_ARGS",
            }
        if octaves < 1:
            return {
                "success": False,
                "error": "octaves must be >= 1",
                "error_code": "INVALID_ARGS",
            }
        try:
            base = get_chord_notes(root, quality, octave, "close")
        except ValueError as e:
            return {"success": False, "error": str(e), "error_code": "INVALID_ARGS"}

        chord_tones = []
        for o in range(octaves):
            chord_tones.extend(n + 12 * o for n in base)
        chord_tones = [n for n in chord_tones if 0 <= n <= 127]

        p = pattern.strip().lower()
        if p in ("up", "ascending"):
            seq = chord_tones
        elif p in ("down", "descending"):
            seq = list(reversed(chord_tones))
        elif p in ("updown", "up_down", "both"):
            seq = chord_tones + list(reversed(chord_tones))[1:]
        else:
            return {
                "success": False,
                "error": f"unknown pattern: {pattern!r} (up/down/updown)",
                "error_code": "INVALID_ARGS",
            }

        start_beat = (start_bars - 1) * beats_per_bar
        notes = []
        for i, midi in enumerate(seq):
            notes.append({
                "midi": midi,
                "time": start_beat + i * note_duration_beats,
                "duration": note_duration_beats,
                "velocity": velocity,
            })
        _write_request({"action": "add_notes", "notes": notes})
        trigger_info = _get_trigger_info(auto_trigger)
        return {
            "success": True,
            "notes": seq,
            "note_names": _names(seq),
            "count": len(seq),
            "message": f"Placed {root}{quality} arpeggio ({len(seq)} notes)."
            + trigger_info,
        }

    @mcp.tool()
    def fl_transpose_selection(
        semitones: int | None = None,
        interval: str | None = None,
        selected_only: bool = True,
        auto_trigger: bool = True,
    ) -> dict:
        """Transpose notes in the open piano roll by semitones or an interval.

        Operates on the currently selected notes; if nothing is selected, it
        transposes all notes in the piano roll. Provide either ``semitones``
        (e.g. 12, -5) or ``interval`` (e.g. "octave", "down_fifth").

        Args:
            semitones: Signed number of semitones to transpose by.
            interval: Interval name instead of semitones (e.g. "fifth",
                      "up_octave", "-major3").
            selected_only: If True, transpose only selected notes (falls back to
                           all notes when nothing is selected).
            auto_trigger: Trigger FL Studio automatically.
        """
        if semitones is None and interval is None:
            return {
                "success": False,
                "error": "provide either 'semitones' or 'interval'",
                "error_code": "INVALID_ARGS",
            }
        if semitones is None:
            try:
                semitones = interval_to_semitones(interval)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_code": "INVALID_ARGS",
                }

        _write_request({
            "action": "transpose",
            "semitones": semitones,
            "selected_only": selected_only,
        })
        trigger_info = _get_trigger_info(auto_trigger)
        return {
            "success": True,
            "semitones": semitones,
            "message": f"Transposed by {semitones} semitones." + trigger_info,
        }
