"""Gap filler used by boundary tests: N sections, each about one minute long."""

from transcript_chapter_marker.intake import parse_text


def section_text(i: int) -> str:
    # distinct keyword per section so titles are predictable
    return f"[{i}:00] Topic word{'%02d' % i} section {i}. " + " filler word sentence " * 6


def make_transcript(sections: int = 4):
    return parse_text("\n\n".join(section_text(i) for i in range(sections)))
