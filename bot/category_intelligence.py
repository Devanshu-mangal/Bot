"""
Category Intelligence Engine: Enhanced category configuration with persuasion rules, social proof templates, vocabulary enforcement, and tone constraints.
"""
from typing import Dict, Any


class CategoryIntelligence:
    CATEGORY_CONFIGS = {
        "dentists": {
            "tone": "peer_clinical",
            "strategy": "lead_with_science",
            "key_signals": ["research_digest", "search_spike", "offer", "performance_drop"],
            "avoid_signals": ["generic_promotion"],
            "persuasion_rules": {
                "primary": "evidence + credibility",
                "what_works": [
                    "cite research sources (JIDA, DCI, etc.)",
                    "use trial numbers (n=2100)",
                    "emphasize patient outcomes",
                    "avoid hype or exaggeration"
                ],
                "what_to_avoid": [
                    "guarantees",
                    "miracle claims",
                    "hard-sell tactics"
                ]
            },
            "social_proof_templates": [
                "Other dental practices in your area are using similar insights to improve patient recall.",
                "Top 10% of dental practices in your locality are seeing significantly better retention with proactive recall campaigns.",
                "High-performing practices in your network leverage patient insights to strengthen their positioning."
            ],
            "vocabulary_enforcement": {
                "allowed": [
                    "fluoride varnish", "caries", "recall", "clinical", "evidence-based",
                    "JIDA", "DCI", "dental", "patient", "treatment", "consultation"
                ],
                "taboo": [
                    "guaranteed", "100% safe", "completely cure", "miracle", "best in city",
                    "cure", "guarantee"
                ]
            },
            "tone_constraints": {
                "sentence_style": "concise, factual",
                "use_contractions": False,
                "use_emoji": False,
                "formality_level": "professional but approachable"
            },
            "templates": {
                "search_spike": "Dr. {owner_first}, {demand_count} people in {locality} searched for '{search_term}' today. Your {offer_title} matches exactly what they want — should I send it to them? Reply YES.",
                "engagement": "Dr. {owner_first}, new research: \"{digest_title}\" from {source}. Should I draft a patient-friendly WhatsApp about this for you to share? Reply YES.",
                "research_digest": "Dr. {owner_first}, new research: \"{digest_title}\" from {source}. Should I draft a patient-friendly WhatsApp about this for you to share? Reply YES.",
                "offer": "Dr. {owner_first}, your {offer_title} is live. {demand_count} people nearby are searching for '{search_term}' — should I push this offer to them now? Reply YES.",
                "performance_drop": "Dr. {owner_first}, your CTR is {ctr_pct:.1f}%, which is {underperformance_pct:.0f}% below what high-performing practices in your area are achieving. Want me to send you 3 proven tactics to improve? Reply YES.",
                "perf_dip": "Dr. {owner_first}, your CTR is {ctr_pct:.1f}%, and there's a clear opportunity to improve. Top practices in your network are implementing targeted recall strategies. Want insights? Reply YES.",

                "temporal": "Dr. {owner_first}, {festival_name} is in {days_until} days — {demand_count} people locally searched for '{search_term}' recently. Your {offer_title} is perfectly timed. Should I push it? Reply YES.",
                "festival": "Dr. {owner_first}, {festival_name} is in {days_until} days — {demand_count} people locally searched for '{search_term}' recently. Your {offer_title} is perfectly timed. Should I push it? Reply YES.",
                "festival_upcoming": "Dr. {owner_first}, {festival_name} is in {days_until} days — {demand_count} people locally searched for '{search_term}' recently. Your {offer_title} is perfectly timed. Should I push it? Reply YES.",
                "milestone": "Dr. {owner_first}! Congratulations on reaching {milestone_count}! Want me to feature this achievement? Reply YES.",
                "milestone_reached": "Dr. {owner_first}! Congratulations on reaching {milestone_count}! Want me to feature this achievement? Reply YES.",
                "perf_spike": "Dr. {owner_first}! Great news — your performance is up! Want me to share insights? Reply YES.",
                "recall_due": "Dr. {owner_first}, patient recall is due. Want me to draft reminder messages? Reply YES.",
                "bridal_followup": "Dr. {owner_first}, bridal follow-up window open. Want me to help? Reply YES.",
                "curious_ask_due": "Dr. {owner_first}, quick check — what's your most asked service this week? Reply YES to share.",
                "supply_alert": "Dr. {owner_first}, supply alert received. Want me to help? Reply YES.",
                "chronic_refill_due": "Dr. {owner_first}, chronic refills due. Want me to draft reminders? Reply YES.",
                "active_planning_intent": "Dr. {owner_first}, let's plan together. What would you like to do? Reply YES to discuss.",
                "competitor_opened": "Dr. {owner_first}, a new competitor opened nearby. Want me to share insights? Reply YES.",
                "review_theme_emerged": "Dr. {owner_first}, a new review theme emerged. Want me to share details? Reply YES.",
                "regulation_change": "Dr. {owner_first}, regulation change update. Want me to share details? Reply YES.",
                "dormant_with_vera": "Dr. {owner_first}, it's been a while. Want to check in? Reply YES.",
                "customer_lapsed_soft": "Dr. {owner_first}, some patients are lapsing. Want me to draft winback messages? Reply YES.",
                "customer_lapsed_hard": "Dr. {owner_first}, some patients haven't been in a while. Want me to help? Reply YES.",
                "ipl_match_today": "Dr. {owner_first}, IPL match today. Want to discuss promotions? Reply YES.",
                "seasonal_perf_dip": "Dr. {owner_first}, seasonal performance dip expected. Want to plan? Reply YES."
            }
        },
        "salons": {
            "tone": "warm_aspirational",
            "strategy": "lead_with_occasion",
            "key_signals": ["temporal", "search_spike", "offer", "engagement"],
            "avoid_signals": ["technical_content"],
            "persuasion_rules": {
                "primary": "occasion + urgency",
                "what_works": [
                    "tie to upcoming events/festivals",
                    "create FOMO (limited time, limited slots)",
                    "use aspirational language",
                    "highlight occasion-specific services"
                ],
                "what_to_avoid": [
                    "technical jargon",
                    "overly clinical descriptions"
                ]
            },
            "social_proof_templates": [
                "Salons nearby are seeing 15-20% more bookings with targeted offers right now.",
                "Top salons in your area are fully booked 3 days in advance for festive season.",
                "Other stylists are using occasion-based campaigns to drive walk-ins."
            ],
            "vocabulary_enforcement": {
                "allowed": [
                    "makeover", "bridal", "party", "festival", "haircut", "color", "facial",
                    "threading", "waxing", "spa", "relax", "glow"
                ],
                "taboo": [
                    "guaranteed", "miracle", "100% results", "permanent"
                ]
            },
            "tone_constraints": {
                "sentence_style": "friendly, energetic",
                "use_contractions": True,
                "use_emoji": True,
                "formality_level": "casual and warm"
            },
            "templates": {
                "search_spike": "Hi {owner_first}! {demand_count} people near {locality} searched for '{search_term}' this week. Your {offer_title} is one of the best-priced — should I send it to them now? Reply YES!",
                "temporal": "Hi {owner_first}! {festival_name} is in {days_until} days — {demand_count} people near {locality} are already searching for '{search_term}'. Your {offer_title} deal is perfectly priced. Want me to push it? Reply YES!",
                "festival": "Hi {owner_first}! {festival_name} is in {days_until} days — {demand_count} people near {locality} are already searching for '{search_term}'. Your {offer_title} deal is perfectly priced. Want me to push it? Reply YES!",
                "festival_upcoming": "Hi {owner_first}! {festival_name} is in {days_until} days — {demand_count} people near {locality} are already searching for '{search_term}'. Your {offer_title} deal is perfectly priced. Want me to push it? Reply YES!",
                "offer": "Hi {owner_first}! Your {offer_title} is live. {demand_count} people searched for '{search_term}' in {locality} recently. Should I send your deal to them? Reply YES!",
                "engagement": "Hi {owner_first}! You had {views} views last month. Adding an offer like {offer_title} could double that. Want me to create one for you? Reply YES!",
                "research_digest": "Hi {owner_first}! New trends available. Want me to share? Reply YES!",
                "performance_drop": "Hi {owner_first}! Your views dropped {underperformance_pct:.0f}% this month. Your {offer_title} could reverse that. Want me to push it to {demand_count} people searching in {locality}? Reply YES!",
                "perf_dip": "Hi {owner_first}! Your views dropped {underperformance_pct:.0f}% this month. Your {offer_title} could reverse that. Want me to push it to {demand_count} people searching in {locality}? Reply YES!",
                "milestone": "Hi {owner_first}! Congratulations on {milestone_count}! Want to celebrate? Reply YES!",
                "milestone_reached": "Hi {owner_first}! Congratulations on {milestone_count}! Want to celebrate? Reply YES!",
                "perf_spike": "Hi {owner_first}! Great news — your performance is up! Want to capitalize? Reply YES.",
                "recall_due": "Hi {owner_first}, client recall due. Want me to help? Reply YES.",
                "bridal_followup": "Hi {owner_first}, bridal follow-up time! Want me to draft messages? Reply YES.",
                "curious_ask_due": "Hi {owner_first}, quick check — what's your most popular service? Reply YES to share.",
                "supply_alert": "Hi {owner_first}, supply alert received. Want me to help? Reply YES.",
                "chronic_refill_due": "Hi {owner_first}, refills due. Want me to help? Reply YES.",
                "active_planning_intent": "Hi {owner_first}, let's plan together! What's your goal? Reply YES to discuss.",
                "competitor_opened": "Hi {owner_first}, new salon opened nearby. Want insights? Reply YES.",
                "review_theme_emerged": "Hi {owner_first}, new review theme! Want details? Reply YES.",
                "regulation_change": "Hi {owner_first}, regulation update. Want to know more? Reply YES.",
                "dormant_with_vera": "Hi {owner_first}, it's been a while! Want to catch up? Reply YES.",
                "customer_lapsed_soft": "Hi {owner_first}, some clients haven't been in. Want to reach out? Reply YES.",
                "customer_lapsed_hard": "Hi {owner_first}, some clients are inactive. Want to help? Reply YES.",
                "ipl_match_today": "Hi {owner_first}, IPL match today! Want to plan promotions? Reply YES.",
                "seasonal_perf_dip": "Hi {owner_first}, seasonal dip coming. Want to plan? Reply YES."
            }
        },
        "restaurants": {
            "tone": "warm_busy_practical",
            "strategy": "lead_with_meal_time",
            "key_signals": ["temporal", "search_spike", "offer", "performance_drop"],
            "avoid_signals": ["long_form"],
            "persuasion_rules": {
                "primary": "practical + revenue-focused",
                "what_works": [
                    "tie to meal times (lunch, dinner, weekend)",
                    "highlight immediate revenue impact",
                    "keep messages short and actionable",
                    "use combo offers (meal + drink)"
                ],
                "what_to_avoid": [
                    "long preambles",
                    "overly formal language"
                ]
            },
            "social_proof_templates": [
                "Restaurants in your locality are pushing offers to capture nearby diners.",
                "Top spots are seeing 30% more orders with time-limited lunch combos.",
                "Other restaurateurs are using nearby search pushes to fill empty tables."
            ],
            "vocabulary_enforcement": {
                "allowed": [
                    "combo", "lunch", "dinner", "weekend", "delivery", "dine-in", "takeaway",
                    "biryani", "pizza", "burger", "discount", "offer", "menu"
                ],
                "taboo": [
                    "guaranteed packed house", "miracle marketing"
                ]
            },
            "tone_constraints": {
                "sentence_style": "snappy, practical",
                "use_contractions": True,
                "use_emoji": False,
                "formality_level": "practical and to-the-point"
            },
            "templates": {
                "search_spike": "Hi {owner_first}! {demand_count} people near {locality} searched for '{search_term}' today. Your {offer_title} is exactly what they want. Should I send it to them now? Reply YES!",
                "temporal": "Hi {owner_first}! Lunch rush in {locality} starts at 12:30 — {demand_count} people are searching for '{search_term}'. Your {offer_title} is perfectly timed. Should I push it before noon? Reply YES!",
                "festival": "Hi {owner_first}! {festival_name} is coming up! Want to plan promotions? Reply YES!",
                "festival_upcoming": "Hi {owner_first}! {festival_name} is coming up! Want to plan promotions? Reply YES!",
                "offer": "Hi {owner_first}! Your {offer_title} is live. {demand_count} people in {locality} searched for '{search_term}' this week. Want me to send your deal to them? Reply YES!",
                "milestone": "Hi {owner_first}! Congratulations on {milestone_count} orders this month. Your {offer_title} could push you to {next_milestone}. Want me to promote it? Reply YES.",
                "milestone_reached": "Hi {owner_first}! Congratulations on {milestone_count} orders this month. Your {offer_title} could push you to {next_milestone}. Want me to promote it? Reply YES.",
                "performance_drop": "Hi {owner_first}! Your orders dropped {underperformance_pct:.0f}% this month. Your {offer_title} in {locality} could help. Want me to send it to {demand_count} people searching for '{search_term}'? Reply YES.",
                "perf_dip": "Hi {owner_first}! Your orders dropped {underperformance_pct:.0f}% this month. Your {offer_title} in {locality} could help. Want me to send it to {demand_count} people searching for '{search_term}'? Reply YES.",
                "perf_spike": "Hi {owner_first}! Great news — orders are up! Want to capitalize? Reply YES.",
                "research_digest": "Hi {owner_first}! New food trends available. Want me to share? Reply YES.",
                "engagement": "Hi {owner_first}! You're doing great. Want to grow more? Reply YES.",
                "recall_due": "Hi {owner_first}, customer recall due. Want me to help? Reply YES.",
                "bridal_followup": "Hi {owner_first}, bridal event coming up. Want to plan? Reply YES.",
                "curious_ask_due": "Hi {owner_first}, quick check — what's your top dish? Reply YES to share.",
                "supply_alert": "Hi {owner_first}, supply alert received. Want me to help? Reply YES.",
                "chronic_refill_due": "Hi {owner_first}, refills due. Want me to help? Reply YES.",
                "active_planning_intent": "Hi {owner_first}, let's plan together! What's your goal? Reply YES.",
                "competitor_opened": "Hi {owner_first}, new restaurant opened nearby. Want insights? Reply YES.",
                "review_theme_emerged": "Hi {owner_first}, new review theme! Want details? Reply YES.",
                "regulation_change": "Hi {owner_first}, regulation update. Want to know more? Reply YES.",
                "dormant_with_vera": "Hi {owner_first}, it's been a while! Want to catch up? Reply YES.",
                "customer_lapsed_soft": "Hi {owner_first}, some customers haven't been in. Want to reach out? Reply YES.",
                "customer_lapsed_hard": "Hi {owner_first}, some customers are inactive. Want to help? Reply YES.",
                "ipl_match_today": "Hi {owner_first}, IPL match today! Want to plan match-day offers? Reply YES.",
                "seasonal_perf_dip": "Hi {owner_first}, seasonal dip expected. Want to plan? Reply YES."
            }
        },
        "gyms": {
            "tone": "motivational_data",
            "strategy": "lead_with_milestones",
            "key_signals": ["engagement", "search_spike", "offer", "milestone"],
            "avoid_signals": [],
            "persuasion_rules": {
                "primary": "motivation + data",
                "what_works": [
                    "highlight member achievements",
                    "use progress data (milestones, attendance)",
                    "focus on community and consistency",
                    "avoid body shaming"
                ],
                "what_to_avoid": [
                    "body shaming terms",
                    "before/after photos",
                    "unrealistic claims"
                ]
            },
            "social_proof_templates": [
                "Gyms nearby are using retention campaigns to keep members engaged through this season.",
                "Top 15% of gyms in your area have 80%+ member retention.",
                "Other gym owners are using milestone shoutouts to keep motivation high."
            ],
            "vocabulary_enforcement": {
                "allowed": [
                    "workout", "fitness", "health", "strength", "cardio", "yoga", "trainer",
                    "membership", "progress", "consistency", "community"
                ],
                "taboo": [
                    "fat", "lazy", "overweight", "skinny", "lose weight fast", "get skinny"
                ]
            },
            "tone_constraints": {
                "sentence_style": "motivational, encouraging",
                "use_contractions": True,
                "use_emoji": False,
                "formality_level": "supportive and encouraging"
            },
            "templates": {
                "search_spike": "Hi {owner_first}! {demand_count} people near {locality} searched for '{search_term}' this week. Your {offer_title} is exactly what they need. Should I send it to them? Reply YES.",
                "milestone": "Hi {owner_first}! {milestone_count} members reached their fitness goals this month — that's amazing. Your {offer_title} could help more. Want me to promote this success story? Reply YES.",
                "milestone_reached": "Hi {owner_first}! {milestone_count} members reached their fitness goals this month — that's amazing. Your {offer_title} could help more. Want me to promote this success story? Reply YES.",
                "offer": "Hi {owner_first}! Your {offer_title} is live. {demand_count} people in {locality} are searching for '{search_term}'. Want me to push it to them? Reply YES.",
                "engagement": "Hi {owner_first}! You have {directions} direction requests this month. Adding a {offer_title} trial offer could convert {conversion_rate:.0f}% of them. Want me to set it up? Reply YES.",
                "research_digest": "Hi {owner_first}! New fitness research available. Want me to share? Reply YES.",
                "temporal": "Hi {owner_first}! {festival_name} is in {days_until} days — {demand_count} people in {locality} are searching for '{search_term}'. Your {offer_title} is perfectly timed. Reply YES to push it.",
                "festival": "Hi {owner_first}! {festival_name} is coming up! Want to plan promotions? Reply YES.",
                "festival_upcoming": "Hi {owner_first}! {festival_name} is coming up! Want to plan promotions? Reply YES.",
                "performance_drop": "Hi {owner_first}! Your performance dipped. Want to turn it around? Reply YES.",
                "perf_dip": "Hi {owner_first}! Your performance dipped. Want to turn it around? Reply YES.",
                "perf_spike": "Hi {owner_first}! Great news — performance is up! Want to keep it going? Reply YES.",
                "recall_due": "Hi {owner_first}, member recall due. Want me to help? Reply YES.",
                "bridal_followup": "Hi {owner_first}, bridal fitness season! Want to plan? Reply YES.",
                "curious_ask_due": "Hi {owner_first}, quick check — what's your most popular class? Reply YES to share.",
                "supply_alert": "Hi {owner_first}, supply alert received. Want me to help? Reply YES.",
                "chronic_refill_due": "Hi {owner_first}, refills due. Want me to help? Reply YES.",
                "active_planning_intent": "Hi {owner_first}, let's plan together! What's your fitness goal? Reply YES.",
                "competitor_opened": "Hi {owner_first}, new gym opened nearby. Want insights? Reply YES.",
                "review_theme_emerged": "Hi {owner_first}, new review theme! Want details? Reply YES.",
                "regulation_change": "Hi {owner_first}, regulation update. Want to know more? Reply YES.",
                "dormant_with_vera": "Hi {owner_first}, it's been a while! Want to catch up? Reply YES.",
                "customer_lapsed_soft": "Hi {owner_first}, some members haven't been in. Want to reach out? Reply YES.",
                "customer_lapsed_hard": "Hi {owner_first}, some members are inactive. Want to help? Reply YES.",
                "ipl_match_today": "Hi {owner_first}, IPL match today! Want to plan fitness challenges? Reply YES.",
                "seasonal_perf_dip": "Hi {owner_first}, seasonal dip expected. Want to plan retention? Reply YES."
            }
        },
        "pharmacies": {
            "tone": "trustworthy_precise",
            "strategy": "lead_with_health",
            "key_signals": ["temporal", "search_spike", "offer", "engagement"],
            "avoid_signals": ["casual"],
            "persuasion_rules": {
                "primary": "trust + precision",
                "what_works": [
                    "be precise about medications and refills",
                    "emphasize health and safety",
                    "use clear, accurate information",
                    "avoid medical claims"
                ],
                "what_to_avoid": [
                    "health guarantees",
                    "miracle cure claims",
                    "exaggerated benefits"
                ]
            },
            "social_proof_templates": [
                "Other pharmacies are using refill reminders to improve customer loyalty by 25%.",
                "Top pharmacies in your area have 90%+ refill retention.",
                "Pharmacists nearby are using timely alerts to keep customers compliant."
            ],
            "vocabulary_enforcement": {
                "allowed": [
                    "medicine", "refill", "prescription", "health", "pharmacy", "delivery",
                    "doctor", "consultation", "OTC", "generic", "brand"
                ],
                "taboo": [
                    "100% safe", "miracle cure", "guaranteed", "cure"
                ]
            },
            "tone_constraints": {
                "sentence_style": "precise, trustworthy",
                "use_contractions": False,
                "use_emoji": False,
                "formality_level": "professional and reliable"
            },
            "templates": {
                "search_spike": "Hi {owner_first}! {demand_count} people in {locality} searched for '{search_term}' today. Your {offer_title} addresses exactly that. Should I send it to them? Reply YES.",
                "temporal": "Hi {owner_first}! {health_day} is in {days_until} days — {demand_count} people in {locality} are already researching '{search_term}'. Your {offer_title} is perfectly relevant. Want me to promote it? Reply YES.",
                "festival": "Hi {owner_first}! {festival_name} is coming up! Want to plan? Reply YES.",
                "festival_upcoming": "Hi {owner_first}! {festival_name} is coming up! Want to plan? Reply YES.",
                "offer": "Hi {owner_first}! Your {offer_title} is active. {demand_count} people near {locality} searched for '{search_term}' recently. Should I send your offer to them? Reply YES.",
                "engagement": "Hi {owner_first}! You have {calls} calls monthly. Setting up home delivery with your {offer_title} could increase that by 30%. Want me to help? Reply YES.",
                "research_digest": "Hi {owner_first}! New health guidelines available. Want me to share? Reply YES.",
                "performance_drop": "Hi {owner_first}! Your footfall dropped {underperformance_pct:.0f}%. Your {offer_title} could help attract {demand_count} people searching for '{search_term}' in {locality}. Reply YES to promote.",
                "perf_dip": "Hi {owner_first}! Your footfall dropped {underperformance_pct:.0f}%. Your {offer_title} could help attract {demand_count} people searching for '{search_term}' in {locality}. Reply YES to promote.",
                "milestone": "Hi {owner_first}! Congratulations on {milestone_count}! Want to celebrate? Reply YES.",
                "milestone_reached": "Hi {owner_first}! Congratulations on {milestone_count}! Want to celebrate? Reply YES.",
                "perf_spike": "Hi {owner_first}! Great news — your performance is up! Want to keep it going? Reply YES.",
                "recall_due": "Hi {owner_first}, medication recall alert. Want me to help? Reply YES.",
                "bridal_followup": "Hi {owner_first}, bridal health season. Want to plan? Reply YES.",
                "curious_ask_due": "Hi {owner_first}, quick check — what's your most asked medication? Reply YES to share.",
                "supply_alert": "Hi {owner_first}, supply alert received. Want me to help? Reply YES.",
                "chronic_refill_due": "Hi {owner_first}, chronic refills due. Want me to draft reminders? Reply YES.",
                "active_planning_intent": "Hi {owner_first}, let's plan together! What's your goal? Reply YES.",
                "competitor_opened": "Hi {owner_first}, new pharmacy opened nearby. Want insights? Reply YES.",
                "review_theme_emerged": "Hi {owner_first}, new review theme! Want details? Reply YES.",
                "regulation_change": "Hi {owner_first}, regulation update. Want to know more? Reply YES.",
                "dormant_with_vera": "Hi {owner_first}, it's been a while! Want to catch up? Reply YES.",
                "customer_lapsed_soft": "Hi {owner_first}, some customers haven't refilled. Want to reach out? Reply YES.",
                "customer_lapsed_hard": "Hi {owner_first}, some customers are inactive. Want to help? Reply YES.",
                "ipl_match_today": "Hi {owner_first}, IPL match today! Want to plan offers? Reply YES.",
                "seasonal_perf_dip": "Hi {owner_first}, seasonal dip expected. Want to plan? Reply YES."
            }
        }
    }

    @staticmethod
    def get_config(category_slug: str) -> Dict[str, Any]:
        return CategoryIntelligence.CATEGORY_CONFIGS.get(category_slug, CategoryIntelligence.CATEGORY_CONFIGS["dentists"])

    @staticmethod
    def get_tone(category_slug: str) -> str:
        return CategoryIntelligence.get_config(category_slug)["tone"]

    @staticmethod
    def get_persuasion_rules(category_slug: str) -> Dict[str, Any]:
        return CategoryIntelligence.get_config(category_slug)["persuasion_rules"]

    @staticmethod
    def get_social_proof_templates(category_slug: str) -> list:
        return CategoryIntelligence.get_config(category_slug)["social_proof_templates"]

    @staticmethod
    def get_vocabulary_enforcement(category_slug: str) -> Dict[str, list]:
        return CategoryIntelligence.get_config(category_slug)["vocabulary_enforcement"]

    @staticmethod
    def get_tone_constraints(category_slug: str) -> Dict[str, Any]:
        return CategoryIntelligence.get_config(category_slug)["tone_constraints"]

    @staticmethod
    def get_template(category_slug: str, signal_type: str) -> str:
        config = CategoryIntelligence.get_config(category_slug)
        templates = config.get("templates", {})

        if signal_type in templates:
            return templates[signal_type]

        fallback_signals = ["engagement", "offer"]
        for fallback in fallback_signals:
            if fallback in templates:
                return templates[fallback]

        return "Hi {owner_first}, quick check — want to review your dashboard?"

    @staticmethod
    def get_key_signals(category_slug: str) -> list:
        return CategoryIntelligence.get_config(category_slug)["key_signals"]
