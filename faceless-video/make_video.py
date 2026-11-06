#!/usr/bin/env python3
"""Faceless video generator.

Topic in -> finished MP4 out:
  1. Script      - Claude writes a hook-first narration split into scenes
                   (or you pass your own with --script-file).
  2. Voiceover   - edge-tts (free Microsoft neural voices) with word timings.
  3. Visuals     - one Pexels stock clip per scene (falls back to a plain
                   background when no PEXELS_API_KEY is set or nothing matches).
  4. Captions    - word-by-word highlighted captions burned in (ASS/libass).
  5. Assembly    - FFmpeg: scale/crop clips, concat, mix music under voice.

Usage:
  python make_video.py "why octopuses have three hearts"
  python make_video.py --script-file my_script.json
  python make_video.py "topic" --format horizontal --voice en-US-AriaNeural
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
FPS = 30
FORMATS = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}
WORDS_PER_SECOND = 2.6  # typical edge-tts pace at +0% rate
MUSIC_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Word:
    text: str
    start: float  # seconds, relative to the start of the whole video
    end: float


@dataclass
class Scene:
    narration: str
    search_query: str
    audio: Path | None = None
    duration: float = 0.0
    words: list[Word] = field(default_factory=list)
    clip: Path | None = None


@dataclass
class Script:
    title: str
    scenes: list[Scene]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def log(msg: str) -> None:
    print(f"[faceless] {msg}", flush=True)


def slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:max_len].rstrip("-")) or "video"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a command, surfacing stderr only on failure."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-25:])
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{tail}")


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def require_binaries() -> None:
    missing = [b for b in ("ffmpeg", "ffprobe") if shutil.which(b) is None]
    if missing:
        sys.exit(f"Missing {', '.join(missing)}. Install FFmpeg and make sure it is on PATH.")


# --------------------------------------------------------------------------- #
# 1. Script
# --------------------------------------------------------------------------- #
SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string"},
                    "search_query": {"type": "string"},
                },
                "required": ["narration", "search_query"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "scenes"],
    "additionalProperties": False,
}

SCRIPT_SYSTEM = """You write narration for faceless short-form videos (YouTube Shorts, TikTok, Reels).
Rules:
- Scene 1 is the hook: a surprising claim or question that makes people stay. No greetings, no "in this video".
- Short spoken sentences. Concrete facts and numbers over vague statements. Only state things that are true.
- Each scene is 1-2 sentences of narration that one stock clip can cover.
- search_query: 2-4 concrete visual words for a stock-footage search (e.g. "octopus swimming reef"). No abstract terms, no text, no people's names.
- End with a payoff or a line that makes people rewatch or comment. No "like and subscribe".
- Plain text only in narration: no emojis, hashtags, markdown or stage directions."""


def write_script_with_claude(topic: str, seconds: int, scenes: int) -> Script:
    import anthropic

    target_words = int(seconds * WORDS_PER_SECOND)
    client = anthropic.Anthropic()
    log(f"Writing script with Claude (~{target_words} words, {scenes} scenes)...")
    response = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": SCRIPT_SCHEMA},
        },
        system=SCRIPT_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Topic: {topic}\n"
                f"Length: about {target_words} words total (~{seconds} seconds spoken).\n"
                f"Scenes: exactly {scenes}."
            ),
        }],
    )
    if response.stop_reason == "refusal":
        sys.exit("Claude declined to write a script for this topic. Try a different topic.")
    if response.stop_reason == "max_tokens":
        sys.exit("Script generation was cut off (max_tokens). Try fewer scenes or seconds.")

    text = next(b.text for b in response.content if b.type == "text")
    return parse_script_data(json.loads(text), fallback_title=topic)


def parse_script_data(data: dict, fallback_title: str) -> Script:
    raw_scenes = data.get("scenes") or []
    scenes = [
        Scene(narration=s["narration"].strip(),
              search_query=(s.get("search_query") or fallback_title).strip())
        for s in raw_scenes if s.get("narration", "").strip()
    ]
    if not scenes:
        sys.exit("Script has no scenes with narration.")
    return Script(title=(data.get("title") or fallback_title).strip(), scenes=scenes)


def load_script_file(path: Path, topic: str | None) -> Script:
    """Accepts the JSON shape Claude returns, or plain text (one scene per paragraph)."""
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return parse_script_data(json.loads(raw), fallback_title=topic or path.stem)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    query = topic or path.stem.replace("_", " ")
    return Script(title=topic or path.stem,
                  scenes=[Scene(narration=p, search_query=query) for p in paragraphs])


# --------------------------------------------------------------------------- #
# 2. Voiceover (edge-tts)
# --------------------------------------------------------------------------- #
async def _tts_scene(text: str, voice: str, rate: str, mp3_path: Path) -> list[tuple[str, float, float]]:
    """Synthesize one scene. Returns [(word, start_s, end_s)] relative to the clip."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary",
                                       proxy=os.getenv("HTTPS_PROXY") or None)
    timings: list[tuple[str, float, float]] = []
    with mp3_path.open("wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000  # 100-ns ticks -> seconds
                timings.append((chunk["text"], start, start + chunk["duration"] / 10_000_000))
    return timings


def _norm(text: str) -> str:
    return re.sub(r"[^\w]", "", text.lower())


def align_to_script(text: str, timings: list[tuple[str, float, float]]) -> list[tuple[str, float, float]]:
    """Map TTS word timings (punctuation stripped) back onto the script's own words,
    so captions keep punctuation and chunk at sentence breaks. Returns the raw
    timings unchanged if the two can't be lined up."""
    tokens = text.split()
    out: list[tuple[str, float, float]] = []
    bi = 0
    for tok in tokens:
        target = _norm(tok)
        if not target:  # pure punctuation like "-" sticks to the previous word
            if out:
                w, s, e = out[-1]
                out[-1] = (f"{w} {tok}", s, e)
            continue
        if bi >= len(timings):
            return timings
        _, start, end = timings[bi]
        acc = _norm(timings[bi][0])
        bi += 1
        # One script word can be spoken as several boundaries (e.g. "don't", "3.5").
        while acc != target and bi < len(timings) and target.startswith(acc + _norm(timings[bi][0])):
            acc += _norm(timings[bi][0])
            end = timings[bi][2]
            bi += 1
        if acc != target:
            return timings
        out.append((tok, start, end))
    return out if bi == len(timings) else timings


def estimate_word_timings(text: str, duration: float) -> list[tuple[str, float, float]]:
    """Fallback when the TTS engine returns no word boundaries: spread by word length."""
    words = text.split()
    if not words:
        return []
    weights = [len(w) + 2 for w in words]
    total, t, out = sum(weights), 0.0, []
    for w, wt in zip(words, weights):
        span = duration * wt / total
        out.append((w, t, t + span))
        t += span
    return out


def synthesize_voice(script: Script, voice: str, rate: str, work: Path) -> Path:
    log(f"Generating voiceover ({voice}, rate {rate})...")

    async def all_scenes():
        sem = asyncio.Semaphore(4)

        async def one(i: int, scene: Scene):
            async with sem:
                return await _tts_scene(scene.narration, voice, rate, work / f"voice_{i:02d}.mp3")

        return await asyncio.gather(*(one(i, s) for i, s in enumerate(script.scenes)))

    all_timings = asyncio.run(all_scenes())

    # Decode each scene to WAV so durations are sample-exact and concat is gapless.
    cursor = 0.0
    concat_list = work / "voice_list.txt"
    with concat_list.open("w") as lst:
        for i, (scene, timings) in enumerate(zip(script.scenes, all_timings)):
            wav = work / f"voice_{i:02d}.wav"
            run(["ffmpeg", "-y", "-i", str(work / f"voice_{i:02d}.mp3"),
                 "-af", "apad=pad_dur=0.25", "-ar", "48000", "-ac", "2", str(wav)])
            scene.audio = wav
            scene.duration = probe_duration(wav)
            if timings:
                timings = align_to_script(scene.narration, timings)
            else:
                timings = estimate_word_timings(scene.narration, scene.duration - 0.25)
            scene.words = [Word(w, cursor + s, cursor + e) for w, s, e in timings]
            cursor += scene.duration
            lst.write(f"file '{wav.name}'\n")

    voice_path = work / "voice.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list.name,
         "-c", "copy", voice_path.name], cwd=work)
    log(f"Voiceover: {cursor:.1f}s across {len(script.scenes)} scenes")
    return voice_path


