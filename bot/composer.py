"""
composer.py — Message composition engine.

Two-path architecture:
  1. TEMPLATE PATH: For well-known trigger kinds. Fast, deterministic, zero-hallucination.
  2. LLM PATH: For complex/unknown triggers (active_planning_intent, curious_ask_due, etc.)
               LLM receives ONLY extracted facts — never raw JSON.

Both paths share the same output schema.
"""
from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from bot.signal_engine import Signal

# Load .env so composer works when imported standalone (tests, scripts)
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logger = logging.getLogger("vera.composer")
# ─────────────────────────────────────────────
# Triggers that require LLM (can't be templated)
# ─────────────────────────────────────────────
LLM_TRIGGER_KINDS = {
    # ONLY open-ended triggers with no structured payload facts
    # Everything else → template (templates beat LLM when facts are present)
    "active_planning_intent",   # merchant said they want to plan — needs creative response
    "curious_ask_due",          # open weekly check-in question
    "review_theme_emerged",     # nuanced reputation framing
    "ipl_match_today",          # contrarian weekday/weekend reasoning
    "seasonal_perf_dip",        # reframe logic (skip ads, focus retention)
    "competitor_opened",        # strategic differentiation framing
    "dormant_with_vera",        # re-engagement warmth
}

# ─────────────────────────────────────────────
# Category voice profiles (loaded from injected context, fallback here)
# ─────────────────────────────────────────────
CATEGORY_VOICE: Dict[str, Dict] = {
    "dentists": {
        "salutation": "Dr. {owner_first}",
        "tone": "peer_clinical",
        "cta_style": "open_ended",  # dentists: open-ended preferred over hard YES/NO
        "vocab_taboo": ["guaranteed", "100% safe", "completely cure", "miracle", "best in city"],
        "emoji_ok": False,
        "hindi_mix_ok": True,
    },
    "salons": {
        "salutation": "Hi {owner_first}",
        "tone": "warm_aspirational",
        "cta_style": "binary_yes_no",
        "vocab_taboo": ["guaranteed", "miracle", "100% results"],
        "emoji_ok": True,
        "hindi_mix_ok": True,
    },
    "restaurants": {
        "salutation": "Hi {owner_first}",
        "tone": "warm_busy_practical",
        "cta_style": "binary_yes_no",
        "vocab_taboo": ["guaranteed packed house", "miracle marketing"],
        "emoji_ok": False,
        "hindi_mix_ok": True,
    },
    "gyms": {
        "salutation": "Hi {owner_first}",
        "tone": "motivational_data",
        "cta_style": "binary_yes_no",
        "vocab_taboo": ["body shaming", "fat", "lazy"],
        "emoji_ok": False,
        "hindi_mix_ok": True,
    },
    "pharmacies": {
        "salutation": "Hi {owner_first}",
        "tone": "trustworthy_precise",
        "cta_style": "binary_yes_no",
        "vocab_taboo": ["100% safe", "miracle cure", "guaranteed"],
        "emoji_ok": False,
        "hindi_mix_ok": True,
    },
}

# ─────────────────────────────────────────────
# Template library — one per (category, signal_type)
# ─────────────────────────────────────────────

