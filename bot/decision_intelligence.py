"""
Decision Intelligence Engine: selects the BEST signal using insights from product_intelligence.
"""
from typing import Dict, Any, List, Tuple, Optional
from product_intelligence import extract_insights


def select_best_signal(
    ranked_signals: List[Tuple[float, Dict[str, Any]]],
    merchant_data: Dict[str, Any],
    category_data: Dict[str, Any],
    customer_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Selects the BEST signal and justifies it using INSIGHTS (not raw data).
    """
    if not ranked_signals:
        return {
            "selected_signal": None,
            "why_this_signal_wins": "No signals available to evaluate",
            "why_others_rejected": "No other signals",
            "expected_outcome": "No action taken",
            "confidence": "LOW",
        }

    top_signal_score, top_signal = ranked_signals[0]
    top_signal_type = top_signal.get("kind", top_signal.get("type", "unknown"))
    runner_up_signal = None
    runner_up_signal_type = "none"

    if len(ranked_signals) > 1:
        runner_up_score, runner_up_signal = ranked_signals[1]
        runner_up_signal_type = runner_up_signal.get("kind", runner_up_signal.get("type", "unknown"))

    insights = extract_insights(
        merchant_data=merchant_data,
        category_data=category_data,
        trigger_data=top_signal,
        customer_data=customer_data,
    )

    selected_signal = {
        "score": top_signal_score,
        "type": top_signal_type,
        "data": top_signal,
    }

    why_this_signal_wins = _build_why_this_signal_wins(
        selected_signal=selected_signal,
        runner_up_type=runner_up_signal_type,
        insights=insights,
        score_gap=top_signal_score - (ranked_signals[1][0] if len(ranked_signals) > 1 else 0),
    )

    why_others_rejected = _build_why_others_rejected(
        ranked_signals=ranked_signals,
        top_insights=insights,
    )

    expected_outcome = _build_expected_outcome(
        selected_signal=selected_signal,
        insights=insights,
    )

    confidence = _calculate_confidence(
        top_score=top_signal_score,
        runner_up_score=ranked_signals[1][0] if len(ranked_signals) > 1 else 0,
        insights=insights,
    )

    return {
        "selected_signal": top_signal_type,
        "why_this_signal_wins": why_this_signal_wins,
        "why_others_rejected": why_others_rejected,
        "expected_outcome": expected_outcome,
        "confidence": confidence,
    }


def _build_why_this_signal_wins(
    selected_signal: Dict,
    runner_up_type: str,
    insights: Dict,
    score_gap: float,
) -> str:
    performance_insights = insights.get("performance_insights", [])
    opportunity_insights = insights.get("opportunity_insights", [])
    urgency_insights = insights.get("urgency_insights", "")
    offer_insights = insights.get("offer_insights", [])

    reasons = []

    if urgency_insights:
        reasons.append(urgency_insights)

    if opportunity_insights:
        reasons.append(opportunity_insights[0])

    if performance_insights:
        reasons.append(f"Aligns with merchant performance: {performance_insights[0]}")

    if offer_insights:
        reasons.append(offer_insights[0])

    if runner_up_type != "none":
        reasons.append(f"Outranks '{runner_up_type}' by {score_gap:.1f} points in scoring")

    if not reasons:
        return f"'{selected_signal['type']}' is the highest-scoring signal"

    return " ".join(reasons)


def _build_why_others_rejected(
    ranked_signals: List[Tuple[float, Dict]],
    top_insights: Dict,
) -> str:
    if len(ranked_signals) <= 1:
        return "No other signals to compare"

    rejected = []
    for score, signal in ranked_signals[1:3]:
        signal_type = signal.get("kind", signal.get("type", "unknown"))
        rejected.append(f"'{signal_type}' (score: {score:.1f})")

    if not rejected:
        return "No other signals"

    return f"Other signals scored lower: {', '.join(rejected)}. Top signal has stronger alignment with merchant insights and urgency."


def _build_expected_outcome(
    selected_signal: Dict,
    insights: Dict,
) -> str:
    signal_type = selected_signal["type"]

    if signal_type in ["research_digest", "digest"]:
        return "Increased engagement through relevant clinical/professional content; potential for recall campaign activation"
    elif signal_type in ["perf_dip", "performance_drop"]:
        return "Performance recovery through targeted improvements; CTR/views restoration to peer levels"
    elif signal_type in ["festival_upcoming", "temporal", "temporal_event"]:
        return "Increased bookings/revenue through timely promotions aligned with event demand"
    elif signal_type in ["recall_due", "recall"]:
        return "Higher retention through customer re-engagement; reduced patient churn"
    elif signal_type in ["offer", "promotion"]:
        return "Higher conversion through active offer promotion; increased walk-ins/transactions"
    else:
        return "Strong merchant engagement; improved business outcomes based on signal relevance"


def _calculate_confidence(
    top_score: float,
    runner_up_score: float,
    insights: Dict,
) -> str:
    score_gap = top_score - runner_up_score

    if score_gap > 20:
        return "HIGH"
    elif score_gap > 10:
        return "MEDIUM"
    else:
        return "LOW"