# --------------------------------------------------------------------------- #
# 3. Visuals (Pexels)
# --------------------------------------------------------------------------- #
def pick_pexels_file(video: dict, width: int, height: int) -> dict | None:
    """Pick the smallest MP4 that still covers the target frame (or the largest available)."""
    files = [f for f in video.get("video_files", [])
             if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
    if not files:
        return None
    covering = [f for f in files if f["width"] >= width * 0.66 and f["height"] >= height * 0.66]
    if covering:
        return min(covering, key=lambda f: f["width"] * f["height"])
    return max(files, key=lambda f: f["width"] * f["height"])


def fetch_pexels_clip(query: str, min_duration: float, orientation: str, size: tuple[int, int],
                      api_key: str, used_ids: set[int], cache: Path) -> Path | None:
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key},
            params={"query": query, "orientation": orientation, "per_page": 15},
            timeout=20,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log(f"  Pexels search failed for '{query}': {exc}")
        return None

    videos = [v for v in resp.json().get("videos", []) if v["id"] not in used_ids]
    if not videos:
        return None
    # Prefer clips long enough to avoid looping; keep Pexels relevance order otherwise.
    videos.sort(key=lambda v: v.get("duration", 0) < min_duration)

    for video in videos:
        chosen = pick_pexels_file(video, *size)
        if not chosen:
            continue
        dest = cache / f"pexels_{video['id']}_{chosen['width']}x{chosen['height']}.mp4"
        if not dest.exists():
            try:
                with requests.get(chosen["link"], stream=True, timeout=60) as r:
                    r.raise_for_status()
                    tmp = dest.with_suffix(".part")
                    with tmp.open("wb") as f:
                        for block in r.iter_content(1 << 20):
                            f.write(block)
                    tmp.rename(dest)
            except requests.RequestException as exc:
                log(f"  Download failed for Pexels video {video['id']}: {exc}")
                continue
        used_ids.add(video["id"])
        return dest
    return None


