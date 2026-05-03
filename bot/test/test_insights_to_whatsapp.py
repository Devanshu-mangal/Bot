import json
import sys
import os

# Ensure project root (two levels up) is on sys.path so `import bot...` works
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from product_intelligence import extract_insights
from insights_to_whatsapp import compose_whatsapp_message


def main():
    # Read sample data from dataset
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\merchants_seed.json") as f:
        merchants = json.load(f)["merchants"]
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\categories\dentists.json") as f:
        category_dentists = json.load(f)
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\triggers_seed.json") as f:
        triggers = json.load(f)["triggers"]

    merchant = merchants[0]
    trigger = triggers[0]

    print("Testing Enhanced Insights to WhatsApp Composer with New Input Format...")
    print("=" * 100)

    # Step 1: Extract insights
    insights = extract_insights(
        merchant_data=merchant,
        category_data=category_dentists,
        trigger_data=trigger,
        customer_data=None,
    )

    # Step 2: Prepare new input format
    merchant_summary = merchant.get("identity", {}).get("name", "Merchant")
    trigger_reason = "JIDA's latest research digest has landed"
    category_voice = {
        "slug": "dentists",
        "tone": "peer_clinical",
    }

    print("\n📥 NEW INPUT FORMAT:")
    print("-" * 100)
    print(f"insights: {json.dumps(insights, indent=2, default=str)[:200]}...")
    print(f"merchant_summary: {merchant_summary}")
    print(f"trigger_reason: {trigger_reason}")
    print(f"category_voice: {json.dumps(category_voice, indent=2)}")

    # Step 3: Compose WhatsApp message
    whatsapp_message = compose_whatsapp_message(
        insights=insights,
        merchant_summary=merchant_summary,
        trigger_reason=trigger_reason,
        category_voice=category_voice,
    )

    print("\n📱 WHATSAPP MESSAGE:")
    print("-" * 100)
    print(whatsapp_message)
    print("-" * 100)
    
    print("\n✅ Enhanced Insights to WhatsApp Composer test passed!")


if __name__ == "__main__":
    main()