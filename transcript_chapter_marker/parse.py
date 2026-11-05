"""Timestamp parsing/formatting and transcript segment model.

Only the Python standard library is used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


class ParseError(ValueError):
    """Raised when a transcript cannot be parsed."""


@dataclass
class Segment:
    """One piece of transcript text, optionally anchored to a time."""

    text: str
    start: Optional[float] = None  # seconds
    end: Optional[float] = None  # seconds

    @property
    def has_time(self) -> bool:
        return self.start is not None


@dataclass
class Transcript:
    segments: List[Segment] = field(default_factory=list)
    had_timestamps: bool = False
    source_format: str = "plain"  # "plain" | "srt" | "vtt"

    @property
    def text(self) -> str:
        return "\n".join(seg.text for seg in self.segments)

    @property
    def duration(self) -> Optional[float]:
        times = [s.start for s in self.segments if s.start is not None]
        if not times:
            return None
        last_end = [s.end for s in self.segments if s.end is not None]
        if times and last_end:
            return max(times[-1], max(last_end))
        return times[-1]


# --------------------------------------------------------------------------
# timestamp helpers
# --------------------------------------------------------------------------

_FULL_TS_RE = re.compile(
    r"""^(?:(?P<h>\d{1,3}):)?
    (?P<m>\d{1,2}):(?P<s>\d{1,2})
    (?:[.,](?P<frac>\d{1,4}))?$""",
    re.VERBOSE,
)
_PLAIN_SECONDS_RE = re.compile(r"^\d+(?:[.,]\d+)?$")

# a timestamp at the start of a plain-text line, e.g. "[00:41] we..." or "0:41 we..."
_LINE_TS_RE = re.compile(
    r"""^\s*\[?\s*
    (?:(?P<h>\d{1,3}):)?
    (?P<m>\d{1,2}):
    (?P<s>\d{1,2})
    (?:[,.](?P<frac>\d{1,4}))?
    \s*\]?\s+""",
    re.VERBOSE,
)


def parse_ts(value: str) -> float:
    """Parse 'mm:ss', 'h:mm:ss', or plain seconds-with-fraction into seconds."""
    v = value.strip().replace(",", ".")
    m = _FULL_TS_RE.match(v)
    if m:
        h = int(m.group("h") or 0)
        mi = int(m.group("m"))
        s = int(m.group("s"))
        frac = m.group("frac") or ""
        frac_s = float("0." + frac) if frac else 0.0
        return h * 3600 + mi * 60 + s + frac_s
    if _PLAIN_SECONDS_RE.match(v):
        return float(v)
    raise ParseError(f"unrecognized timestamp: {value!r}")


def clamp_seconds(sec: float) -> int:
    return max(0, int(round(sec)))


def format_mmss(sec: Optional[float]) -> str:
    """'mm:ss' index style used by YouTube descriptions (zero-padded)."""
    if sec is None:
        return "--:--"
    t = clamp_seconds(sec)
    m, s = divmod(t, 60)
    if m < 100:
        return f"{m:02d}:{s:02d}"
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}"


def format_hhmmss(sec: Optional[float]) -> str:
    """'hh:mm:ss' style used for audiobook chapter lists."""
    if sec is None:
        return "--:--:--"
    t = clamp_seconds(sec)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def extract_leading_ts(line: str) -> Optional[float]:
    """If *line* starts with a timestamp (optionally bracketed), return its
    seconds and drop the timestamp from the line."""
    m = _LINE_TS_RE.match(line)
    if not m:
        return None
    h = int(m.group("h") or 0)
    seconds = h * 3600 + int(m.group("m")) * 60 + int(m.group("s"))
    frac = m.group("frac") or ""
    if frac:
        seconds += float("0." + frac)
    return seconds


def strip_leading_ts(line: str) -> str:
    m = _LINE_TS_RE.match(line)
    return line[m.end():] if m else line
