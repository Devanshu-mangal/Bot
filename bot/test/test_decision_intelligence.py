import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from decision_intelligence import select_best_signal


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
    
    # Create ranked signals (top 3 triggers)
    ranked_signals = [
        (95.0, triggers[0]),   # research_digest
        (75.0, triggers[1]),   # perf_dip
        (60.0, triggers[2]),   # festival_upcoming
    ]

    print("Testing Decision Intelligence System with Dr. Meera's Dental Clinic...")
    print("=" * 100)

    decision = select_best_signal(
        ranked_signals=ranked_signals,
        merchant_data=merchant,
        category_data=category_dentists,
        customer_data=None,
    )

    for key, value in decision.items():
        print(f"\n{key.upper()}:")
        print(f"  {value}")
    
    print("\n" + "=" * 100)
    print("Decision Intelligence System test passed!")


if __name__ == "__main__":
    main()