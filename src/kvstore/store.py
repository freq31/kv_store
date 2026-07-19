"""
The core in-memory key-value store.

A key-value store is basically a dictionary you talk to through a clean,
well-defined API. Redis, etcd, and DynamoDB are all (much bigger) versions
of this same idea. Today you build the in-memory core.

Your job: implement each method below so the tests in tests/test_store.py pass.
Run the tests with:   ./.venv/bin/pytest -v
"""

from __future__ import annotations

import threading


class KeyNotFoundError(KeyError):
    """Raised when a key does not exist in the store."""

    def __init__(self, message: str, key: str):
        super().__init__(message)
        self.key = key


class KVStore:
    def __init__(self) -> None:
        # The actual data lives in a plain Python dict for now.
        # Later milestones will replace/back this with disk persistence.
        self._data: dict[str, str] = {}
        # Milestone 4: a lock to make compound operations safe when many threads
        # (e.g. many network clients) hit the store at once. RLock = "reentrant":
        # the same thread may acquire it more than once (incr -> set) without deadlock.
        self._lock = threading.RLock()

    def set(self, key: str, value: str) -> None:
        """Store `value` under `key`. Overwrites if the key already exists."""
        with self._lock:
            self._data[key] = value

    def get(self, key: str) -> str:
        """Return the value for `key`, or raise KeyNotFoundError if missing."""
        # TODO: return the value; raise KeyNotFoundError(key) if not present
        if key not in self._data:
            raise KeyNotFoundError(f"Key '{key}' not found.", key)
        return self._data[key]

    def delete(self, key: str) -> None:
        """Remove `key`. Raise KeyNotFoundError if it isn't there."""
        # TODO: remove the key; raise KeyNotFoundError(key) if not present
        with self._lock:
            if key not in self._data:
                raise KeyNotFoundError(f"Key '{key}' not found.", key)
            del self._data[key]

    def exists(self, key: str) -> bool:
        """Return True if `key` is in the store, else False."""
        if key in self._data:
            return True
        return False

    def keys(self) -> list[str]:
        """Return all keys currently stored (order does not matter)."""
        return [_key for _key in self._data.keys()]

    def __len__(self) -> int:
        """Number of keys stored. Lets you call len(store)."""
        return len(self._data)

    def incr(self, key: str, amount: int = 1) -> int:
        """Atomically add `amount` to the integer at `key` and return the new value.

        If `key` doesn't exist yet, treat its current value as 0. Values are stored
        as strings, so you convert to int and back.

        *** THE STAR OF MILESTONE 4 ***
        This is a "read-modify-write": read the current number, add to it, write it
        back. If two threads run this at the same time WITHOUT a lock, both can read
        the same old value (say 5), both compute 6, and both write 6 — so one +1 is
        silently lost. Holding self._lock across ALL THREE steps makes them one
        indivisible unit, so no update is ever lost. This bug is called a race
        condition, and it's a classic interview topic.
        """
        with self._lock:
            current = int(self._data.get(key, "0"))
            total = current + amount
            self.set(key, str(total))
            return total
