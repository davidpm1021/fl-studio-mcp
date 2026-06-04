"""Unit tests for the pure music-theory helpers in theory.py.

These cover only the pure functions (no FL Studio communication required).
"""

import pytest

from fl_studio_mcp.tools.theory import (
    apply_voicing,
    bars_to_beats,
    build_scale_sequence,
    get_chord_notes,
    get_scale_notes,
    interval_to_semitones,
    midi_to_note_name,
    note_to_midi,
    parse_chord_symbol,
    parse_pitch_class,
    parse_roman,
    progression_to_chords,
)

# --- pitch parsing -----------------------------------------------------------

@pytest.mark.parametrize("name,pc", [
    ("C", 0), ("C#", 1), ("Db", 1), ("D", 2), ("E", 4), ("F", 5),
    ("F#", 6), ("Gb", 6), ("G", 7), ("A", 9), ("B", 11),
    ("B#", 0), ("Cb", 11), ("F##", 7), ("Bbb", 9),
])
def test_parse_pitch_class(name, pc):
    assert parse_pitch_class(name) == pc


def test_parse_pitch_class_invalid():
    with pytest.raises(ValueError):
        parse_pitch_class("H")
    with pytest.raises(ValueError):
        parse_pitch_class("")
    with pytest.raises(ValueError):
        parse_pitch_class("Cx")


@pytest.mark.parametrize("name,octave,midi", [
    ("C", 4, 60), ("A", 4, 69), ("C", -1, 0), ("G", 9, 127), ("C", 5, 72),
])
def test_note_to_midi(name, octave, midi):
    assert note_to_midi(name, octave) == midi


def test_note_to_midi_out_of_range():
    with pytest.raises(ValueError):
        note_to_midi("C", 10)  # 132


@pytest.mark.parametrize("midi,name", [
    (60, "C4"), (61, "C#4"), (69, "A4"), (0, "C-1"), (127, "G9"),
])
def test_midi_to_note_name(midi, name):
    assert midi_to_note_name(midi) == name


def test_midi_roundtrip():
    for midi in range(0, 128):
        assert note_to_midi(*_split(midi_to_note_name(midi))) == midi


def _split(name):
    # split "C#4" / "C-1" into (letter+accidental, octave)
    i = len(name)
    while name[i - 1].isdigit() or name[i - 1] == "-":
        i -= 1
    return name[:i], int(name[i:])


# --- chords ------------------------------------------------------------------

@pytest.mark.parametrize("root,quality,octave,expected", [
    ("C", "maj", 4, [60, 64, 67]),
    ("C", "min", 4, [60, 63, 67]),
    ("A", "min", 4, [69, 72, 76]),
    ("C", "maj7", 4, [60, 64, 67, 71]),
    ("C", "min7", 4, [60, 63, 67, 70]),
    ("G", "7", 4, [67, 71, 74, 77]),
    ("C", "dim7", 4, [60, 63, 66, 69]),
    ("C", "sus4", 4, [60, 65, 67]),
])
def test_get_chord_notes(root, quality, octave, expected):
    assert get_chord_notes(root, quality, octave) == expected


def test_get_chord_quality_aliases():
    assert get_chord_notes("C", "major") == get_chord_notes("C", "maj")
    assert get_chord_notes("C", "m") == get_chord_notes("C", "min")
    assert get_chord_notes("C", "dom7") == get_chord_notes("C", "7")
    assert get_chord_notes("C", "M7") == get_chord_notes("C", "maj7")


def test_get_chord_notes_invalid_quality():
    with pytest.raises(ValueError):
        get_chord_notes("C", "bogus")


# --- voicings ----------------------------------------------------------------

def test_voicing_close_is_identity():
    assert apply_voicing([60, 64, 67], "close") == [60, 64, 67]


def test_voicing_inversions():
    assert apply_voicing([60, 64, 67], "first") == [64, 67, 72]
    assert apply_voicing([60, 64, 67], "second") == [67, 72, 76]
    assert apply_voicing([60, 64, 67, 71], "third") == [71, 72, 76, 79]


def test_voicing_drop2_drop3():
    assert apply_voicing([60, 64, 67], "drop2") == [52, 60, 67]
    assert apply_voicing([60, 64, 67, 71], "drop3") == [52, 60, 67, 71]


def test_voicing_open():
    assert apply_voicing([60, 64, 67], "open") == [60, 67, 76]


def test_voicing_invalid():
    with pytest.raises(ValueError):
        apply_voicing([60, 64, 67], "sideways")


# --- scales ------------------------------------------------------------------

def test_get_scale_notes_major():
    assert get_scale_notes("C", "major", 4) == [60, 62, 64, 65, 67, 69, 71]


