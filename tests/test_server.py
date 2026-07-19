"""
Tests for Milestone 3 — the network server.

Most tests hit handle_command directly (fast, no sockets). The last one starts
the REAL server on a background thread and talks to it over a real TCP socket,
proving the whole thing works end-to-end.
"""

import socket
import threading

from kvstore.server import KVServer, handle_command
from kvstore.store import KVStore

# --- handle_command: the command parser/dispatcher ---


def test_set_returns_ok_and_stores_value():
    store = KVStore()
    assert handle_command(store, "SET name aditya") == "OK"
    assert store.get("name") == "aditya"


def test_get_returns_value():
    store = KVStore()
    store.set("name", "aditya")
    assert handle_command(store, "GET name") == "VALUE aditya"


def test_get_missing_key_returns_not_found():
    store = KVStore()
    assert handle_command(store, "GET nope") == "NOT_FOUND"


def test_value_may_contain_spaces():
    store = KVStore()
    assert handle_command(store, "SET greeting hello world") == "OK"
    assert handle_command(store, "GET greeting") == "VALUE hello world"


def test_delete_ok_then_not_found():
    store = KVStore()
    store.set("temp", "1")
    assert handle_command(store, "DEL temp") == "OK"
    assert handle_command(store, "DEL temp") == "NOT_FOUND"


def test_exists_true_and_false():
    store = KVStore()
    assert handle_command(store, "EXISTS a") == "FALSE"
    store.set("a", "1")
    assert handle_command(store, "EXISTS a") == "TRUE"


def test_commands_are_case_insensitive():
    store = KVStore()
    assert handle_command(store, "set a 1") == "OK"
    assert handle_command(store, "get a") == "VALUE 1"


def test_unknown_command():
    store = KVStore()
    assert handle_command(store, "FLY a b") == "ERROR unknown command: FLY"


def test_set_without_value_is_usage_error():
    store = KVStore()
    assert handle_command(store, "SET onlykey") == "ERROR usage: SET <key> <value>"


def test_get_without_key_is_usage_error():
    store = KVStore()
    assert handle_command(store, "GET") == "ERROR usage: GET <key>"


# --- Full end-to-end test over a real TCP socket ---


def test_server_end_to_end():
    server = KVServer("127.0.0.1", 0, KVStore())  # port 0 = pick any free port
    port = server.server_address[1]
    # Small poll interval so server.shutdown() returns almost instantly (default is 0.5s).
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
    thread.start()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
            sock.sendall(b"SET name aditya\n")
            assert sock.recv(1024) == b"OK\n"
            sock.sendall(b"GET name\n")
            assert sock.recv(1024) == b"VALUE aditya\n"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)  # ensure the server thread is fully stopped before returning
