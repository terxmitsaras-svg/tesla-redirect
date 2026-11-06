# Faceless Video Generator

Turns a topic into a finished, captioned faceless video (Shorts/TikTok/Reels or 16:9 YouTube).

```
topic ─▶ Claude writes script ─▶ edge-tts voiceover ─▶ Pexels stock clips ─▶ word-by-word captions ─▶ FFmpeg ─▶ output/<title>.mp4
```

## Setup (once)

1. Install **Python 3.10+** and **FFmpeg** (`brew install ffmpeg` on Mac, `winget install ffmpeg` on Windows).
2. In this folder:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env      # then paste your keys into .env
   ```
   - `ANTHROPIC_API_KEY`: needed only when Claude writes the script.
   - `PEXELS_API_KEY`: free, gives stock footage. Without it you get plain dark backgrounds.
3. Optional: drop royalty-free tracks (`.mp3`, `.wav`, ...) into `music/`. One is picked at random and mixed under the voice.

## Usage

```bash
# Claude writes the script
python make_video.py "why octopuses have three hearts"

# Your own script (JSON like examples/octopus.json, or .txt with one scene per paragraph)
python make_video.py --script-file examples/octopus.json

# Long-form 16:9, different voice, longer
python make_video.py "the history of the bicycle" --format horizontal --seconds 180 --scenes 20 --voice en-GB-RyanNeural
```

| Option | Default | What it does |
|---|---|---|
| `--format` | `vertical` | `vertical` 1080x1920 or `horizontal` 1920x1080 |
| `--seconds` / `--scenes` | `50` / `8` | Target length and scene count (Claude-written scripts) |
| `--voice` | `en-US-AndrewMultilingualNeural` | Any edge-tts voice; list them with `edge-tts --list-voices` |
| `--rate` | `+8%` | Speaking speed |
| `--music-dir` / `--music-volume` | `music/` / `0.12` | Background music folder and level relative to the voice |
| `--out-dir` | `output/` | Where the `.mp4` and its `.json` script are written |
| `--keep-work` | off | Keep intermediate files (per-scene audio/video, captions) for debugging |

Each render also saves `output/<title>.json` with the script. Edit it and re-run with `--script-file` to tweak wording without paying for a new script.

## Tests

```bash
pip install pytest && python -m pytest tests
```

## Before you post

- Pexels footage is free to use commercially. Only put music in `music/` that you have the rights to.
- YouTube can demonetize "mass-produced or repetitive" content, so review and edit scripts instead of uploading raw output in bulk.
- Follow each platform's AI-content disclosure rules for the synthetic voice.