def gather_clips(script: Script, fmt: str, size: tuple[int, int], fallback_query: str) -> None:
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not api_key:
        log("No PEXELS_API_KEY set - using plain backgrounds. Get a free key at pexels.com/api")
        return
    cache = ROOT / ".cache" / "pexels"
    cache.mkdir(parents=True, exist_ok=True)
    orientation = "portrait" if fmt == "vertical" else "landscape"
    used: set[int] = set()
    log("Fetching stock clips from Pexels...")
    for i, scene in enumerate(script.scenes, 1):
        clip = None
        for query in dict.fromkeys([scene.search_query, fallback_query]):  # dedupe, keep order
            clip = fetch_pexels_clip(query, scene.duration, orientation, size, api_key, used, cache)
            if clip:
                break
        scene.clip = clip
        log(f"  Scene {i}: '{scene.search_query}' -> {clip.name if clip else 'plain background'}")


# --------------------------------------------------------------------------- #
# 4. Captions (ASS)
# --------------------------------------------------------------------------- #
def chunk_words(words: list[Word], max_words: int = 3, max_chars: int = 18) -> list[list[Word]]:
    """Group words into short on-screen phrases, breaking after punctuation."""
    chunks: list[list[Word]] = []
    current: list[Word] = []
    for w in words:
        projected = len(" ".join(x.text for x in current + [w]))
        if current and (len(current) >= max_words or projected > max_chars):
            chunks.append(current)
            current = []
        current.append(w)
        if re.search(r"[.!?,;:]$", w.text):
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def ass_time(t: float) -> str:
    cs = max(0, int(round(t * 100)))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def build_ass(words: list[Word], size: tuple[int, int], highlight_bgr: str = "00E5FF") -> str:
    w, h = size
    font_size = int(min(w, h) * 0.085)
    margin_v = int(h * (0.28 if h > w else 0.12))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{max(4, font_size // 12)},2,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    chunks = chunk_words(words)
    for k, chunk in enumerate(chunks):
        # Hold the phrase on screen through short pauses so captions don't flicker.
        chunk_end = chunk[-1].end + 0.2
        if k + 1 < len(chunks):
            next_start = chunks[k + 1][0].start
            chunk_end = next_start if next_start - chunk[-1].end < 0.5 else min(chunk_end, next_start)
        for i, word in enumerate(chunk):
            start = word.start
            end = chunk[i + 1].start if i + 1 < len(chunk) else chunk_end
            if end - start < 0.02:
                continue
            parts = []
            for j, other in enumerate(chunk):
                token = ass_escape(other.text.upper())
                if j == i:
                    token = f"{{\\c&H{highlight_bgr}&\\fscx112\\fscy112}}{token}{{\\r}}"
                parts.append(token)
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{' '.join(parts)}")
    return header + "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# 5. Assembly (FFmpeg)
# --------------------------------------------------------------------------- #
BG_COLORS = ["0x0f172a", "0x1e1b4b", "0x052e16", "0x3f0d12", "0x172554", "0x27272a"]


def render_scene(scene: Scene, index: int, size: tuple[int, int], work: Path) -> Path:
    w, h = size
    out = work / f"scene_{index:02d}.mp4"
    encode = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
              "-pix_fmt", "yuv420p", "-r", str(FPS)]
    if scene.clip:
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
              f"setsar=1,fps={FPS},format=yuv420p")
        run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(scene.clip),
             "-t", f"{scene.duration:.3f}", "-vf", vf, *encode, str(out)])
    else:
        color = BG_COLORS[index % len(BG_COLORS)]
        run(["ffmpeg", "-y", "-f", "lavfi",
             "-i", f"color=c={color}:s={w}x{h}:r={FPS}:d={scene.duration:.3f}",
             "-vf", "vignette=PI/5,format=yuv420p", *encode, str(out)])
    return out


