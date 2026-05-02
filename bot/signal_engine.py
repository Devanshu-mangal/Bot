"""
signal_engine.py — Signal collection, scoring, and selection.

Architecture:
  collect_signals() → List[Signal]        (all observable signals)
  score_signal()    → float               (mathematical scoring formula)
  rank_signals()    → List[(score, Signal)]  (sorted, best first)
  pick_winner()     → Optional[Signal]    (best non-suppressed signal)
"""
from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────
# Signal dataclass
# ─────────────────────────────────────────────

@dataclass
class Signal:
    type: str               # canonical signal type name
    tier: int               # 1=immediate-opportunity, 2=recovery, 3=relationship, 4=weak
    base_score: float       # 0–100
    data: Dict[str, Any]    # extracted payload facts
    source: str             # "trigger" | "merchant" | "category"
    trigger_kind: str = ""  # original trigger.kind
    occurred_at: Optional[str] = None

    @property
    def suppression_key(self) -> str:
        """Deterministic suppression key from signal identity."""
        merchant_id = self.data.get("merchant_id", "unknown")
        offer_id = self.data.get("offer_id", "")
        locality = self.data.get("locality", "")
        search_term = self.data.get("search_term", "")
        raw = f"{self.type}:{merchant_id}:{offer_id}:{locality}:{search_term}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]


# ─────────────────────────────────────────────
# Trigger kind → signal type mapping (complete)
# ─────────────────────────────────────────────

TRIGGER_KIND_MAP: Dict[str, Tuple[str, int, float]] = {
    # (signal_type, tier, base_score)
    # Tier 1 — Immediate opportunities
    "search_spike":              ("search_spike",         1, 95.0),
    "perf_spike":                ("performance_spike",    1, 88.0),
    "festival_upcoming":         ("festival",             1, 87.0),
    "ipl_match_today":           ("temporal_event",       1, 90.0),
    "supply_alert":              ("urgent_compliance",    1, 100.0),
    "regulation_change":         ("compliance",           1, 92.0),
    "competitor_opened":         ("competitive",          1, 85.0),
    "active_planning_intent":    ("intent",               1, 95.0),
    # Tier 2 — Recovery
    "perf_dip":                  ("performance_drop",     2, 82.0),
    "customer_lapsed_hard":      ("recall_hard",          2, 85.0),
    "customer_lapsed_soft":      ("recall_soft",          2, 78.0),
    "recall_due":                ("recall_soft",          2, 80.0),
    "chronic_refill_due":        ("refill_due",           2, 88.0),
    "review_theme_emerged":      ("reputation",           2, 75.0),
    "seasonal_perf_dip":         ("seasonal_dip",         2, 70.0),
    # Tier 3 — Relationship / lifecycle
    "research_digest":           ("research_digest",      3, 72.0),
    "milestone_reached":         ("milestone",            3, 68.0),
    "bridal_followup":           ("customer_followup",    3, 75.0),
    "dormant_with_vera":         ("re_engage",            3, 60.0),
    "curious_ask_due":           ("curiosity",            3, 55.0),
    # Tier 4 — Weak / generic
    "offer_available":           ("offer_push",           4, 50.0),
    "scheduled_recurring":       ("generic_nudge",        4, 35.0),
    "appointment_tomorrow":      ("appointment_reminder", 3, 65.0),
}

# Category preference multipliers — which signal types a category values most
CATEGORY_SIGNAL_PREFERENCE: Dict[str, Dict[str, float]] = {
    "dentists": {
        "research_digest": 1.4, "compliance": 1.4, "recall_soft": 1.3,
        "recall_hard": 1.3, "search_spike": 1.2, "appointment_reminder": 1.2,
    },
    "salons": {
        "festival": 1.4, "search_spike": 1.3, "customer_followup": 1.3,
        "seasonal_dip": 1.2, "offer_push": 1.1,
    },
    "restaurants": {
        "temporal_event": 1.5, "festival": 1.3, "performance_drop": 1.3,
        "search_spike": 1.2, "competitive": 1.2,
    },
    "gyms": {
        "milestone": 1.3, "recall_hard": 1.3, "seasonal_dip": 1.2,
        "search_spike": 1.2, "research_digest": 1.1,
    },
    "pharmacies": {
        "urgent_compliance": 1.5, "refill_due": 1.5, "recall_hard": 1.4,
        "compliance": 1.4, "search_spike": 1.1,
    },
}


