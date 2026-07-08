"""Process-global bounded result cache, shared by the REST API and MCP faces.

Both faces re-scan the R2-backed Parquet on every read, and public clients (the
dashboard, a chatbot) repeat the same popular queries. Gold is immutable between
deploys and each topic/dimension ``schema_hash`` is rebuilt at boot, so a small
LRU keyed on ``(tool, normalized args, schema_hash)`` is a safe, cheap win: a
contract change bumps ``schema_hash`` → cache miss, and a process restart clears
the cache.

This module provides:

- ``make_key`` — a pure, stable key builder (shared by both faces).
- ``ResultCache`` — an instance-based bounded LRU so each face owns an isolated
  namespace + capacity (REST and MCP do not share or evict each other's entries).

Only SUCCESS payloads under the per-entry byte cap are stored — error payloads (a
top-level ``"error"`` key) are never cached, and an oversize payload simply isn't
stored (it still returns normally). Each instance is a single ``OrderedDict``
guarded by a lock; capacity + byte cap are passed in per ``put`` call so there is
no import cycle with config.
"""

from __future__ import annotations

import json
import threading
from collections import OrderedDict
from typing import Any


def make_key(tool: str, args: dict[str, Any], schema_hash: str) -> str:
    """Stable cache key from the tool name, its args, and the topic schema hash.

    Args are canonicalized with ``sort_keys`` so call-order / formatting
    differences collapse to one key; ``schema_hash`` scopes the key to the
    current contract, so a schema change (new deploy) yields a fresh namespace.
    """
    return json.dumps(
        {"tool": tool, "schema_hash": schema_hash, "args": args},
        sort_keys=True,
        default=str,
    )


class ResultCache:
    """A bounded LRU of success payloads keyed by ``make_key``.

    Instance-based: each caller (REST face, MCP face) holds its own instance so
    the two never collide or evict one another. Safe to share across threads —
    every access is guarded by an internal lock.
    """

    def __init__(self) -> None:
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        """Return a cached payload (marking it most-recently-used), or ``None``."""
        with self._lock:
            value = self._cache.get(key)
            if value is None:
                return None
            self._cache.move_to_end(key)
            # Shallow copy so a caller can't mutate the stored top-level dict;
            # nested structures are only ever read (serialized) downstream.
            return dict(value)

    def put(
        self,
        key: str,
        payload: dict[str, Any],
        *,
        max_entries: int,
        max_entry_bytes: int,
    ) -> None:
        """Store a SUCCESS payload, honoring the byte cap + LRU capacity.

        No-ops on error payloads (an ``"error"`` key) or payloads whose JSON
        encoding exceeds ``max_entry_bytes`` (e.g. a large data page).
        """
        if "error" in payload:
            return
        try:
            encoded = json.dumps(payload, default=str)
        except (TypeError, ValueError):
            return
        if len(encoded.encode("utf-8")) > max_entry_bytes:
            return
        with self._lock:
            self._cache[key] = dict(payload)
            self._cache.move_to_end(key)
            while len(self._cache) > max_entries:
                self._cache.popitem(last=False)

    def reset(self) -> None:
        """Clear the cache (test helper / manual invalidation)."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Current number of cached entries (test / inspection helper)."""
        with self._lock:
            return len(self._cache)