def pick_music(music_dir: Path) -> Path | None:
    if not music_dir.is_dir():
        return None
    tracks = [p for p in music_dir.iterdir() if p.suffix.lower() in MUSIC_EXTS]
    return random.choice(tracks) if tracks else None


def assemble(script: Script, voice: Path, size: tuple[int, int], music: Path | None,
             music_volume: float, work: Path, out_path: Path) -> None:
    log("Rendering scenes...")
    with (work / "scenes.txt").open("w") as lst:
        for i, scene in enumerate(script.scenes):
            lst.write(f"file '{render_scene(scene, i, size, work).name}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "scenes.txt",
         "-c", "copy", "video.mp4"], cwd=work)

    all_words = [w for s in script.scenes for w in s.words]
    (work / "captions.ass").write_text(build_ass(all_words, size), encoding="utf-8")

    total = sum(s.duration for s in script.scenes)
    cmd = ["ffmpeg", "-y", "-i", "video.mp4", "-i", voice.name]
    if music:
        log(f"Mixing music: {music.name}")
        fade_start = max(0.0, total - 1.5)
        cmd += ["-stream_loop", "-1", "-i", str(music.resolve()),
                "-filter_complex",
                f"[0:v]ass=captions.ass[v];"
                f"[2:a]volume={music_volume},afade=t=out:st={fade_start:.2f}:d=1.5[bg];"
                f"[1:a][bg]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-filter_complex", "[0:v]ass=captions.ass[v]", "-map", "[v]", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}",
            "-movflags", "+faststart", str(out_path.resolve())]
    log("Burning captions and encoding final video...")
    run(cmd, cwd=work)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Make a faceless video from a topic.")
    p.add_argument("topic", nargs="?", help="What the video is about")
    p.add_argument("--script-file", type=Path,
                   help="Use your own script: .json ({title, scenes:[{narration, search_query}]}) "
                        "or .txt (one scene per paragraph)")
    p.add_argument("--format", choices=FORMATS, default="vertical")
    p.add_argument("--seconds", type=int, default=50, help="Target length when Claude writes the script")
    p.add_argument("--scenes", type=int, default=8, help="Scene count when Claude writes the script")
    p.add_argument("--voice", default="en-US-AndrewMultilingualNeural",
                   help="edge-tts voice (list them with: edge-tts --list-voices)")
    p.add_argument("--rate", default="+8%", help="Speech rate, e.g. +0%%, +10%%, -5%%")
    p.add_argument("--music-dir", type=Path, default=ROOT / "music")
    p.add_argument("--music-volume", type=float, default=0.12, help="0.0-1.0, relative to the voice")
    p.add_argument("--out-dir", type=Path, default=ROOT / "output")
    p.add_argument("--keep-work", action="store_true", help="Keep intermediate files for debugging")
    args = p.parse_args(argv)
    if not args.topic and not args.script_file:
        p.error("give a topic or --script-file")
    if not re.fullmatch(r"[+-]\d{1,3}%", args.rate):
        p.error("--rate must look like +10% or -5%")
    return args


def main(argv: list[str] | None = None) -> None:
    load_dotenv(ROOT / ".env")
    args = parse_args(argv)
    require_binaries()
    size = FORMATS[args.format]

    if args.script_file:
        script = load_script_file(args.script_file, args.topic)
    else:
        script = write_script_with_claude(args.topic, args.seconds, args.scenes)
    log(f"Title: {script.title}")

    slug = slugify(script.title)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    work = args.out_dir / f".{slug}_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "script.json").write_text(json.dumps({
        "title": script.title,
        "scenes": [{"narration": s.narration, "search_query": s.search_query} for s in script.scenes],
    }, indent=2), encoding="utf-8")

    voice = synthesize_voice(script, args.voice, args.rate, work)
    gather_clips(script, args.format, size, fallback_query=args.topic or script.title)
    out_path = args.out_dir / f"{slug}.mp4"
    assemble(script, voice, size, pick_music(args.music_dir), args.music_volume, work, out_path)

    # Keep the script next to the video so you can reuse it for titles/descriptions.
    shutil.copy(work / "script.json", args.out_dir / f"{slug}.json")
    if not args.keep_work:
        shutil.rmtree(work, ignore_errors=True)
    log(f"Done: {out_path}")


if __name__ == "__main__":
    main()