# ─────────────────────────────────────────────
# Signal collection
# ─────────────────────────────────────────────

def collect_signals(
    category: Dict, merchant: Dict, trigger: Dict, customer: Optional[Dict] = None
) -> List[Signal]:
    signals: List[Signal] = []
    merchant_id = merchant.get("merchant_id", "")

    # 1. Primary: from trigger
    trigger_kind = trigger.get("kind", "")
    mapping = TRIGGER_KIND_MAP.get(trigger_kind)
    if mapping:
        sig_type, tier, base = mapping
        occurred_at = trigger.get("occurred_at") or trigger.get("delivered_at")
        data = _extract_trigger_data(trigger, merchant, category, customer)
        data["merchant_id"] = merchant_id
        signals.append(Signal(
            type=sig_type, tier=tier, base_score=base,
            data=data, source="trigger",
            trigger_kind=trigger_kind, occurred_at=occurred_at
        ))
    else:
        # Unknown trigger kind → fallback engagement signal
        signals.append(Signal(
            type="generic_nudge", tier=4, base_score=30.0,
            data={"merchant_id": merchant_id, "trigger_kind": trigger_kind},
            source="trigger", trigger_kind=trigger_kind
        ))

    # 2. Supplementary: from merchant state
    signals.extend(_signals_from_merchant(merchant))

    # 3. Supplementary: from category digest/trends
    signals.extend(_signals_from_category(category, merchant))

    return signals


