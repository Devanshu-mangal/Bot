#!/usr/bin/env python3
"""Quick test to confirm Groq fires for LLM-routed triggers."""
import sys, os

# Ensure project root (two levels up) is on sys.path so `import bot...` works
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bot.signal_engine import Signal
from bot.composer import compose_message

# Build a signal that IS in LLM_TRIGGER_KINDS
signal = Signal(
    type="competitive",
    tier=1,
    base_score=85.0,
    trigger_kind="competitor_opened",   # ← this IS in LLM_TRIGGER_KINDS
    data={
        "owner_first_name": "Meera",
        "merchant_name": "Dr. Meera's Dental Clinic",
        "locality": "Lajpat Nagar",
        "competitor_name": "SmileCare Dental",
        "competitor_distance_km": 0.8,
        "offer_title": "Dental Cleaning @ ₹299",
        "offer_price": "299",
        "ctr": 0.021,
        "views": 2410,
        "calls": 18,
    },
    source="trigger",
    occurred_at="2026-05-03T10:00:00Z"
)

category = {
    "slug": "dentists",
    "peer_stats": {"avg_ctr": 0.03, "avg_views_30d": 1820, "active_merchants_locality": 14},
    "voice": {"tone": "peer_clinical", "vocab_taboo": ["guaranteed", "miracle"]}
}

merchant = {
    "identity": {"owner_first_name": "Meera", "locality": "Lajpat Nagar"},
    "performance": {"ctr": 0.021, "views": 2410, "calls": 18},
    "signals": ["ctr_below_peer_median", "stale_google_posts"]
}

print("Calling compose_message with competitor_opened trigger (should use Groq)...")
body, cta, send_as = compose_message(signal, category, merchant, None, "dentists")
print(f"\nCTA: {cta} | send_as: {send_as}")
print(f"\nBody:\n{body}")
print("\nDone.")