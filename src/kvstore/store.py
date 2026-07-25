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
import time


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
        # Milestone 5: absolute expiry time (epoch seconds) for keys that have a TTL.
        # A key is in here only if it has a TTL; plain keys never appear.
        self._expiry: dict[str, float] = {}
        # Milestone 6: background sweeper that actively evicts expired keys.
        self._sweeper_thread: threading.Thread | None = None
        self._sweeper_stop = threading.Event()

    def set(self, key: str, value: str, ttl: float | None = None) -> None:
        """Store `value` under `key`. Overwrites if the key already exists.

        Milestone 5: if `ttl` (in seconds) is given, the key auto-expires that many
        seconds from now. A plain set with no ttl must CLEAR any previous expiry on
        the key — like Redis, overwriting a key with SET removes its old TTL.
        """
        with self._lock:
            self._data[key] = value
            if ttl is not None:
                self._expiry[key] = time.time() + ttl
            else:
                self._expiry.pop(key, None)

    def get(self, key: str) -> str:
        """Return the value for `key`, or raise KeyNotFoundError if missing."""
        # TODO: return the value; raise KeyNotFoundError(key) if not present
        with self._lock:
            self._purge_if_expired(key)
            if key not in self._data:
                raise KeyNotFoundError(f"Key '{key}' not found.", key)
            return self._data[key]

    def delete(self, key: str) -> None:
        """Remove `key`. Raise KeyNotFoundError if it isn't there."""
        # TODO: remove the key; raise KeyNotFoundError(key) if not present
        with self._lock:
            self._purge_if_expired(key)
            if key not in self._data:
                raise KeyNotFoundError(f"Key '{key}' not found.", key)
            del self._data[key]
            self._expiry.pop(key, None)

    def exists(self, key: str) -> bool:
        """Return True if `key` is in the store, else False."""
        with self._lock:
            self._purge_if_expired(key)
            if key in self._data:
                return True
            return False

    def keys(self) -> list[str]:
        """Return all keys currently stored (order does not matter)."""
        with self._lock:
            return [_key for _key in self._data.keys()]

    def __len__(self) -> int:
        """Number of keys stored. Lets you call len(store)."""
        with self._lock:
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
            self._purge_if_expired(key)
            current = int(self._data.get(key, "0"))
            total = current + amount
            self.set(key, str(total))
            return total

    # ------------------------------------------------------------------
    # Milestone 5 — TTL / expiry (implement the three stubs below)
    # ------------------------------------------------------------------

    def _purge_if_expired(self, key: str) -> None:
        """If `key` has a TTL that has already passed, delete it now (lazy expiration).

        'Lazy' means we don't run a background timer — we simply check-and-drop a key
        the moment someone touches it. This is Redis's primary expiry strategy: cheap,
        and a key you never look at again costs nothing until you do.

        Wire this into `get` and `exists` (call it at the top) so expired keys look gone.
        """
        with self._lock:
            if key in self._expiry and time.time() >= self._expiry[key]:
                self._data.pop(key, None)
                del self._expiry[key]

    def expire(self, key: str, seconds: float) -> bool:
        """Attach (or replace) a TTL on an EXISTING key.

        Return True if the TTL was set, or False if the key doesn't exist (or has
        already expired). Purge first so an expired key correctly reports False.
        """
        # TODO
        with self._lock:
            self._purge_if_expired(key)
            if key not in self._data:
                return False
            # only if key is present in data set an expiry time
            self._expiry[key] = time.time() + seconds
            return True

    def ttl(self, key: str) -> float | None:
        """Return the seconds remaining before `key` expires.

        - key missing (or already expired) -> raise KeyNotFoundError
        - key exists but has NO expiry      -> return None
        - otherwise                         -> remaining seconds (a float >= 0.0)
        """
        with self._lock:
            self._purge_if_expired(key)
            if key not in self._data:
                raise KeyNotFoundError(f"Key: {key} not found", key)
            if key in self._expiry:
                time_rem = self._expiry[key] - time.time()
                return time_rem
            return None

    # ------------------------------------------------------------------
    # Milestone 6 — active expiration (a background sweeper thread)
    # ------------------------------------------------------------------

    def _sweep_expired(self) -> int:
        """Remove ALL currently-expired keys in one pass. Return how many were removed.

        Lazy expiration (Milestone 5) only drops a key when someone touches it, so an
        expired key nobody looks at sits in memory forever. This is the *active* half:
        a single sweep that evicts every expired key right now. The background thread
        below calls this on a timer.

        Note: build the `expired` list FIRST, then delete — you can't delete from a
        dict while iterating over it.
        """
        with self._lock:
            now = time.time()
            expired = [key for key, value in self._expiry.items() if now >= value]
            for key in expired:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
            return len(expired)

    def start_expiry_sweeper(self, interval: float = 1.0) -> None:
        """Start a background thread that calls _sweep_expired() every `interval` seconds.

        Steps:
          1. If a sweeper is already running (self._sweeper_thread is not None), just return.
          2. Clear the stop flag: self._sweeper_stop.clear()
          3. Define a loop that runs until stopped:
                 while not self._sweeper_stop.wait(interval):
                     self._sweep_expired()
             (Event.wait returns True the moment stop() is called — so the loop exits
             promptly — and returns False on timeout, which is when you sweep.)
          4. Start it as a daemon thread and store it in self._sweeper_thread.
        """
        with self._lock:
            if self._sweeper_thread is not None:
                return None

            self._sweeper_stop.clear()

            def loop() -> None:
                while not self._sweeper_stop.wait(interval):
                    self._sweep_expired()

            self._sweeper_thread = threading.Thread(target=loop, daemon=True)
            self._sweeper_thread.start()

    def stop_expiry_sweeper(self) -> None:
        """Stop the background sweeper and wait for the thread to finish.

        Set self._sweeper_stop, join the thread (with a timeout), then reset
        self._sweeper_thread back to None so it can be started again later.
        """
        self._sweeper_stop.set()

        thread = self._sweeper_thread

        if thread is not None:
            thread.join(5.0)

        self._sweeper_thread = None
