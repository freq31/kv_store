# kv_store

A key-value store built from scratch, in Python, to learn storage-engine internals
(the ideas behind Redis, etcd, and DynamoDB).

## What is a key-value store?

The simplest kind of database: you `set(key, value)`, later you `get(key)` it back,
and you can `delete(key)`. Think of a giant dictionary that lives in a server, survives
restarts, and can be talked to over a network. We build up to that in milestones.

## Roadmap

- [x] **Milestone 1 — In-memory core:** `set` / `get` / `delete` / `exists` / `keys`, backed by a dict, with tests.
- [x] **Milestone 2 — Persistence:** append-only log on disk so data survives a restart.
- [x] **Milestone 3 — Network server:** talk to the store over TCP with a line-based text protocol.
- [x] **Milestone 4 — Concurrency & compaction:** a lock for thread-safe writes, atomic `INCR`, and log compaction.
- [x] **Milestone 5 — TTL / expiry:** keys that auto-expire (lazy expiration), plus `INCR` / `EXPIRE` / `TTL` over the network.
- [ ] **Milestone 6 — Durable expiry & background maintenance:** persist TTLs across restarts, actively evict expired keys, and auto-trigger compaction.

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
```

## Run the tests

```bash
./.venv/bin/pytest -v
```

## Project layout

```
src/kvstore/store.py             # KVStore: in-memory core, locking, INCR, TTL
src/kvstore/persistent_store.py  # PersistentKVStore: append-only log + compaction
src/kvstore/server.py            # TCP server + text-protocol command handler
tests/                           # one spec file per area — make every test pass
```