def _extract_trigger_data(trigger: Dict, merchant: Dict, category: Dict, customer: Optional[Dict]) -> Dict:
    """Extract all concrete facts from trigger payload."""
    payload = trigger.get("payload", {})
    kind = trigger.get("kind", "")
    identity = merchant.get("identity", {})
    perf = merchant.get("performance", {})

    data: Dict[str, Any] = {
        # Trigger facts
        "trigger_id": trigger.get("id", ""),
        "trigger_kind": kind,
        "trigger_urgency": trigger.get("urgency", 2),
        "trigger_scope": trigger.get("scope", "merchant"),
        "trigger_suppression_key": trigger.get("suppression_key", ""),
        "trigger_expires_at": trigger.get("expires_at", ""),

        # Merchant identity
        "merchant_id": merchant.get("merchant_id", ""),
        "merchant_name": identity.get("name", ""),
        "owner_first_name": identity.get("owner_first_name", identity.get("name", "").split()[0] if identity.get("name") else ""),
        "locality": identity.get("locality", ""),
        "city": identity.get("city", ""),
        "languages": identity.get("languages", ["en"]),
        "category_slug": merchant.get("category_slug", ""),

        # Performance
        "views": perf.get("views", 0),
        "calls": perf.get("calls", 0),
        "directions": perf.get("directions", 0),
        "ctr": perf.get("ctr", 0),
        "views_delta_7d": perf.get("delta_7d", {}).get("views_pct", 0),
        "calls_delta_7d": perf.get("delta_7d", {}).get("calls_pct", 0),
    }

    # Peer stats
    peer = category.get("peer_stats", {})
    data["peer_avg_ctr"] = peer.get("avg_ctr", 0.03)
    data["peer_avg_rating"] = peer.get("avg_rating", 4.3)
    data["peer_avg_views"] = peer.get("avg_views_30d", 2000)

    # Customer aggregate
    ca = merchant.get("customer_aggregate", {})
    data["customer_total"] = ca.get("total_unique_ytd", 0)
    data["lapsed_count"] = ca.get("lapsed_180d_plus", 0)
    data["high_risk_count"] = ca.get("high_risk_adult_count", 0)
    data["retention_pct"] = ca.get("retention_6mo_pct", 0)
    data["active_members"] = ca.get("active_members", 0)
    data["chronic_rx_count"] = ca.get("chronic_rx_customers", 0)

    # Derived signals list
    data["merchant_signals"] = merchant.get("signals", [])

    # Active offers
    offers = merchant.get("offers", [])
    active = [o for o in offers if o.get("status") == "active"]
    if active:
        o = active[0]
        data["offer_id"] = o.get("id", "")
        data["offer_title"] = o.get("title", "")
        data["offer_price"] = _extract_price(o.get("title", ""))
        data["has_active_offer"] = True
    else:
        data["has_active_offer"] = False

    # Subscription
    sub = merchant.get("subscription", {})
    data["subscription_plan"] = sub.get("plan", "")
    data["subscription_days"] = sub.get("days_remaining", 0)

    # Kind-specific payload extraction
    if kind == "search_spike":
        data["demand_count"] = payload.get("search_count") or payload.get("local_searches") or payload.get("demand_count") or 0
        data["search_term"] = payload.get("query") or payload.get("search_term") or data["category_slug"]
        data["locality"] = payload.get("locality") or payload.get("area") or data["locality"]

    elif kind == "research_digest":
        top_item_id = payload.get("top_item_id")
        digest_items = category.get("digest", [])
        if top_item_id:
            matched = next((d for d in digest_items if d.get("id") == top_item_id), None)
            if matched:
                data["digest_item"] = matched
                data["digest_title"] = matched.get("title", "")
                data["digest_source"] = matched.get("source", "")
                data["digest_trial_n"] = matched.get("trial_n", 0)
                data["digest_patient_segment"] = matched.get("patient_segment", "")
                data["digest_summary"] = matched.get("summary", "")
                data["digest_actionable"] = matched.get("actionable", "")
        # Even if no top_item_id, try first digest
        if not data.get("digest_item") and digest_items:
            d = digest_items[0]
            data["digest_item"] = d
            data["digest_title"] = d.get("title", "")
            data["digest_source"] = d.get("source", "")
            data["digest_trial_n"] = d.get("trial_n", 0)
            data["digest_patient_segment"] = d.get("patient_segment", "")
            data["digest_summary"] = d.get("summary", "")

    elif kind in ("perf_dip", "seasonal_perf_dip"):
        data["dip_pct"] = abs(payload.get("dip_pct") or payload.get("views_delta_pct") or
                              (data["views_delta_7d"] * 100 if data["views_delta_7d"] < 0 else 12))
        data["metric_name"] = payload.get("metric", "views")

    elif kind == "perf_spike":
        data["spike_pct"] = payload.get("spike_pct") or payload.get("views_delta_pct") or 28

    elif kind in ("festival_upcoming", "festival"):
        data["festival_name"] = payload.get("festival_name") or payload.get("name") or "the upcoming festival"
        data["days_until"] = payload.get("days_away") or payload.get("days_until") or 4

    elif kind == "ipl_match_today":
        data["match_teams"] = payload.get("teams") or payload.get("match_teams") or "today's match"
        data["match_time"] = payload.get("start_time") or payload.get("match_time") or "7:30pm"
        data["match_venue"] = payload.get("venue") or ""
        data["is_weekend"] = payload.get("is_weekend", False)

    elif kind in ("customer_lapsed_soft", "customer_lapsed_hard", "recall_due", "bridal_followup", "chronic_refill_due"):
        if customer:
            cid = customer.get("identity", {})
            data["customer_name"] = cid.get("name", "")
            data["customer_language"] = cid.get("language_pref", "en")
            data["customer_id"] = customer.get("customer_id", "")
            rel = customer.get("relationship", {})
            data["last_visit"] = rel.get("last_visit", "")
            data["visits_total"] = rel.get("visits_total", 0)
            data["services_received"] = rel.get("services_received", [])
            prefs = customer.get("preferences", {})
            data["preferred_slot"] = prefs.get("preferred_slots", "")
            data["customer_state"] = customer.get("state", "lapsed_soft")
            data["customer_goal"] = payload.get("goal") or payload.get("focus") or ""

    elif kind == "milestone_reached":
        data["milestone_value"] = payload.get("value") or payload.get("count") or 100
        data["milestone_metric"] = payload.get("metric") or "reviews"

    elif kind == "supply_alert":
        data["recall_batches"] = payload.get("batch_numbers") or payload.get("batches") or []
        data["recall_molecule"] = payload.get("molecule") or payload.get("drug") or ""
        data["recall_risk"] = payload.get("risk_level") or "sub-potency"
        data["affected_count"] = payload.get("affected_customers") or data.get("chronic_rx_count", 0)

    elif kind == "regulation_change":
        data["regulation_title"] = payload.get("title") or payload.get("rule") or ""
        data["regulation_source"] = payload.get("source") or ""
        data["effective_date"] = payload.get("effective_date") or ""

    elif kind == "review_theme_emerged":
        data["review_theme"] = payload.get("theme") or payload.get("topic") or "service"
        data["review_count"] = payload.get("count") or 3

    elif kind == "competitor_opened":
        data["competitor_distance_km"] = payload.get("distance_km") or 1.5
        data["competitor_name"] = payload.get("name") or "a new competitor"

    elif kind == "chronic_refill_due":
        if customer:
            cid = customer.get("identity", {})
            data["customer_name"] = cid.get("name", "")
            data["customer_language"] = cid.get("language_pref", "en")
            rel = customer.get("relationship", {})
            data["medications"] = rel.get("services_received", [])
            data["refill_date"] = payload.get("refill_due_date") or payload.get("due_date") or ""

    return data