def test_get_scale_notes_minor():
    assert get_scale_notes("A", "minor", 4) == [69, 71, 72, 74, 76, 77, 79]


def test_get_scale_notes_dorian():
    assert get_scale_notes("D", "dorian", 4) == [62, 64, 65, 67, 69, 71, 72]


def test_get_scale_mode_aliases():
    assert get_scale_notes("C", "ionian") == get_scale_notes("C", "major")
    assert get_scale_notes("A", "aeolian") == get_scale_notes("A", "minor")


def test_get_scale_notes_invalid_mode():
    with pytest.raises(ValueError):
        get_scale_notes("C", "bogus")


def test_build_scale_sequence_up_includes_top_tonic():
    assert build_scale_sequence("C", "major", 4, 1, "up") == [
        60, 62, 64, 65, 67, 69, 71, 72
    ]


def test_build_scale_sequence_down():
    assert build_scale_sequence("C", "major", 4, 1, "down") == [
        72, 71, 69, 67, 65, 64, 62, 60
    ]


def test_build_scale_sequence_updown_no_repeat_peak():
    seq = build_scale_sequence("C", "major", 4, 1, "updown")
    assert seq[:8] == [60, 62, 64, 65, 67, 69, 71, 72]
    assert seq[7] == 72 and seq.count(72) == 1
    assert seq[-1] == 60


def test_build_scale_sequence_two_octaves():
    seq = build_scale_sequence("C", "major", 4, 2, "up")
    assert seq[0] == 60 and seq[-1] == 84
    assert len(seq) == 15  # 7*2 + top tonic


# --- chord symbols -----------------------------------------------------------

@pytest.mark.parametrize("symbol,root_pc,quality", [
    ("C", 0, "maj"),
    ("Am", 9, "min"),
    ("F#m7", 6, "min7"),
    ("Bb7", 10, "7"),
    ("Gsus4", 7, "sus4"),
    ("Dmaj7", 2, "maj7"),
])
def test_parse_chord_symbol(symbol, root_pc, quality):
    assert parse_chord_symbol(symbol) == (root_pc, quality)


# --- roman numerals ----------------------------------------------------------

@pytest.mark.parametrize("roman,offset,quality", [
    ("I", 0, "maj"),
    ("ii", 2, "min"),
    ("iii", 4, "min"),
    ("IV", 5, "maj"),
    ("V", 7, "maj"),
    ("vi", 9, "min"),
    ("V7", 7, "7"),
    ("ii7", 2, "min7"),
    ("Imaj7", 0, "maj7"),
    ("bVII", 10, "maj"),
    ("#iv", 6, "min"),
])
def test_parse_roman(roman, offset, quality):
    assert parse_roman(roman) == (offset, quality)


def test_parse_roman_invalid():
    with pytest.raises(ValueError):
        parse_roman("Q")
    with pytest.raises(ValueError):
        parse_roman("")


def test_progression_roman_in_key():
    # fifties in C: I vi IV V
    chords = progression_to_chords(["I", "vi", "IV", "V"], key="C", octave=4)
    assert chords == [
        [60, 64, 67],   # C
        [69, 72, 76],   # Am
        [65, 69, 72],   # F
        [67, 71, 74],   # G
    ]


def test_progression_roman_in_g():
    # I IV V in G major. Roots are placed by pitch class within the given
    # octave, so IV (C) and V (D) land in octave 4, not above G4.
    chords = progression_to_chords(["I", "IV", "V"], key="G", octave=4)
    assert chords[0] == get_chord_notes("G", "maj", 4)
    assert chords[1] == get_chord_notes("C", "maj", 4)
    assert chords[2] == get_chord_notes("D", "maj", 4)


def test_progression_chord_symbols():
    chords = progression_to_chords(["C", "Am7", "F", "G"], octave=4)
    assert chords[0] == [60, 64, 67]
    assert chords[1] == [69, 72, 76, 79]  # Am7


# --- intervals ---------------------------------------------------------------

@pytest.mark.parametrize("interval,semitones", [
    ("octave", 12),
    ("fifth", 7),
    ("perfect5", 7),
    ("major3", 4),
    ("up_octave", 12),
    ("down_fifth", -7),
    ("-major3", -4),
    ("+octave", 12),
])
def test_interval_to_semitones(interval, semitones):
    assert interval_to_semitones(interval) == semitones


def test_interval_invalid():
    with pytest.raises(ValueError):
        interval_to_semitones("bogus")


# --- bars/beats --------------------------------------------------------------

def test_bars_to_beats():
    assert bars_to_beats(1, 4) == 4
    assert bars_to_beats(2, 3) == 6
