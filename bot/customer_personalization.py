"""
Customer Personalization Engine: Generates structured personalization object from customer data.
"""
from typing import Dict, Any, Optional


def generate_personalization(customer_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generates a structured personalization object from customer data.
    """
    if not customer_data:
        return {
            "personalization_hooks": {
                "use_name": False,
                "name": "",
                "visit_reference": "",
                "service_relevance": ""
            },
            "behavioral_strategy": "standard",
            "language_style": "en",
            "language_mix": False
        }
    
    identity = customer_data.get("identity", {})
    relationship = customer_data.get("relationship", {})
    state = customer_data.get("state", "active")
    preferences = customer_data.get("preferences", {})
    
    personalization_hooks = _build_personalization_hooks(identity, relationship)
    behavioral_strategy = _determine_behavioral_strategy(state)
    language_style = _determine_language_style(preferences, identity)
    language_mix = "hi" in language_style.lower() or "mix" in language_style.lower()
    
    return {
        "personalization_hooks": personalization_hooks,
        "behavioral_strategy": behavioral_strategy,
        "language_style": language_style,
        "language_mix": language_mix
    }


def _build_personalization_hooks(identity: Dict, relationship: Dict) -> Dict[str, Any]:
    name = identity.get("name", "")
    last_visit = relationship.get("last_visit", "")
    services = relationship.get("services_received", [])
    visits_total = relationship.get("visits_total", 0)
    
    visit_reference = ""
    if last_visit:
        visit_reference = f"last visited on {last_visit}"
    if visits_total > 0:
        if visits_total == 1:
            visit_reference = "first-time patient"
        elif visits_total <= 3:
            visit_reference = f"returning patient ({visits_total} visits)"
        else:
            visit_reference = f"valued patient ({visits_total}+ visits)"
    
    service_relevance = ""
    if services:
        if len(services) == 1:
            service_relevance = f"you previously had {services[0]}"
        else:
            service_relevance = f"you've had services like {', '.join(services[:2])}"
    
    return {
        "use_name": bool(name),
        "name": name,
        "visit_reference": visit_reference,
        "service_relevance": service_relevance
    }


def _determine_behavioral_strategy(state: str) -> str:
    if state == "lapsed_soft":
        return "gentle_reminder"
    elif state == "lapsed_hard":
        return "stronger_incentive"
    elif state == "new":
        return "welcome"
    else:
        return "standard"


def _determine_language_style(preferences: Dict, identity: Dict) -> str:
    pref = preferences.get("preferred_language", "")
    if pref:
        return pref
    lang_pref = identity.get("language_pref", "")
    if lang_pref:
        return lang_pref
    return "en"
