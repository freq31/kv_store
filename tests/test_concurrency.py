"""
Milestone 4, Part A — thread safety.

test_incr_is_atomic_under_threads is the important one: it fires many threads at a
single counter. WITHOUT a lock around the read-modify-write, updates get lost and
the final total is too low. WITH the lock, it's always exactly right.
"""

import json
import threading

from kvstore import KVStore, PersistentKVStore


def test_incr_from_missing_key_starts_at_zero():
    s = KVStore()
    assert s.incr("counter") == 1
    assert s.incr("counter") == 2
    assert s.incr("counter", 5) == 7
    assert s.get("counter") == "7"  # stored as a string


def test_incr_is_atomic_under_threads():
    s = KVStore()
    n_threads, per_thread = 20, 500

    def worker() -> None:
        for _ in range(per_thread):
            s.incr("counter")

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # If the lock is missing, some increments are lost and this is < 10000.
    assert s.get("counter") == str(n_threads * per_thread)


def test_concurrent_persistent_writes_keep_log_valid(tmp_path):
    """Many threads writing to the persistent store must not corrupt the log file."""
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    n_threads, per_thread = 10, 200

    def worker(tid: int) -> None:
        for i in range(per_thread):
            s.set(f"k{tid}-{i}", "v")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    with open(path) as f:
        lines = [line for line in f if line.strip()]
    assert len(lines) == n_threads * per_thread
    for line in lines:
        json.loads(line)  # every line must be valid JSON — no interleaved writes
    assert len(s) == n_threads * per_thread