def _signals_from_merchant(merchant: Dict) -> List[Signal]:
    """Secondary signals derived from merchant state."""
    signals = []
    merchant_id = merchant.get("merchant_id", "")
    perf = merchant.get("performance", {})
    offers = [o for o in merchant.get("offers", []) if o.get("status") == "active"]
    mq_signals = merchant.get("signals", [])
    ca = merchant.get("customer_aggregate", {})

    # Stale posts signal
    for s in mq_signals:
        if "stale_posts" in s:
            signals.append(Signal(
                type="stale_content", tier=3, base_score=45.0,
                data={"merchant_id": merchant_id, "signal_flag": s},
                source="merchant"
            ))
            break

    # High lapsed customer count
    lapsed = ca.get("lapsed_180d_plus", 0)
    if lapsed > 20:
        signals.append(Signal(
            type="lapse_pool_large", tier=2, base_score=60.0,
            data={"merchant_id": merchant_id, "lapsed_count": lapsed},
            source="merchant"
        ))

    return signals


def _signals_from_category(category: Dict, merchant: Dict) -> List[Signal]:
    """Tertiary: category digest and seasonal context."""
    signals = []
    merchant_id = merchant.get("merchant_id", "")

    # Seasonal beat match (check current month)
    current_month = datetime.now(timezone.utc).strftime("%b")
    for beat in category.get("seasonal_beats", []):
        month_range = beat.get("month_range", "")
        if _month_in_range(current_month, month_range):
            signals.append(Signal(
                type="seasonal_moment", tier=3, base_score=55.0,
                data={"merchant_id": merchant_id, "seasonal_note": beat.get("note", ""), "month_range": month_range},
                source="category"
            ))
            break

    return signals


# ─────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────

def score_signal(signal: Signal, category_slug: str, merchant: Dict) -> float:
    """
    signal_score = base_score
                 × recency_multiplier      (0.5–1.0)
                 × magnitude_multiplier    (0.8–1.5)
                 × category_preference     (0.8–1.5)
                 × offer_availability      (0.7 if no offer for offer-dependent signals, 1.0 otherwise)
                 × merchant_state_fit      (0.6–1.0)
    """
    score = signal.base_score

    # Recency
    score *= _recency_multiplier(signal)

    # Magnitude (tier-specific)
    score *= _magnitude_multiplier(signal, merchant)

    # Category preference
    cat_prefs = CATEGORY_SIGNAL_PREFERENCE.get(category_slug, {})
    cat_mult = cat_prefs.get(signal.type, 1.0)
    score *= cat_mult

    # Offer availability for offer-dependent signals
    offer_dependent = {"offer_push", "search_spike", "festival", "temporal_event"}
    if signal.type in offer_dependent and not signal.data.get("has_active_offer"):
        score *= 0.75

    # Merchant state fit
    mem_state = signal.data.get("_merchant_state", "new")
    if mem_state == "cold":
        # Penalize push signals for cold merchants
        if signal.tier == 1 and signal.type not in ("research_digest", "compliance", "urgent_compliance"):
            score *= 0.6
    elif mem_state == "engaged":
        score *= 1.1

    # Urgency from trigger
    urgency = signal.data.get("trigger_urgency", 2)
    if urgency >= 4:
        score *= 1.15
    elif urgency <= 1:
        score *= 0.9

    return round(score, 2)


