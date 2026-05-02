import json
from product_intelligence import extract_insights
from insights_to_whatsapp import compose_whatsapp_message


def main():
    # Read sample data
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\merchants_seed.json") as f:
        merchants = json.load(f)["merchants"]
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\categories\dentists.json") as f:
        category_dentists = json.load(f)
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\triggers_seed.json") as f:
        triggers = json.load(f)["triggers"]

    merchant = merchants[0]
    trigger = triggers[0]

    insights = extract_insights(
        merchant_data=merchant,
        category_data=category_dentists,
        trigger_data=trigger,
        customer_data=None,
    )

    merchant_summary = merchant.get("identity", {}).get("name", "Merchant")
    trigger_reason = "JIDA's latest research digest has landed"
    category_voice = {"slug": "dentists", "tone": "peer_clinical"}

    print("DEBUG: Raw insights:")
    print(json.dumps(insights, indent=2))

    print("\nDEBUG: Top insights selected:")
    from insights_to_whatsapp import _select_top_insights
    top_insights = _select_top_insights(insights, 2)
    for i, ins in enumerate(top_insights):
        print(f"{i+1}. Type: {ins['type']}, Content: '{ins['content']}'")

    print("\nDEBUG: Blended insights:")
    from insights_to_whatsapp import _blend_insights_into_sentences
    blended = _blend_insights_into_sentences(top_insights, "dentists")
    print(f"Blended: '{blended}'")
    print(f"Length: {len(blended)}, Has spaces at end: '{blended[-5:]}'")

    print("\nDEBUG: Final message:")
    message = compose_whatsapp_message(
        insights=insights,
        merchant_summary=merchant_summary,
        trigger_reason=trigger_reason,
        category_voice=category_voice,
    )
    print(repr(message))


if __name__ == "__main__":
    main()
