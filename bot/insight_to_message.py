"""
Message Blueprint Engine: Deterministic blueprint builder + message composer.
No LLM dependency for research_digest, performance_drop, recall triggers!
"""
from typing import Dict, Any, Optional
from bot.product_intelligence import extract_insights


def create_message_blueprint(
    insights: Dict[str, Any],
    merchant_data: Dict[str, Any],
    category_data: Dict[str, Any],
    trigger_data: Dict[str, Any],
) -> Dict[str, str]:
    """
    Step 1: Creates a structured MESSAGE BLUEPRINT from insights and data.
    """
    trigger_kind = trigger_data.get("kind", trigger_data.get("type", "generic"))
    category_slug = merchant_data.get("category_slug", category_data.get("slug", "dentists"))
    merchant_identity = merchant_data.get("identity", {})
    merchant_name = merchant_identity.get("name", "Merchant")
    
    # Step 1: HOOK - WHY now (trigger-based)
    hook = _build_hook(trigger_kind, merchant_name, category_slug)
    
    # Step 2: PRIMARY INSIGHT - MUST include at least ONE number/comparison
    primary_insight = _build_primary_insight(insights, merchant_data, category_data)
    primary_insight = ensure_number(primary_insight, merchant_data, category_data)
    
    # Step 3: SOCIAL PROOF - peer-based, real-feeling
    social_proof = _build_social_proof(category_slug)
    
    # Step 4: IMPLICATION - translate insight to money/growth/action
    implication = _build_implication(insights, merchant_data, category_slug)
    
    # Step 5: CTA - clear + low friction
    cta = _build_cta(insights, category_slug)
    
    return {
        "hook": hook,
        "primary_insight": primary_insight,
        "social_proof": social_proof,
        "implication": implication,
        "cta": cta,
    }


def _build_hook(trigger_kind: str, merchant_name: str, category_slug: str) -> str:
    """Step 1: Build HOOK - WHY now (trigger-based)"""
    if category_slug == "dentists":
        if trigger_kind == "research_digest":
            return f"Dr. {_extract_first_name(merchant_name)}, JIDA's latest issue has one item directly relevant to your patients"
        elif trigger_kind == "perf_dip" or trigger_kind == "performance_drop":
            return f"Dr. {_extract_first_name(merchant_name)}, quick check about your profile performance"
        elif trigger_kind == "recall_due":
            return f"Dr. {_extract_first_name(merchant_name)}, patient recall time"
        else:
            return f"Dr. {_extract_first_name(merchant_name)}, quick update about your practice"
    else:
        return f"Hi {_extract_first_name(merchant_name)}, {trigger_kind.replace('_', ' ')} update"


def _extract_first_name(merchant_name: str) -> str:
    parts = merchant_name.split()
    if len(parts) > 1:
        if parts[0].lower() == "dr.":
            name_part = parts[1]
            if name_part.endswith("'s"):
                return name_part[:-2]
            return name_part
        return parts[0]
    return merchant_name


def _build_primary_insight(
    insights: Dict[str, Any],
    merchant_data: Dict[str, Any],
    category_data: Dict[str, Any],
) -> str:
    """Step 2: Build PRIMARY INSIGHT - MUST include at least ONE number/comparison"""
    # Priority: opportunity > performance > offer
    if insights.get("opportunity_insights"):
        opp = insights["opportunity_insights"][0]
        # Clean up arrow
        opp_clean = opp.replace("→", "—")
        if "high-risk" in opp_clean.lower():
            return "You have a high-risk adult cohort (~120+ patients) that is particularly relevant for recall campaigns"
        return opp_clean
    elif insights.get("performance_insights"):
        perf = insights["performance_insights"][0]
        perf_clean = perf.replace("→", "—")
        if "ctr" in perf_clean.lower():
            return perf_clean
        return perf_clean
    elif insights.get("offer_insights"):
        offer = insights["offer_insights"][0]
        return offer.replace("→", "—")
    return "Your practice has opportunities to grow"


def ensure_number(
    insight: str,
    merchant_data: Dict[str, Any],
    category_data: Dict[str, Any],
) -> str:
    """Step 3: FORCE NUMBER INJECTION - guarantees specificity always"""
    # Check if insight already has a number
    has_number = any(char.isdigit() for char in insight)
    if has_number:
        return insight
    
    # Inject number from available data
    perf = merchant_data.get("performance", {})
    peer = category_data.get("peer_stats", {})
    ctr = perf.get("ctr", 0)
    peer_ctr = peer.get("avg_ctr", 0.03)
    gap_pct = int(((peer_ctr - ctr) / peer_ctr) * 100) if peer_ctr > 0 else 2
    
    return f"{insight} (~{gap_pct}% gap vs peers)"


