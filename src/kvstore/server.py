"""
Milestone 3 — a network server.

THE IDEA
--------
Right now, the only way to use your store is to `import` it from Python. A real
database runs as a *server*: it listens on a network port, clients connect and send
text commands, and it sends text replies back. Redis, for example, listens on port
6379 and speaks a simple text protocol. We build a tiny version of that.

We split the work into two clean layers:

1. handle_command(store, line)  <-- YOU implement this (the interesting part)
   A pure function: takes one line of text, decides what it means, calls the store,
   and returns a reply string. No sockets involved, so it's trivial to test.

2. The socket plumbing (KVServer / _Handler)  <-- provided for you, fully working
   The fiddly, arcane part of accepting TCP connections and reading lines. Read it
   to understand it, but you don't have to write it. It just calls handle_command
   once per line the client sends.

THE PROTOCOL (the "language" clients speak)
-------------------------------------------
One command per line. Reply is one line. Your handle_command must return EXACTLY
these reply strings so clients (and the tests) know what happened:

    SET <key> <value>   ->  "OK"
    GET <key>           ->  "VALUE <value>"   (or "NOT_FOUND" if missing)
    DEL <key>           ->  "OK"              (or "NOT_FOUND" if missing)
    EXISTS <key>        ->  "TRUE" / "FALSE"

    unknown command     ->  "ERROR unknown command: <cmd>"
    SET with no value   ->  "ERROR usage: SET <key> <value>"
    GET/DEL/EXISTS with no key -> "ERROR usage: <CMD> <key>"

Note: a value may contain spaces. `SET greeting hello world` stores the value
"hello world". (Hint: str.split(maxsplit=2) splits into at most 3 pieces.)

Run the server by hand:   ./.venv/bin/python -m kvstore.server
Then in another terminal:  nc 127.0.0.1 6380     (type SET/GET commands)
"""

from __future__ import annotations

import socketserver
from enum import Enum

from kvstore.store import KeyNotFoundError, KVStore


class Messages(Enum):
    OK = "OK"
    NOT_FOUND = "NOT_FOUND"
    TRUE = "TRUE"
    FALSE = "FALSE"
    ERROR_UNKNOWN_COMMAND = "ERROR unknown command: {}"
    ERROR_USAGE_SET = "ERROR usage: SET <key> <value>"
    ERROR_USAGE_GET_DEL_EXISTS = "ERROR usage: {} <key>"
    ERROR_EMPTY_COMMAND = "ERROR empty command"
    GET_VALUE = "VALUE {}"


def handle_command(store: KVStore, line: str) -> str:
    """Parse one command line, act on the store, and return the reply string.

    Steps to implement:
      1. Strip whitespace/newline off `line`. If it's empty, return "ERROR empty command".
      2. Split into pieces. The first piece (uppercased) is the command.
      3. Branch on the command (SET / GET / DEL / EXISTS) and:
           - check it has enough arguments (return the ERROR usage string if not)
           - call the matching store method
           - return the correct reply string from the protocol above
      4. Anything else -> "ERROR unknown command: <cmd>".

    Reminder: store.get()/delete() raise KeyNotFoundError when a key is missing —
    catch that and turn it into "NOT_FOUND".
    """
    if not line.strip():
        return Messages.ERROR_EMPTY_COMMAND.value

    command_list = line.strip().split(sep=" ", maxsplit=5)
    op = command_list[0].upper()

    if op == "SET":
        if len(command_list) < 3:
            return Messages.ERROR_USAGE_SET.value
        key = command_list[1]
        value = " ".join(command_list[2:])
        store.set(key, value)
        return Messages.OK.value
    elif op == "GET":
        if len(command_list) < 2:
            return Messages.ERROR_USAGE_GET_DEL_EXISTS.value.format(op)
        key = command_list[1]
        try:
            value = store.get(key)
            return Messages.GET_VALUE.value.format(value)
        except KeyNotFoundError:
            return Messages.NOT_FOUND.value
    elif op == "DEL":
        if len(command_list) < 2:
            return Messages.ERROR_USAGE_GET_DEL_EXISTS.value.format(op)
        key = command_list[1]
        try:
            store.delete(key)
            return Messages.OK.value
        except KeyNotFoundError:
            return Messages.NOT_FOUND.value
    elif op == "EXISTS":
        if len(command_list) < 2:
            return Messages.ERROR_USAGE_GET_DEL_EXISTS.value.format(op)
        key = command_list[1]
        if store.exists(key):
            return Messages.TRUE.value
        else:
            return Messages.FALSE.value
    elif op == "EXPIRE":
        if len(command_list) < 3:
            return Messages.ERROR_USAGE_GET_DEL_EXISTS.value.format(op)
        key = command_list[1]
        seconds = float(command_list[2])
        found = store.expire(key, seconds)
        if found:
            return Messages.OK.value
        else:
            return Messages.NOT_FOUND.value
    elif op == "TTL":
        if len(command_list) < 2:
            return Messages.ERROR_USAGE_GET_DEL_EXISTS.value.format(op)
        key = command_list[1]
        try:
            ttl = store.ttl(key)
            if not ttl:
                ttl = -1
            return Messages.GET_VALUE.value.format(int(ttl))
        except KeyNotFoundError:
            return Messages.NOT_FOUND.value
    elif op == "INCR":
        if len(command_list) < 2:
            return Messages.ERROR_USAGE_GET_DEL_EXISTS.value.format(op)
        key = command_list[1]
        amount = 1
        if len(command_list) == 3:
            amount = int(command_list[2])
        total = store.incr(key, amount)
        return Messages.GET_VALUE.value.format(total)
    else:
        return Messages.ERROR_UNKNOWN_COMMAND.value.format(op)


# ---------------------------------------------------------------------------
# Socket plumbing below — provided and working. Read it, but you needn't edit it.
# ---------------------------------------------------------------------------


class _Handler(socketserver.StreamRequestHandler):
    """Handles one client connection: read lines, reply to each until they disconnect."""

    def handle(self) -> None:
        server = self.server
        assert isinstance(server, KVServer)  # tells the type checker what .store is
        for raw in self.rfile:  # self.rfile yields one line (bytes) at a time
            line = raw.decode("utf-8")
            if line.strip().upper() == "QUIT":
                break
            reply = handle_command(server.store, line)
            self.wfile.write((reply + "\n").encode("utf-8"))


class KVServer(socketserver.ThreadingTCPServer):
    """A threaded TCP server that shares one store across all client connections."""

    allow_reuse_address = True  # lets you restart quickly without "address in use"
    daemon_threads = True  # handler threads die with the process — they can never hang shutdown

    def __init__(self, host: str, port: int, store: KVStore) -> None:
        super().__init__((host, port), _Handler)
        self.store = store


def serve(host: str = "127.0.0.1", port: int = 6380, store: KVStore | None = None) -> None:
    """Start the server and block forever, serving requests."""
    server = KVServer(host, port, store or KVStore())
    print(f"kvstore listening on {host}:{port} (Ctrl-C to stop)")
    server.serve_forever()


if __name__ == "__main__":
    serve()
