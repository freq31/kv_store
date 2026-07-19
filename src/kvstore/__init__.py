"""kvstore — a small key-value store built from scratch."""

from kvstore.persistent_store import PersistentKVStore
from kvstore.store import KVStore

__all__ = ["KVStore", "PersistentKVStore"]
