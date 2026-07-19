"""kvstore — a small key-value store built from scratch."""

from kvstore.store import KVStore
from kvstore.persistent_store import PersistentKVStore

__all__ = ["KVStore", "PersistentKVStore"]
