"""
main.py — Vera AI Challenge Bot — Production FastAPI Server

Endpoints:
  GET  /v1/healthz    — liveness probe
  GET  /v1/metadata   — bot identity
  POST /v1/context    — receive and store context (idempotent by version)
  POST /v1/tick       — periodic compose (async parallel, ≤20 actions)
  POST /v1/reply      — multi-turn reply handler
"""
from __future__ import annotations
import asyncio
import logging
import os
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# ── Local modules ───────────────────────────────────
import context_store
from signal_engine import collect_signals, rank_signals, pick_winner
from composer import compose_message
from rationale_engine import build_rationale
from reply_handler import handle_reply

# ── Logging ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s"
)
logger = logging.getLogger("vera.main")

# ── App ──────────────────────────────────────────────
app = FastAPI(title="Vera AI Challenge Bot", version="3.0.0")

# ── Config ──────────────────────────────────────────
TEAM_NAME = os.getenv("TEAM_NAME", "Vera Champions")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "team@example.com")
MAX_ACTIONS_PER_TICK = 20
TICK_TIMEOUT_SECONDS = 25  # leave 5s buffer vs 30s judge limit

# ── Suppression TTLs (seconds) ──────────────────────
SUPPRESSION_TTL = {
    1: 4 * 3600,       # Tier 1: 4 hours
    2: 24 * 3600,      # Tier 2: 24 hours
    3: 72 * 3600,      # Tier 3: 72 hours
    4: 7 * 24 * 3600,  # Tier 4: 7 days
}


# ═══════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════

class ContextRequest(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: str = ""


class TickRequest(BaseModel):
    now: str
    available_triggers: List[str] = []


class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str = "merchant"
    message: str
    received_at: str = ""
    turn_number: int = 1


# ═══════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/v1/healthz")
async def healthz():
    counts = context_store.count_by_scope()
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - context_store.START_TIME),
        "contexts_loaded": counts,
        "version": "3.0.0",
    }


@app.get("/v1/metadata")
async def metadata():
    model = "Deterministic insight-driven reasoning engine (Groq-backed for LLM triggers)"
        
    return {
        "team_name": "MangalAI Team",
        "team_members": ["Devanshu"],
        "model": model,
        "approach": (
            "4-context composition: Signal Ranker → Category Router → "
            "Decision Engine → Template/LLM Composer → CTA Enforcer. "
            "Deterministic (temp=0). Zero hallucination via fact injection."
        ),
        "contact_email": CONTACT_EMAIL,
        "version": "3.0.0",
        "submitted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "supported_trigger_kinds": list({
            "research_digest", "search_spike", "perf_spike", "perf_dip",
            "festival_upcoming", "ipl_match_today", "supply_alert", "regulation_change",
            "competitor_opened", "active_planning_intent", "customer_lapsed_hard",
            "customer_lapsed_soft", "recall_due", "chronic_refill_due", "seasonal_perf_dip",
            "bridal_followup", "dormant_with_vera", "curious_ask_due", "milestone_reached",
            "offer_available", "appointment_tomorrow", "review_theme_emerged",
        }),
        "supported_categories": ["dentists", "salons", "restaurants", "gyms", "pharmacies"],
    }


@app.post("/v1/context")
async def push_context(body: ContextRequest):
    # Validate scope
    if body.scope not in ("category", "merchant", "customer", "trigger"):
        return JSONResponse(
            status_code=400,
            content={"accepted": False, "reason": "invalid_scope",
                     "details": f"scope must be one of: category, merchant, customer, trigger"}
        )

    # Auto reset when first category context (version 1) is sent
    if body.scope == "category" and body.version == 1:
        context_store.reset_store()

    accepted, reason, current_version = context_store.store_context(
        body.scope, body.context_id, body.version, body.payload
    )

    stored_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if not accepted:
        # Gracefully handle stale versions instead of rejecting
        return {
            "accepted": True,
            "reason": "duplicate_ignored",
            "current_version": current_version,
            "ack_id": f"ack_{body.context_id}_v{current_version}",
            "stored_at": stored_at,
        }

    # After store_context() succeeds for scope=merchant or scope=category, clear last_body_hash
    if body.scope == "merchant":
        mem = context_store.get_merchant_memory(body.context_id)
        if "last_body_hash" in mem:
            del mem["last_body_hash"]
            context_store.update_merchant_memory(body.context_id, mem)
    elif body.scope == "category":
        # New category version = new digest items → force recompose for all merchants
        import context_store as cs
        for merchant_id in list(cs._merchant_memory.keys()):
            mem = cs.get_merchant_memory(merchant_id)
            if mem.get("last_body_hash"):
                mem.pop("last_body_hash", None)
                cs._merchant_memory[merchant_id] = mem

    return {
        "accepted": True,
        "ack_id": f"ack_{body.context_id}_v{body.version}",
        "stored_at": stored_at,
    }


