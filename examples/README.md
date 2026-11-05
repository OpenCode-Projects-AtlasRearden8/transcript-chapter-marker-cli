# Examples

Run any of these yourself:

```bash
python -m transcript_chapter_marker examples/workshop.txt --target-min 4
python -m transcript_chapter_marker examples/workshop.srt --target-min 4
python -m transcript_chapter_marker examples/workshop.vtt --target-min 4
python -m transcript_chapter_marker examples/workshop_untimed.txt --interval 1:00 --target-min 4
```

## Sample output (`workshop.srt`, `--target-min 4`)

This is the exact, reproducible output of the offline run (kept in
`workshop_output.txt`):

```text
Chapters
00:00 Model & Command
04:12 Model & Loaded

Audiobook chapters
00:00:00 - Chapter 1: Model & Command
00:04:12 - Chapter 2: Model & Loaded

Topics
Model (4)
Local (2)
Command (2)
Pull (2)
...
```

Untimed plain text with `--interval 1:00` spaces paragraphs a minute apart,
so every paragraph becomes an indexable entry. Keyword titles are deliberately
rough; pass `--llm` with a local model for friendly ones:

```text
Chapters
00:00 Welcome
00:45 Installing Ollama
01:02 Pulling Your First Model
04:12 Calling the Model
05:30 Modelfiles
07:05 Recap
```

With `--clickable "https://youtu.be/EXAMPLE"` the index becomes:

```text
[00:00](https://youtu.be/EXAMPLE?t=0s) Workshop & Welcome
[01:02](https://youtu.be/EXAMPLE?t=62s) Model & Pull
```

## Sample input (`workshop.txt`)

```text
[0:00] Welcome to the Local AI Workshop...
```

Files:

- `workshop.txt` — plain text with leading timestamps
- `workshop_untimed.txt` — plain text, no timestamps
- `workshop.srt` — SubRip captions
- `workshop.vtt` — WebVTT captions
- `workshop_output.txt` — what the tool prints for the SRT version
  (regenerate any time; the tool is deterministic offline)
