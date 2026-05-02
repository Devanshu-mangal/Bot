
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC

class Signal:
    def __init__(self, type: str, priority: int, data: Dict[str, Any], source: str, occurred_at: Optional[str] = None):
        self.type = type
        self.priority = priority
        self.data = data
        self.source = source
        self.occurred_at = occurred_at or datetime.now(UTC).isoformat() + "Z"

class SignalCollector:
    BASE_PRIORITIES = {
        "urgent": 100,
        "search_spike": 95,
        "live_demand": 95,
        "competitor_opened": 92,
        "regulation_change": 90,
        "supply_alert": 90,
        "chronic_refill_due": 88,
        "recall_due": 87,
        "bridal_followup": 86,
        "customer_lapsed_soft": 85,
        "performance_drop": 80,
        "perf_dip": 80,
        "milestone_reached": 85,
        "perf_spike": 82,
        "review_theme_emerged": 78,
        "dormant_with_vera": 75,
        "customer_lapsed_hard": 75,
        "ipl_match_today": 72,
        "seasonal_perf_dip": 72,
        "offer": 70,
        "curious_ask_due": 68,
        "offer_available": 70,
        "active_planning_intent": 65,
        "temporal": 60,
        "festival_upcoming": 60,
        "festival": 60,
        "engagement": 90,
        "research_digest": 100,
        "milestone": 85
    }
    
    @staticmethod
    def collect_signals(category: Dict, merchant: Dict, trigger: Dict) -> List[Signal]:
        signals = []
        
        signals.extend(SignalCollector._from_trigger(trigger))
        signals.extend(SignalCollector._from_merchant(merchant))
        signals.extend(SignalCollector._from_category(category, merchant))
        
        return signals
    
    @staticmethod
    def _from_trigger(trigger: Dict) -> List[Signal]:
        signals = []
        trigger_kind = trigger.get("kind", "")
        payload = trigger.get("payload", {})
        occurred_at = trigger.get("occurred_at")
        
        trigger_kind_map = {
            "perf_spike": ("performance_spike", 88),
            "perf_dip": ("performance_drop", 82),
            "milestone_reached": ("milestone", 85),
            "dormant_with_vera": ("relationship", 65),
            "customer_lapsed_soft": ("recall", 80),
            "customer_lapsed_hard": ("recall", 85),
            "ipl_match_today": ("temporal_event", 90),
            "seasonal_perf_dip": ("seasonal", 70),
            "bridal_followup": ("relationship", 82),
            "curious_ask_due": ("curiosity", 60),
            "supply_alert": ("urgent", 100),
            "chronic_refill_due": ("recall", 88),
            "active_planning_intent": ("intent", 95),
            "competitor_opened": ("competitive", 85),
            "review_theme_emerged": ("reputation", 75),
            "regulation_change": ("compliance", 92),
            "festival_upcoming": ("temporal", 88),
            "recall_due": ("recall", 80),
            "research_digest": ("research_digest", 100),
            "festival": ("temporal", 60),
            "holiday": ("temporal", 60),
            "milestone": ("milestone", 85),
            "performance_drop": ("performance_drop", 80),
            "offer_available": ("offer", 70),
            "offer": ("offer", 70),
            "search_spike": ("search_spike", 95)
        }
        
        if trigger_kind in trigger_kind_map:
            signal_type, priority = trigger_kind_map[trigger_kind]
            
            if trigger_kind == "search_spike":
                demand_count = payload.get("search_count") or payload.get("local_searches") or payload.get("demand_count")
                signals.append(Signal(signal_type, priority, {
                    **payload,
                    "demand_count": demand_count,
                    "locality": payload.get("locality") or payload.get("area"),
                    "search_term": payload.get("query") or payload.get("search_term")
                }, "trigger", occurred_at))
            else:
                signals.append(Signal(signal_type, priority, payload, "trigger", occurred_at))

        return signals
    
    @staticmethod
    def _from_merchant(merchant: Dict) -> List[Signal]:
        signals = []
        perf = merchant.get("performance", {})
        offers = merchant.get("offers", [])
        merchant_signals = merchant.get("signals", [])

        active_offers = [o for o in offers if o.get("status") == "active"]
        if active_offers:
            signals.append(Signal("offer", 70, {"offer": active_offers[0]}, "merchant", datetime.now(UTC).isoformat() + "Z"))

        avg_ctr = 0.03
        ctr = perf.get("ctr", 0)
        if ctr < avg_ctr * 0.8:
            signals.append(Signal("performance_drop", 80, {"metric": "ctr", "current": ctr, "avg": avg_ctr}, "merchant", datetime.now(UTC).isoformat() + "Z"))

        return signals

    @staticmethod
    def _from_category(category: Dict, merchant: Dict) -> List[Signal]:
        signals = []

        if category.get("digest"):
            signals.append(Signal("engagement", 90, {"digest_available": True, "digest": category.get("digest", [])}, "category", datetime.now(UTC).isoformat() + "Z"))

        if category.get("tips"):
            signals.append(Signal("engagement", 80, {"tips_available": True}, "category", datetime.now(UTC).isoformat() + "Z"))

        return signals

