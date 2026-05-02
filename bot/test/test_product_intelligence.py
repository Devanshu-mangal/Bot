import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from product_intelligence import extract_insights


def main():
    # Read sample data from dataset
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\merchants_seed.json") as f:
        merchants = json.load(f)["merchants"]
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\categories\dentists.json") as f:
        category_dentists = json.load(f)
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\triggers_seed.json") as f:
        triggers = json.load(f)["triggers"]

    # Test with merchant 001 (Dr. Meera's Dental Clinic)
    merchant = merchants[0]
    trigger = triggers[0]
    print("Testing Product Intelligence System with Dr. Meera's Dental Clinic and Research Digest Trigger...")
    print("=" * 100)

    insights = extract_insights(
        merchant_data=merchant,
        category_data=category_dentists,
        trigger_data=trigger,
        customer_data=None,
    )

    for key, value in insights.items():
        print(f"\n{key.upper()}:")
        if isinstance(value, list):
            for item in value:
                print(f" - {item}")
        elif value is None:
            print(" - No data")
        else:
            print(f" - {value}")
    print("\n" + "=" * 100)
    print("Product Intelligence System test passed!")


if __name__ == "__main__":
    main()