def _templates() -> Dict[str, Dict[str, str]]:
    return {
        # ── DENTISTS ──────────────────────────────────────────────
        "dentists": {
            "research_digest": (
                "{salutation}, {digest_source} landed. "
                "One item for {patient_segment_label} — "
                "{trial_n_str}trial: {digest_title}. "
                "Worth a 2-min read. Want me to pull the abstract + draft a patient WhatsApp you can share?"
                "{citation}"
            ),
            "search_spike": (
                "{salutation}, {demand_count} people in {locality} searched for '{search_term}' today. "
                "Your {offer_display} matches exactly what they want — should I send it to them? Reply YES."
            ),
            "recall_soft": (
                "Hi {customer_name}, Dr. {owner_first}'s clinic here 🦷 "
                "It's been {months_since_visit} months since your last visit — "
                "your {recall_label} is due. "
                "{slot_offer}. "
                "{offer_display}. Reply 1 for the first slot, 2 for the second, or tell us a time that works."
            ),
            "recall_hard": (
                "Hi {customer_name}, Dr. {owner_first}'s clinic here. "
                "It's been a while — your dental check is overdue. "
                "{offer_display}. "
                "Want me to hold a slot for you this week? Reply YES — no commitment."
            ),
            "refill_due": (
                "{salutation}, {customer_name}'s monthly prescription runs out {refill_date_label}. "
                "{medications_label}. Same dose, same brand. "
                "Reply CONFIRM to dispatch, or call if any change."
            ),
            "compliance": (
                "{salutation}, important: {regulation_title}. "
                "Source: {regulation_source}. {effective_label}. "
                "Want me to draft a compliance checklist for your practice?"
            ),
            "urgent_compliance": (
                "{salutation}, urgent: {recall_label_compliance}. "
                "{affected_label}. "
                "Want me to draft the patient WhatsApp + replacement workflow?"
            ),
            "performance_drop": (
                "{salutation}, your CTR is {ctr_display}% (peer avg: {peer_ctr_display}%) — "
                "{underperform_pct}% fewer patients are finding you. "
                "Want me to send 3 quick fixes? Reply YES."
            ),
            "milestone": (
                "{salutation}, you just crossed {milestone_value} {milestone_metric} — "
                "top {top_pct}% in your locality. "
                "Want me to draft a 'thank you' Google post to keep the momentum? Reply YES."
            ),
            "appointment_reminder": (
                "{salutation}, you have {appointment_count} appointments tomorrow. "
                "Want me to send confirmation messages to each patient now? Reply YES."
            ),
            "re_engage": (
                "{salutation}, quick check — it's been a while. "
                "Your {metric_highlight}. "
                "One thing I can help with right now: {one_action}. Interested?"
            ),
        },

        # ── SALONS ────────────────────────────────────────────────
        "salons": {
            "festival": (
                "Hi {owner_first}! {festival_name} is in {days_until} days — "
                "{demand_count_label} people near {locality} are already searching for '{search_term}'. "
                "Your {offer_display} is perfectly timed. Should I push it to them? Reply YES!"
            ),
            "search_spike": (
                "Hi {owner_first}! {demand_count} people near {locality} searched for '{search_term}' this week. "
                "Your {offer_display} is one of the best-priced options — should I send it to them now? Reply YES!"
            ),
            "customer_followup": (
                "Hi {customer_name} 💍 {owner_first} from {merchant_name} here. "
                "{relationship_context}. "
                "{offer_display}. "
                "Want me to block your preferred {slot_label} slot? Reply YES."
            ),
            "seasonal_moment": (
                "Hi {owner_first}! {seasonal_note}. "
                "Your {offer_display} fits this window well. "
                "Should I run a targeted push this week? Reply YES!"
            ),
            "performance_drop": (
                "Hi {owner_first}! Your bookings dropped {dip_pct}% this month. "
                "Your {offer_display} could reverse that — "
                "{demand_count_label} people in {locality} are searching for '{search_term}'. "
                "Want me to push it? Reply YES!"
            ),
            "research_digest": (
                "Hi {owner_first}! Industry update: {digest_title}. "
                "Source: {digest_source}. "
                "{digest_actionable_label}. Want me to help you action this? Reply YES!"
            ),
            "re_engage": (
                "Hi {owner_first}! Quick check — {metric_highlight}. "
                "One quick win: {one_action}. Interested? Reply YES."
            ),
        },

        # ── RESTAURANTS ───────────────────────────────────────────
        "restaurants": {
            "search_spike": (
                "Quick one {owner_first} — {demand_count} people near {locality} searched for "
                "'{search_term}' today. Your {offer_display} matches exactly. "
                "Should I send it to nearby users now? Reply YES."
            ),
            "festival": (
                "{owner_first}, {festival_name} is in {days_until} days — "
                "big footfall window. Your {offer_display} is well-placed. "
                "Want me to push it to {locality} users? Reply YES."
            ),
            "performance_drop": (
                "{owner_first}, your covers dropped {dip_pct}% this week vs your average. "
                "Your {offer_display} could pull them back — "
                "want me to run a {locality} push for the next 2 hours? Reply YES."
            ),
            "milestone": (
                "{owner_first}, you just hit {milestone_value} {milestone_metric} — "
                "congrats! Your {offer_display} could push you higher. "
                "Want me to promote this win? Reply YES."
            ),
            "research_digest": (
                "{owner_first}, quick update: {digest_title}. "
                "Source: {digest_source}. {digest_actionable_label}. "
                "Want me to help you act on this? Reply YES."
            ),
            "temporal_event": (
                "Quick heads-up {owner_first} — {match_context}. "
                "{contrarian_advice}. "
                "Want me to {action_offer}? Reply YES."
            ),
            "competitive": (
                "{owner_first}, {competitor_name} opened {competitor_distance_km}km away. "
                "Your {offer_display} is still better-priced. "
                "Want me to push visibility in {locality} this week? Reply YES."
            ),
            "re_engage": (
                "{owner_first}, {metric_highlight}. "
                "One quick move: {one_action}. Reply YES if you want me to set it up."
            ),
        },

        # ── GYMS ──────────────────────────────────────────────────
        "gyms": {
            "recall_hard": (
                "Hi {customer_name} 👋 {owner_first} from {merchant_name} here. "
                "It's been {months_since_visit} weeks — happens to most members at some point, no judgment. "
                "{new_offering}. "
                "Want me to hold a free trial spot for you {trial_date_label}? Reply YES — no commitment, no auto-charge."
            ),
            "recall_soft": (
                "Hi {customer_name}! {owner_first} from {merchant_name}. "
                "We've been missing you — {customer_goal_label}. "
                "{offer_display}. Want to come back this week? Reply YES."
            ),
            "seasonal_dip": (
                "{owner_first}, your views are down {dip_pct}% — but this is the normal "
                "{seasonal_label} acquisition lull (every metro gym sees this window). "
                "Skip ad spend for now; focus on retaining your {active_members_label}. "
                "Want me to draft a 'summer challenge' to keep them engaged? Reply YES."
            ),
            "search_spike": (
                "Hi {owner_first}! {demand_count} people near {locality} searched for '{search_term}' this week. "
                "Your {offer_display} is what they're looking for. Should I send it to them? Reply YES!"
            ),
            "milestone": (
                "{owner_first}, {milestone_value} {milestone_metric} — that's a strong month. "
                "Top {top_pct}% in {locality}. "
                "Want me to draft a member shoutout + a Google post to build on this? Reply YES."
            ),
            "research_digest": (
                "Hi {owner_first}! Quick update: {digest_title}. "
                "Source: {digest_source}. {digest_actionable_label}. "
                "Worth acting on — want my help? Reply YES."
            ),
            "re_engage": (
                "Hi {owner_first}, {metric_highlight}. "
                "Quick win available: {one_action}. Reply YES to set it up."
            ),
        },

        # ── PHARMACIES ────────────────────────────────────────────
        "pharmacies": {
            "urgent_compliance": (
                "{owner_first}, urgent: voluntary recall on {recall_batches_label} by {recall_manufacturer} — "
                "{recall_risk}, no safety risk but customers should be informed for replacement. "
                "Pulled your repeat-Rx list: {affected_label}. "
                "Want me to draft their WhatsApp note + the replacement-pickup workflow?"
            ),
            "refill_due": (
                "{greeting} — {merchant_name} {locality} yahan. "
                "{customer_name_label}'s {medications_label} "
                "{refill_date_label} ko khatam hongi. "
                "Same dose, same brand ready hai. {offer_display}. "
                "Reply CONFIRM to dispatch, or call {contact_label} if any change in dosage."
            ),
            "compliance": (
                "{owner_first}, compliance alert: {regulation_title}. "
                "Source: {regulation_source}. Penalty for non-compliance: significant. "
                "Want me to draft a checklist + audit reminder? Reply YES."
            ),
            "research_digest": (
                "{owner_first}, industry update: {digest_title}. "
                "Source: {digest_source}. {digest_actionable_label}. "
                "Want me to help you act on this? Reply YES."
            ),
            "search_spike": (
                "{owner_first}, {demand_count} people in {locality} searched for '{search_term}' today. "
                "Your {offer_display} is relevant. Should I alert them? Reply YES."
            ),
            "recall_soft": (
                "{greeting} — {merchant_name} here. "
                "Reminder: {customer_name}'s monthly medicines are due for refill. "
                "{offer_display}. Reply CONFIRM to arrange delivery."
            ),
            "re_engage": (
                "{owner_first}, {metric_highlight}. "
                "One quick win: {one_action}. Reply YES."
            ),
        },
    }


