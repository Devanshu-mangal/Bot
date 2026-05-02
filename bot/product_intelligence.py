"""
Product Intelligence System: transforms raw structured JSON into HIGH-VALUE INSIGHTS.
"""
from typing import Dict, Any, Optional


def extract_insights(
    merchant_data: Dict[str, Any],
    category_data: Dict[str, Any],
    trigger_data: Dict[str, Any],
    customer_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Returns a structured INSIGHT OBJECT.
    """
    performance_insights = _extract_performance_insights(merchant_data, category_data)
    opportunity_insights = _extract_opportunity_insights(merchant_data, category_data)
    urgency_insights = _extract_urgency_insights(trigger_data)
    customer_insights = _extract_customer_insights(customer_data)
    offer_insights = _extract_offer_insights(merchant_data, category_data)
    risk_flags = _extract_risk_flags(merchant_data, category_data)

    return {
        "performance_insights": performance_insights,
        "opportunity_insights": opportunity_insights,
        "urgency_insights": urgency_insights,
        "customer_insights": customer_insights,
        "offer_insights": offer_insights,
        "risk_flags": risk_flags,
    }


def _extract_performance_insights(merchant_data: Dict, category_data: Dict) -> list:
    insights = []
    perf = merchant_data.get("performance", {})
    peer = category_data.get("peer_stats", {})

    if perf.get("ctr") is not None and peer.get("avg_ctr") is not None:
        merchant_ctr_pct = perf["ctr"] * 100
        peer_ctr_pct = peer["avg_ctr"] * 100
        ctr_delta_pct = ((perf["ctr"] - peer["avg_ctr"]) / peer["avg_ctr"]) * 100
        if ctr_delta_pct < 0:
            insights.append(
                f"CTR is {merchant_ctr_pct:.1f}% vs peer avg {peer_ctr_pct:.1f}% → ~{abs(ctr_delta_pct):.0f}% underperformance"
            )
        elif ctr_delta_pct > 0:
            insights.append(
                f"CTR is {merchant_ctr_pct:.1f}% vs peer avg {peer_ctr_pct:.1f}% → ~{ctr_delta_pct:.0f}% outperformance"
            )
        else:
            insights.append(
                f"CTR is {merchant_ctr_pct:.1f}% (matches peer avg {peer_ctr_pct:.1f}%)"
            )

    if perf.get("views") is not None and peer.get("avg_views_30d") is not None:
        if perf["views"] < peer["avg_views_30d"]:
            insights.append(
                f"Views are {perf['views']} vs peer avg {peer['avg_views_30d']} → below average"
            )
        else:
            insights.append(
                f"Views are {perf['views']} vs peer avg {peer['avg_views_30d']} → above average"
            )

    if perf.get("calls") is not None and peer.get("avg_calls_30d") is not None:
        if perf["calls"] < peer["avg_calls_30d"]:
            insights.append(
                f"Calls are {perf['calls']} vs peer avg {peer['avg_calls_30d']} → below average"
            )
        else:
            insights.append(
                f"Calls are {perf['calls']} vs peer avg {peer['avg_calls_30d']} → above average"
            )

    return insights


def _extract_opportunity_insights(merchant_data: Dict, category_data: Dict) -> list:
    insights = []
    customer_agg = merchant_data.get("customer_aggregate", {})

    if customer_agg.get("high_risk_adult_count"):
        insights.append(
            f"High-risk adult cohort ({customer_agg['high_risk_adult_count']} patients) → recall campaigns can increase revenue"
        )
    elif customer_agg.get("lapsed_180d_plus"):
        insights.append(
            f"{customer_agg['lapsed_180d_plus']} lapsed customers (180+ days) → winback campaigns can drive recovery"
        )

    active_offers = [o for o in merchant_data.get("offers", []) if o.get("status") == "active"]
    if not active_offers:
        insights.append(
            "No active offers → activating a relevant offer can boost conversions"
        )

    signals = merchant_data.get("signals", [])
    if "stale_posts" in " ".join(signals):
        insights.append(
            "Stale Google Posts → fresh posts can improve CTR"
        )

    return insights


def _extract_urgency_insights(trigger_data: Dict) -> str:
    trigger_kind = trigger_data.get("kind", "")
    if trigger_kind == "research_digest":
        return "Trigger = research_digest → new clinical info relevant to merchant segment"
    elif trigger_kind == "perf_dip":
        return "Trigger = perf_dip → performance is down; prompt action can recover"
    elif trigger_kind == "festival_upcoming":
        return f"Trigger = festival_upcoming → {trigger_data.get('payload', {}).get('festival', 'event')} coming up; high booking demand expected"
    elif trigger_kind == "ipl_match_today":
        return f"Trigger = ipl_match_today → {trigger_data.get('payload', {}).get('match', 'match')} today; opportunity for promotions"
    elif trigger_kind == "recall_due":
        return "Trigger = recall_due → customer recall is due; high retention potential"
    elif trigger_kind == "chronic_refill_due":
        return "Trigger = chronic_refill_due → patient medications are due; immediate reminder needed"
    elif trigger_kind == "supply_alert":
        return "Trigger = supply_alert → product recall alert; critical to inform patients"
    elif trigger_kind == "regulation_change":
        return "Trigger = regulation_change → compliance update; important to act before deadline"
    else:
        return f"Trigger = {trigger_kind} → timely to engage merchant"


def _extract_customer_insights(customer_data: Optional[Dict]) -> Optional[list]:
    if not customer_data:
        return None
    insights = []
    state = customer_data.get("state", "")
    rel = customer_data.get("relationship", {})
    if state == "lapsed_soft":
        insights.append(
            "Customer is lapsed_soft → high probability of return with reminder"
        )
    elif state == "lapsed_hard":
        insights.append(
            "Customer is lapsed_hard → personalized offer may help win back"
        )
    if rel.get("last_visit"):
        insights.append(
            f"Customer's last visit was {rel['last_visit']} → recent engagement or lapsed depending on timeframe"
        )
    return insights


def _extract_offer_insights(merchant_data: Dict, category_data: Dict) -> list:
    insights = []
    active_offers = [o for o in merchant_data.get("offers", []) if o.get("status") == "active"]
    if active_offers:
        offer_title = active_offers[0].get("title", "your offer")
        insights.append(
            f"{offer_title} aligns with current demand signals"
        )
    else:
        catalog = category_data.get("offer_catalog", [])
        if catalog:
            insights.append(
                f"Consider activating an offer from catalog: {catalog[0].get('title', 'recommended offer')}"
            )
    return insights


def _extract_risk_flags(merchant_data: Dict, category_data: Dict) -> list:
    risks = []
    active_offers = [o for o in merchant_data.get("offers", []) if o.get("status") == "active"]
    if not active_offers:
        risks.append("No active offers → lost conversion opportunity")
    sub = merchant_data.get("subscription", {})
    if sub.get("status") == "expired":
        risks.append("Subscription expired → profile maintenance paused")
    signals = merchant_data.get("signals", [])
    if "unverified_gbp" in " ".join(signals):
        risks.append("Unverified GBP → lost visibility and trust")
    return risks


def prioritize_insights(insights: Dict) -> list:
    """Fix 7: Improve insight engine prioritization"""
    ordered = []
    
    if insights.get("urgency_insights"):
        ordered.append(insights["urgency_insights"])

    ordered += insights.get("opportunity_insights", [])
    ordered += insights.get("performance_insights", [])
    ordered += insights.get("offer_insights", [])

    return ordered[:2]
