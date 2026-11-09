"""Dub timing: the rhythm must stay continuous and in sync with the speaker."""

from tarjuman.captions.models import Cue
from tarjuman.dub.planner import condense_for_dub, fit_rate, group_dub_blocks, pace_blocks, split_speakers


def blocks(*rows):
    return [{"start": s, "end": e, "d": d} for s, e, d in rows]


def dur(b):
    return b["d"]


def test_a_dense_sentence_borrows_from_a_roomy_neighbour_instead_of_racing():
    out = pace_blocks(blocks((0, 14, 10), (14.1, 17.7, 6), (17.8, 25, 6)), dur)
    dense = out[1]
    assert dense["rate"] < 40, f"dense sentence rate stays sane, got {dense['rate']}%"
    assert dense["at"] < 14.1, "it starts a little early to keep the flow"


def test_lag_behind_the_speaker_stays_bounded_over_a_long_continuous_talk():
    out = pace_blocks(blocks(*[(i * 3, i * 3 + 2.9, 3.9) for i in range(200)]), dur)
    assert max(r["at"] - r["start"] for r in out) < 1.6


def test_pace_changes_gradually_between_neighbouring_sentences_when_sync_allows():
    out = pace_blocks(blocks(*[(i * 4, i * 4 + 3.9, 3.4 if i % 2 else 4.4) for i in range(40)]), dur)
    for a, b in zip(out, out[1:]):
        assert abs(b["rate"] - a["rate"]) <= 12, f"{a['rate']}% -> {b['rate']}%"


def test_spare_time_slows_down_slightly_instead_of_leaving_long_silences():
    out = pace_blocks(blocks((0, 6, 3), (6.2, 12, 3)), dur)
    assert -8 <= out[0]["rate"] < 0


def test_a_new_paragraph_after_a_pause_starts_on_time_never_early():
    out = pace_blocks(blocks((0, 3, 2.5), (10, 13, 2.5)), dur)
    assert out[1]["at"] == 10


def test_sentences_never_overlap():
    bs = blocks(*[(i * 2, i * 2 + 1.9, 1.5 + (i % 5) * 0.4) for i in range(50)])
    out = pace_blocks(bs, dur)
    for k in range(1, len(out)):
        prev_end = out[k - 1]["at"] + bs[k - 1]["d"] / (1 + out[k - 1]["rate"] / 100)
        assert out[k]["at"] >= prev_end - 0.05, f"overlap at {k}"


def test_condense_for_dub_drops_spoken_filler_but_keeps_meaning():
    assert condense_for_dub("So, um, basically you know we build the level.") == "We build the level."
    assert condense_for_dub("All right, so here we are") == "Here we are"
    assert condense_for_dub("But why stop there?") == "But why stop there?"
    assert condense_for_dub("um") == "um", "never returns empty"
    assert (
        condense_for_dub("I am going to show you how to really build a lot of levels in order to test them.")
        == "I'll show you how to build many levels to test them."
    )
    assert condense_for_dub("We are going to be able to just export it, pretty much.") == "We'll be able to export it."
    assert condense_for_dub("Just click the button.") == "Click the button."


def test_group_dub_blocks_merges_caption_fragments_into_whole_sentences():
    out = group_dub_blocks(
        [
            Cue(0, 2, "what are AI's strengths and"),
            Cue(2, 3, "limitations so you know when to use it."),
            Cue(3.1, 5, "As a test, I made three games."),
        ]
    )
    assert len(out) == 2
    assert "strengths and limitations" in out[0].src


def test_group_dub_blocks_strips_caption_markers_that_are_not_speech():
    out = group_dub_blocks(
        [Cue(0, 3, ">> So [Music] here we go.", ">> إذن [موسيقى] يلا بينا."), Cue(3.1, 6, "♪ Next part. ♪", "♪ الجزء التالي. ♪")],
        use_ar=True,
    )
    assert out[0].cueAr == "إذن يلا بينا."
    assert out[0].src == "Here we go."
    assert out[1].cueAr == "الجزء التالي."


def test_fit_rate_never_slows_down_and_caps_at_80():
    assert fit_rate(0, 4, 2) == 80
    assert fit_rate(20, 1, 5) == 20
    assert fit_rate(0, 2.2, 2) == 13


def test_split_speakers_gives_each_clear_speaker_a_voice():
    f0 = [120, 118, 125, 210, 215, 205, 119, 0, 121, 122]
    s = split_speakers(list(range(10)), f0)
    assert s.primary == "auto-m"
    assert s.per_sentence is not None
    assert s.per_sentence[4] == "auto-f"
    assert s.per_sentence[0] == "auto-m"
    assert s.per_sentence[7] == s.per_sentence[6], "unclear pitch keeps the previous voice"
    assert split_speakers([0, 1, 2], [120, 0, 130]).per_sentence is None
