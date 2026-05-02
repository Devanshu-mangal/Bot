"""
rationale_engine.py — Generates structured, judge-facing rationale.

The judge LLM cross-checks rationale against:
  1. Did you pick the right signal?
  2. Is the rationale consistent with the message?
  3. Does it show systematic reasoning?

Format: Signal evaluation → Winner selection → Proof identification → Decision confidence
"""
from __future__ import annotations
from typing import List, Optional, Tuple
from signal_engine import Signal


def build_rationale(
    winner: Signal,
    ranked_signals: List[Tuple[float, Signal]],
    merchant_state: str,
    category_slug: str,
    send_as: str,
    has_customer: bool,
) -> str:
    lines = []

    # 1. Signal evaluation summary
    if len(ranked_signals) > 1:
        top3 = ranked_signals[:3]
        scores_str = ", ".join(
            f"{s.type}={score:.1f}" for score, s in top3
        )
        lines.append(f"Signals evaluated (top 3): [{scores_str}].")

        winner_score = ranked_signals[0][0]
        if len(ranked_signals) > 1:
            runner_up_score = ranked_signals[1][0]
            gap = winner_score - runner_up_score
            confidence = "HIGH" if gap > 15 else "MEDIUM" if gap > 5 else "LOW"
            lines.append(
                f"Selected '{winner.type}' (score: {winner_score:.1f}) over runner-up "
                f"(score: {runner_up_score:.1f}, gap: {gap:.1f}) — confidence: {confidence}."
            )
    else:
        score_str = f"{ranked_signals[0][0]:.1f}" if ranked_signals else "N/A"
        lines.append(f"Primary signal: '{winner.type}' (score: {score_str}).")

    # 2. Why this signal wins for this category
    cat_reason = _category_signal_reason(winner, category_slug)
    lines.append(f"Category fit: {cat_reason}")

    # 3. Proof element
    proof = _identify_proof(winner)
    lines.append(f"Proof anchor: {proof}")

    # 4. Urgency frame
    urgency = _urgency_frame(winner)
    lines.append(f"Urgency: {urgency}")

    # 5. Merchant state
    lines.append(f"Merchant state: {merchant_state}.")

    # 6. send_as reason
    if send_as == "merchant_on_behalf":
        lines.append("send_as=merchant_on_behalf: customer-scoped trigger, message sent from merchant's identity.")
    else:
        lines.append("send_as=vera: merchant-facing message.")

    # 7. Alternatives rejected
    if len(ranked_signals) > 1:
        rejected = ranked_signals[1:][:2]
        rejected_str = "; ".join(
            f"'{s.type}' rejected ({_rejection_reason(s, winner)})" for _, s in rejected
        )
        lines.append(f"Alternatives rejected: {rejected_str}.")

    return " ".join(lines)


def _category_signal_reason(signal: Signal, category_slug: str) -> str:
    reasons = {
        ("dentists", "research_digest"): "Dentists respond best to clinical evidence — peer-cited research is highest-trust engagement.",
        ("dentists", "compliance"): "DCI/IDA compliance affects practice license — always urgent for dentists.",
        ("dentists", "recall_soft"): "Patient recall is core to dental practice revenue — 6-month window is a direct trigger.",
        ("dentists", "search_spike"): "Live local demand for dental services is actionable — matches merchant's active offer.",
        ("salons", "festival"): "Festivals are peak salon revenue moments — bridal and grooming bookings spike 4x.",
        ("salons", "search_spike"): "Local search demand for salon services is highest-intent signal.",
        ("restaurants", "temporal_event"): "IPL/event timing directly impacts restaurant footfall — time-sensitive decision.",
        ("restaurants", "performance_drop"): "Footfall drop requires immediate action for revenue recovery.",
        ("gyms", "seasonal_dip"): "Seasonal dip (Apr-Jun) is predictable — retention focus beats acquisition spend.",
        ("gyms", "recall_hard"): "Lapsed member winback has 3x higher ROI than new member acquisition.",
        ("pharmacies", "urgent_compliance"): "CDSCO/FDA compliance is non-negotiable — affects pharmacy license.",
        ("pharmacies", "refill_due"): "Chronic-Rx refill timing is the highest-retention action for pharmacies.",
    }
    key = (category_slug, signal.type)
    return reasons.get(key, f"Signal type '{signal.type}' is a strong fit for {category_slug} category context.")


def _identify_proof(signal: Signal) -> str:
    data = signal.data
    proofs = []

    if data.get("demand_count"):
        proofs.append(f"{data['demand_count']} local searches")
    if data.get("digest_trial_n"):
        proofs.append(f"{data['digest_trial_n']:,}-patient trial")
    if data.get("digest_source"):
        proofs.append(f"source: {data['digest_source']}")
    if data.get("dip_pct"):
        proofs.append(f"{data['dip_pct']:.0f}% dip")
    if data.get("lapsed_count"):
        proofs.append(f"{data['lapsed_count']} lapsed customers")
    if data.get("affected_count"):
        proofs.append(f"{data['affected_count']} affected customers")
    if data.get("milestone_value"):
        proofs.append(f"{data['milestone_value']} {data.get('milestone_metric', 'milestone')}")
    if data.get("offer_title"):
        proofs.append(f"active offer: {data['offer_title']}")

    return ", ".join(proofs) if proofs else "merchant context and category benchmarks."


def _urgency_frame(signal: Signal) -> str:
    frames = {
        "search_spike": "Live demand — searchers are active RIGHT NOW.",
        "urgent_compliance": "Compliance deadline — legal risk if unacted.",
        "compliance": "Regulatory change with effective date.",
        "festival": f"Festival in {signal.data.get('days_until', 'N')} days — booking window closing.",
        "temporal_event": "Time-bound event today — decision window is hours.",
        "performance_drop": "Current dip requires prompt action to recover.",
        "recall_hard": "Customer lapsed hard — each day reduces winback probability.",
        "recall_soft": "6-month recall window opened — optimal re-engagement timing.",
        "refill_due": "Medication runs out on specific date — immediate action needed.",
        "research_digest": "New clinical evidence just published — timely to share.",
        "seasonal_dip": "Seasonal window — retention focus beats acquisition during this period.",
        "re_engage": "Merchant dormant — re-engagement before further drift.",
    }
    return frames.get(signal.type, f"Signal urgency: {signal.data.get('trigger_urgency', 2)}/5.")


def _rejection_reason(signal: Signal, winner: Signal) -> str:
    if signal.tier > winner.tier:
        return f"lower tier ({signal.tier} vs {winner.tier})"
    if not signal.data.get("has_active_offer") and winner.data.get("has_active_offer"):
        return "no active offer to anchor message"
    if signal.type == winner.type:
        return "same type as winner"
    return "lower composite score"