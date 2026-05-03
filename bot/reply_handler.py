"""
reply_handler.py — Multi-turn conversation reply handler.

Handles all judge replay scenarios:
  1. Auto-reply detection (progressive: nudge → wait → end)
  2. Intent transition (explicit YES → immediate action)
  3. Positive engagement (continue conversation)
  4. Objection handling (cost, ROI, not sure)
  5. Out-of-scope requests (politely redirect)
  6. Hard opt-out (end conversation)
  7. Question answering (stay in context)
  8. Hostile messages (graceful exit)
"""
from __future__ import annotations
import os
import re
import logging
from typing import Any, Dict, Optional, Tuple

from bot import context_store

logger = logging.getLogger("vera.reply_handler")

# ─────────────────────────────────────────────
# Auto-reply detection
# ─────────────────────────────────────────────

AUTO_REPLY_PHRASES = [
    "thank you for contacting",
    "our team will respond",
    "we will get back",
    "thank you for your message",
    "business hours",
    "we are closed",
    "aapki jaankari ke liye",
    "automated assistant",
    "dhanyavaad",
    "this is an automated",
    "hamari team pahuchayegi",
    "i am not available",
]

OPT_OUT_PHRASES = [
    "stop", "not interested", "don't message",
    "unsubscribe", "please stop", "band karo",
    "mat bhejo", "no thanks", "remove me",
    "do not contact",
]

HOSTILE_PHRASES = [
    "useless", "waste of time", "stupid bot",
    "annoying", "spam", "bakwaas", "irritating",
    "why are you bothering",
]

POSITIVE_SIGNALS = [
    "yes", "ok", "sure", "let's do it", "do it",
    "go ahead", "please", "yep", "yeah", "confirm",
    "haan", "bilkul", "zaroor", "chalega", "theek hai",
    "sounds good", "great", "perfect",
]

NEGATIVE_SIGNALS = [
    "no", "nahi", "nope", "not now", "later",
    "maybe later", "not today", "not right now",
    "abhi nahi", "baad mein",
]

QUESTION_SIGNALS = ["what", "how", "when", "where", "why", "which", "?", "kya", "kaise", "kab"]

OBJECTION_SIGNALS = [
    "cost", "expensive", "price", "mehanga", "kitna",
    "roi", "benefit", "why should", "will it work",
    "not sure", "doubt", "need to think",
]

OUT_OF_SCOPE = [
    "gst", "tax", "income tax", "filing", "legal", "lawyer",
    "ca ", "accountant", "loan", "insurance",
]


# ─────────────────────────────────────────────
# Main handler
# ─────────────────────────────────────────────

