from transcript_chapter_marker.chapters import build_chapters
from transcript_chapter_marker.intake import parse_text
from transcript_chapter_marker.render import (
    annotate_transcript,
    audiobook_chapters,
    render,
    youtube_index,
)
from . import FIXTURES

TEXT = (FIXTURES / "timestamped.txt").read_text(encoding="utf-8")


def chapters_of(text=TEXT, target=5.0):
    t = parse_text(text)
    return t, build_chapters(t.segments, target_minutes=target, had_timestamps=True)


def test_plain_index_lines():
    _, chs = chapters_of()
    lines = youtube_index(chs)
    assert lines[0].startswith("00:00 ")
    assert lines[1].startswith("05:12 ")
    assert len(lines) == 2


def test_clickable_index_lines():
    _, chs = chapters_of()
    lines = youtube_index(chs, clickable_url="https://youtu.be/abc123")
    assert "[00:00](https://youtu.be/abc123?t=0s)" in lines[0]
    assert "[05:12](https://youtu.be/abc123?t=312s)" in lines[1]
    assert lines[0].endswith(chs[0].title)


def test_clickable_url_with_existing_query():
    _, chs = chapters_of()
    lines = youtube_index(chs, clickable_url="https://x.com/watch?v=1")
    assert "?v=1&t=0s" in lines[0]


def test_audiobook_chapters():
    _, chs = chapters_of()
    lines = audiobook_chapters(chs)
    assert lines[0].startswith("00:00:00 - Chapter 1:")
    assert lines[1].startswith("00:05:12 - Chapter 2:")


def test_annotated_transcript_inserts_markers():
    t, chs = chapters_of()
    annotated = annotate_transcript(t, chs)
    assert "=== 00:05:12 | " in annotated
    assert annotated.count("===") == 2  # only non-first chapters get a marker
    assert "Welcome to the workshop" in annotated


def test_render_all_sections():
    t, chs = chapters_of()
    out = render(t, chs, formats=["index", "chapter-list", "topics"])
    assert out.startswith("Chapters\n")
    assert "05:12" in out
    assert "Audiobook chapters" in out
    assert "Topics" in out


def test_render_no_timestamps_warns_in_index():
    text = (FIXTURES / "plain_no_ts.txt").read_text(encoding="utf-8")
    t = parse_text(text)
    chs = build_chapters(t.segments, target_minutes=1.0, had_timestamps=False)
    out = render(t, chs, formats=["index"])
    assert "(no timestamps; pass --interval)" in out
    assert "--:--" in out
