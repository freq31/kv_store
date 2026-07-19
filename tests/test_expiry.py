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