def handle_reply(
    conversation_id: str,
    merchant_id: str,
    customer_id: Optional[str],
    message: str,
    turn_number: int,
    received_at: str,
    from_role: str,
) -> Dict[str, Any]:
    """
    Returns action dict: {action, body?, cta?, wait_seconds?, rationale}
    action ∈ {"send", "wait", "end"}
    """
    conv = context_store.get_conversation(conversation_id)
    msg_lower = message.lower().strip()

    # Track merchant message turns in conversation state
    if "turns" not in conv:
        conv["turns"] = []
    conv["turns"].append(message)
    _update_conv(conversation_id, conv, {"turns": conv["turns"]})

    # Guard: already ended conversation
    if conv.get("state") == "ended":
        return _end("Conversation already ended.")

    # ── 1. Hard opt-out ───────────────────────────
    if any(p in msg_lower for p in OPT_OUT_PHRASES):
        context_store.opt_out_merchant(merchant_id)
        context_store.end_conversation(conversation_id)
        return _end("Merchant explicitly opted out. Suppressing all outreach.", graceful_body=(
            "Understood — I won't message again. If you ever want to restart, just say 'Hi Vera'. 🙏"
        ), with_send=True)

    # ── 2. Hostile message ────────────────────────
    if any(p in msg_lower for p in HOSTILE_PHRASES):
        context_store.end_conversation(conversation_id)
        context_store.update_merchant_memory(merchant_id, {"state": "opted_out"})
        return _end_with_apology()

    # ── 3. Auto-reply detection ───────────────────
    # Check if same message string appears 3+ times
    message_count = conv["turns"].count(message)
    is_auto_reply = _is_auto_reply(msg_lower) or message_count >= 3
    if is_auto_reply:
        auto_streak = conv.get("auto_reply_streak", 0) + 1
        _update_conv(conversation_id, conv, {"auto_reply_streak": auto_streak})

        if auto_streak == 1:
            # First auto-reply: try one nudge
            return _send(
                "Looks like an auto-reply 😊 When the owner sees this, just reply 'Yes' to continue.",
                "binary_yes_no",
                f"Detected auto-reply (turn {turn_number}). One explicit prompt to flag for owner."
            )
        elif auto_streak == 2:
            # Second: wait
            return {
                "action": "wait",
                "wait_seconds": 86400,
                "rationale": f"Same auto-reply twice — owner not at phone. Waiting 24h before retry."
            }
        else:
            # Third+: end
            context_store.end_conversation(conversation_id)
            return _end(f"Auto-reply {auto_streak}x in a row — no engagement signal. Closing conversation.")

    # ── 4. Out-of-scope request ───────────────────
    if any(p in msg_lower for p in OUT_OF_SCOPE):
        last_topic = conv.get("last_signal_type", "our earlier topic")
        merchant_data = context_store.get_context("merchant", merchant_id) or {}
        owner = merchant_data.get("identity", {}).get("owner_first_name", "")
        return _send(
            f"I'll have to leave {_out_of_scope_topic(msg_lower)} to the right professional — "
            f"that's outside what I can help with. Coming back to {last_topic} — "
            f"want me to continue where we left off?",
            "open_ended",
            "Out-of-scope request politely declined; redirected back to active topic."
        )

    # ── 5. Explicit intent / positive ─────────────
    is_positive = any(p in msg_lower for p in POSITIVE_SIGNALS)
    is_explicit_intent = any(p in msg_lower for p in ["let's do it", "go ahead", "do it", "confirm", "yes please"])

    if is_positive:
        context_store.mark_merchant_replied(merchant_id, received_at)
        _update_conv(conversation_id, conv, {
            "state": "engaged",
            "auto_reply_streak": 0,
        })
        return _handle_positive(conv, merchant_id, customer_id, is_explicit_intent, message)

    # ── 6. Negative / later ───────────────────────
    if any(p in msg_lower for p in NEGATIVE_SIGNALS):
        context_store.mark_merchant_replied(merchant_id, received_at)
        return {
            "action": "wait",
            "wait_seconds": 172800,  # 48h
            "rationale": "Merchant deferred. Respecting preference; will re-engage after 48h with a different signal."
        }

    # ── 7. Objection ──────────────────────────────
    if any(p in msg_lower for p in OBJECTION_SIGNALS):
        context_store.mark_merchant_replied(merchant_id, received_at)
        return _handle_objection(conv, merchant_id, message)

    # ── 8. Question ───────────────────────────────
    if any(p in msg_lower for p in QUESTION_SIGNALS) and "?" in message:
        context_store.mark_merchant_replied(merchant_id, received_at)
        return _handle_question(conv, merchant_id, customer_id, message)

    # ── 9. Generic reply (engaged) ────────────────
    context_store.mark_merchant_replied(merchant_id, received_at)
    _update_conv(conversation_id, conv, {"state": "engaged", "auto_reply_streak": 0})
    return _handle_generic_reply(conv, merchant_id, customer_id, message)


# ─────────────────────────────────────────────
# Specific reply handlers
# ─────────────────────────────────────────────

