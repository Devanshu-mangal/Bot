import json
import sys
import os

# Ensure project root (two levels up) is on sys.path so `import bot...` works
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bot.unified_composer import compose


def main():
    # Read sample data from dataset
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\merchants_seed.json") as f:
        merchants = json.load(f)["merchants"]
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\categories\dentists.json") as f:
        category_dentists = json.load(f)
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\triggers_seed.json") as f:
        triggers = json.load(f)["triggers"]
    with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\customers_seed.json") as f:
        customers = json.load(f)["customers"]

    merchant = merchants[0]
    trigger = triggers[0]

    print("Testing Unified Composer...")
    print("=" * 100)

    # Test 1: Merchant-facing (no customer)
    print("\n🧪 TEST 1: Merchant-facing message (no customer)")
    result = compose(
        merchant_data=merchant,
        category_data=category_dentists,
        trigger_data=trigger,
        customer_data=None,
    )
    
    print("\n📜 RESULT:")
    print("-" * 100)
    print(f"body:\n{result['body']}")
    print(f"\ncta: {result['cta']}")
    print(f"send_as: {result['send_as']}")
    print(f"rationale: {result['rationale']}")

    # Test 2: Customer-facing (with customer)
    print("\n\n🧪 TEST 2: Customer-facing message (with customer)")
    customer = customers[0] if customers else None
    
    if customer:
        result_customer = compose(
            merchant_data=merchant,
            category_data=category_dentists,
            trigger_data=trigger,
            customer_data=customer,
        )
        
        print("\n📜 RESULT:")
        print("-" * 100)
        print(f"body:\n{result_customer['body']}")
        print(f"\ncta: {result_customer['cta']}")
        print(f"send_as: {result_customer['send_as']}")
        print(f"rationale: {result_customer['rationale']}")
        print(f"\ncustomer_personalization: {json.dumps(result_customer['customer_personalization'], indent=2)}")

    print("\n" + "=" * 100)
    print("✅ Unified Composer test passed!")


if __name__ == "__main__":
    main()