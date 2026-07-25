"""
Milestone 6, Part A — durable expiry.

TTLs must survive a restart. Today the log records only value writes, so on reload
a key comes back permanently (its expiry is forgotten). Here we persist the expiry
in the log and honor it on replay.
"""

import time

from kvstore import PersistentKVStore


def test_ttl_survives_restart(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("k", "v", ttl=100)
    del s  # simulate shutdown

    s2 = PersistentKVStore(path)
    assert s2.get("k") == "v"
    remaining = s2.ttl("k")
    assert remaining is not None
    assert 0 < remaining <= 100  # the expiry came back, still ticking


def test_expired_key_is_dropped_on_reload(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("k", "v", ttl=0.05)
    time.sleep(0.1)  # key expires while "offline"
    del s

    s2 = PersistentKVStore(path)  # replay must drop already-expired keys
    assert s2.exists("k") is False
    assert len(s2) == 0


def test_expire_command_persists(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("k", "v")
    s.expire("k", 100)  # add a TTL after the fact
    del s

    s2 = PersistentKVStore(path)
    assert s2.ttl("k") is not None  # the EXPIRE was logged and replayed


def test_plain_overwrite_clears_persisted_ttl(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("k", "v", ttl=100)
    s.set("k", "v2")  # overwrite with no ttl -> TTL must be gone, even after restart
    del s

    s2 = PersistentKVStore(path)
    assert s2.get("k") == "v2"
    assert s2.ttl("k") is None