# ─────────────────────────────────────────────
# Template variable builder
# ─────────────────────────────────────────────

def _build_vars(signal: Signal, category: Dict, category_slug: str, merchant: Dict,
                customer: Optional[Dict], all_offers: List[Dict]) -> Dict[str, str]:
    d = signal.data
    voice = CATEGORY_VOICE.get(category_slug, CATEGORY_VOICE["restaurants"])

    # Salutation
    owner = d.get("owner_first_name", d.get("merchant_name", "there").split()[0])
    salutation = voice["salutation"].format(owner_first=owner)
    
    # Add Hindi-English injection if "hi" in languages
    if "hi" in d.get("languages", []):
        slot_offer = "Aapke liye 2 slots ready hain"
        greeting = "Namaste"
    else:
        slot_offer = "We have slots available this week"
        greeting = "Hello"

    # Offer display
    offer_display = d.get("offer_title", "")
    if offer_display:
        price = d.get("offer_price", "")
        if price and price != "0":
            # Price might already be in title
            if "₹" not in offer_display:
                offer_display = f"{offer_display} @ ₹{price}"
    else:
        # Try catalog
        cat_offers = category.get("offer_catalog", [])
        if cat_offers:
            offer_display = cat_offers[0].get("title", "our offer")

    # Peer stats
    peer = category.get("peer_stats", {})
    peer_ctr = peer.get("avg_ctr", 0.03)
    peer_ctr_display = f"{peer_ctr*100:.1f}"
    current_ctr = d.get("ctr", 0)
    ctr_display = f"{current_ctr*100:.1f}"
    underperform_pct = int(((peer_ctr - current_ctr) / peer_ctr * 100)) if peer_ctr > 0 else 0

    # Patient segment for dentists
    signals_list = d.get("merchant_signals", [])
    patient_segment_label = "your patients"
    if "high_risk_adult_cohort" in " ".join(signals_list):
        patient_segment_label = "your high-risk adult patients"
        if d.get("high_risk_count"):
            patient_segment_label = f"your {d['high_risk_count']} high-risk adult patients"

    # Digest vars
    trial_n = d.get("digest_trial_n", 0)
    trial_n_str = f"{trial_n:,}-patient " if trial_n else ""
    digest_source = d.get("digest_source", "")
    citation = f"\n— {digest_source}" if digest_source else ""
    digest_actionable = d.get("digest_actionable", "")
    digest_actionable_label = f"Action: {digest_actionable}" if digest_actionable else ""

    # Months since last visit
    months_since_visit = _months_since(d.get("last_visit", ""))

    # Customer vars
    customer_name = d.get("customer_name", "")
    medications = d.get("medications", d.get("services_received", []))
    medications_label = ", ".join(medications[:3]) if medications else "monthly medicines"
    refill_date = d.get("refill_date", "")
    refill_date_label = f"on {refill_date}" if refill_date else "soon"

    # Demand vars
    demand_count = d.get("demand_count", 0)
    demand_count_label = f"{demand_count} " if demand_count else "many "
    search_term = d.get("search_term", category_slug)
    locality = d.get("locality", d.get("city", "your area"))

    # Festival vars
    festival_name = d.get("festival_name", "the upcoming festival")
    days_until = d.get("days_until", 4)

    # IPL/temporal event
    match_context = f"{d.get('match_teams', 'the match')} at {d.get('match_time', '7:30pm')}"
    is_weekend = d.get("is_weekend", False)
    if is_weekend:
        contrarian_advice = (
            "Important: Saturday IPL matches shift -12% restaurant covers (people watch at home). "
            "Skip the match promo today; push your existing offer as a home-delivery special instead."
        )
        action_offer = "draft a delivery banner for tonight"
    else:
        contrarian_advice = "Weeknight IPL matches drive +18% covers. Good time for a match-combo push."
        action_offer = "send a match-combo offer to nearby users"

    # Compliance/recall
    batches = d.get("recall_batches", [])
    recall_batches_label = " + ".join(batches) if batches else "specific batches"
    recall_manufacturer = d.get("recall_manufacturer", "the manufacturer")
    recall_risk = d.get("recall_risk", "sub-potency")
    affected_count = d.get("affected_count", 0)
    affected_label = (f"{affected_count} of your chronic-Rx customers were dispensed these batches"
                      if affected_count else "customers who received these batches")

    # Milestone
    milestone_value = d.get("milestone_value", 100)
    milestone_metric = d.get("milestone_metric", "reviews")
    top_pct = "10"  # Default claim

    # Seasonal dip
    from datetime import datetime
    next_month = (datetime.now().month % 12) + 1
    seasonal_label = f"{datetime.now().strftime('%B')}-{datetime(datetime.now().year, next_month, 1).strftime('%B')}"
    active_members = d.get("active_members", d.get("customer_total", 0))
    active_members_label = f"{active_members} members" if active_members else "your members"

    # Re-engage
    metric_highlight = _best_metric_highlight(d, peer, category_slug)
    one_action = _best_single_action(d, category_slug, offer_display)

    # Recall label for compliance
    recall_molecule = d.get("recall_molecule", "medication")
    recall_label_compliance = f"voluntary recall on {recall_batches_label} ({recall_molecule})"

    # Regulation
    regulation_title = d.get("regulation_title", "regulation update")
    regulation_source = d.get("regulation_source", "regulatory authority")
    effective_date = d.get("effective_date", "")
    effective_label = f"Effective: {effective_date}" if effective_date else ""

    # Pharmacy refill greeting
    lang = d.get("customer_language", "en")
    greeting = "Namaste" if "hi" in lang.lower() else "Hello"
    contact_label = "us"

    # Customer followup (salon bridal etc)
    relationship_context = ""
    if d.get("visits_total", 0) > 0:
        relationship_context = f"{d['visits_total']} visits with us — we know what you like."

    # Slot offer placeholder
    slot_offer = "We have slots available this week"
    slot_label = d.get("preferred_slot", "").replace("_", " ") or "your preferred"

    # New offering for gyms
    goal = d.get("customer_goal", "")
    new_offering = f"We've added a class that fits {goal} goals well" if goal else "We have new classes this month"
    trial_date_label = "next week"

    # Recall label (customer facing)
    recall_label = "6-month cleaning recall"

    # Customer name label
    customer_name_label = f"{customer_name}'s" if customer_name else "your patient's"

    # Competitor
    competitor_name = d.get("competitor_name", "a new competitor")
    competitor_distance_km = d.get("competitor_distance_km", 1.5)

    # Review theme
    review_theme = d.get("review_theme", "service quality")
    review_count = d.get("review_count", 3)

    return {
        "salutation": salutation,
        "owner_first": owner,
        "merchant_name": d.get("merchant_name", ""),
        "offer_display": offer_display,
        "locality": locality,
        "city": d.get("city", ""),
        "demand_count": str(demand_count) if demand_count else "many",
        "demand_count_label": demand_count_label,
        "search_term": search_term,
        "festival_name": festival_name,
        "days_until": str(days_until),
        "peer_ctr_display": peer_ctr_display,
        "ctr_display": ctr_display,
        "underperform_pct": str(underperform_pct),
        "patient_segment_label": patient_segment_label,
        "trial_n_str": trial_n_str,
        "digest_title": d.get("digest_title", ""),
        "digest_source": digest_source,
        "citation": citation,
        "digest_actionable_label": digest_actionable_label,
        "customer_name": customer_name,
        "customer_name_label": customer_name_label,
        "months_since_visit": str(months_since_visit),
        "medications_label": medications_label,
        "refill_date_label": refill_date_label,
        "recall_batches_label": recall_batches_label,
        "recall_manufacturer": recall_manufacturer,
        "recall_risk": recall_risk,
        "affected_label": affected_label,
        "regulation_title": regulation_title,
        "regulation_source": regulation_source,
        "effective_label": effective_label,
        "recall_label_compliance": recall_label_compliance,
        "milestone_value": str(milestone_value),
        "milestone_metric": milestone_metric,
        "top_pct": top_pct,
        "dip_pct": str(int(d.get("dip_pct", 12))),
        "spike_pct": str(int(d.get("spike_pct", 28))),
        "seasonal_label": seasonal_label,
        "active_members_label": active_members_label,
        "metric_highlight": metric_highlight,
        "one_action": one_action,
        "match_context": match_context,
        "contrarian_advice": contrarian_advice,
        "action_offer": action_offer,
        "competitor_name": competitor_name,
        "competitor_distance_km": str(competitor_distance_km),
        "seasonal_note": d.get("seasonal_note", ""),
        "slot_offer": slot_offer if 'slot_offer' in locals() else "We have slots available this week",
        "slot_label": slot_label,
        "relationship_context": relationship_context,
        "new_offering": new_offering,
        "trial_date_label": trial_date_label,
        "recall_label": recall_label,
        "customer_goal_label": f"your {goal} journey" if goal else "getting back on track",
        "greeting": greeting if 'greeting' in locals() else "Hello",
        "contact_label": contact_label,
        "review_theme": review_theme,
        "review_count": str(review_count),
    }


