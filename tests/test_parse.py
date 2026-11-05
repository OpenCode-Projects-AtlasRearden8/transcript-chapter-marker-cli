import pytest

from transcript_chapter_marker.intake import detect_format, parse_file, parse_text
from transcript_chapter_marker.parse import (
    ParseError,
    format_hhmmss,
    format_mmss,
    parse_ts,
)
from .fixtures.long_transcript import make_transcript

FIXTURES = "tests/fixtures"


def test_parse_ts_variants():
    assert parse_ts("0:41") == 41
    assert parse_ts("1:02:03") == 3600 + 2 * 60 + 3
    assert parse_ts("00:00:41,500") == 41.5
    assert parse_ts("41") == 41.0


def test_format_helpers():
    assert format_mmss(0) == "00:00"
    assert format_mmss(301) == "05:01"
    assert format_mmss(None) == "--:--"
    assert format_hhmmss(0) == "00:00:00"
    assert format_hhmmss(3671) == "01:01:11"


def test_detect_format():
    assert detect_format("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhi") == "vtt"
    assert detect_format("1\n00:00:00,000 --> 00:00:01,000\nhi") == "srt"
    assert detect_format("just some words") == "plain"


def test_parse_srt_fixture():
    t = parse_file(f"{FIXTURES}/sample.srt")
    assert len(t.segments) == 5
    assert t.had_timestamps and t.source_format == "srt"
    assert t.segments[0].start == 0.0
    assert t.segments[4].start == 185.0
    assert "Ollama" in t.segments[1].text


def test_parse_vtt_fixture():
    t = parse_file(f"{FIXTURES}/sample.vtt")
    assert len(t.segments) == 5
    assert t.had_timestamps and t.source_format == "vtt"
    assert "laptop" in t.segments[0].text


def test_parse_plain_with_leading_timestamps():
    t = parse_file(f"{FIXTURES}/timestamped.txt")
    assert len(t.segments) == 8
    assert t.had_timestamps
    assert t.segments[2].start == 90.0
    assert not t.segments[2].text.startswith("[")


def test_parse_plain_no_timestamps_interval():
    text = (open(f"{FIXTURES}/plain_no_ts.txt", encoding="utf-8").read())
    t = parse_text(text)
    assert not t.had_timestamps
    assert all(s.start is None for s in t.segments)

    with_interval = parse_text(text, interval=60.0)
    assert with_interval.had_timestamps
    assert [s.start for s in with_interval.segments] == [0.0, 60.0, 120.0, 180.0, 240.0]


def test_stdin_style_strings():
    t = parse_text("[0:10] hello\n[0:30] world")
    assert t.segments[0].start == 10 and t.segments[1].start == 30


def test_empty_input_raises():
    with pytest.raises(ParseError):
        parse_text("")


def test_long_transcript_helper():
    t = make_transcript(4)
    assert len(t.segments) == 4
    assert t.segments[-1].start == 180
