"""
Tests that define what your KVStore must do.

Read each test top-to-bottom: it's a plain-English spec of the behavior.
Make them all pass (green) and today's core is done.
"""

import pytest

from kvstore import KVStore
from kvstore.store import KeyNotFoundError


def test_set_then_get():
    store = KVStore()
    store.set("name", "aditya")
    assert store.get("name") == "aditya"


def test_set_overwrites_existing_value():
    store = KVStore()
    store.set("city", "hyderabad")
    store.set("city", "bangalore")
    assert store.get("city") == "bangalore"


def test_get_missing_key_raises():
    store = KVStore()
    with pytest.raises(KeyNotFoundError):
        store.get("nope")


def test_delete_removes_key():
    store = KVStore()
    store.set("temp", "1")
    store.delete("temp")
    assert store.exists("temp") is False


def test_delete_missing_key_raises():
    store = KVStore()
    with pytest.raises(KeyNotFoundError):
        store.delete("ghost")


def test_exists():
    store = KVStore()
    assert store.exists("a") is False
    store.set("a", "1")
    assert store.exists("a") is True


def test_keys_lists_all_keys():
    store = KVStore()
    store.set("a", "1")
    store.set("b", "2")
    assert sorted(store.keys()) == ["a", "b"]


def test_len_counts_keys():
    store = KVStore()
    assert len(store) == 0
    store.set("a", "1")
    store.set("b", "2")
    assert len(store) == 2
