"""
Milestone 5, Part A — TTL / expiry (in-memory, lazy expiration).

These tests use tiny real sleeps to let a TTL elapse. Keep them short.
"""

import time

import pytest

from kvstore import KVStore
from kvstore.store import KeyNotFoundError


def test_set_with_ttl_readable_before_expiry():
    s = KVStore()
    s.set("k", "v", ttl=0.2)
    assert s.get("k") == "v"  # still alive
    assert s.exists("k") is True


def test_key_expires_after_ttl():
    s = KVStore()
    s.set("k", "v", ttl=0.1)
    time.sleep(0.15)
    with pytest.raises(KeyNotFoundError):
        s.get("k")


def test_exists_is_false_after_expiry():
    s = KVStore()
    s.set("k", "v", ttl=0.1)
    time.sleep(0.15)
    assert s.exists("k") is False


def test_plain_set_clears_previous_ttl():
    s = KVStore()
    s.set("k", "v", ttl=0.1)
    s.set("k", "v2")  # overwrite with no ttl -> TTL must be cleared
    time.sleep(0.15)
    assert s.get("k") == "v2"  # did NOT expire
    assert s.ttl("k") is None


def test_expire_sets_ttl_on_existing_key():
    s = KVStore()
    s.set("k", "v")
    assert s.expire("k", 0.1) is True
    time.sleep(0.15)
    assert s.exists("k") is False


def test_expire_returns_false_for_missing_key():
    s = KVStore()
    assert s.expire("ghost", 10) is False


def test_ttl_returns_remaining_seconds():
    s = KVStore()
    s.set("k", "v", ttl=10)
    remaining = s.ttl("k")
    assert remaining is not None
    assert 0 < remaining <= 10


def test_ttl_is_none_without_expiry():
    s = KVStore()
    s.set("k", "v")
    assert s.ttl("k") is None


def test_ttl_raises_for_missing_key():
    s = KVStore()
    with pytest.raises(KeyNotFoundError):
        s.ttl("nope")


# --- Regression tests: _data and _expiry must never drift out of sync ---


def test_delete_clears_ttl_and_does_not_crash_later():
    """Regression for the delete-with-TTL bug.

    Deleting a key with a TTL must also remove its _expiry entry. Otherwise a later
    lazy-purge sees the stale expiry, tries to del a key that's no longer in _data,
    and crashes with KeyError.
    """
    s = KVStore()
    s.set("k", "v", ttl=0.1)
    s.delete("k")
    assert "k" not in s._expiry  # the delete cleared the expiry entry too
    time.sleep(0.15)  # let the (would-be) stale expiry lapse
    assert s.exists("k") is False  # must NOT raise KeyError
    with pytest.raises(KeyNotFoundError):
        s.get("k")  # a clean KeyNotFoundError, not a KeyError crash


def test_expire_on_already_expired_key_returns_false():
    s = KVStore()
    s.set("k", "v", ttl=0.1)
    time.sleep(0.15)
    # The key has lapsed; you can't attach a fresh TTL to something that's gone.
    assert s.expire("k", 100) is False


def test_ttl_raises_after_expiry():
    s = KVStore()
    s.set("k", "v", ttl=0.1)
    time.sleep(0.15)
    with pytest.raises(KeyNotFoundError):
        s.ttl("k")


def test_incr_refreshes_read_of_expired_key():
    """incr on an expired key should treat it as absent (start from 0), not reuse
    the stale value."""
    s = KVStore()
    s.set("counter", "41", ttl=0.1)
    time.sleep(0.15)
    assert s.incr("counter") == 1  # expired -> starts from 0, not 42