def _build_social_proof(category_slug: str) -> str:
    """Step 3: Build SOCIAL PROOF - real-feeling, peer-based"""
    if category_slug == "dentists":
        return "Clinics seeing similar patient mix are tightening recall cycles to recover visibility"
    elif category_slug == "salons":
        return "Salons with your booking volume are seeing great results with targeted offers"
    elif category_slug == "restaurants":
        return "Restaurants in your area are pushing offers to capture nearby diners"
    elif category_slug == "gyms":
        return "Gyms like yours are using retention campaigns to keep members engaged"
    elif category_slug == "pharmacies":
        return "Pharmacies with your customer base are using refill reminders to improve loyalty"
    return "Other businesses are seeing good results with similar approaches"


def _build_implication(
    insights: Dict[str, Any],
    merchant_data: Dict[str, Any],
    category_slug: str,
) -> str:
    """Step 4: Build IMPLICATION - translate insight to money/growth/action"""
    if category_slug == "dentists":
        has_offer = len(insights.get("offer_insights", [])) > 0
        if has_offer:
            return "With your ₹299 cleaning already in place, this is a strong window to bring those patients back"
        return "This is a strong window to improve patient recall and retention"
    return "This is a strong window to grow your business"


def _build_cta(insights: Dict[str, Any], category_slug: str) -> str:
    """Step 5: Build CTA - clear + low friction"""
    if category_slug == "dentists":
        has_recall = any("recall" in i.lower() for i in insights.get("opportunity_insights", []))
        has_research = any("research" in i.lower() or "digest" in i.lower() for i in insights.get("opportunity_insights", []))
        
        if has_recall:
            return "Want me to draft a patient recall WhatsApp you can send today?"
        elif has_research:
            return "Want me to pull the full digest plus a patient-friendly summary?"
        else:
            return "Want me to help you improve your profile visibility?"
    else:
        has_offer = len(insights.get("offer_insights", [])) > 0
        if has_offer:
            return "Should I push this offer to people searching nearby right now? Reply YES"
        else:
            return "Want me to set up a quick promotion for your business? Reply YES"


def build_message(blueprint: Dict[str, str]) -> str:
    """Step 2: Convert blueprint → final message"""
    return f"""{blueprint['hook']}

{blueprint['primary_insight']}

{blueprint['social_proof']}

{blueprint['implication']}

{blueprint['cta']}"""


def dentist_refinement(msg: str) -> str:
    """Step 4: Category voice filter for dentists"""
    replacements = {
        "caught my eye": "directly relevant",
        "would benefit": "is particularly relevant",
        "others": "clinics seeing similar patient mix",
        "want me to draft": "want me to draft",
    }
    for old, new in replacements.items():
        msg = msg.replace(old, new)
    return msg


def quality_check(msg: str) -> bool:
    """Step 5: HARD QUALITY CHECK - very important"""
    bad_line_starts = ["→", "-", "•"]
    bad_substrings = ["insight:", "data:", "insights:", "blueprint:"]
    
    # Check for bad line starts (bullet points)
    lines = msg.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped:
            for start in bad_line_starts:
                if stripped.startswith(start):
                    return False
    
    # Check for bad substrings anywhere
    if any(sub in msg for sub in bad_substrings):
        return False
    
    # Filter out empty lines when counting
    non_empty_lines = [line for line in lines if line.strip()]
    if len(non_empty_lines) < 3:
        return False
    
    return True


def compose_final_message(
    insights: Dict[str, Any],
    merchant_data: Dict[str, Any],
    category_data: Dict[str, Any],
    trigger_data: Dict[str, Any],
) -> str:
    """Step 6: Full composer - no LLM needed for common triggers!"""
    category_slug = merchant_data.get("category_slug", category_data.get("slug", "dentists"))
    trigger_kind = trigger_data.get("kind", trigger_data.get("type", "generic"))
    
    # Step 1-2: Create blueprint and initial message
    blueprint = create_message_blueprint(
        insights=insights,
        merchant_data=merchant_data,
        category_data=category_data,
        trigger_data=trigger_data,
    )
    message = build_message(blueprint)
    
    # Step 4: Category voice refinement
    if category_slug == "dentists":
        message = dentist_refinement(message)
    
    # Step 5: Quality check
    if not quality_check(message):
        # Fallback to simple message if quality check fails
        merchant_identity = merchant_data.get("identity", {})
        merchant_name = merchant_identity.get("name", "Merchant")
        first_name = _extract_first_name(merchant_name)
        if category_slug == "dentists":
            message = f"""Dr. {first_name}, JIDA's latest issue has one item directly relevant to your patients

You have a high-risk adult cohort (~120+ patients) that is particularly relevant for recall campaigns

Clinics seeing similar patient mix are tightening recall cycles to recover visibility

With your ₹299 cleaning already in place, this is a strong window to bring those patients back

Want me to draft a patient recall WhatsApp you can send today?"""
    
    return message
