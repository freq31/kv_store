"""
Milestone 5, Part B — expose INCR / EXPIRE / TTL over the network protocol.

You already built incr()/expire()/ttl() on the store; here you teach the server's
handle_command to speak them. Protocol replies to implement:

    INCR <key> [amount]   -> "VALUE <n>"                (amount defaults to 1)
    EXPIRE <key> <secs>   -> "OK"  (or "NOT_FOUND" if the key doesn't exist)
    TTL <key>             -> "VALUE <seconds>"          (integer)
                             "VALUE -1" if the key has no expiry
                             "NOT_FOUND" if the key is missing

Usage errors mirror the existing commands, e.g. "ERROR usage: INCR <key>".
"""

from kvstore.server import handle_command
from kvstore.store import KVStore


def test_incr_returns_new_value():
    s = KVStore()
    assert handle_command(s, "INCR counter") == "VALUE 1"
    assert handle_command(s, "INCR counter") == "VALUE 2"
    assert handle_command(s, "INCR counter 5") == "VALUE 7"


def test_incr_without_key_is_usage_error():
    s = KVStore()
    assert handle_command(s, "INCR") == "ERROR usage: INCR <key>"


def test_expire_ok_and_not_found():
    s = KVStore()
    s.set("k", "v")
    assert handle_command(s, "EXPIRE k 100") == "OK"
    assert handle_command(s, "EXPIRE ghost 100") == "NOT_FOUND"


def test_ttl_reports_remaining():
    s = KVStore()
    s.set("k", "v")
    handle_command(s, "EXPIRE k 100")
    reply = handle_command(s, "TTL k")
    assert reply.startswith("VALUE ")
    remaining = int(reply.split()[1])
    assert 90 <= remaining <= 100


def test_ttl_minus_one_when_no_expiry():
    s = KVStore()
    s.set("k", "v")
    assert handle_command(s, "TTL k") == "VALUE -1"


def test_ttl_not_found_for_missing_key():
    s = KVStore()
    assert handle_command(s, "TTL nope") == "NOT_FOUND"
