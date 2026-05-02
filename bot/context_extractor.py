from typing import Dict, Any, Optional

class ContextExtractor:
    @staticmethod
    def extract_merchant_data(merchant: Dict) -> Dict[str, Any]:
        identity = merchant.get("identity", {})
        perf = merchant.get("performance", {})
        customer_agg = merchant.get("customer_aggregate", {})
        
        return {
            "merchant_id": merchant.get("merchant_id", ""),
            "category_slug": merchant.get("category_slug", ""),
            "name": identity.get("name", "Merchant"),
            "owner_first_name": identity.get("owner_first_name", ""),
            "location": identity.get("locality", identity.get("location", "")),
            "established_year": identity.get("established_year", None),
            "views": perf.get("views", 0),
            "ctr": perf.get("ctr", 0.0),
            "ctr_pct": perf.get("ctr", 0.0) * 100,
            "calls": perf.get("calls", 0),
            "directions": perf.get("directions", 0),
            "footfall": perf.get("footfall", 0),
            "offers": merchant.get("offers", []),
            "active_offers": [o for o in merchant.get("offers", []) if o.get("status") == "active"],
            "metadata": merchant.get("metadata", {}),
            "subscription": merchant.get("subscription", {}),
            "signals": merchant.get("signals", []),
            "derived_signals": merchant.get("signals", []),
            "customer_aggregate": customer_agg,
            "lapsed_customers": customer_agg.get("lapsed_180d_plus", 0),
            "retention_pct": customer_agg.get("retention_6mo_pct", 0),
            "conversation_history": merchant.get("conversation_history", [])
        }
    
    @staticmethod
    def extract_category_data(category: Dict) -> Dict[str, Any]:
        voice = category.get("voice", {})
        return {
            "slug": category.get("slug", ""),
            "tone": voice.get("tone", "neutral"),
            "vocab_allowed": voice.get("vocab_allowed", []),
            "vocab_taboo": voice.get("vocab_taboo", []),
            "salutation_style": voice.get("salutation_examples", ["Hi {name}"])[0],
            "digest": category.get("digest", []),
            "peer_stats": category.get("peer_stats", {}),
            "seasonal_beats": category.get("seasonal_beats", []),
            "trend_signals": category.get("trend_signals", []),
            "voice": voice
        }
    
    @staticmethod
    def extract_trigger_data(trigger: Dict) -> Dict[str, Any]:
        payload = trigger.get("payload", {})
        return {
            "trigger_id": trigger.get("trigger_id", ""),
            "kind": trigger.get("kind", ""),
            "merchant_id": trigger.get("merchant_id", ""),
            "customer_id": trigger.get("customer_id"),
            "payload": payload,
            "occurred_at": trigger.get("occurred_at", ""),
            "suppression_key": trigger.get("suppression_key", "")
        }
    
    @staticmethod
    def get_digest_item(category: Dict, digest_id: str) -> Optional[Dict]:
        for item in category.get("digest", []):
            if item.get("id") == digest_id:
                return item
        return None
    
    @staticmethod
    def validate_data(data: Dict, required_fields: list) -> bool:
        for field in required_fields:
            if data.get(field) in [None, "", 0]:
                return False
        return True