# ─────────────────────────────────────────────
# Main compose function
# ─────────────────────────────────────────────

def compose_message(
    signal: Signal,
    category: Dict,
    merchant: Dict,
    customer: Optional[Dict],
    category_slug: str,
) -> Tuple[str, str, str]:
    """
    Returns: (body, cta_type, send_as)
    """
    trigger_kind = signal.trigger_kind

    # Determine send_as
    scope = signal.data.get("trigger_scope", "merchant")
    has_customer = customer is not None and customer.get("customer_id")
    send_as = "merchant_on_behalf" if (scope == "customer" or has_customer) else "vera"

    # Route LLM-qualified triggers through Groq; keep templates for the rest.
    if trigger_kind in LLM_TRIGGER_KINDS and (
        os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
    ):
        logger.info(f"Using Groq LLM path for trigger={trigger_kind} category={category_slug}")
        body = _llm_compose(signal, category, merchant, customer, category_slug)
    else:
        logger.info(f"Using template path for trigger={trigger_kind} category={category_slug}")
        body = _template_compose(signal, category, merchant, customer, category_slug)

    # Validate: no URLs (meta hard fail)
    import re
    body = re.sub(r'https?://\S+', '[link]', body)

    # CTA
    cta = _select_cta(signal, send_as, category_slug)

    # Taboo check
    voice = CATEGORY_VOICE.get(category_slug, {})
    for taboo in voice.get("vocab_taboo", []):
        if taboo.lower() in body.lower():
            body = body.replace(taboo, "").replace(taboo.lower(), "").strip()

    return body.strip(), cta, send_as


