"""
Milestone 6, Part B — active expiration.

A background thread sweeps out expired keys on a timer, so memory doesn't fill with
expired-but-untouched keys. The headline test evicts a key that NOBODY reads.
"""

import time

from kvstore import KVStore


def test_sweep_removes_only_expired_keys():
    s = KVStore()
    s.set("a", "1", ttl=0.05)
    s.set("b", "2")  # no TTL — must survive
    s.set("c", "3", ttl=0.05)
    time.sleep(0.1)

    removed = s._sweep_expired()
    assert removed == 2
    assert "a" not in s._data
    assert "c" not in s._data
    assert "b" in s._data  # untouched, no TTL


def test_active_expiry_evicts_without_anyone_reading():
    """The whole point of active expiration: a key leaves memory on its own."""
    s = KVStore()
    s.start_expiry_sweeper(interval=0.05)
    try:
        s.set("k", "v", ttl=0.1)
        time.sleep(0.3)  # sweeper runs several times in this window
        assert "k" not in s._data  # gone, even though we never called get/exists
        assert "k" not in s._expiry
    finally:
        s.stop_expiry_sweeper()


def test_stop_sweeper_ends_the_thread():
    s = KVStore()
    s.start_expiry_sweeper(interval=0.05)
    s.stop_expiry_sweeper()
    assert s._sweeper_thread is None


def test_start_is_idempotent():
    s = KVStore()
    s.start_expiry_sweeper(interval=0.05)
    first = s._sweeper_thread
    s.start_expiry_sweeper(interval=0.05)  # calling again must not spawn a second thread
    try:
        assert s._sweeper_thread is first
    finally:
        s.stop_expiry_sweeper()
