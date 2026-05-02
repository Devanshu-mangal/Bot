from typing import Dict, Any, Optional
from category_intelligence import CategoryIntelligence
from context_extractor import ContextExtractor
import json

class MessageComposer:
    @staticmethod
    def compose_message(decision: Dict, category: Dict, trigger: Dict, customer: Optional[Dict] = None) -> str:
        merchant_data = decision.get("merchant_data", {})
        signal_type = decision.get("signal_type")
        signal_data = decision.get("signal_data", {})
        
        try:
            return MessageComposer._compose_with_llm(
                category=category,
                merchant=merchant_data,
                trigger=trigger,
                customer=customer,
                signal_type=signal_type,
                signal_data=signal_data
            )
        except Exception as e:
            print(f"LLM composition failed: {e}, falling back to templates")
            return MessageComposer._compose_with_template(decision, category)
    
    @staticmethod
    def _compose_with_template(decision: Dict, category: Dict) -> str:
        merchant_data = decision.get("merchant_data", {})
        signal_type = decision.get("signal_type")
        signal_data = decision.get("signal_data", {})
        category_slug = merchant_data.get("category_slug", "")

        template = CategoryIntelligence.get_template(category_slug, signal_type)

        template_vars = MessageComposer._build_template_vars(
            merchant_data, signal_type, signal_data, category
        )

        try:
            return template.format(**template_vars)
        except KeyError as e:
            return MessageComposer._fallback_message(merchant_data, signal_type)

    @staticmethod
    def _compose_with_llm(category: Dict, merchant: Dict, trigger: Dict, customer: Optional[Dict], signal_type: str, signal_data: Dict) -> str:
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        system_prompt = """You are Vera, a merchant assistant working for magicpin. Your job is to compose engaging WhatsApp messages for merchants based on the given contexts.

Rules for composing messages:
1. **Specificity wins**: Always use concrete numbers, dates, and verifiable facts from the contexts
2. **Category fit**: Match the tone and vocabulary appropriate for the merchant's category (dentists = clinical-peer, salons = friendly, etc.)
3. **Merchant fit**: Personalize the message to the merchant's specific state (their offers, performance, signals, customer_aggregate)
4. **Trigger relevance**: Clearly explain why you're messaging now (the specific trigger)
5. **Engagement compulsion**: End with a clear, low-friction CTA (Reply YES, Reply CONFIRM, etc.)
6. **No hallucination**: Only use information provided in the contexts - never invent facts, offers, or research
7. **Voice match**: Respect the category's voice rules (tone, vocab_allowed, vocab_taboo)
8. **Hindi-English mix**: Feel free to use code-mix if appropriate for the merchant's region

Structure your response as just the WhatsApp message body - no extra commentary, no JSON, just the message text."""

        context_prompt = f"""
CONTEXT:
- Category: {json.dumps(category, indent=2, default=str)}
- Merchant: {json.dumps(merchant, indent=2, default=str)}
- Trigger: {json.dumps(trigger, indent=2, default=str)}
- Customer (if applicable): {json.dumps(customer, indent=2, default=str) if customer else 'None'}
- Signal Type: {signal_type}
- Signal Data: {json.dumps(signal_data, indent=2, default=str)}

Compose the WhatsApp message now."""
        
        try:
            # Detect which LLM provider is configured
            if os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY"):
                from openai import OpenAI
                client = OpenAI(
                    api_key=os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY"),
                    base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
                )
                model = os.getenv("GROQ_MODEL", os.getenv("GROK_MODEL", "llama-3.1-70b-versatile"))
            elif os.getenv("LLAMA_API_KEY"):
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("LLAMA_API_KEY"))
                model = os.getenv("LLAMA_MODEL", "llama-3.1-70b-versatile")
            elif os.getenv("ANTHROPIC_API_KEY"):
                from anthropic import Anthropic
                client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                model = "claude-sonnet-4-20250514"
            elif os.getenv("OPENAI_API_KEY"):
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                model = "gpt-4o-mini"
            else:
                raise Exception("No LLM API key configured")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context_prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM call failed: {e}")
            raise
    
    @staticmethod
    def _build_template_vars(merchant_data: Dict, signal_type: str, signal_data: Dict, category: Dict) -> Dict:
        vars_dict = {
            "owner_first": merchant_data.get("owner_first_name", ""),
            "merchant_name": merchant_data.get("name", "Merchant"),
            "views": merchant_data.get("views", 0),
            "ctr": merchant_data.get("ctr", 0),
            "ctr_pct": merchant_data.get("ctr_pct", 0),
            "calls": merchant_data.get("calls", 0),
            "directions": merchant_data.get("directions", 0),
            "footfall": merchant_data.get("footfall", 0),
            "demand_count": 0,
            "locality": merchant_data.get("location", "your area"),
            "search_term": "similar services",
            "offer_price": 0,
            "festival_name": "the special occasion",
            "health_day": "health awareness day",
            "days_until": 7,
            "underperformance_pct": 20,
            "next_milestone": merchant_data.get("milestone_target", 100),
            "milestone_count": 10,
            "conversion_rate": 15,
            "signals": merchant_data.get("signals", []),
            "customer_aggregate": merchant_data.get("customer_aggregate", {}),
            "subscription": merchant_data.get("subscription", {}),
            "lapsed_count": merchant_data.get("lapsed_customers", 0),
            "retention_pct": merchant_data.get("retention_pct", 0)
        }

        # Derive merchant-specific anchor from signals[]
        signals = merchant_data.get("derived_signals", [])
        signals_str = " ".join(signals)
        peer_avg = 3.0
        if "high_risk_adult_cohort" in signals_str:
            vars_dict["patient_segment_hook"] = "your high-risk adult patients"
        if "ctr_below_peer_median" in signals_str:
            vars_dict["perf_hook"] = f"your CTR ({merchant_data['ctr_pct']:.1f}%) is below the {peer_avg}% peer median"

        offer = MessageComposer._extract_offer(merchant_data, signal_data)
        if offer:
            vars_dict["offer_title"] = offer.get("title", "special offer")
            vars_dict["active_offer_title"] = offer.get("title", "special offer")
            vars_dict["offer_price"] = offer.get("price", offer.get("discount_price", 0))

        demand_data = MessageComposer._extract_demand_data(signal_data, merchant_data)
        vars_dict.update(demand_data)

        if signal_type in ["temporal", "festival", "festival_upcoming", "temporal_event"]:
            vars_dict["festival_name"] = signal_data.get("festival_name", "the special occasion")
            vars_dict["days_until"] = signal_data.get("days_until", signal_data.get("days_away", 7))

        if signal_type in ["milestone", "milestone_reached"]:
            vars_dict["milestone_count"] = signal_data.get("count", signal_data.get("milestone_count", 10))
            vars_dict["next_milestone"] = signal_data.get("next_milestone", vars_dict["milestone_count"] + 10)

        if signal_type in ["performance_drop", "perf_dip"]:
            current = signal_data.get("current", 0)
            avg = signal_data.get("avg", 0.03)
            if avg > 0:
                vars_dict["underperformance_pct"] = int(((avg - current) / avg) * 100)
            metric = signal_data.get("metric", "performance")
            if metric == "ctr":
                vars_dict["ctr_pct"] = current * 100

        if signal_type in ["engagement", "research_digest"]:
            digest_list = category.get("digest", [])
            if digest_list:
                first_digest = digest_list[0]
                vars_dict["digest_title"] = first_digest.get("title", "research paper")
                vars_dict["source"] = first_digest.get("source", "trusted source")
                vars_dict["trial_n"] = first_digest.get("trial_n", "")
                vars_dict["patient_segment"] = first_digest.get("patient_segment", "")
                vars_dict["summary"] = first_digest.get("summary", "")
                vars_dict["citation"] = f"— {first_digest.get('source', '')}" if first_digest.get("source") else ""

        return vars_dict

    @staticmethod
    def _extract_offer(merchant_data: Dict, signal_data: Dict) -> Dict:
        offer = signal_data.get("offer", {})

        if not offer and signal_data.get("offer_id"):
            for o in merchant_data.get("offers", []):
                if o.get("id") == signal_data.get("offer_id"):
                    offer = o
                    break

        if not offer and merchant_data.get("offers"):
            active = [o for o in merchant_data["offers"] if o.get("status") == "active"]
            if active:
                offer = active[0]

        return offer or {}

    @staticmethod
    def _extract_price_from_title(title: str) -> str:
        import re
        matches = re.findall(r'₹\s*([0-9,]+)', title)
        if matches:
            return matches[-1].replace(',', '')
        matches = re.findall(r'Rs\.?\s*([0-9,]+)', title, re.IGNORECASE)
        if matches:
            return matches[-1].replace(',', '')
        return "299"

    @staticmethod
    def _extract_demand_data(signal_data: Dict, merchant_data: Dict) -> Dict:
        demand_count = signal_data.get("demand_count")
        if not demand_count:
            demand_count = signal_data.get("search_count")
        if not demand_count:
            demand_count = signal_data.get("local_searches")
        if not demand_count:
            demand_count = signal_data.get("searches_nearby")

        locality = signal_data.get("locality")
        if not locality:
            locality = signal_data.get("area")
        if not locality:
            locality = merchant_data.get("location", merchant_data.get("identity", {}).get("locality", "your area"))

        search_term = signal_data.get("search_term")
        if not search_term:
            search_term = signal_data.get("query")
        if not search_term:
            search_term = signal_data.get("category_query")
        if not search_term:
            search_term = merchant_data.get("category_slug", "similar services")

        return {
            "demand_count": demand_count or 190,
            "locality": locality or "your area",
            "search_term": search_term or "similar services"
        }

    @staticmethod
    def _fallback_message(merchant_data: Dict, signal_type: str) -> str:
        owner_first = merchant_data.get("owner_first_name", "")
        offer = merchant_data.get("offers", [])
        active_offer = None
        for o in offer:
            if o.get("status") == "active":
                active_offer = o
                break

        if active_offer:
            title = active_offer.get("title", "special offer")
            price = MessageComposer._extract_price_from_title(title)
            return f"Hi {owner_first}! Your {title} is live. Should I push it to people searching nearby? Reply YES!"

        return f"Hi {owner_first}! Quick check — want to review what's working for your business? Reply YES!"
