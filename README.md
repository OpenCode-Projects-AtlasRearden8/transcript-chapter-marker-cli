# transcript-chapter-marker-cli

Offline CLI that takes a raw transcript (plain text, SRT or WebVTT) and turns it
into something you can actually publish: chapter markers, a clickable `-mm:ss`
index, and a topics list — ready for YouTube descriptions or audiobook chapter
lists.

Everything runs locally with the Python standard library only. Topic naming via
an OpenAI-compatible endpoint (Ollama, LM Studio, llama.cpp server, ...) is
**off by default** and requires no API keys.

Built by **Asdale Dynamics, LLC** — plain-English AI tools, tested first.
Part of the beginner-friendly toolset around *The Massive AI Manual*
(hub site: dylanasdale.github.io). Distinct sibling project:
`voice-notes-transcriber-cli` (capturing voice memos to text). This one works on
transcripts you already have.

## Why

Auto-transcribers give you a wall of text. YouTube wants:

```text
00:00 Setup
05:12 When Things Go Sideways
```

Audiobook tools want a chapter list with `hh:mm:ss`. Readers want topic hints.
This tool writes all three from one file, on your machine, in under a second.

## Install

```bash
# Python 3.10+ required. Nothing to install beyond pytest if you want tests.
pip install -e .            # optional: gives you the `tcm` command
# or run straight from the repo:
python -m transcript_chapter_marker <transcript-file> [options]
```

## Quick start

```bash
# Plain transcript with [mm:ss] prefixes
python -m transcript_chapter_marker talk.txt

# SubRip or WebVTT captions
python -m transcript_chapter_marker captions.srt
python -m transcript_chapter_marker captions.vtt

# Clickable YouTube index for a specific video
python -m transcript_chapter_marker talk.txt --clickable "https://youtu.be/VIDEO_ID"

# Shorter chapters, only the description blocks, save to file
python -m transcript_chapter_marker talk.txt --format index topics --target-min 3 -o description.txt

# No timestamps in your plain text? Space paragraphs a minute apart:
python -m transcript_chapter_marker notes.txt --interval 1:00

# Name chapters with a local Ollama model (no API key needed)
python -m transcript_chapter_marker talk.txt --llm --llm-model llama3.2
```

## Input formats

| File | How it is understood |
|---|---|
| Plain text with timestamps | Lines like `[0:41] today we...` or `00:41 today we...` |
| Plain text without timestamps | Paragraphs split on blank lines; give `--interval` to space them |
| `.srt` | Standard SubRip cues (`00:00:41,000 --> 00:00:44,000`) |
| `.vtt` | WebVTT cues (`00:00:41.000 --> 00:00:44.000`) |
| stdin | Pass `-` to pipe a transcript in |

## Output sections

- **Chapters** — the YouTube description block, `mm:ss Title` per line.
  With `--clickable URL` each stamp becomes `[mm:ss](URL?t=…s)` markdown.
- **Audiobook chapters** — `00:05:12 - Chapter 2: …` lines for chapter tools.
- **Topics** — the most-repeated keyphrases, computed locally.
- **Annotated transcript** — with `--format annotated`, chapter markers
  (`=== 00:05:12 | When Things Go Sideways ===`) are inserted into the
  transcript itself.

Default output is all description-ready sections. Pick any subset with
`--format index chapter-list topics annotated` (or `all`).

## CLI reference

```
usage: transcript-chapter-marker [-h] [--format FMT ...] [--clickable URL]
       [--target-min MIN] [--topics N] [--interval TS] [--offset TS]
       [--llm] [--llm-base-url URL] [--llm-model MODEL]
       [--llm-timeout SEC] [--out FILE] [--version] input
```

| Option | Default | Meaning |
|---|---|---|
| `input` | required | transcript file (`.txt`, `.srt`, `.vtt`) or `-` for stdin |
| `--format` | `all` | `index`, `chapter-list`, `topics`, `annotated`, or `all` |
| `--clickable URL` | off | make index stamps deep-link to this URL |
| `--target-min` | `5.0` | rough chapter length in minutes |
| `--topics` | `8` | how many topics to list |
| `--interval TS` | off | assign synthetic timestamps to untimed paragraphs |
| `--offset TS` | `0:00` | shift every timestamp forward |
| `--out FILE` | stdout | write the result to a file |
| `--llm` | off | **opt in** to naming chapters via a chat endpoint |

## Topic naming with LLMs (optional, off by default)

Chapter titles are guessed offline from word statistics, which is fine for
most things. If you want friendlier titles, pass `--llm` and the tool sends
*only* the transcript excerpts to the endpoint you config:

```bash
ollama pull llama3.2          # once
python -m transcript_chapter_marker talk.txt --llm \
    --llm-base-url http://localhost:11434/v1 --llm-model llama3.2
```

- Works with **any OpenAI-compatible** `/v1/chat/completions` endpoint: Ollama,
  LM Studio, llama.cpp, vLLM, or a hosted one.
- API keys are never stored. If your endpoint needs one, set the
  `TRANSCRIPT_LLM_API_KEY` environment variable; it is used per-request and
  never written anywhere.
- **Privacy guard:** plain `http://` endpoints are only allowed for loopback
  addresses (localhost/127.0.0.1). A remote server must use `https://` so your
  words are never sent unencrypted. No transcript data is ever used for
  training or telemetry by this tool.

## Examples

See `examples/` for a sample plain transcript, SRT and VTT file, plus the
exact output each produces.

## Testing

```bash
pip install -e ".[dev]"   # or: pip install pytest
pytest                    # 42 offline tests; no network used
```

## Project layout

```
transcript_chapter_marker/
  __main__.py   entry point (`python -m transcript_chapter_marker`)
  cli.py        argparse interface end to end
  parse.py      timestamp parsing/formatting, Segment/Transcript models
  intake.py     plain-text / SRT / VTT readers
  chapters.py   chapter segmentation + offline keyword titles
  topics.py     keyphrase extraction (bigram-aware)
  llm.py        optional OpenAI-compatible naming, privacy-guarded
tests/          pytest suite with fixture transcripts
examples/       runnable sample inputs and outputs
```

## Roadmap / known gaps

- Chapter titles without `--llm` are keyword-based and occasionally clunky
  ("Model & Small"); the LLM path fixes that when you can run a local model.
- No `.mp4`/`.md` container support; no audio processing of any kind.
- Only `t`-parameter deep links tested for YouTube-style URLs.

## License

MIT — see [LICENSE](LICENSE).
Copyright (c) 2026 Asdale Dynamics, LLC.

## Credits

Asdale Dynamics, LLC — Dylan Asdale, registered nurse turned AI author.
Tools and manuals that explain AI like a friend would: plain English, step by
step, never condescending. *The Massive AI Manual* — dylanasdale.github.io