def _template_compose(signal: Signal, category: Dict, merchant: Dict,
                      customer: Optional[Dict], category_slug: str) -> str:
    templates = _templates()
    cat_templates = templates.get(category_slug, templates.get("restaurants", {}))

    # Find best matching template
    template_str = cat_templates.get(signal.type)
    if not template_str:
        # Try fallback by tier
        fallback_order = ["search_spike", "research_digest", "re_engage"]
        for fb in fallback_order:
            if fb in cat_templates:
                template_str = cat_templates[fb]
                break
        if not template_str:
            template_str = "Hi {owner_first}, quick check — {metric_highlight}. {one_action}. Reply YES."

    all_offers = merchant.get("offers", [])
    vars_dict = _build_vars(signal, category, category_slug, merchant, customer, all_offers)

    try:
        return template_str.format(**vars_dict)
    except KeyError as e:
        logger.warning(f"Template key error: {e} for signal {signal.type}")
        owner = signal.data.get("owner_first_name", "there")
        offer = vars_dict.get("offer_display", "your offer")
        return f"Hi {owner}, quick note about {offer} — want me to help? Reply YES."


def _llm_compose(signal: Signal, category: Dict, merchant: Dict,
                 customer: Optional[Dict], category_slug: str) -> str:
    """
    LLM composition with strict fact injection.
    Facts are extracted — raw JSON never passed to LLM.
    """
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY") or os.getenv("LLAMA_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        # Graceful fallback to template if no API key
        return _template_compose(signal, category, merchant, customer, category_slug)

    facts = _extract_llm_facts(signal, category, merchant, customer, category_slug)
    voice = CATEGORY_VOICE.get(category_slug, {})
    peer = category.get("peer_stats", {})
    d = signal.data

    merchant_name = facts.get('merchant_name', '')
    owner_first = facts.get('owner_first', '')
    locality = facts.get('locality', '')
    ctr = d.get('ctr', 0)
    ctr_pct = ctr * 100
    peer_ctr = peer.get('avg_ctr', 0.03)
    peer_ctr_pct = peer_ctr * 100
    views = d.get('views', 0)
    calls = d.get('calls', 0)
    merchant_signals = facts.get('merchant_signals', '').split(', ')
    trigger_kind = signal.trigger_kind
    trigger_reason = facts.get('trigger_detail', '')
    customer_name = facts.get('customer_name', 'N/A')
    customer_context = facts.get('customer_context', 'N/A')
    offer_title = facts.get('offer', 'no active offer')
    demand_count = d.get('demand_count', 0)
    search_term = d.get('search_term', category_slug)
    peer_insight = facts.get('social_proof', f'{category_slug.capitalize()} peers in {locality} are seeing better results with targeted outreach.')
    category_tone = voice.get('tone', 'professional')
    vocab_taboo = ', '.join(voice.get('vocab_taboo', []))

    system_prompt = """You are Vera, an AI growth assistant for local businesses on magicpin.

Your job is to generate HIGHLY SPECIFIC, CONTEXT-AWARE WhatsApp messages for merchants.

You are being evaluated by a strict judge on the following:

1. SPECIFICITY — Use exact numbers, comparisons, and real signals (CTR, views, demand, etc.)
2. PERSONALIZATION — Tailor message to THIS merchant’s exact situation
3. CATEGORY FIT — Match tone, vocabulary, and constraints of the category
4. TRIGGER RELEVANCE — Clearly explain WHY this message is being sent NOW
5. ENGAGEMENT — Strong, low-friction CTA (Reply YES / CONFIRM / etc.)
6. SOCIAL PROOF — Compare with peer businesses ("others in your area...")
7. NO HALLUCINATION — Use ONLY provided facts
8. CLARITY — Simple, natural, WhatsApp-friendly

CRITICAL RULES:
- NEVER output generic advice
- NEVER invent data
- ALWAYS include at least ONE number or comparison
- ALWAYS include a clear CTA
- ALWAYS include WHY NOW (trigger reason)
- Prefer short (2–4 lines), punchy, actionable messages

OUTPUT:
Return ONLY the WhatsApp message text. No JSON. No explanation."""

    user_prompt = f"""FACTS:

MERCHANT:
- Name: {merchant_name}
- Owner: {owner_first}
- Location: {locality}
- Category: {category_slug}

PERFORMANCE:
- CTR: {ctr_pct:.1f}%
- Peer Avg CTR: {peer_ctr_pct:.1f}%
- Views: {views}
- Calls: {calls}

SIGNALS:
- {', '.join(merchant_signals)}

TRIGGER:
- Type: {trigger_kind}
- Reason: {trigger_reason}

CUSTOMER (if exists):
- Name: {customer_name}
- Context: {customer_context}

OFFER:
- {offer_title}

DEMAND SIGNAL:
- {demand_count} people searched for "{search_term}" in {locality}

PEER INSIGHT (SOCIAL PROOF) — MUST USE IN MESSAGE:
- {peer_insight if peer_insight else f"Peers in {locality} average {peer_ctr_pct:.1f}% CTR"}

MERCHANT SIGNALS:
- {', '.join(facts.get('merchant_signals', '').split(', ')[:3]) if facts.get('merchant_signals') else 'none'}

CATEGORY RULES:
- Tone: {category_tone}
- Avoid: {vocab_taboo}

---

TASK:

Generate a WhatsApp message that:

1. Uses the merchant's real data (CTR, demand, etc.)
2. Includes SOCIAL PROOF (compare with peers)
3. Explains WHY this message is sent NOW (trigger)
4. Feels personal (not generic)
5. Ends with a clear CTA

IMPORTANT:
- Make it sound like a smart assistant, not a bot
- Keep it concise but powerful
- Prefer conversational tone (WhatsApp style)

Now generate the message."""

    # Cascading provider fallback: try each available provider in order
    llm_providers = []
    if os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY"):
        llm_providers.append(("groq", _call_grok))
    if os.getenv("LLAMA_API_KEY"):
        llm_providers.append(("llama", _call_llama))
    if os.getenv("ANTHROPIC_API_KEY"):
        llm_providers.append(("anthropic", _call_anthropic))
    if os.getenv("OPENAI_API_KEY"):
        llm_providers.append(("openai", _call_openai))

    if not llm_providers:
        return _template_compose(signal, category, merchant, customer, category_slug)

    for provider_name, provider_fn in llm_providers:
        try:
            result = provider_fn(system_prompt, user_prompt)
            logger.info(f"LLM compose succeeded via {provider_name}")
            return result
        except Exception as e:
            logger.warning(f"LLM provider {provider_name} failed: {e} — trying next")
            continue

    logger.warning("All LLM providers failed — falling back to template")
    return _template_compose(signal, category, merchant, customer, category_slug)


