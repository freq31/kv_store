"""
Milestone 4, Part B — log compaction.

Compaction rewrites the append-only log so it holds only the current state
(one line per live key), instead of the full history of every write.
"""

from kvstore import PersistentKVStore


def _line_count(path) -> int:
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def test_compact_shrinks_repeated_writes(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    for i in range(100):
        s.set("counter", str(i))
    assert _line_count(path) == 100  # 100 writes -> 100 log lines

    s.compact()
    assert _line_count(path) == 1  # one live key -> one line
    assert s.get("counter") == "99"  # newest value preserved


def test_compact_drops_deleted_keys(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("a", "1")
    s.set("b", "2")
    s.delete("a")

    s.compact()
    assert _line_count(path) == 1  # only "b" survives
    assert s.exists("a") is False
    assert s.get("b") == "2"


def test_compacted_log_survives_restart(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    for i in range(50):
        s.set("x", str(i))
    s.set("y", "hello")
    s.compact()
    del s  # simulate shutdown

    s2 = PersistentKVStore(path)  # rebuild from the compacted log
    assert s2.get("x") == "49"
    assert s2.get("y") == "hello"
    assert len(s2) == 2


def test_writes_after_compaction_still_work(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("a", "1")
    s.compact()
    s.set("b", "2")  # appending after a compaction must keep working

    assert _line_count(path) == 2
    assert s.get("a") == "1"
    assert s.get("b") == "2"
