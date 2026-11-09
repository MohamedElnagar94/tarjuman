from tarjuman.api.security import post_allowed, request_allowed
from tarjuman.captions.formats import srt_time, to_srt, to_txt, to_vtt
from tarjuman.captions.models import Cue, Line
from tarjuman.captions.parse import parse_captions
from tarjuman.captions.repair import align_source, dedupe_rolling, reconstruct_asr, unroll_lines
from tarjuman.core.text import parse_video_id, safe_name
from tarjuman.translate.service import chunk_texts


def L(start, end, text=""):
    return Line(start, end, text)


def test_parse_video_id_handles_every_link_shape():
    vid = "dQw4w9WgXcQ"
    for u in [
        vid,
        f"https://www.youtube.com/watch?v={vid}",
        f"https://youtube.com/watch?feature=share&v={vid}&t=10",
        f"https://youtu.be/{vid}?si=abc",
        f"https://www.youtube.com/shorts/{vid}",
        f"https://www.youtube.com/embed/{vid}",
        f"https://www.youtube.com/live/{vid}",
        f"https://m.youtube.com/watch?v={vid}",
    ]:
        assert parse_video_id(u) == vid, u
    assert parse_video_id("https://example.com") is None
    assert parse_video_id("") is None


def test_parse_captions_reads_timedtext_xml_and_json3():
    xml = '<timedtext><body><p t="1000" d="2000">Hello &amp; <s>world</s></p><p t="4000" d="500"> </p></body></timedtext>'
    assert parse_captions(xml) == [L(1, 3, "Hello & world")]
    j3 = '{"events":[{"tStartMs":500,"dDurationMs":1500,"segs":[{"utf8":"Hi"},{"utf8":" there"}]},{"tStartMs":9}]}'
    assert parse_captions(j3) == [L(0.5, 2, "Hi there")]
    assert parse_captions("{broken") == []


def test_dedupe_rolling_merges_rolling_window_repeats():
    out = dedupe_rolling([L(0, 1, "so we"), L(1, 2, "so we went home"), L(2, 3, "then")])
    assert len(out) == 2
    assert out[0].text == "so we went home"
    assert out[0].end == 2


def test_reconstruct_asr_joins_fragments_into_sentences_without_overlaps():
    out = reconstruct_asr(
        [L(0, 1, "hello there my"), L(1, 2, "friend. how are"), L(2, 3, "you today?"), L(10, 11, "new group")]
    )
    assert [c.text for c in out] == ["hello there my friend.", "how are you today?", "new group"]
    for a, b in zip(out, out[1:]):
        assert a.end <= b.start


def test_chunk_texts_respects_size_and_count_limits():
    chunks = chunk_texts([f"line {i}" for i in range(60)])
    assert all(len(c) <= 24 for c in chunks)
    assert sum(len(c) for c in chunks) == 60
    assert len(chunk_texts(["x" * 1000, "y" * 1000])) == 2


CUES = [Cue(1.2, 3.4, "Hello", "مرحبا"), Cue(4, 4.1, "", ""), Cue(5, 7, "Bye --> now", "")]


def test_to_srt_numbers_sequentially_even_when_cues_are_skipped():
    srt = to_srt(CUES, "ar")
    assert srt.startswith("1\n00:00:01,200 --> 00:00:03,400\nمرحبا\n")
    assert "\n2\n00:00:05,000 --> 00:00:07,000\nBye --> now\n" in srt
    assert "\n3\n" not in srt
    assert "Hello\nمرحبا" in to_srt(CUES, "bi")


def test_to_vtt_and_to_txt():
    vtt = to_vtt(CUES, "src")
    assert vtt.startswith("WEBVTT\n")
    assert "00:00:01.200 --> 00:00:03.400\nHello" in vtt
    assert "Bye → now" in vtt, "cue text must not contain the --> separator"
    assert to_txt(CUES, "ar") == "مرحبا\nBye --> now"


def test_srt_time_and_safe_name():
    assert srt_time(3661.5) == "01:01:01,500"
    assert srt_time(-2) == "00:00:00,000"
    assert safe_name('a/b:c*?"<>|d') == "a b c d"
    assert safe_name("") == "video"


def test_request_allowed_blocks_cross_site_pages_and_dns_rebinding():
    def req(**h):
        return {"host": "127.0.0.1:4318", **{k.replace("_", "-"): v for k, v in h.items()}}

    assert request_allowed(req())
    assert request_allowed(req(origin="http://127.0.0.1:4318"))
    assert request_allowed(req(origin="chrome-extension://abcdef"))
    assert request_allowed({"host": "192.168.1.5:4318", "origin": "http://192.168.1.5:4318"})
    assert not request_allowed(req(origin="https://evil.example"))
    assert not request_allowed(req(sec_fetch_site="cross-site"))
    assert not request_allowed({"host": "evil.example:4318"})


def test_posts_must_be_json_except_uploads():
    assert post_allowed("/api/translate", "application/json; charset=utf-8")
    assert not post_allowed("/api/translate", "text/plain")
    assert not post_allowed("/api/translate", "application/x-www-form-urlencoded")
    assert post_allowed("/api/media/upload", "application/octet-stream")
    assert not post_allowed("/api/vocab", "application/octet-stream")


def test_unroll_roll_up_captions_keep_only_new_words_and_stop_overlapping():
    out = unroll_lines(
        [
            L(0, 6, "This beginner course teaches vector databases"),
            L(3, 9, "This beginner course teaches vector databases"),
            L(6, 12, "vector databases from scratch, starting with"),
            L(9, 15, "starting with vectors and cosine similarity."),
            L(12, 18, "Then we move on."),
        ]
    )
    assert [c.text for c in out] == [
        "This beginner course teaches vector databases",
        "from scratch, starting with",
        "vectors and cosine similarity.",
        "Then we move on.",
    ]
    for a, b in zip(out, out[1:]):
        assert b.start >= a.end, "no overlap"
    assert out[0].end == 6, "a dropped duplicate's time goes to the line before it"


def test_unroll_leaves_normal_captions_alone():
    lines = [L(0, 2, "really really"), L(2, 4, "really good"), L(4, 6, "stuff here"), L(6, 8, "and more")]
    assert unroll_lines(lines) == lines


def test_align_source_gives_each_source_line_to_exactly_one_target_line():
    targets = [L(0, 3), L(3, 6), L(6, 9)]
    sources = [L(0, 2.5, "one"), L(2.5, 4, "two"), L(4, 8.8, "three")]  # "two" overlaps the 2nd more
    assert align_source(targets, sources) == ["one", "two", "three"]
