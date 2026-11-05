# STATUS.md — transcript-chapter-marker-cli

_last verified: 2026-11-05 (all commands below re-run before this commit)_

## What was built

`transcript-chapter-marker` (`tcm`), an **offline** Python-stdlib-only CLI that
turns a raw transcript into publish-ready chapter output:

- **Input formats:** plain text with leading `[mm:ss]` / `mm:ss` stamps,
  plain text without timestamps (paragraph mode, or `--interval` spaced),
  SubRip `.srt`, WebVTT `.vtt`, and stdin (`-`).
- **Outputs:**
  - `Chapters` — YouTube description block, `mm:ss Title`, or clickable
    `[mm:ss](URL?t=Ns)` with `--clickable`.
  - `Audiobook chapters` — `hh:mm:ss - Chapter N: Title` lines.
  - `Topics` — locally computed keyphrases (bigram-aware, stopword-filtered).
  - `Annotated transcript` — with `--format annotated`, chapter markers are
    inserted into the transcript text.
- **Optional LLM naming (`--llm`, off by default, no keys required):** names
  chapters via any OpenAI-compatible `/v1/chat/completions` endpoint
  (default: local Ollama at `http://localhost:11434/v1`). Privacy guards:
  plaintext `http://` allowed only on loopback; API key only via the
  `TRANSCRIPT_LLM_API_KEY` env var, never written to disk; nothing leaves the
  machine without `--llm`.
- **Package:** `transcript_chapter_marker/` (`parse`, `intake`, `chapters`,
  `topics`, `llm`, `render`, `cli`, `__main__`), installable via pip
  (`pyproject.toml`), console scripts `tcm` and `transcript-chapter-marker`.
- **Docs:** `README.md` (usage, CLI reference, LLM section, privacy notes,
  credit to Asdale Dynamics, LLC), `LICENSE` (MIT, "Copyright (c) 2026
  Asdale Dynamics, LLC"), runnable `examples/`.
- **Tests:** 42 pytest tests covering parsing, timestamp math, chapter
  segmentation, keyphrase ranking, renderers, the CLI end to end (stdin,
  out-files, offsets, interval mode, missing files) and the LLM path against a
  local stub HTTP server (including unencrypted-remote refusal and
  wrong-count replies).

## How to run

```bash
python3 -m transcript_chapter_marker tests/fixtures/timestamped.txt
# or after `pip install -e .`:
tcm talk.txt --clickable "https://youtu.be/VIDEO_ID"

# optional local LLM naming:
ollama pull llama3.2
python3 -m transcript_chapter_marker talk.txt --llm --llm-model llama3.2
```

Full CLI reference in `README.md`.

## Verification results

| Check | Result |
|---|---|
| `python3 -m pytest -q` | **42 passed** in ~3 s (fully offline) |
| `python3 -m pyflakes transcript_chapter_marker tests` | clean (no unused/undefined) |
| `python3 -m transcript_chapter_marker --help` / `--version` | OK (0.1.0) |
| CLI on `sample.srt`, `sample.vtt`, `timestamped.txt`, untimed text with `--interval` | OK, plausible output (see `examples/workshop_output.txt`) |
| stdin (`-`) + `--format index` | OK |
| `--out file` writing | OK |
| `pip install -e .` in a fresh venv; `tcm --version`; both console scripts | OK |
| LLM naming against local stub endpoint | OK (titles swapped in); remote plain-http refused with a warning, fallback to offline titles keeps exit 0 |
| Examples in `examples/` | regenerated and byte-checked |

## Known gaps

- Offline keyword chapter titles are heuristic and occasionally clunky
  ("Model & Command"); `--llm` with a small local model gives polished titles.
- Chapter splitting starts chapters at paragraph/cue boundaries only — no
  silence detection or audio analysis (the tool never touches audio files).
- Clickable links assume a YouTube-style `?t=N` URL parameter; other
  platforms' deep-link formats are untested.
- No `.md`/`.json` output containers, no i18n word lists (stopwords are
  English-only), and `--topics N` does not paraphrase topics (count-annotated
  keyphrases only).
- Windows line endings are tolerated by the parser but not tested explicitly.
