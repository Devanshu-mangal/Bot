"""
context_store.py — Versioned in-memory store for all 4 context types.
Thread-safe. Idempotent by (scope, context_id, version).
"""
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

_lock = threading.Lock()

# (scope, context_id) -> {"version": int, "payload": dict, "stored_at": str}
_store: Dict[Tuple[str, str], Dict] = {}

# Conversation memory: conversation_id -> ConversationState dict
_conversations: Dict[str, Dict] = {}

# Merchant-level engagement memory: merchant_id -> EngagementState dict
_merchant_memory: Dict[str, Dict] = {}

# Opted-out merchants (never message again until reset)
_opted_out: set = set()

# Suppressed (suppression_key -> expires_at_epoch)
_suppressed: Dict[str, float] = {}

START_TIME = time.time()


# ─────────────────────────────────────────────
# Context CRUD
# ─────────────────────────────────────────────

def store_context(scope: str, context_id: str, version: int, payload: dict) -> Tuple[bool, str, int]:
    """
    Store context. Returns (accepted, reason, current_version).
    accepted=False if incoming version <= stored version.
    """
    key = (scope, context_id)
    with _lock:
        existing = _store.get(key)
        if existing and existing["version"] >= version:
            return False, "stale_version", existing["version"]
        _store[key] = {
            "version": version,
            "payload": payload,
            "stored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        return True, "ok", version


def get_context(scope: str, context_id: str) -> Optional[Dict]:
    """Return payload dict or None."""
    key = (scope, context_id)
    entry = _store.get(key)
    return entry["payload"] if entry else None


def get_context_version(scope: str, context_id: str) -> int:
    key = (scope, context_id)
    entry = _store.get(key)
    return entry["version"] if entry else 0


def count_by_scope() -> Dict[str, int]:
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    with _lock:
        for (scope, _) in _store:
            if scope in counts:
                counts[scope] += 1
    return counts


def all_triggers() -> Dict[str, dict]:
    """Return all stored trigger payloads keyed by trigger_id."""
    result = {}
    with _lock:
        for (scope, ctx_id), entry in _store.items():
            if scope == "trigger":
                result[ctx_id] = entry["payload"]
    return result


# ─────────────────────────────────────────────
# Conversation memory
# ─────────────────────────────────────────────

def get_conversation(conv_id: str) -> Dict:
    return _conversations.get(conv_id, {
        "turns": [],
        "merchant_id": None,
        "customer_id": None,
        "last_signal_type": None,
        "last_trigger_kind": None,
        "last_body": None,
        "state": "new",           # new | active | engaged | cold | ended
        "auto_reply_streak": 0,
        "opted_out": False,
    })


def save_conversation(conv_id: str, state: Dict):
    with _lock:
        _conversations[conv_id] = state


def end_conversation(conv_id: str):
    with _lock:
        if conv_id in _conversations:
            _conversations[conv_id]["state"] = "ended"


def get_all_conversation_ids_for_merchant(merchant_id: str):
    return [cid for cid, c in _conversations.items() if c.get("merchant_id") == merchant_id]


# ─────────────────────────────────────────────
# Merchant engagement memory
# ─────────────────────────────────────────────

def get_merchant_memory(merchant_id: str) -> Dict:
    return _merchant_memory.get(merchant_id, {
        "messages_sent": 0,
        "no_reply_streak": 0,
        "last_reply_at": None,
        "last_signal_types_sent": [],   # last 5 signal types sent
        "state": "new",                 # new | warm | engaged | cold
        "opted_out": False,
    })


def update_merchant_memory(merchant_id: str, updates: Dict):
    with _lock:
        mem = _merchant_memory.get(merchant_id, {
            "messages_sent": 0, "no_reply_streak": 0,
            "last_reply_at": None, "last_signal_types_sent": [],
            "state": "new", "opted_out": False,
        })
        mem.update(updates)
        _merchant_memory[merchant_id] = mem


def mark_merchant_replied(merchant_id: str, received_at: str):
    with _lock:
        mem = get_merchant_memory(merchant_id)
        mem["no_reply_streak"] = 0
        mem["last_reply_at"] = received_at
        mem["state"] = "engaged"
        _merchant_memory[merchant_id] = mem


def increment_message_sent(merchant_id: str, signal_type: str):
    with _lock:
        mem = get_merchant_memory(merchant_id)
        mem["messages_sent"] = mem.get("messages_sent", 0) + 1
        mem["no_reply_streak"] = mem.get("no_reply_streak", 0) + 1
        recent = mem.get("last_signal_types_sent", [])
        recent.append(signal_type)
        mem["last_signal_types_sent"] = recent[-5:]  # keep last 5
        # Auto-downgrade state
        if mem["no_reply_streak"] >= 3:
            mem["state"] = "cold"
        _merchant_memory[merchant_id] = mem


def is_opted_out(merchant_id: str) -> bool:
    return merchant_id in _opted_out or get_merchant_memory(merchant_id).get("opted_out", False)


def opt_out_merchant(merchant_id: str):
    with _lock:
        _opted_out.add(merchant_id)
        mem = get_merchant_memory(merchant_id)
        mem["opted_out"] = True
        _merchant_memory[merchant_id] = mem


# ─────────────────────────────────────────────
# Suppression
# ─────────────────────────────────────────────

def is_suppressed(key: str) -> bool:
    expires = _suppressed.get(key)
    if expires is None:
        return False
    if time.time() > expires:
        with _lock:
            _suppressed.pop(key, None)
        return False
    return True


def suppress(key: str, ttl_seconds: int):
    with _lock:
        _suppressed[key] = time.time() + ttl_seconds


def clear_suppression(key: str):
    with _lock:
        _suppressed.pop(key, None)


def _clear_all():
    """Wipe all state (for /v1/teardown)."""
    with _lock:
        global _store, _conversations, _merchant_memory, _opted_out, _suppressed
        _store = {}
        _conversations = {}
        _merchant_memory = {}
        _opted_out = set()
        _suppressed = {}


def reset_store():
    """Reset store completely (for new test session)."""
    _clear_all()