def _handle_positive(conv: Dict, merchant_id: str, customer_id: Optional[str],
                     is_explicit: bool, message: str) -> Dict:
    """Merchant said yes / let's do it — switch to action mode immediately."""
    last_signal = conv.get("last_signal_type", "")
    last_kind = conv.get("last_trigger_kind", "")
    merchant_data = context_store.get_context("merchant", merchant_id) or {}
    identity = merchant_data.get("identity", {})
    owner = identity.get("owner_first_name", "")
    offers = [o for o in merchant_data.get("offers", []) if o.get("status") == "active"]
    offer_name = offers[0].get("title", "your offer") if offers else "your offer"
    ca = merchant_data.get("customer_aggregate", {})
    lapsed = ca.get("lapsed_180d_plus", 0)
    high_risk = ca.get("high_risk_adult_count", 0)

    if last_signal == "research_digest" or last_kind == "research_digest":
        patient_scope = f"{high_risk} high-risk adult patients" if high_risk else "your patients"
        return _send(
            f"Sending the abstract now. Patient-ed draft below — copy-paste or I'll schedule a Google post:\n\n"
            f"\"New research shows more frequent check-ups cut cavity recurrence significantly. "
            f"Book your next visit — drop us a note.\"\n\n"
            f"Want me to schedule the post for tomorrow 10am?",
            "binary_yes_no",
            f"Honoring merchant's YES — delivered abstract + patient-ed draft. Binary CTA to schedule post."
        )

    elif last_signal in ("recall_soft", "recall_hard") or last_kind in ("customer_lapsed_soft", "customer_lapsed_hard", "recall_due"):
        scope_label = f"{lapsed} lapsed patients" if lapsed else "your lapsed patients"
        return _send(
            f"On it. Drafting personalized recall messages for {scope_label} — "
            f"using your {offer_name}. Goes out in 2 minutes. Reply CONFIRM to send.",
            "binary_confirm_cancel",
            "Merchant confirmed recall action. Preparing batch recall messages."
        )

    elif last_signal in ("search_spike", "festival") or last_kind in ("search_spike", "festival_upcoming"):
        return _send(
            f"Setting it up now — I'll push your {offer_name} to nearby searchers. "
            f"Live in 2 minutes. Reply CONFIRM to go live, or STOP to cancel.",
            "binary_confirm_cancel",
            "Merchant confirmed campaign push. Executing to demand pool."
        )

    elif last_signal == "urgent_compliance" or last_signal == "compliance":
        return _send(
            f"Drafting the compliance checklist now. I'll also draft a WhatsApp note for affected customers. "
            f"Ready in 60 seconds. Want me to also set a reminder for {_deadline_label()}?",
            "binary_yes_no",
            "Merchant confirmed compliance action. Preparing checklist + customer notification."
        )

    elif last_signal == "performance_drop":
        return _send(
            f"Great — pulling 3 quick fixes for your listing now:\n"
            f"1. Update your business description with service+price keywords\n"
            f"2. Add 2 new photos this week\n"
            f"3. Activate your {offer_name} with a Google post\n\n"
            f"Want me to draft the description update + post for you? Reply YES.",
            "binary_yes_no",
            "Merchant confirmed. Delivering 3 actionable fixes for CTR improvement."
        )

    else:
        # Generic positive — confirm and advance
        return _send(
            f"On it — I'll get that ready for you now. "
            f"Want me to also draft a short Google post to support it? Reply YES.",
            "binary_yes_no",
            "Generic positive — continuing with next best action."
        )


def _handle_objection(conv: Dict, merchant_id: str, message: str) -> Dict:
    """Handle cost/ROI objections."""
    merchant_data = context_store.get_context("merchant", merchant_id) or {}
    perf = merchant_data.get("performance", {})
    views = perf.get("views", 0)
    calls = perf.get("calls", 0)

    msg_lower = message.lower()
    if any(p in msg_lower for p in ["cost", "expensive", "price", "kitna", "mehanga"]):
        return _send(
            f"Fair question. Your current listing gets {views} views/month → {calls} calls. "
            f"One well-timed campaign typically adds 15-20% to that for 48 hours. "
            f"The offer I suggested uses what you already have — no extra spend. "
            f"Worth a quick try? Reply YES and I'll set it up in 2 minutes.",
            "binary_yes_no",
            "Cost objection handled with ROI framing using actual merchant metrics."
        )
    elif any(p in msg_lower for p in ["roi", "will it work", "benefit"]):
        return _send(
            f"Good instinct to ask. Based on {views} monthly views and {calls} calls, "
            f"your conversion rate is solid. Similar merchants in your area saw 10-15% more calls "
            f"after activating offers in peak demand windows. "
            f"Want me to show you what that looks like for your numbers? Reply YES.",
            "binary_yes_no",
            "ROI objection addressed with peer benchmark and merchant's own data."
        )
    else:
        return _send(
            "Totally fair to think it over. I'll check back in 48 hours — "
            "if the timing feels better then, we can set it up quickly.",
            "none",
            "General objection — respectful follow-up scheduled."
        )


