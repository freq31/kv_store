"""
Milestone 7 — auto-triggered compaction.

The log grows by one line per write. Until now you had to call compact() by hand.
Here the store watches its own log size and compacts automatically once it's mostly
dead weight (overwrites/deletes), so the log stays bounded on its own.

We pass a tiny `auto_compact_threshold` so tests trigger compaction quickly.
"""

import time

from kvstore import PersistentKVStore


def _line_count(path) -> int:
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def test_auto_compaction_shrinks_a_growing_log(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path, auto_compact_threshold=10)
    for i in range(50):
        s.set("k", str(i))  # same key overwritten 50 times

    # Without auto-compaction the log would have 50 lines; with it, far fewer.
    assert _line_count(path) < 50
    assert s.get("k") == "49"  # data is correct


def test_no_compaction_below_threshold(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path, auto_compact_threshold=1000)
    for i in range(5):
        s.set(f"k{i}", "v")
    assert _line_count(path) == 5  # below threshold -> log untouched


def test_large_dataset_not_compacted_prematurely(tmp_path):
    """The 2*len(data) term: a legitimately large store shouldn't compact just for
    being big — only when the log is ~2x the live-key count."""
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path, auto_compact_threshold=10)
    for i in range(40):
        s.set(f"key{i}", "v")  # 40 DISTINCT keys, no overwrites
    # 40 entries vs 40 live keys: log is not mostly dead weight, so no compaction.
    assert _line_count(path) == 40
    assert len(s) == 40


def test_auto_compacted_data_survives_restart(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path, auto_compact_threshold=10)
    for i in range(50):
        s.set("k", str(i))
    s.set("other", "x")
    del s

    s2 = PersistentKVStore(path)
    assert s2.get("k") == "49"
    assert s2.get("other") == "x"


def test_writes_work_after_auto_compaction(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path, auto_compact_threshold=10)
    for i in range(30):
        s.set("k", str(i))
    s.set("new", "1")  # appending after an auto-compaction still works
    assert s.get("new") == "1"
    assert s.get("k") == "29"


def test_auto_compaction_handles_ttl_keys(tmp_path):
    """Regression: auto-compaction runs compact() often, and compact() must not crash
    when a key has expired (the dict-mutation-during-iteration bug)."""
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path, auto_compact_threshold=10)
    s.set("temp", "v", ttl=0.05)
    for i in range(20):
        s.set("k", str(i))  # drives the log past the threshold -> triggers compact
    time.sleep(0.1)
    for i in range(20, 40):
        s.set("k", str(i))  # more writes -> another compact, now with "temp" expired
    assert s.exists("temp") is False
    assert s.get("k") == "39"
