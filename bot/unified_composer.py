"""
Unified Composer: Single compose() function that brings everything together!
Combines: product_intelligence, decision_intelligence, customer_personalization, category_intelligence, and message composition.
"""
from typing import Dict, Any, Optional, List, Tuple
from bot.product_intelligence import extract_insights
from bot.customer_personalization import generate_personalization
from bot.category_intelligence import CategoryIntelligence
from bot.insights_to_whatsapp import compose_whatsapp_message


def compose(
    merchant_data: Dict[str, Any],
    category_data: Dict[str, Any],
    trigger_data: Dict[str, Any],
    customer_data: Optional[Dict[str, Any]] = None,
    ranked_signals: Optional[List[Tuple[float, Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    Unified compose function!
    
    Steps:
    1. Extract insights from data
    2. Generate customer personalization if applicable
    3. Compose final WhatsApp message
    
    Returns:
        Composed message with all metadata!
    """
    category_slug = merchant_data.get("category_slug", category_data.get("slug", "dentists"))
    
    # Step 1: Extract insights
    insights = extract_insights(
        merchant_data=merchant_data,
        category_data=category_data,
        trigger_data=trigger_data,
        customer_data=customer_data,
    )
    
    # Step 2: Generate customer personalization
    customer_personalization = generate_personalization(customer_data)
    
    # Step 3: Get category config
    category_config = CategoryIntelligence.get_config(category_slug)
    category_voice = {
        "slug": category_slug,
        "tone": category_config.get("tone", "friendly"),
    }
    
    # Step 4: Prepare inputs for message composition
    merchant_identity = merchant_data.get("identity", {})
    merchant_summary = merchant_identity.get("name", "Merchant")
    
    trigger_kind = trigger_data.get("kind", trigger_data.get("type", "generic"))
    trigger_reason = _build_trigger_reason(trigger_kind, trigger_data)
    
    # Step 5: Compose message
    body = compose_whatsapp_message(
        insights=insights,
        merchant_summary=merchant_summary,
        trigger_reason=trigger_reason,
        category_voice=category_voice,
    )
    
    # Step 5a: Inject customer personalization
    if customer_personalization:
        hooks = customer_personalization.get("personalization_hooks", {})
        if hooks.get("use_name") and hooks.get("name"):
            name = hooks["name"].split()[0]
            # Only replace "Hi" at the start of the message
            if body.startswith("Hi"):
                body = body.replace("Hi", f"Hi {name},", 1)
        if hooks.get("visit_reference"):
            # Integrate visit reference naturally based on context
            visit_ref = hooks['visit_reference']
            if "first-time" in visit_ref:
                # For new patients, acknowledge their first visit
                body = body.replace("Hi", "Welcome! Hi", 1)
            elif "returning" in visit_ref or "valued" in visit_ref:
                # For returning patients, integrate naturally
                sentences = body.split("\n\n")
                if len(sentences) > 1:
                    # Insert after first sentence with personalization reference
                    sentences[1] = f"As a {visit_ref}, you're a key part of our practice family. " + sentences[1]
                    body = "\n\n".join(sentences)
            body = body.strip()
    
    # Step 6: Determine CTA and send_as
    cta = _determine_cta(trigger_kind, category_slug, customer_data)
    send_as = _determine_send_as(customer_data)
    suppression_key = trigger_data.get("suppression_key", f"{category_slug}:{trigger_kind}")
    
    # Step 7: Build rationale
    rationale = _build_rationale(
        insights=insights,
        customer_personalization=customer_personalization,
        category_slug=category_slug,
        trigger_kind=trigger_kind,
    )
    
    return {
        "body": body,
        "cta": cta,
        "send_as": send_as,
        "suppression_key": suppression_key,
        "rationale": rationale,
        "insights": insights,
        "customer_personalization": customer_personalization,
    }


def _build_trigger_reason(trigger_kind: str, trigger_data: Dict) -> str:
    if trigger_kind == "research_digest":
        return "JIDA's latest research digest has landed"
    elif trigger_kind == "perf_dip" or trigger_kind == "performance_drop":
        return "I noticed a performance dip recently"
    elif trigger_kind == "festival_upcoming" or trigger_kind == "festival":
        festival = trigger_data.get("payload", {}).get("festival", "the upcoming festival")
        return f"{festival} is coming up soon"
    elif trigger_kind == "recall_due":
        return "patient recall time"
    elif trigger_kind == "chronic_refill_due":
        return "medication refill is due"
    else:
        return "quick update about your business"


def _determine_cta(trigger_kind: str, category_slug: str, customer_data: Optional[Dict]) -> str:
    if customer_data:
        return "open_ended"
    if category_slug == "dentists" and trigger_kind == "research_digest":
        return "open_ended"
    return "binary_yes_no"


def _determine_send_as(customer_data: Optional[Dict]) -> str:
    if customer_data:
        return "merchant_on_behalf"
    return "vera"


def _build_rationale(
    insights: Dict,
    customer_personalization: Dict,
    category_slug: str,
    trigger_kind: str,
) -> str:
    parts = []
    if insights.get("urgency_insights"):
        parts.append(insights["urgency_insights"])
    if insights.get("opportunity_insights"):
        parts.append(insights["opportunity_insights"][0])
    if customer_personalization.get("personalization_hooks", {}).get("use_name"):
        parts.append(f"Personalized for {customer_personalization['personalization_hooks']['name']}")
    
    return " ".join(parts) if parts else f"Composed message for {category_slug} merchant with {trigger_kind} trigger"