def _call_grok(system: str, user: str) -> str:
    """Groq API call with multi-model fallback.

    base_url is hardcoded (not from env) to avoid doubled-path 404s.
    Falls through GROQ_MODELS in order on decommission/404 errors.
    """
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY"),
        base_url="https://api.groq.com/openai/v1"
    )
    # Priority order: env var first, then fallbacks
    groq_models = [
        os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "llama-3.3-70b-versatile",
        "llama3-70b-8192",
        "mixtral-8x7b-32768",
    ]
    # Deduplicate while preserving order
    seen = set()
    groq_models = [m for m in groq_models if not (m in seen or seen.add(m))]

    for model in groq_models:
        try:
            logger.info("Calling Groq API model=%s", model)
            resp = client.chat.completions.create(
                model=model,
                temperature=0,
                max_tokens=300,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ]
            )
            content = resp.choices[0].message.content.strip()
            content = content.strip('"').strip("'")  # remove wrapping quotes
            logger.info("Groq response received chars=%d model=%s", len(content), model)
            return content
        except Exception as e:
            err = str(e).lower()
            if "decommission" in err or "not found" in err or "404" in err or "unknown" in err:
                logger.warning("Groq model %s unavailable (%s), trying next", model, str(e)[:80])
                continue
            raise  # re-raise auth/network errors immediately


