import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import make_video as mv  # noqa: E402


def test_align_keeps_punctuation_and_merges_split_words():
    timings = [("Hello", 0.0, 0.3), ("there", 0.3, 0.6), ("don", 0.6, 0.7), ("t", 0.7, 0.8), ("stop", 0.8, 1.0)]
    out = mv.align_to_script("Hello there, don't stop.", timings)
    assert [w for w, _, _ in out] == ["Hello", "there,", "don't", "stop."]
    assert out[2] == ("don't", 0.6, 0.8)


def test_align_falls_back_on_mismatch():
    timings = [("one", 0.0, 0.2), ("thousand", 0.2, 0.6)]
    assert mv.align_to_script("1,000", timings) == timings


def test_estimate_word_timings_covers_duration():
    out = mv.estimate_word_timings("a bb ccc", 3.0)
    assert out[0][1] == 0.0
    assert abs(out[-1][2] - 3.0) < 1e-9


def test_chunks_break_on_punctuation_and_size():
    words = [mv.Word(t, i, i + 1) for i, t in enumerate("One two. Three four five six".split())]
    chunks = [[w.text for w in c] for c in mv.chunk_words(words, max_words=3)]
    assert chunks == [["One", "two."], ["Three", "four", "five"], ["six"]]


def test_ass_time_format():
    assert mv.ass_time(0) == "0:00:00.00"
    assert mv.ass_time(3725.456) == "1:02:05.46"


def test_build_ass_highlights_each_word_and_escapes():
    words = [mv.Word("a{b}", 0.0, 0.5), mv.Word("c", 0.5, 1.0)]
    ass = mv.build_ass(words, (1080, 1920))
    events = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert len(events) == 2
    assert "A(B)" in events[0] and "{" not in events[0].split(",,")[-1].replace("{\\c", "").replace("{\\r}", "")


def test_pick_pexels_file_prefers_smallest_covering_mp4():
    video = {"video_files": [
        {"file_type": "video/mp4", "width": 2160, "height": 3840, "link": "4k"},
        {"file_type": "video/mp4", "width": 1080, "height": 1920, "link": "hd"},
        {"file_type": "video/mp4", "width": 360, "height": 640, "link": "sd"},
    ]}
    assert mv.pick_pexels_file(video, 1080, 1920)["link"] == "hd"


def test_load_text_script(tmp_path):
    f = tmp_path / "my_story.txt"
    f.write_text("First scene.\n\nSecond scene.\n", encoding="utf-8")
    script = mv.load_script_file(f, None)
    assert [s.narration for s in script.scenes] == ["First scene.", "Second scene."]
    assert script.scenes[0].search_query == "my story"
