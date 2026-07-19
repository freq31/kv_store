"""
Milestone 2 — Persistence via an append-only log.

THE PROBLEM
-----------
Your Milestone 1 KVStore keeps everything in a Python dict. When the program
stops, the dict is gone. A real database must survive restarts.

THE IDEA: an append-only log (a.k.a. write-ahead log)
-----------------------------------------------------
Every time someone changes the data, we write that change to the END of a file
before touching memory. The file becomes a history of everything that happened:

    {"op": "set", "key": "name", "value": "aditya"}
    {"op": "set", "key": "city", "value": "hyderabad"}
    {"op": "delete", "key": "name"}

When the store starts up, we REPLAY that file from top to bottom to rebuild the
in-memory dict. After replaying the three lines above, memory holds
{"city": "hyderabad"} — exactly where we left off. This is (a simplified version
of) how Redis AOF and Bitcask actually work.

Why append-only? Appending is fast and never corrupts earlier data. We never edit
or delete lines in place — a later line simply overrides an earlier one on replay.

YOUR JOB
--------
Implement the stubs so tests/test_persistent_store.py passes. We reuse Milestone 1
by subclassing KVStore: the in-memory logic is inherited; you only add the disk part.
"""

from __future__ import annotations

import json
from pathlib import Path

from kvstore.store import KVStore, KeyNotFoundError


class PersistentKVStore(KVStore):
    def __init__(self, path: str) -> None:
        # Sets up an empty self._data dict (Milestone 1's __init__).
        super().__init__()
        self._path = Path(path)
        # Rebuild state from the log file (if one exists) before serving requests.
        self._load()

    def _append(self, record: dict) -> None:
        """Append one operation to the log file as a single JSON line.

        Hint: open the file in append mode ("a"), json.dumps(record), write it,
        then write a newline "\\n" so each record sits on its own line.
        """
        with open(self._path, "a") as f:
            f.write(json.dumps(record) + "\n")

    def _load(self) -> None:
        """Replay the log file to rebuild self._data.

        Steps:
          1. If self._path does not exist yet, there's nothing to replay — return.
          2. Otherwise read the file line by line.
          3. For each non-empty line: json.loads(line) -> record dict.
          4. If record["op"] == "set":  self._data[record["key"]] = record["value"]
             If record["op"] == "delete": self._data.pop(record["key"], None)

        IMPORTANT: write to self._data DIRECTLY here. Do NOT call self.set()/self.delete()
        during replay, or you'd append the whole history back onto the log every startup.
        """
        if self._path.exists():
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record= json.loads(line)
                        if record["op"] == "set":
                            super().set(record["key"], record["value"])
                        elif record["op"] == "delete":
                            super().delete(record["key"])

    def set(self, key: str, value: str) -> None:
        """Persist the write, then apply it in memory.

        Order matters: log to disk FIRST (durability), THEN update memory by
        calling super().set(key, value).
        """
        self._append({"op": "set", "key": key, "value": value})
        super().set(key, value)

    def delete(self, key: str) -> None:
        """Persist the delete, then apply it in memory.

        Careful: only log the delete if the key actually exists, so a failed
        delete doesn't leave a junk line in the log. super().delete() already
        raises KeyNotFoundError for a missing key — let that happen first.
        """
        try:
            super().delete(key)
            self._append({"op": "delete", "key": key})
        except KeyNotFoundError:
            raise