@app.post("/v1/teardown")
async def teardown():
    """Wipes all state."""
    import context_store
    context_store._clear_all()
    return {
        "wiped": True,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }


@app.post("/v1/tick")
async def tick(body: TickRequest):
    """
    Process all available triggers concurrently.
    Returns up to MAX_ACTIONS_PER_TICK actions.
    Respects TICK_TIMEOUT_SECONDS hard limit.
    """
    start = time.time()
    trigger_ids = body.available_triggers[:MAX_ACTIONS_PER_TICK]

    tasks = [
        asyncio.create_task(_process_trigger(tid, body.now))
        for tid in trigger_ids
    ]

    actions = []
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=TICK_TIMEOUT_SECONDS
        )
        for r in results:
            if isinstance(r, dict) and r.get("body"):
                actions.append(r)
    except asyncio.TimeoutError:
        logger.warning("Tick timeout — returning partial results")

    elapsed = time.time() - start
    logger.info(f"Tick: processed {len(trigger_ids)} triggers → {len(actions)} actions in {elapsed:.2f}s")

    return {"actions": actions}


@app.post("/v1/reply")
async def reply(body: ReplyRequest):
    """Multi-turn reply handler."""
    result = handle_reply(
        conversation_id=body.conversation_id,
        merchant_id=body.merchant_id or "",
        customer_id=body.customer_id,
        message=body.message,
        turn_number=body.turn_number,
        received_at=body.received_at or datetime.now(timezone.utc).isoformat(),
        from_role=body.from_role,
    )
    return result


# ═══════════════════════════════════════════════════
# COMPOSE PIPELINE (called per trigger in tick)
# ═══════════════════════════════════════════════════

async def _process_trigger(trigger_id: str, now: str) -> Optional[Dict]:
    """
    Full compose pipeline for one trigger:
    context lookup → opt-out check → signal collection →
    ranking → winner selection → suppression check →
    message composition → output assembly
    """
    try:
        # ── 1. Load trigger ──────────────────────────────
        trigger = context_store.get_context("trigger", trigger_id)
        if not trigger:
            logger.debug(f"Trigger {trigger_id} not found in store")
            return None

        merchant_id = trigger.get("merchant_id")
        customer_id = trigger.get("customer_id")
        if not merchant_id:
            return None

        # ── 2. Load merchant ─────────────────────────────
        merchant = context_store.get_context("merchant", merchant_id)
        if not merchant:
            logger.debug(f"Merchant {merchant_id} not in store for trigger {trigger_id}")
            return None

        category_slug = merchant.get("category_slug", "")
        if not category_slug:
            return None

        # ── 3. Load category ─────────────────────────────
        category = context_store.get_context("category", category_slug) or {}

        # ── 4. Load customer (if applicable) ─────────────
        customer = None
        if customer_id:
            customer = context_store.get_context("customer", customer_id)

        # ── 5. Opt-out guard ──────────────────────────────
        if context_store.is_opted_out(merchant_id):
            logger.info(f"Merchant {merchant_id} opted out — skipping")
            return None

        # ── 6. Trigger suppression check ──────────────────
        trigger_suppression_key = trigger.get("suppression_key", "")
        if trigger_suppression_key and context_store.is_suppressed(trigger_suppression_key):
            logger.debug(f"Trigger suppression key active: {trigger_suppression_key}")
            return None

        # ── 7. Merchant memory state ──────────────────────
        mem = context_store.get_merchant_memory(merchant_id)
        merchant_state = mem.get("state", "new")
        recent_signal_types = mem.get("last_signal_types_sent", [])

        # ── 8. Collect & rank signals ─────────────────────
        signals = collect_signals(category, merchant, trigger, customer)
        ranked = rank_signals(signals, category_slug, merchant, merchant_state)

        if not ranked:
            return None

        # ── 9. Pick winner (anti-repetition) ─────────────
        winner = pick_winner(ranked, recent_signal_types)
        if not winner:
            return None

        # ── 10. Signal-level suppression ──────────────────
        sig_supp_key = winner.suppression_key
        if context_store.is_suppressed(sig_supp_key):
            logger.debug(f"Signal suppressed: {sig_supp_key}")
            return None

        # ── 11. Compose message ───────────────────────────
        body, cta, send_as = compose_message(
            winner, category, merchant, customer, category_slug
        )

        if not body or not body.strip():
            return None
        
        # Unfilled variable guard: check if any {var} remains
        import re
        if re.search(r'\{[a-z_]+\}', body):
            logger.warning(f"Unfilled variables found in body: {body} — using fallback")
            # Fallback: create a simple generic message
            owner = merchant.get("identity", {}).get("owner_first_name", "")
            body = f"Hi {owner}! Quick check — want to review what's working for your business? Reply YES."

        # ── 12. Build rationale ───────────────────────────
        rationale = build_rationale(
            winner=winner,
            ranked_signals=ranked,
            merchant_state=merchant_state,
            category_slug=category_slug,
            send_as=send_as,
            has_customer=customer is not None,
        )

        # ── 13. Anti-repetition: check last body ──────────
        last_body = mem.get("last_body_hash", "")
        body_hash = _hash_body(body)
        if body_hash == last_body:
            logger.debug("Same body as last send — skipping (anti-repetition)")
            return None

        # ── 14. Conversation ID ───────────────────────────
        conversation_id = f"conv_{merchant_id}_{trigger_id[:20]}"

        # ── 15. Template name/params (for WhatsApp template format) ──
        template_name, template_params = _build_template_fields(
            winner, merchant, customer, category_slug, body
        )

        # ── 16. Record send ───────────────────────────────
        context_store.increment_message_sent(merchant_id, winner.type)
        context_store.update_merchant_memory(merchant_id, {"last_body_hash": body_hash})

        # Save conversation state for reply handler
        conv = context_store.get_conversation(conversation_id)
        conv.update({
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "last_signal_type": winner.type,
            "last_trigger_kind": trigger.get("kind", ""),
            "last_body": body,
            "state": "active",
            "auto_reply_streak": 0,
        })
        context_store.save_conversation(conversation_id, conv)

        # ── 17. Suppression registration ──────────────────
        ttl = SUPPRESSION_TTL.get(winner.tier, 86400)
        context_store.suppress(sig_supp_key, ttl)
        if trigger_suppression_key:
            context_store.suppress(trigger_suppression_key, ttl)

        # ── 18. Final output ──────────────────────────────
        return {
            "conversation_id": conversation_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "send_as": send_as,
            "trigger_id": trigger_id,
            "template_name": template_name,
            "template_params": template_params,
            "body": body,
            "cta": cta,
            "suppression_key": trigger_suppression_key or sig_supp_key,
            "rationale": rationale,
        }

    except Exception as e:
        logger.error(f"Error processing trigger {trigger_id}: {e}", exc_info=True)
        return None