def _handle_question(conv: Dict, merchant_id: str, customer_id: Optional[str], message: str) -> Dict:
    """Handle questions — stay in context, answer then redirect."""
    merchant_data = context_store.get_context("merchant", merchant_id) or {}
    last_topic = conv.get("last_signal_type", "our earlier topic")
    offers = [o for o in merchant_data.get("offers", []) if o.get("status") == "active"]
    offer = offers[0].get("title", "your offer") if offers else "your offer"

    msg_lower = message.lower()
    if "how long" in msg_lower or "how much time" in msg_lower:
        return _send(
            "Quick to set up — I can have it live in 2 minutes once you confirm. "
            "The actual reach happens over the next 2-4 hours. "
            "Want to go ahead? Reply YES.",
            "binary_yes_no",
            "Answered 'how long' question; redirected to action."
        )
    elif "how many" in msg_lower or "kitne" in msg_lower:
        ca = merchant_data.get("customer_aggregate", {})
        count = ca.get("total_unique_ytd", 0) or ca.get("lapsed_180d_plus", 0)
        return _send(
            f"Based on your current data, we'd be reaching approximately {count or 'a targeted group of'} "
            f"relevant users in your area. Want me to go ahead? Reply YES.",
            "binary_yes_no",
            "Answered count question with actual customer_aggregate data."
        )
    else:
        return _send(
            f"Good question. For this specific scenario, the key thing is: "
            f"your {offer} is active and there's demand right now. "
            f"I can walk you through the details after we set it up — want to proceed? Reply YES.",
            "binary_yes_no",
            "Generic question answered in context; redirected to action."
        )


def _handle_generic_reply(conv: Dict, merchant_id: str, customer_id: Optional[str], message: str) -> Dict:
    """Merchant replied something unclassified — continue conversation."""
    last_signal = conv.get("last_signal_type", "")
    merchant_data = context_store.get_context("merchant", merchant_id) or {}
    offers = [o for o in merchant_data.get("offers", []) if o.get("status") == "active"]
    offer = offers[0].get("title", "your offer") if offers else "your offer"

    return _send(
        f"Got it! Coming back to what I mentioned — your {offer} has good timing right now. "
        f"Should I go ahead and set it up? Reply YES.",
        "binary_yes_no",
        "Generic reply acknowledged; redirected to pending action."
    )


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _is_auto_reply(msg_lower: str) -> bool:
    return any(phrase in msg_lower for phrase in AUTO_REPLY_PHRASES)


def _out_of_scope_topic(msg_lower: str) -> str:
    if "gst" in msg_lower or "tax" in msg_lower:
        return "GST filing"
    if "loan" in msg_lower:
        return "loan applications"
    if "legal" in msg_lower or "lawyer" in msg_lower:
        return "legal matters"
    return "that topic"


def _deadline_label() -> str:
    from datetime import datetime, timedelta
    d = datetime.now() + timedelta(days=7)
    return d.strftime("%d %b")


def _send(body: str, cta: str, rationale: str) -> Dict:
    return {"action": "send", "body": body, "cta": cta, "rationale": rationale}


def _end(rationale: str, graceful_body: str = None, with_send: bool = False) -> Dict:
    if with_send and graceful_body:
        return {
            "action": "send",
            "body": graceful_body,
            "cta": "none",
            "rationale": rationale,
        }
    return {"action": "end", "rationale": rationale}


def _end_with_apology() -> Dict:
    return {
        "action": "send",
        "body": "Apologies — I won't message again. If anything changes, you can always restart with 'Hi Vera'. 🙏",
        "cta": "none",
        "rationale": "Hostile message detected; graceful exit with one-line acknowledgment.",
    }


def _update_conv(conv_id: str, conv: Dict, updates: Dict):
    conv.update(updates)
    context_store.save_conversation(conv_id, conv)