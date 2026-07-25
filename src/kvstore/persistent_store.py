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
import os
import time
import zlib
from pathlib import Path

from kvstore.store import KVStore


class PersistentKVStore(KVStore):
    def __init__(self, path: str, auto_compact_threshold: int = 1000) -> None:
        # Sets up an empty self._data dict (Milestone 1's __init__).
        super().__init__()
        self._path = Path(path)
        # Milestone 7: auto-compaction. Track how many records the log holds so we can
        # compact automatically once it grows too large relative to the live key count.
        self._auto_compact_threshold = auto_compact_threshold
        self._log_entries = 0
        # Rebuild state from the log file (if one exists) before serving requests.
        self._load()

    def _append(self, record: dict) -> None:
        """Append one operation to the log file as a single JSON line.

        Hint: open the file in append mode ("a"), json.dumps(record), write it,
        then write a newline "\\n" so each record sits on its own line.
        """
        with open(self._path, "a") as f:
            # compute checksum for data integrity
            record = self._store_checksum(record)
            f.write(json.dumps(record) + "\n")
            f.flush()
            os.fsync(f.fileno())

        self._log_entries += 1

    def _get_expiry(self, record: dict) -> float | None:
        expiry = record.get("expiry", None)
        if expiry is not None:
            return float(expiry)
        return None

    def _get_ttl(self, expiry: float) -> tuple[bool, float | None]:
        now = time.time()
        if expiry > now:
            return (False, expiry - now)
        return (True, None)

    def _store_checksum(self, record: dict) -> dict:
        crc = self._checksum(record)
        record["crc"] = crc
        return record

    def _is_corrupt_record(self, record: dict) -> bool:
        actual_crc = record["crc"]
        record.pop("crc", None)
        current_crc = self._checksum(record)
        return not (actual_crc == current_crc)

    def _checksum(self, record: dict) -> int:
        """Return a CRC32 checksum of `record` (which must NOT contain a 'crc' key).

        A checksum is a short number derived from the bytes of the record. If even one
        byte changes on disk — corruption, a torn write, tampering — the recomputed
        checksum won't match the stored one, so we can DETECT bad data on reload instead
        of silently loading garbage.

        Implement:
            import zlib   # add at the top of the file
            payload = json.dumps(record, sort_keys=True)   # sort_keys => stable bytes
            return zlib.crc32(payload.encode())

        `sort_keys=True` is essential: it makes serialization deterministic so the write
        side and the read side hash exactly the same bytes.
        """
        payload = json.dumps(record, sort_keys=True)
        return zlib.crc32(payload.encode())

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
        count = 0
        if self._path.exists():
            with open(self._path, "r+") as f:
                while True:
                    offset = f.tell()
                    line = f.readline()

                    if not line:
                        break

                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                        except json.JSONDecodeError:
                            f.seek(offset)
                            f.truncate()  # drop the torn line + everything after
                            break
                        count += 1
                        if record["op"] == "set":
                            ttl = None
                            expiry = self._get_expiry(record)
                            if expiry is not None:
                                (is_expired, ttl) = self._get_ttl(expiry)
                                if is_expired:
                                    continue
                            if self._is_corrupt_record(record):
                                f.seek(offset)
                                f.truncate()  # drop the torn line + everything after
                                break

                            super().set(record["key"], record["value"], ttl)
                        elif record["op"] == "delete":
                            if self._is_corrupt_record(record):
                                f.seek(offset)
                                f.truncate()  # drop the torn line + everything after
                                break
                            super().delete(record["key"])
                        elif record["op"] == "expire":
                            expiry = self._get_expiry(record)
                            if expiry is None:
                                continue
                            (is_expired, ttl) = self._get_ttl(expiry)
                            if is_expired:
                                self._data.pop(record["key"], None)
                                self._expiry.pop(record["key"], None)
                            elif ttl is not None:
                                if self._is_corrupt_record(record):
                                    f.seek(offset)
                                    f.truncate()  # drop the torn line + everything after
                                    break
                                super().expire(record["key"], ttl)

        with self._lock:
            self._log_entries = count

    def set(self, key: str, value: str, ttl: float | None = None) -> None:
        """Persist the write, then apply it in memory.

        Order matters: log to disk FIRST (durability), THEN update memory by
        calling super().set(key, value).

        NOTE (M5): `ttl` is forwarded so TTL works in-memory on the persistent store,
        but the log does NOT yet record the expiry — so a TTL set here is lost on
        restart. Persisting expiry (a new log field + replay handling) is Milestone 6.
        """
        with self._lock:
            if ttl is not None:
                self._append({"op": "set", "key": key, "value": value, "expiry": time.time() + ttl})
            else:
                self._append({"op": "set", "key": key, "value": value})
            super().set(key, value, ttl)
            self._maybe_compact()

    def delete(self, key: str) -> None:
        """Persist the delete, then apply it in memory.

        Careful: only log the delete if the key actually exists, so a failed
        delete doesn't leave a junk line in the log. super().delete() already
        raises KeyNotFoundError for a missing key — let that happen first.
        """
        with self._lock:
            super().delete(key)
            self._append({"op": "delete", "key": key})
            self._maybe_compact()

    def expire(self, key: str, seconds: float) -> bool:
        with self._lock:
            isPresent = super().expire(key, seconds)
            if isPresent:
                self._append({"op": "expire", "key": key, "expiry": time.time() + seconds})
                self._maybe_compact()
            return isPresent

    def _maybe_compact(self) -> None:
        """Compact automatically once the log has grown too large.

        Milestone 7. The log grows by one line per write; compaction shrinks it back
        to one line per live key. We want to compact when the log has a lot of *dead*
        weight (overwrites + deletes), but NOT every write, and NOT just because the
        dataset is legitimately big.

        A good trigger:
            self._log_entries >= max(self._auto_compact_threshold, 2 * len(self._data))

        - The `2 * len(self._data)` term means "compact once the log is ~twice the size
          it would be if compacted" — i.e. roughly half the log is dead weight. This
          scales with the dataset so a store with 1M live keys doesn't compact until
          the log hits ~2M entries.
        - The `threshold` term is a floor so tiny stores don't compact on every write.

        If the trigger fires, call self.compact() (which will reset self._log_entries).

        Call this at the END of every write path (set / delete / expire), after the
        record has been appended.
        """
        if self._log_entries >= max(self._auto_compact_threshold, 2 * len(self._data)):
            self.compact()

    def compact(self) -> None:
        """Rewrite the log so it holds only the CURRENT state — one 'set' per key.

        THE PROBLEM: the log only ever grows. Set the same key 1000 times and the
        file has 1000 lines, even though memory holds just 1 key. That wastes disk
        and makes startup (replay) slow. Compaction rebuilds a minimal log from the
        current in-memory state and throws the history away.

        Do it SAFELY so a crash mid-compaction can't destroy your data:
          1. Take self._lock (no writes should sneak in while we rebuild).
          2. Write current self._data to a NEW temporary file — one 'set' record per key.
             (A deleted key simply isn't in self._data, so it won't be written.)
          3. os.replace(tmp_path, self._path) to swap it in. os.replace is ATOMIC on
             the same filesystem: at every instant readers see either the whole old
             file or the whole new file — never a half-written one. (Contrast: if you
             truncated and rewrote the real file in place, a crash halfway would
             leave a corrupt log.)

        You'll need `import os` at the top of the file for os.replace.
        Hint for the temp path:  tmp = self._path.with_suffix(self._path.suffix + ".tmp")

        After compaction: the log has exactly len(self._data) lines, and the data is
        unchanged — including after a restart.
        """
        with self._lock:
            temp_path = self._path.with_suffix(self._path.suffix + ".tmp")
            expired_keys = []
            with open(temp_path, "w") as f:
                for key, value in self._data.items():
                    now = time.time()
                    expiry = self._expiry.get(key, None)
                    if expiry is not None:
                        if expiry <= now:
                            expired_keys.append(key)
                            continue
                        record = {"op": "set", "key": key, "value": value, "expiry": expiry}
                        record = self._store_checksum(record)
                    else:
                        record = {"op": "set", "key": key, "value": value}
                        record = self._store_checksum(record)
                    f.write(json.dumps(record) + "\n")

            for key in expired_keys:
                self._data.pop(key, None)
                self._expiry.pop(key, None)

            self._log_entries = len(self._data)

            os.replace(temp_path, self._path)