def _hash_body(body: str) -> str:
    import hashlib
    return hashlib.md5(body.encode()).hexdigest()[:12]


def _build_template_fields(
    signal, merchant: Dict, customer: Optional[Dict], category_slug: str, body: str
) -> tuple:
    """Build WhatsApp template name and params from signal context."""
    d = signal.data
    owner = d.get("owner_first_name", d.get("merchant_name", ""))
    kind = signal.trigger_kind

    template_map = {
        "research_digest": ("vera_research_digest_v1", [owner, d.get("digest_source", ""), d.get("digest_title", "")]),
        "search_spike": ("vera_demand_spike_v1", [owner, str(d.get("demand_count", "")), d.get("search_term", ""), d.get("offer_title", "")]),
        "recall_due": ("merchant_recall_reminder_v1", [d.get("customer_name", ""), owner, "", d.get("offer_title", "")]),
        "customer_lapsed_soft": ("merchant_recall_reminder_v1", [d.get("customer_name", ""), owner, "", d.get("offer_title", "")]),
        "customer_lapsed_hard": ("merchant_winback_v1", [d.get("customer_name", ""), owner, d.get("offer_title", "")]),
        "chronic_refill_due": ("merchant_refill_reminder_v1", [d.get("customer_name", ""), owner, ", ".join(d.get("medications", d.get("services_received", []))[:2])]),
        "festival_upcoming": ("vera_festival_push_v1", [owner, d.get("festival_name", ""), d.get("offer_title", "")]),
        "supply_alert": ("vera_compliance_alert_v1", [owner, d.get("recall_batches_label", ""), ""]),
        "milestone_reached": ("vera_milestone_v1", [owner, str(d.get("milestone_value", "")), d.get("milestone_metric", "")]),
        "perf_dip": ("vera_perf_recovery_v1", [owner, str(d.get("dip_pct", "")), d.get("offer_title", "")]),
    }

    result = template_map.get(kind)
    if result:
        return result

    # Generic fallback
    return ("vera_generic_v1", [owner, kind, d.get("offer_title", "")])


# ═══════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    logger.info("Vera AI Challenge Bot v3.0.0 starting up")
    llm = "Anthropic" if os.getenv("ANTHROPIC_API_KEY") else \
          "OpenAI" if os.getenv("OPENAI_API_KEY") else "Template-only (no LLM key set)"
    logger.info(f"LLM provider: {llm}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_level="info",
        reload=False,
    )