"""Transcript ingestion: plain text (optionally timestamped), SRT and WebVTT."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from .parse import (
    ParseError,
    Segment,
    Transcript,
    extract_leading_ts,
    parse_ts,
    strip_leading_ts,
)

_ARROW = "-->"

_CUE_TS_RE = re.compile(
    r"""(?P<start>\d{1,3}:\d{1,2}:\d{1,2}(?:[.,]\d{1,3})?|\d{1,2}:\d{1,2}(?:[.,]\d{1,3})?)
        \s*-->\s*
        (?P<end>\d{1,3}:\d{1,2}:\d{1,2}(?:[.,]\d{1,3})?|\d{1,2}:\d{1,2}(?:[.,]\d{1,3})?)""",
    re.VERBOSE,
)


def detect_format(text: str, filename: Optional[str] = None) -> str:
    """Best-effort guess: 'srt' or 'vtt' when cue arrows appear, else 'plain'."""
    suffix = (Path(filename).suffix.lower() if filename else "")
    if suffix in (".srt", ".vtt"):
        return "vtt" if suffix == ".vtt" else "srt"
    lowered = text[:2000].lstrip().lower()
    if lowered.startswith("webvtt") or "NOTE" in text[:400]:
        return "vtt"
    if _ARROW in text:
        return "srt"
    return "plain"


def parse_file(path: str) -> Transcript:
    p = Path(path)
    if not p.is_file():
        raise ParseError(f"input file not found: {path}")
    text = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix.lower() == ".srt":
        return parse_srt(text)
    if p.suffix.lower() == ".vtt":
        return parse_vtt(text)
    fmt = detect_format(text, str(p))
    if fmt == "srt":
        return parse_srt(text)
    if fmt == "vtt":
        return parse_vtt(text)
    return parse_plain(text)


def parse_text(
    text: str,
    fmt: Optional[str] = None,
    interval: Optional[float] = None,
    offset: float = 0.0,
) -> Transcript:
    fmt = fmt or detect_format(text)
    if fmt == "srt":
        return parse_srt(text)
    if fmt == "vtt":
        return parse_vtt(text)
    return parse_plain(text, interval=interval, offset=offset)


def _seconds(raw: str) -> float:
    return parse_ts(raw.replace(",", "."))


# --------------------------------------------------------------------------
# SRT / VTT
# --------------------------------------------------------------------------

def parse_srt(text: str) -> Transcript:
    segments: List[Segment] = []
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    for block in blocks:
        lines = block.strip().splitlines()
        cue_line = next((ln for ln in lines if _ARROW in ln), None)
        if cue_line is None:
            continue
        m = _CUE_TS_RE.search(cue_line)
        if not m:
            continue
        start = _seconds(m.group("start"))
        end = _seconds(m.group("end"))
        body = lines[lines.index(cue_line) + 1:]
        body_text = " ".join(strip_speaker_dashes(l.strip()) for l in body).strip()
        if body_text:
            segments.append(Segment(text=body_text, start=start, end=end))
    if not segments:
        raise ParseError("no subtitle cues found; file does not look like SRT")
    segments.sort(key=lambda s: s.start)
    return Transcript(segments=segments, had_timestamps=True, source_format="srt")


def parse_vtt(text: str) -> Transcript:
    segments: List[Segment] = []
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    for block in blocks:
        lines = block.strip().splitlines()
        if lines and lines[0].lower().startswith(("webvtt", "note", "style")):
            lines = lines[1:]
        cue_line = next((ln for ln in lines if _ARROW in ln), None)
        if cue_line is None:
            continue
        m = _CUE_TS_RE.search(cue_line)
        if not m:
            continue
        start = _seconds(m.group("start"))
        end = _seconds(m.group("end"))
        body = lines[lines.index(cue_line) + 1:]
        body_text = " ".join(strip_speaker_dashes(l.strip()) for l in body).strip()
        if body_text:
            segments.append(Segment(text=body_text, start=start, end=end))
    if not segments:
        raise ParseError("no cues found; file does not look like WebVTT")
    segments.sort(key=lambda s: s.start)
    return Transcript(segments=segments, had_timestamps=True, source_format="vtt")


def strip_speaker_dashes(line: str) -> str:
    return line.lstrip("-–—").strip()


# --------------------------------------------------------------------------
# plain text
# --------------------------------------------------------------------------

def parse_plain(
    text: str,
    interval: Optional[float] = None,
    offset: float = 0.0,
) -> Transcript:
    """Parse a raw plain-text transcript.

    Lines beginning with a timestamp (``[0:41] today we...`` or
    ``00:41 today we...``) become time-anchored paragraphs. Lines are grouped
    into paragraphs separated by blank lines. If the transcript carries no
    timestamps and *interval* (seconds) is given, each paragraph is assigned an
    evenly spaced synthetic timestamp starting at *offset*.
    """
    segments: List[Segment] = []
    had_ts = False

    current_text: List[str] = []
    current_start: Optional[float] = None

    def flush() -> None:
        nonlocal current_text, current_start
        body = " ".join(current_text).strip()
        if body:
            segments.append(Segment(text=body, start=current_start))
        current_text, current_start = [], None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        ts = extract_leading_ts(line)
        if ts is not None:
            had_ts = True
            flush()
            current_start = ts
            line = strip_leading_ts(line)
            if not line:
                continue
            current_text.append(line)
        elif current_start is None:
            # No anchor yet: keep original blank-line paragraph grouping.
            flush()
            current_text.append(line)
        else:
            current_text.append(line)
    flush()

    if not segments:
        raise ParseError("transcript is empty")

    if not had_ts and interval is not None:
        t = offset
        for seg in segments:
            seg.start = t
            t += interval
        had_ts = True

    if offset:
        for seg in segments:
            if seg.start is not None:
                seg.start += offset

    return Transcript(segments=segments, had_timestamps=had_ts, source_format="plain")
