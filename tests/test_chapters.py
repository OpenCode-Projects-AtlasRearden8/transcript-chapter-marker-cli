from transcript_chapter_marker.chapters import build_chapters
from transcript_chapter_marker.intake import parse_text
from transcript_chapter_marker.topics import top_terms, title_case
from . import FIXTURES


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_chapter_boundaries_five_minute_target():
    # five timestamped paragraphs spanning 0..7:05 -> 2 chapters at 5 min target
    from transcript_chapter_marker.intake import parse_text

    t = parse_text(read("timestamped.txt"))
    chapters = build_chapters(t.segments, target_minutes=5.0, had_timestamps=True)
    assert len(chapters) == 2
    assert chapters[0].start == 0.0
    assert chapters[1].start == 312.0  # 5:12 is the first cue past 5 minutes
    assert all(ch.title for ch in chapters)


def test_chapter_titles_are_derived_from_text():
    import re

    t = parse_text(read("timestamped.txt"))
    chapters = build_chapters(t.segments, target_minutes=5.0, had_timestamps=True)
    for ch in chapters:
        assert re.fullmatch(r"[A-Z][A-Za-z& ]+", ch.title), ch.title
        assert "Chapter" not in ch.title


def test_top_terms_captures_named_topics():
    top = top_terms(["Privacy is the point: your words never leave this machine."], n=3)
    assert any("privacy" == t for t, _c in top)


def test_no_timestamps_segment_count_fallback():
    from transcript_chapter_marker.intake import parse_text

    t = parse_text(read("plain_no_ts.txt"))  # 4 paragraphs, no times
    chapters = build_chapters(t.segments, target_minutes=1.0, had_timestamps=False)
    assert len(chapters) >= 2
    assert all(ch.start is None for ch in chapters)


def test_top_terms_prefers_repeated_bigrams():
    text = "the studio lights glow. the studio lights glow again. hello world"
    top = top_terms([text], n=3)
    assert top[0][0] == "studio lights"


def test_title_case():
    assert title_case("studio lights") == "Studio Lights"
    assert title_case("law of the sea") == "Law of the Sea"
