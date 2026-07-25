"""
Milestone 8 — crash durability.

Three guarantees:
  1. fsync — a write is on physical disk before we call it done.
  2. checksums — a corrupted/tampered record is detected on reload, not loaded blindly.
  3. torn-write recovery — a partial final line (crash mid-append) doesn't crash replay.
"""

import json
import os

from kvstore import PersistentKVStore


def test_log_records_have_a_checksum(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("a", "1")
    with open(path) as f:
        record = json.loads(f.readline())
    assert "crc" in record


def test_data_survives_restart_with_checksums(tmp_path):
    """Guard: adding checksums must not break normal persistence."""
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("a", "1")
    s.set("b", "2")
    del s
    s2 = PersistentKVStore(path)
    assert s2.get("a") == "1"
    assert s2.get("b") == "2"


def test_fsync_is_called_on_write(tmp_path, monkeypatch):
    calls = {"n": 0}
    real_fsync = os.fsync

    def counting_fsync(fd):
        calls["n"] += 1
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", counting_fsync)
    s = PersistentKVStore(tmp_path / "log.jsonl")
    s.set("a", "1")
    assert calls["n"] >= 1  # the write was flushed to disk


def test_torn_final_line_is_ignored_on_reload(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("a", "1")
    s.set("b", "2")
    del s
    # Simulate a crash mid-append: a partial, invalid final line (no newline).
    with open(path, "a") as f:
        f.write('{"op": "set", "key": "c", "valu')
    s2 = PersistentKVStore(path)  # must NOT raise
    assert s2.get("a") == "1"
    assert s2.get("b") == "2"
    assert s2.exists("c") is False  # the torn record is dropped


def test_tampered_record_is_rejected(tmp_path):
    path = tmp_path / "log.jsonl"
    s = PersistentKVStore(path)
    s.set("a", "1")
    del s
    # Flip the value but keep valid JSON — the stored checksum no longer matches.
    with open(path) as f:
        record = json.loads(f.readline())
    record["value"] = "tampered"
    with open(path, "w") as f:
        f.write(json.dumps(record) + "\n")
    s2 = PersistentKVStore(path)
    assert s2.exists("a") is False  # checksum mismatch -> record not trusted
