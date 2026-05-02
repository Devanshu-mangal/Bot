#!/usr/bin/env python3
"""Test script for local FastAPI server"""

import sys
import os
import json
import time
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8080"


def test_healthz():
    """Test GET /v1/healthz"""
    print("\n" + "="*100)
    print("TEST: GET /v1/healthz")
    print("="*100)
    try:
        resp = requests.get(f"{BASE_URL}/v1/healthz", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_metadata():
    """Test GET /v1/metadata"""
    print("\n" + "="*100)
    print("TEST: GET /v1/metadata")
    print("="*100)
    try:
        resp = requests.get(f"{BASE_URL}/v1/metadata", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_context():
    """Test POST /v1/context with sample data"""
    print("\n" + "="*100)
    print("TEST: POST /v1/context")
    print("="*100)
    
    # Load sample data
    try:
        with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\categories\dentists.json") as f:
            category = json.load(f)
        with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\merchants_seed.json") as f:
            merchants = json.load(f)["merchants"]
        merchant = merchants[0]
        with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\triggers_seed.json") as f:
            triggers = json.load(f)["triggers"]
        trigger = triggers[0]
    except Exception as e:
        print(f"❌ Could not load sample data: {e}")
        return False
    
    # Test category context
    try:
        resp = requests.post(
            f"{BASE_URL}/v1/context",
            json={
                "scope": "category",
                "context_id": "dentists",
                "version": 1,
                "payload": category
            },
            timeout=5
        )
        print(f"POST /context (category) status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Error posting category context: {e}")
    
    # Test merchant context
    try:
        resp = requests.post(
            f"{BASE_URL}/v1/context",
            json={
                "scope": "merchant",
                "context_id": merchant["merchant_id"],
                "version": 1,
                "payload": merchant
            },
            timeout=5
        )
        print(f"POST /context (merchant) status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Error posting merchant context: {e}")
    
    # Test trigger context
    try:
        resp = requests.post(
            f"{BASE_URL}/v1/context",
            json={
                "scope": "trigger",
                "context_id": trigger["id"],
                "version": 1,
                "payload": trigger
            },
            timeout=5
        )
        print(f"POST /context (trigger) status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        return resp.status_code in (200, 201)
    except Exception as e:
        print(f"❌ Error posting trigger context: {e}")
        return False


def test_tick():
    """Test POST /v1/tick"""
    print("\n" + "="*100)
    print("TEST: POST /v1/tick")
    print("="*100)
    try:
        with open(r"d:\MagicPin\Example\magicpin-ai-challenge\dataset\triggers_seed.json") as f:
            triggers = json.load(f)["triggers"]
        
        available_triggers = [t["id"] for t in triggers[:3]]
        
        resp = requests.post(
            f"{BASE_URL}/v1/tick",
            json={
                "now": "2026-05-02T18:00:00Z",
                "available_triggers": available_triggers
            },
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "="*100)
    print("LOCAL API TESTER")
    print("="*100)
    print(f"\nBase URL: {BASE_URL}")
    print("\nMake sure the server is running first with:")
    print("  cd d:\\MagicPin\\bot ; python main.py")
    print("\n" + "="*100)
    
    input("\nPress Enter to start testing (make sure server is running!)...")
    
    results = []
    results.append(("GET /v1/healthz", test_healthz()))
    results.append(("GET /v1/metadata", test_metadata()))
    results.append(("POST /v1/context", test_context()))
    results.append(("POST /v1/tick", test_tick()))
    
    print("\n" + "="*100)
    print("TEST SUMMARY")
    print("="*100)
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