def _recency_multiplier(signal: Signal) -> float:
    if not signal.occurred_at:
        return 0.85
    try:
        ts_str = signal.occurred_at.replace("Z", "+00:00")
        ts = datetime.fromisoformat(ts_str)
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        if age_hours <= 1:
            return 1.0
        elif age_hours <= 6:
            return 0.95
        elif age_hours <= 24:
            return 0.85
        elif age_hours <= 72:
            return 0.70
        else:
            return 0.55
    except Exception:
        return 0.85


def _magnitude_multiplier(signal: Signal, merchant: Dict) -> float:
    data = signal.data
    perf = merchant.get("performance", {})
    peer_ctr = data.get("peer_avg_ctr", 0.03)
    current_ctr = data.get("ctr", perf.get("ctr", 0.03))

    if signal.type == "search_spike":
        count = data.get("demand_count", 0)
        if count >= 200:
            return 1.5
        elif count >= 100:
            return 1.3
        elif count >= 50:
            return 1.1
        return 0.9

    elif signal.type == "performance_drop":
        dip = abs(data.get("dip_pct", 0))
        if dip >= 30:
            return 1.4
        elif dip >= 15:
            return 1.2
        return 0.9

    elif signal.type == "performance_spike":
        spike = data.get("spike_pct", 0)
        if spike >= 30:
            return 1.4
        elif spike >= 15:
            return 1.2
        return 1.0

    elif signal.type in ("recall_hard", "recall_soft"):
        lapsed = data.get("lapsed_count", 0)
        total = data.get("customer_total", 1)
        if total > 0 and lapsed / total > 0.3:
            return 1.3
        return 1.0

    elif signal.type == "festival":
        days = data.get("days_until", 7)
        if days <= 2:
            return 1.5
        elif days <= 4:
            return 1.3
        return 1.0

    elif signal.type == "urgent_compliance":
        return 1.5  # Always max urgency

    return 1.0


# ─────────────────────────────────────────────
# Ranking & selection
# ─────────────────────────────────────────────

def rank_signals(signals: List[Signal], category_slug: str, merchant: Dict,
                 merchant_state: str = "new") -> List[Tuple[float, Signal]]:
    """Score and sort all signals. Inject merchant_state into signal data for scoring."""
    ranked = []
    for sig in signals:
        sig.data["_merchant_state"] = merchant_state
        score = score_signal(sig, category_slug, merchant)
        ranked.append((score, sig))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked


def pick_winner(ranked: List[Tuple[float, Signal]], recent_signal_types: List[str]) -> Optional[Signal]:
    """
    Select the best signal, applying anti-repetition logic.
    Never pick the same signal type that was used in the last 2 sends.
    """
    avoid_types = set(recent_signal_types[-2:]) if recent_signal_types else set()

    for score, sig in ranked:
        # Skip if same type was recently used (anti-repetition) — UNLESS tier 1 and score > 80
        if sig.type in avoid_types and not (sig.tier == 1 and score > 80):
            continue
        return sig

    # Fallback: just return highest-scored regardless of repetition
    return ranked[0][1] if ranked else None


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _extract_price(title: str) -> str:
    import re
    m = re.search(r'[₹Rs\.]+\s*([0-9,]+)', title)
    if m:
        return m.group(1).replace(",", "")
    return "0"


def _month_in_range(month_abbr: str, month_range: str) -> bool:
    """Check if abbreviated month (e.g. 'Apr') falls within range like 'Apr-Jun' or 'Jan'."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    if "-" in month_range:
        parts = month_range.split("-")
        if len(parts) == 2:
            try:
                start = months.index(parts[0].strip())
                end = months.index(parts[1].strip())
                current = months.index(month_abbr)
                if start <= end:
                    return start <= current <= end
                else:
                    return current >= start or current <= end
            except ValueError:
                return False
    else:
        return month_abbr in month_range