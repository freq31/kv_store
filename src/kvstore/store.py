"""
The core in-memory key-value store.

A key-value store is basically a dictionary you talk to through a clean,
well-defined API. Redis, etcd, and DynamoDB are all (much bigger) versions
of this same idea. Today you build the in-memory core.

Your job: implement each method below so the tests in tests/test_store.py pass.
Run the tests with:   ./.venv/bin/pytest -v
"""

from __future__ import annotations


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

    def set(self, key: str, value: str) -> None:
        """Store `value` under `key`. Overwrites if the key already exists."""
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
