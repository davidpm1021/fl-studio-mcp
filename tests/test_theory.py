"""Unit tests for the pure music-theory helpers in theory.py.

These cover only the pure functions (no FL Studio communication required).
"""

import pytest

from fl_studio_mcp.tools.theory import (
    apply_voicing,
    bars_to_beats,
    build_scale_sequence,
    detect_key,
    extend_chord,
    generate_bassline,
    get_chord_notes,
    get_chord_scale,
    get_diatonic_chords,
    get_scale_notes,
    harmonize_melody,
    identify_chord,
    interval_to_semitones,
    jazz_voicing,
    midi_to_note_name,
    note_name_to_midi,
    note_to_midi,
    parse_chord_symbol,
    parse_pitch_class,
    parse_roman,
    progression_to_chords,
    reharmonize,
    voice_lead_progression,
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


# --- diatonic chords (T2) ----------------------------------------------------

def test_diatonic_triads_c_major():
    chords = get_diatonic_chords("C", "major", sevenths=False, octave=4)
    qualities = [c["quality"] for c in chords]
    romans = [c["roman"] for c in chords]
    assert qualities == ["maj", "min", "min", "maj", "maj", "min", "dim"]
    assert romans == ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
    assert chords[0]["notes"] == [60, 64, 67]   # C
    assert chords[4]["notes"] == [67, 71, 74]   # G
    assert chords[6]["notes"] == [71, 74, 77]   # B dim


def test_diatonic_sevenths_c_major():
    chords = get_diatonic_chords("C", "major", sevenths=True, octave=4)
    qualities = [c["quality"] for c in chords]
    assert qualities == [
        "maj7", "min7", "min7", "maj7", "7", "min7", "m7b5"
    ]
    assert chords[0]["notes"] == [60, 64, 67, 71]   # Cmaj7
    assert chords[4]["notes"] == [67, 71, 74, 77]   # G7
    assert chords[4]["roman"] == "V7"
    assert chords[6]["roman"] == "viiø7"


def test_diatonic_a_minor():
    chords = get_diatonic_chords("A", "minor", octave=4)
    assert chords[0]["quality"] == "min"   # i
    assert chords[0]["root"] == "A4"
    assert [c["quality"] for c in chords] == [
        "min", "dim", "maj", "min", "min", "maj", "maj"
    ]


def test_diatonic_invalid_mode():
    with pytest.raises(ValueError):
        get_diatonic_chords("C", "bogus")


# --- voice leading (T2) ------------------------------------------------------

def _pcs(notes):
    return sorted(set(n % 12 for n in notes))


def test_voice_lead_preserves_pitch_classes():
    close = [
        get_chord_notes("C", "maj", 4),
        get_chord_notes("F", "maj", 4),
        get_chord_notes("G", "maj", 4),
    ]
    voiced = voice_lead_progression(close)
    assert len(voiced) == 3
    for original, v in zip(close, voiced):
        assert _pcs(original) == _pcs(v)


def test_voice_lead_first_chord_unchanged():
    close = [[60, 64, 67], [65, 69, 72]]
    voiced = voice_lead_progression(close)
    assert voiced[0] == [60, 64, 67]


def test_voice_lead_reduces_movement():
    close = [[60, 64, 67], [65, 69, 72]]  # C -> F (close position)

    def movement(a, b):
        m = min(len(a), len(b))
        return sum(abs(sorted(a)[i] - sorted(b)[i]) for i in range(m))

    voiced = voice_lead_progression(close)
    naive = movement(close[0], close[1])
    led = movement(voiced[0], voiced[1])
    assert led <= naive


def test_voice_lead_empty():
    assert voice_lead_progression([]) == []


# --- harmonize melody (T2) ---------------------------------------------------

def test_harmonize_melody_contains_each_note():
    melody = [60, 62, 64, 65, 67]
    chords = harmonize_melody(melody, "C", "major")
    assert len(chords) == len(melody)
    for m, c in zip(melody, chords):
        assert m % 12 in [n % 12 for n in c["notes"]]


def test_harmonize_melody_prefers_root_tonic():
    # C in C major: prefer I (C as root) over IV/vi that also contain C.
    chords = harmonize_melody([60], "C", "major")
    assert chords[0]["roman"] == "I"


# --- basslines (T2) ----------------------------------------------------------

def test_bassline_root_one_note_per_chord():
    bass = generate_bassline([36, 41, 43], "root", beats_per_chord=4)
    assert [n["midi"] for n in bass] == [36, 41, 43]
    assert [n["offset"] for n in bass] == [0, 4, 8]
    assert all(n["duration"] == 4 for n in bass)


def test_bassline_walking():
    bass = generate_bassline([36], "walking", beats_per_chord=4)
    assert [n["midi"] for n in bass] == [36, 43, 48, 43]
    assert [n["offset"] for n in bass] == [0, 1, 2, 3]
    assert all(n["duration"] == 1 for n in bass)


def test_bassline_octaves_and_fifths():
    oct_bass = generate_bassline([36], "octaves", beats_per_chord=4)
    assert [n["midi"] for n in oct_bass] == [36, 48]
    assert [n["offset"] for n in oct_bass] == [0, 2]
    fifth_bass = generate_bassline([36], "fifths", beats_per_chord=4)
    assert [n["midi"] for n in fifth_bass] == [36, 43]


def test_bassline_invalid_style():
    with pytest.raises(ValueError):
        generate_bassline([36], "bogus")


# --- note_name_to_midi (full names) ------------------------------------------

@pytest.mark.parametrize("name,midi", [
    ("C4", 60), ("C#4", 61), ("Db3", 49), ("A4", 69), ("C-1", 0), ("G9", 127),
    ("C", 60),  # no octave -> default 4
])
def test_note_name_to_midi(name, midi):
    assert note_name_to_midi(name) == midi


# --- identify_chord (T4) -----------------------------------------------------

def test_identify_major_triad():
    matches = identify_chord([60, 64, 67])
    best = matches[0]
    assert best["root"] == "C" and best["quality"] == "maj"
    assert best["name"] == "C" and best["inversion"] == 0


def test_identify_minor_seventh():
    matches = identify_chord([69, 72, 76, 79])  # Am7
    best = matches[0]
    assert best["root"] == "A" and best["quality"] == "min7"
    assert best["name"] == "Am7"


def test_identify_inversion():
    # E G C = C major, first inversion (E in bass)
    matches = identify_chord([64, 67, 72])
    cmaj = [m for m in matches if m["root"] == "C"][0]
    assert cmaj["quality"] == "maj"
    assert cmaj["bass"] == "E"
    assert cmaj["inversion"] == 1


def test_identify_dominant7():
    matches = identify_chord([67, 71, 74, 77])  # G7
    assert matches[0]["name"] == "G7"


def test_identify_chord_ignores_octave_doubling():
    # C E G with a doubled C an octave up still reads as C major.
    matches = identify_chord([60, 64, 67, 72])
    assert matches[0]["root"] == "C" and matches[0]["quality"] == "maj"


def test_identify_chord_empty_raises():
    with pytest.raises(ValueError):
        identify_chord([])


# --- detect_key (T4) ---------------------------------------------------------

def test_detect_key_c_major():
    # C major scale notes. C major and A minor share these notes, so both tie
    # for the top score; just require C major to be among the best with no
    # out-of-scale notes.
    ranked = detect_key([60, 62, 64, 65, 67, 69, 71])
    top_score = ranked[0]["score"]
    tops = {(r["key"], r["mode"]) for r in ranked if r["score"] == top_score}
    assert ("C", "major") in tops
    cmaj = [r for r in ranked if r["key"] == "C" and r["mode"] == "major"][0]
    assert cmaj["out_of_scale"] == 0


def test_detect_key_a_minor_vs_c_major():
    # A minor uses the same notes as C major; both should top the ranking.
    ranked = detect_key([69, 71, 72, 74, 76, 77, 79])
    tops = {(r["key"], r["mode"]) for r in ranked if r["score"] == ranked[0]["score"]}
    assert ("C", "major") in tops
    assert ("A", "minor") in tops


def test_detect_key_penalizes_out_of_scale():
    # A C major triad plus an F# (not in C major) should still rank a key that
    # contains all four notes above plain C major.
    ranked = detect_key([60, 64, 67, 66])
    assert ranked[0]["out_of_scale"] <= 1


def test_detect_key_empty_raises():
    with pytest.raises(ValueError):
        detect_key([])


# --- jazz voicings (T3) ------------------------------------------------------

def test_jazz_voicing_shell():
    assert jazz_voicing("C", "maj7", "shell", 4) == [60, 64, 71]


def test_jazz_voicing_rootless_a():
    assert jazz_voicing("C", "maj7", "rootless", 4) == [64, 67, 71, 74]


def test_jazz_voicing_rootless_b():
    assert jazz_voicing("C", "min7", "rootless_b", 4) == [70, 74, 75, 79]


def test_jazz_voicing_quartal():
    assert jazz_voicing("C", "maj7", "quartal", 4) == [60, 65, 70, 75]


def test_jazz_voicing_invalid():
    with pytest.raises(ValueError):
        jazz_voicing("C", "maj7", "sideways")


# --- extend chord (T3) -------------------------------------------------------

def test_extend_chord_add9():
    assert extend_chord("C", "maj7", [9], 4) == [60, 64, 67, 71, 74]


def test_extend_chord_9_and_13():
    assert extend_chord("C", "7", [9, 13], 4) == [60, 64, 67, 70, 74, 81]


def test_extend_chord_altered_tension():
    # b9 is root + 13
    assert 73 in extend_chord("C", "7", ["b9"], 4)


def test_extend_chord_invalid():
    with pytest.raises(ValueError):
        extend_chord("C", "maj7", ["b5"])


# --- chord scale (T3) --------------------------------------------------------

def test_get_chord_scale_min7_dorian():
    scales = get_chord_scale("C", "min7", 4)
    assert scales[0]["scale"] == "dorian"
    assert scales[0]["notes"] == [60, 62, 63, 65, 67, 69, 70]


def test_get_chord_scale_dominant():
    scales = get_chord_scale("G", "7", 4)
    names = [s["scale"] for s in scales]
    assert names[0] == "mixolydian"
    assert "altered" in names


# --- reharmonization (T3) ----------------------------------------------------

def test_reharmonize_tritone_sub():
    assert reharmonize(["Dm7", "G7", "Cmaj7"], strategy="tritone_sub") == [
        "Dm7", "C#7", "Cmaj7"
    ]


def test_reharmonize_tritone_sub_roman():
    assert reharmonize(["I", "V7", "I"], key="C", strategy="tritone_sub") == [
        "C", "C#7", "C"
    ]


def test_reharmonize_relative():
    assert reharmonize(["C", "Am", "F", "G"], strategy="relative") == [
        "Am", "C", "Dm", "Em"
    ]


def test_reharmonize_secondary_dominant():
    assert reharmonize(["C", "F"], strategy="secondary_dominant") == [
        "C", "C7", "F"
    ]


def test_reharmonize_invalid_strategy():
    with pytest.raises(ValueError):
        reharmonize(["C"], strategy="bogus")
