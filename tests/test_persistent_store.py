"""
Tests for Milestone 2 — persistence.

The star of the show is test_data_survives_restart: we simulate a restart by
throwing away one store object and building a brand-new one from the same file.
If the data comes back, you've built real persistence.

`tmp_path` is a pytest built-in: a fresh temporary directory per test, so tests
never clash and clean up after themselves.
"""

import pytest

from kvstore import PersistentKVStore
from kvstore.store import KeyNotFoundError


def test_inherited_behavior_still_works(tmp_path):
    store = PersistentKVStore(tmp_path / "log.jsonl")
    store.set("name", "aditya")
    assert store.get("name") == "aditya"
    assert store.exists("name") is True
    assert len(store) == 1


def test_log_file_is_created_on_write(tmp_path):
    path = tmp_path / "log.jsonl"
    store = PersistentKVStore(path)
    assert path.exists() is False  # nothing written yet
    store.set("a", "1")
    assert path.exists() is True  # the write created the log


def test_data_survives_restart(tmp_path):
    path = tmp_path / "log.jsonl"

    first = PersistentKVStore(path)
    first.set("name", "aditya")
    first.set("city", "hyderabad")
    del first  # simulate the process shutting down

    second = PersistentKVStore(path)  # fresh object, same file
    assert second.get("name") == "aditya"
    assert second.get("city") == "hyderabad"
    assert len(second) == 2


def test_overwrite_survives_restart(tmp_path):
    path = tmp_path / "log.jsonl"

    first = PersistentKVStore(path)
    first.set("city", "hyderabad")
    first.set("city", "bangalore")  # newer value should win
    del first

    second = PersistentKVStore(path)
    assert second.get("city") == "bangalore"
    assert len(second) == 1


def test_delete_survives_restart(tmp_path):
    path = tmp_path / "log.jsonl"

    first = PersistentKVStore(path)
    first.set("temp", "1")
    first.delete("temp")
    del first

    second = PersistentKVStore(path)
    assert second.exists("temp") is False
    with pytest.raises(KeyNotFoundError):
        second.get("temp")


def test_missing_file_starts_empty(tmp_path):
    store = PersistentKVStore(tmp_path / "does_not_exist_yet.jsonl")
    assert len(store) == 0


def test_delete_missing_key_still_raises(tmp_path):
    store = PersistentKVStore(tmp_path / "log.jsonl")
    with pytest.raises(KeyNotFoundError):
        store.delete("ghost")
