"""The streaming separator must give exactly what the whole-track version gives."""

import numpy as np

from tarjuman.media.separator import CHUNK, GEN, SR, separate, separate_stream


class FakeModel:
    """Stands in for MDX-Net: an output that depends on the input, so any misalignment shows."""

    def get_inputs(self):
        return [type("I", (), {"name": "input"})()]

    def run(self, _names, feeds):
        x = feeds["input"]
        return [x * 0.5 + np.tanh(x) * 0.1]


def test_streaming_matches_the_whole_track_version_exactly():
    rng = np.random.default_rng(3)
    for seconds in (3.0, 17.3, float(GEN * 3) / SR):  # short, uneven, and an exact multiple of a piece
        mix = (rng.standard_normal((2, int(seconds * SR))) * 0.2).astype(np.float32)
        whole = separate(FakeModel(), mix)
        got, mixes = [], []
        frames = (mix[:, i : i + 1024] for i in range(0, mix.shape[1], 1024))  # like a decoder's frames
        n = separate_stream(FakeModel(), frames, lambda b, m: (got.append(b), mixes.append(m)))
        streamed = np.concatenate(got, axis=1)
        assert n == mix.shape[1] and streamed.shape == whole.shape
        assert np.allclose(streamed, whole, atol=1e-5), f"{seconds}s differs"
        assert np.allclose(np.concatenate(mixes, axis=1), mix), "the mix passed along lines up"


def test_memory_stays_small_for_long_audio():
    # The buffer never needs more than a few pieces: CHUNK samples × a small batch.
    seen = []
    frames = (np.zeros((2, 4096), np.float32) for _ in range(400))  # ~37 s
    separate_stream(FakeModel(), frames, lambda b, m: seen.append(b.shape[1]))
    assert max(seen) <= GEN and sum(seen) == 400 * 4096 and CHUNK < SR * 7
