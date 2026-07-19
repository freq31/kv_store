# kv_store

A key-value store built from scratch, in Python, to learn storage-engine internals
(the ideas behind Redis, etcd, and DynamoDB).

## What is a key-value store?

The simplest kind of database: you `set(key, value)`, later you `get(key)` it back,
and you can `delete(key)`. Think of a giant dictionary that lives in a server, survives
restarts, and can be talked to over a network. We build up to that in milestones.

## Roadmap

- [ ] **Milestone 1 — In-memory core (today):** `set` / `get` / `delete` / `exists` / `keys`, backed by a dict, with tests.
- [ ] **Milestone 2 — Persistence:** save writes to disk (append-only log) so data survives a restart.
- [ ] **Milestone 3 — Network server:** talk to the store over TCP or HTTP.
- [ ] **Milestone 4 — Extras:** TTL/expiry, LRU eviction, benchmarks.

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
src/kvstore/store.py   # the KVStore class — the code you write
tests/test_store.py    # the spec: make every test pass
```
