"""Chapter segmentation and keyword-based chapter titles (offline)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .parse import Segment
from .topics import title_case, top_terms


@dataclass
class Chapter:
    index: int
    start: Optional[float]  # seconds; None when the transcript has no timing
    end: Optional[float]
    title: str
    segments: List[Segment]


def _keyword_title(texts: Sequence[str], index: int) -> str:
    terms = top_terms(texts, n=3)
    if not terms:
        return f"Chapter {index + 1}"
    picks: list = []
    for phrase, _count in terms[:2]:
        if not any(set(phrase.split()) & set(p.split()) for p in picks):
            picks.append(phrase)
    return title_case(" & ".join(picks))


def build_chapters(
    segments: Sequence[Segment],
    target_minutes: float = 5.0,
    had_timestamps: bool = True,
) -> List[Chapter]:
    """Split *segments* into chapters of roughly *target_minutes*.

    A new chapter starts at the first segment that begins at least
    ``target_minutes`` after the previous chapter's start. Without timestamps,
    segmentation falls back to even shares of the segment count.
    """
    if not segments:
        return []

    total = len(segments)
    target_sec = max(0.5, float(target_minutes)) * 60.0

    starts: List[int] = [0]
    if had_timestamps:
        anchor = segments[0].start or 0.0
        for i, seg in enumerate(segments):
            if seg.start is None:
                continue
            if seg.start - anchor >= target_sec:
                if i != starts[-1]:
                    starts.append(i)
                anchor = seg.start
    else:
        step = max(1, round(target_sec / 60.0))
        pos = step
        while pos < total:
            starts.append(pos)
            pos += step

    chapters: List[Chapter] = []
    for n, s in enumerate(starts):
        e = starts[n + 1] if n + 1 < len(starts) else total
        chunks = list(segments[s:e])
        start = chunks[0].start if had_timestamps else None
        end = chunks[-1].end
        if end is None and had_timestamps and chunks[-1].start is not None:
            end = chunks[-1].start
        title = _keyword_title([c.text for c in chunks], n)
        chapters.append(
            Chapter(index=n, start=start, end=end, title=title, segments=chunks)
        )
    return chapters
