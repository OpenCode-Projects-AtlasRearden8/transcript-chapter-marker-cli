"""Renderers: YouTube index, audiobook chapter list, annotated transcript, topics."""

from __future__ import annotations

from typing import List, Optional, Sequence

from .chapters import Chapter
from .parse import Transcript, format_hhmmss, format_mmss
from .topics import top_terms

CLICKABLE_URL = "https://www.example.com/watch?v=VIDEO"


def _t_seconds(sec: Optional[float]) -> int:
    return max(0, int(round(sec or 0)))


def youtube_index(
    chapters: Sequence[Chapter], clickable_url: Optional[str] = None
) -> List[str]:
    lines: List[str] = []
    for ch in chapters:
        stamp = format_mmss(ch.start) if ch.start is not None else "--:--"
        if clickable_url:
            url = clickable_url.rstrip("/")
            joiner = "&" if "?" in url else "?"
            lines.append(f"[{stamp}]({url}{joiner}t={_t_seconds(ch.start)}s) {ch.title}")
        else:
            lines.append(f"{stamp} {ch.title}")
    return lines


def audiobook_chapters(chapters: Sequence[Chapter]) -> List[str]:
    lines = []
    for ch in chapters:
        stamp = format_hhmmss(ch.start) if ch.start is not None else "00:00:00"
        lines.append(f"{stamp} - Chapter {ch.index + 1}: {ch.title}")
    return lines


def topics_lines(transcript: Transcript, max_topics: int = 8) -> List[str]:
    texts = [s.text for s in transcript.segments]
    terms = top_terms(texts, n=max_topics)
    return [f"{title_case_ok(t)} ({c})" for t, c in terms]


def title_case_ok(phrase: str) -> str:
    from .topics import title_case

    return title_case(phrase)


def annotate_transcript(
    transcript: Transcript,
    chapters: Sequence[Chapter],
    marker: str = "=== {stamp} | {title} ===",
) -> str:
    """Insert chapter marker lines before the first segment of each chapter."""
    chapter_starts = {}
    for ch in chapters:
        if ch.segments:
            chapter_starts[id(ch.segments[0])] = ch

    out_lines: List[str] = []
    for seg in transcript.segments:
        ch = chapter_starts.get(id(seg))
        if ch is not None and ch.index > 0:
            stamp = format_hhmmss(ch.start) if ch.start is not None else "00:00:00"
            out_lines.append(marker.format(stamp=stamp, title=ch.title))
        text = seg.text
        out_lines.append(text)
    return "\n\n".join(out_lines)


def render(
    transcript: Transcript,
    chapters: Sequence[Chapter],
    *,
    formats: Sequence[str],
    clickable_url: Optional[str] = None,
    max_topics: int = 8,
) -> str:
    sections: List[str] = []
    if "index" in formats:
        lines = youtube_index(chapters, clickable_url)
        suffix = "" if transcript.had_timestamps else " (no timestamps; pass --interval)"
        sections.append("Chapters\n" + "\n".join(lines) + suffix)
    if "chapter-list" in formats:
        sections.append(
            "Audiobook chapters\n" + "\n".join(audiobook_chapters(chapters))
        )
    if "topics" in formats:
        tl = topics_lines(transcript, max_topics)
        sections.append("Topics\n" + "\n".join(tl))
    if "annotated" in formats:
        sections.append(
            "Annotated transcript\n" + annotate_transcript(transcript, chapters)
        )
    return "\n\n".join(sections) + "\n"
