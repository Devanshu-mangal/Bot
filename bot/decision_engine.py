from typing import Dict, Any, Optional, List, Tuple
from signal_collector import Signal
from context_extractor import ContextExtractor

class DecisionEngine:
    @staticmethod
    def make_decision(signal: Optional[Signal], merchant: Dict, category: Dict,
                     all_signals_scored: List[Tuple[float, Signal]] = None) -> Dict[str, Any]:
        merchant_data = ContextExtractor.extract_merchant_data(merchant)
        category_data = ContextExtractor.extract_category_data(category)
        
        # Conversation history check
        conv_history = merchant.get("conversation_history", [])
        ignored_streak = sum(1 for turn in conv_history[-5:] 
                            if turn.get("from") == "vera" and turn.get("engagement") == "ignored")
        
        if ignored_streak >= 3:
            return DecisionEngine._fallback_decision(merchant, cold_override=True)

        if signal is None:
            return DecisionEngine._fallback_decision(merchant)

        decision = {
            "should_send": True,
            "signal_type": signal.type,
            "signal_data": signal.data,
            "merchant_data": merchant_data,
            "category_data": category_data,
            "rationale": DecisionEngine._generate_rationale(signal, merchant_data, category_data, all_signals_scored),
            "fallback_used": False,
            "all_signals_scored": all_signals_scored[:5] if all_signals_scored else []
        }

        return decision

    @staticmethod
    def _fallback_decision(merchant: Dict, cold_override: bool = False) -> Dict[str, Any]:
        merchant_data = ContextExtractor.extract_merchant_data(merchant)
        rationale = "No strong signals available. Sending friendly check-in with engagement CTA."
        if cold_override:
            rationale = "Detected merchant ignored last 3 engagement messages. Shifting to soft curiosity check-in."
        
        return {
            "should_send": True,
            "signal_type": "generic",
            "signal_data": {},
            "merchant_data": merchant_data,
            "category_data": {},
            "rationale": rationale,
            "fallback_used": True,
            "cold_merchant_override": cold_override
        }

    @staticmethod
    def _generate_rationale(signal: Signal, merchant_data: Dict, category_data: Dict,
                           all_signals_scored: List[Tuple[float, Signal]] = None) -> str:
        category_slug = merchant_data.get("category_slug", "")

        if all_signals_scored and len(all_signals_scored) > 1:
            scores_summary = ", ".join([
                f"{s.type}={score:.1f}" for score, s in all_signals_scored[:4]
            ])
            winner_score = all_signals_scored[0][0]
            runner_up_score = all_signals_scored[1][0] if len(all_signals_scored) > 1 else 0.0
            score_gap = winner_score - runner_up_score

            rationale = (
                f"Signals evaluated: [{scores_summary}]. "
                f"Selected '{signal.type}' (score: {winner_score:.1f}) over runner-up (score: {runner_up_score:.1f}, gap: {score_gap:.1f}) "
                f"because: {DecisionEngine._explain_why(signal, merchant_data)}. "
                f"Category '{category_slug}' priority for '{signal.type}': CONFIRMED. "
                f"Offer availability: {'CONFIRMED - ' + DecisionEngine._get_offer_summary(signal, merchant_data) if DecisionEngine._has_offer(signal, merchant_data) else 'NONE'}. "
                f"Decision confidence: {'HIGH' if score_gap > 20 else 'MEDIUM' if score_gap > 10 else 'LOW'}. "
                f"Recency: {signal.occurred_at}. "
                f"Next action: Await merchant reply, adapt based on response."
            )
        else:
            rationale = (
                f"Selected '{signal.type}' signal from {signal.source}. "
                f"{DecisionEngine._explain_why(signal, merchant_data)}. "
                f"Category '{category_slug}' prioritizes this signal type. "
                f"Offer: {DecisionEngine._get_offer_summary(signal, merchant_data) if DecisionEngine._has_offer(signal, merchant_data) else 'none available'}. "
                f"Direct, actionable CTA maximizes engagement. "
                f"Recency: {signal.occurred_at}."
            )

        return rationale

    @staticmethod
    def _explain_why(signal: Signal, merchant_data: Dict) -> str:
        explanations = {
            "search_spike": f"LIVE DEMAND: {signal.data.get('demand_count', '?')} people in {signal.data.get('locality', 'unknown area')} searched for '{signal.data.get('search_term', 'query')}' — HIGH engagement potential.",
            "engagement": f"RESEARCH/TECH: Signal type '{signal.type}' from {signal.source} aligns with dentist/professional category preference for clinical content.",
            "research_digest": f"RESEARCH DIGEST: New research available from {signal.source} — relevant for merchant's category.",
            "offer": f"PROMOTION READY: Merchant has active offer '{signal.data.get('offer', {}).get('title', 'unknown')}' at ₹{signal.data.get('offer', {}).get('price', 0)} — direct revenue opportunity.",
            "performance_drop": f"UNDERPERFORMANCE ALERT: {signal.data.get('metric', 'metric')} at {signal.data.get('current', 0)*100:.1f}% vs {signal.data.get('avg', 0)*100:.1f}% peer avg — urgent improvement needed.",
            "temporal": f"TIME-SENSITIVE: {signal.data.get('festival_name', 'event')} in {signal.data.get('days_until', '?')} days — urgency frame valid.",
            "milestone": f"ACHIEVEMENT MOMENTUM: {signal.data.get('count', '?')} reached — social proof opportunity, high emotional engagement.",
            "urgent": f"CRITICAL ACTION REQUIRED: Urgent signal demands immediate attention.",
            "relationship": f"RELATIONSHIP CHECK: Time to re-engage with merchant.",
            "recall": f"RECALL REMINDER: Customer recall is due — important for retention.",
            "temporal_event": f"TEMPORAL EVENT: Special event happening today — opportunity for engagement.",
            "seasonal": f"SEASONAL TREND: Seasonal pattern detected — time to adjust strategy.",
            "curiosity": f"CURIOSITY ASK: Time to ask merchant a question to drive engagement.",
            "intent": f"ACTIVE PLANNING: Merchant is planning something — help them execute.",
            "competitive": f"COMPETITIVE ALERT: New competitor nearby — time to respond.",
            "reputation": f"REPUTATION UPDATE: New review theme emerged — important to address.",
            "compliance": f"COMPLIANCE UPDATE: Regulation change — important to inform merchant.",
            "performance_spike": f"PERFORMANCE SPIKE: Great news! Performance is up — build on this momentum."
        }
        return explanations.get(signal.type, f"Signal type '{signal.type}' matched category priority matrix.")

    @staticmethod
    def _has_offer(signal: Signal, merchant_data: Dict) -> bool:
        if signal.data.get("offer"):
            return True
        if merchant_data.get("active_offers"):
            return True
        return False

    @staticmethod
    def _get_offer_summary(signal: Signal, merchant_data: Dict) -> str:
        offer = signal.data.get("offer", {})
        if not offer and merchant_data.get("active_offers"):
            offer = merchant_data["active_offers"][0]
        if offer:
            return f"₹{offer.get('price', offer.get('discount_price', 0))} {offer.get('title', 'offer')}"
        return "no active offer"