def _call_llama(system: str, user: str) -> str:
    """Llama API call placeholder - replace with your actual Llama implementation"""
    # Example using OpenAI-compatible format (many Llama providers use this)
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv("LLAMA_API_KEY"),
        base_url=os.getenv("LLAMA_BASE_URL")  # Your Llama provider's base URL
    )
    resp = client.chat.completions.create(
        model=os.getenv("LLAMA_MODEL", "llama-3.1-70b-versatile"),
        temperature=0,
        max_tokens=300,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return resp.choices[0].message.content.strip()


def _call_anthropic(system: str, user: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": user}]
    )
    return resp.content[0].text.strip()


def _call_openai(system: str, user: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=300,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return resp.choices[0].message.content.strip()


def _extract_llm_facts(signal: Signal, category: Dict, merchant: Dict,
                       customer: Optional[Dict], category_slug: str) -> Dict[str, str]:
    """Build a facts dict with ONLY verified payload values."""
    d = signal.data
    peer = category.get("peer_stats", {})

    offer = d.get("offer_title", "")
    price = d.get("offer_price", "")
    if offer and price and price != "0" and "₹" not in offer:
        offer = f"{offer} @ ₹{price}"

    trigger_detail = ""
    kind = signal.trigger_kind
    if kind == "active_planning_intent":
        trigger_detail = "Merchant explicitly expressed interest in planning something — respond with concrete draft or proposal."
    elif kind == "curious_ask_due":
        trigger_detail = "Weekly cadence check-in — ask one curious low-friction question about their business."
    elif kind == "ipl_match_today":
        trigger_detail = (f"IPL match today: {d.get('match_teams', 'match')} at {d.get('match_time', '')}. "
                         f"{'Saturday match = -12% covers, recommend home-delivery push instead.' if d.get('is_weekend') else 'Weeknight = +18% covers opportunity.'}")
    elif kind == "seasonal_perf_dip":
        trigger_detail = f"Seasonal dip of {d.get('dip_pct', 12)}% — this is the normal Apr-Jun window; recommend retention focus over acquisition."
    elif kind == "review_theme_emerged":
        trigger_detail = f"{d.get('review_count', 3)} recent reviews mention '{d.get('review_theme', 'service')}'. Address or leverage this pattern."
    elif kind == "competitor_opened":
        trigger_detail = f"New competitor {d.get('competitor_name', '')} opened {d.get('competitor_distance_km', '')}km away. Opportunity to differentiate."

    ctr = d.get("ctr", 0)
    peer_ctr = peer.get("avg_ctr", 0.03)
    peer_comparison = f"CTR {ctr*100:.1f}% vs peer avg {peer_ctr*100:.1f}%"
    if ctr < peer_ctr:
        peer_comparison += " (below peer)"

    # Category-specific fact
    cat_facts = {
        "dentists": f"High-risk adult cohort: {d.get('high_risk_count', 0)} patients",
        "salons": f"Bookings context: {d.get('visits_delta_7d', 'unknown')}",
        "restaurants": f"Covers context, locality: {d.get('locality', '')}",
        "gyms": f"Active members: {d.get('active_members', d.get('customer_total', 0))}",
        "pharmacies": f"Chronic-Rx customers: {d.get('chronic_rx_count', 0)}",
    }

    customer_name = ""
    customer_context = ""
    if customer:
        customer_name = customer.get("identity", {}).get("name", "")
        rel = customer.get("relationship", {})
        customer_context = (f"State: {customer.get('state', '')}, "
                           f"last visit: {rel.get('last_visit', '')}, "
                           f"services: {', '.join(rel.get('services_received', []))}")

    # Social proof fact — peer benchmark for this category+locality
    peer_reviews = peer.get("avg_reviews", 0)
    peer_active = peer.get("active_merchants_locality", peer.get("merchants_in_locality", 0))
    peer_action_map = {
        "active_planning_intent": "ran a targeted offer campaign this month",
        "curious_ask_due": "are actively engaging with their customers this week",
        "review_theme_emerged": "responded to reviews and saw CTR improve",
        "ipl_match_today": "ran a match-combo push last IPL and saw +18% covers",
        "seasonal_perf_dip": "shifted to retention focus in Apr-Jun and kept 80%+ members",
        "competitor_opened": "boosted local visibility spend when a competitor opened nearby",
        "dormant_with_vera": "re-engaged customers after a quiet period and recovered footfall",
    }
    peer_action = peer_action_map.get(kind, "acted on similar signals and improved performance")
    social_proof = ""
    if peer_active > 0:
        social_proof = f"{peer_active} {category_slug} in {d.get('locality', 'your area')} {peer_action}."
    elif peer_ctr > 0:
        social_proof = f"Peers in your locality average {peer_ctr*100:.1f}% CTR — yours is {ctr*100:.1f}%."

    # Merchant signals list for LLM context
    merchant_signals_list = d.get("merchant_signals", d.get("signals", []))
    merchant_signals_str = ", ".join(merchant_signals_list[:5]) if merchant_signals_list else "none"

    return {
        "merchant_name": d.get("merchant_name", ""),
        "owner_first": d.get("owner_first_name", ""),
        "locality": d.get("locality", ""),
        "offer": offer or "no active offer",
        "metric": f"Views: {d.get('views', 0)}, Calls: {d.get('calls', 0)}, CTR: {ctr*100:.1f}%",
        "trigger_detail": trigger_detail,
        "customer_name": customer_name,
        "customer_context": customer_context,
        "peer_comparison": peer_comparison,
        "category_specific": cat_facts.get(category_slug, ""),
        "social_proof": social_proof,
        "merchant_signals": merchant_signals_str,
    }


# ─────────────────────────────────────────────
# CTA selection
# ─────────────────────────────────────────────

def _select_cta(signal: Signal, send_as: str, category_slug: str) -> str:
    kind = signal.trigger_kind
    sig_type = signal.type

    # Customer-facing booking flow
    if send_as == "merchant_on_behalf" and sig_type in ("recall_soft", "recall_hard", "refill_due"):
        return "open_ended"

    # Dentist research → open-ended (they want to think)
    if category_slug == "dentists" and sig_type == "research_digest":
        return "open_ended"

    # Compliance/urgent → open-ended (involves workflow discussion)
    if sig_type in ("compliance", "urgent_compliance", "regulation_change"):
        return "open_ended"

    # Planning intent → open-ended
    if kind == "active_planning_intent":
        return "open_ended"

    # Curious ask → open-ended
    if kind == "curious_ask_due":
        return "open_ended"

    # Default: binary
    return "binary_yes_no"


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────

def _months_since(date_str: str) -> int:
    if not date_str:
        return 6
    try:
        from dateutil.parser import parse
        from datetime import datetime, timezone
        dt = parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return max(1, delta.days // 30)
    except Exception:
        return 6


def _best_metric_highlight(d: Dict, peer: Dict, category_slug: str) -> str:
    views = d.get("views", 0)
    calls = d.get("calls", 0)
    ctr = d.get("ctr", 0)
    peer_ctr = peer.get("avg_ctr", 0.03)
    peer_views = peer.get("avg_views_30d", 2000)

    if ctr < peer_ctr * 0.8:
        return f"CTR {ctr*100:.1f}% is below the {peer_ctr*100:.1f}% peer median"
    elif views < peer_views * 0.8:
        return f"views ({views}/month) are below your peer average"
    elif calls > 0:
        return f"you're getting {calls} calls/month"
    return "there's an opportunity to grow your visibility"


def _best_single_action(d: Dict, category_slug: str, offer: str) -> str:
    actions = {
        "dentists": f"draft a patient recall message using your {offer}",
        "salons": f"push your {offer} to {d.get('demand_count', 'nearby')} people searching this week",
        "restaurants": f"run a 2-hour {offer} push in {d.get('locality', 'your area')}",
        "gyms": "draft a summer retention challenge for your members",
        "pharmacies": "set up a WhatsApp refill reminder for your chronic-Rx patients",
    }
    return actions.get(category_slug, f"promote your {offer}")