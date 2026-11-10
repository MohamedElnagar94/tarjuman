import os
import time

from tarjuman.storage import prune_clips


def test_the_voice_cache_drops_the_least_recently_used_clips_first(tmp_path):
    now = time.time()
    meta = {}
    for i in range(10):
        f = tmp_path / f"clip{i}.mp3"
        f.write_bytes(b"x" * 1000)
        os.utime(f, (now - 1000 + i, now - 1000 + i))  # clip0 is the oldest
        meta[f"clip{i}"] = 1.0
    os.utime(tmp_path / "clip0.mp3")  # ...but it was just played again
    (tmp_path / "_meta.json").write_text("{}")  # not a clip: never deleted

    deleted = prune_clips(tmp_path, limit=6000, meta=meta)
    left = sorted(p.name for p in tmp_path.glob("*.mp3"))
    assert deleted == 5 and len(left) == 5, "down to 90% of the limit"
    assert "clip0.mp3" in left, "a recently played clip stays"
    assert "clip1.mp3" not in left and "clip9.mp3" in left
    assert "clip1" not in meta and "clip0" in meta, "durations of deleted clips are forgotten"
    assert (tmp_path / "_meta.json").exists()
    assert prune_clips(tmp_path, limit=6000, meta=meta) == 0, "nothing to do under the limit"
