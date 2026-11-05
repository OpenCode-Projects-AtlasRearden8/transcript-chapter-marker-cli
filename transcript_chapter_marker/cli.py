"""Command line interface for transcript-chapter-marker."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .chapters import build_chapters
from .intake import parse_plain, parse_text
from .llm import LLMError, UnsafeEndpointError, name_chapters
from .parse import ParseError, parse_ts
from .render import render
from .topics import title_case

_FORMATS = ("index", "chapter-list", "topics", "annotated", "all")

EPILOG = (
    "Runs fully offline unless --llm is passed. Topic naming works with any "
    "OpenAI-compatible endpoint, e.g. Ollama:\n"
    "  --llm --llm-base-url http://localhost:11434/v1 --llm-model llama3.2\n"
    "A key (if your endpoint needs one) is read from env TRANSCRIPT_LLM_API_KEY.\n"
    "Built by Asdale Dynamics, LLC. MIT licensed."
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="transcript-chapter-marker",
        description="Add chapter markers, a clickable mm:ss index and a topics "
        "list to a raw transcript (plain text, SRT or VTT).",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help="transcript file (plain text, .srt, .vtt) or '-' for stdin")
    p.add_argument(
        "--format",
        nargs="*",
        default=["all"],
        choices=_FORMATS,
        metavar="FMT",
        help="one or more of: index, chapter-list, topics, annotated, all "
        "(default: all)",
    )
    p.add_argument(
        "--clickable",
        metavar="URL",
        help="make the mm:ss index clickable, e.g. the watch URL of a "
        "YouTube video (adds t=...s deep links)",
    )
    p.add_argument(
        "--target-min",
        type=float,
        default=5.0,
        metavar="MIN",
        help="target chapter length in minutes (default: 5)",
    )
    p.add_argument(
        "--topics",
        type=int,
        default=8,
        metavar="N",
        help="number of topics to list (default: 8)",
    )
    p.add_argument(
        "--interval",
        metavar="TS",
        help="plain text without timestamps: assume paragraphs spaced "
        "this far apart, e.g. 0:30",
    )
    p.add_argument(
        "--offset",
        default="0:00",
        metavar="TS",
        help="shift all timestamps by this amount (default: 0:00)",
    )
    p.add_argument(
        "--llm",
        action="store_true",
        help="opt in: name chapters via an OpenAI-compatible endpoint "
        "(off by default; nothing leaves your machine without this)",
    )
    p.add_argument(
        "--llm-base-url",
        default="http://localhost:11434/v1",
        metavar="URL",
        help="endpoint base URL (default: local Ollama)",
    )
    p.add_argument(
        "--llm-model",
        default="llama3.2",
        metavar="MODEL",
        help="model name (default: llama3.2)",
    )
    p.add_argument(
        "--llm-timeout",
        type=float,
        default=30.0,
        metavar="SEC",
        help="LLM request timeout in seconds (default: 30)",
    )
    p.add_argument("--out", metavar="FILE", help="write result to FILE instead of stdout")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _expand_formats(formats: List[str]) -> List[str]:
    out: List[str] = []
    for f in formats:
        if f == "all":
            out.extend(["index", "chapter-list", "topics"])
        else:
            out.append(f)
    seen, ordered = set(), []
    for f in out:
        if f not in seen:
            seen.add(f)
            ordered.append(f)
    return ordered


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.input == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.input).read_text(encoding="utf-8", errors="replace")

    try:
        transcript = parse_text(text)
    except ParseError:
        # wrong extension/content mix fallbacks were handled; plain errors here
        raise

    interval = None
    if args.interval:
        interval = parse_ts(args.interval)
        if not transcript.had_timestamps and transcript.source_format == "plain":
            transcript = parse_plain(text, interval=interval, offset=0.0)

    if args.offset:
        off = parse_ts(args.offset)
        for seg in transcript.segments:
            if seg.start is not None:
                seg.start += off

    chapters = build_chapters(
        transcript.segments,
        target_minutes=args.target_min,
        had_timestamps=transcript.had_timestamps,
    )

    warnings: List[str] = []
    if args.llm and chapters:
        try:
            titles = name_chapters(
                chapters,
                excerpt_chars=400,
                base_url=args.llm_base_url,
                model=args.llm_model,
                timeout=args.llm_timeout,
            )
            for ch, t in zip(chapters, titles):
                ch.title = title_case(t.lower() if t.isupper() else t)
        except UnsafeEndpointError as exc:
            print(f"warning: {exc}; keeping offline keyword titles", file=sys.stderr)
        except LLMError as exc:
            warnings.append(f"LLM naming failed ({exc}); using offline titles")
            print(f"warning: {warnings[-1]}", file=sys.stderr)

    output = render(
        transcript,
        chapters,
        formats=_expand_formats(args.format),
        clickable_url=args.clickable,
        max_topics=args.topics,
    )

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"wrote {args.out}")
        for w in warnings:
            print(w, file=sys.stderr)
    else:
        print(output, end="")
    return 0


def cli() -> None:
    try:
        raise SystemExit(main())
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    cli()
