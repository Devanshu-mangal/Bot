#!/usr/bin/env python3
"""
test_system.py — Tests the LIVE pipeline (signal_engine + composer + rationale_engine)
NOT the legacy pipeline. Run from the bot/ directory.
"""
import sys, os

# Ensure project root (two levels up) is on sys.path so `import bot...` works
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bot.signal_engine import collect_signals, rank_signals, pick_winner, Signal
from bot.composer import compose_message
from bot.rationale_engine import build_rationale

DENTIST_MERCHANT = {
    "merchant_id": "m_001_drmeera_dentist_delhi",
    "category_slug": "dentists",
    "identity": {"name": "Dr. Meera's Dental Clinic", "owner_first_name": "Meera", "locality": "Lajpat Nagar"},
    "performance": {"views": 2410, "ctr": 0.021, "calls": 18},
    "offers": [{"id": "offr_001", "title": "Dental Cleaning @ ₹299", "status": "active", "discount_price": 299}],
    "signals": ["high_risk_adult_cohort", "stale_google_posts", "ctr_below_peer_median"],
    "customer_aggregate": {"lapsed_180d_plus": 78, "retention_6mo_pct": 0.62}
}

DENTIST_CATEGORY = {
    "slug": "dentists",
    "voice": {"tone": "peer_clinical", "vocab_allowed": ["evidence-based", "clinical", "peer-reviewed"],
              "vocab_taboo": ["guaranteed", "100% safe", "miracle"]},
    "peer_stats": {"avg_ctr": 0.03, "avg_views_30d": 1820, "avg_calls": 12,
                   "active_merchants_locality": 14, "avg_reviews": 62},
    "digest": [{"id": "dg_001", "title": "3-month fluoride varnish recall outperforms 6-month for high-risk adult caries",
                "source": "JIDA Oct 2026, p.14", "trial_n": 2100,
                "patient_segment": "high-risk adults", "actionable": "Update recall protocol to 3-month for high-risk adult cohort"}]
}

RESEARCH_TRIGGER = {
    "trigger_id": "trg_001_research_digest_dentists",
    "kind": "research_digest",
    "merchant_id": "m_001_drmeera_dentist_delhi",
    "payload": {"top_item_id": "dg_001", "digest_available": True},
    "occurred_at": "2026-05-02T10:00:00Z",
    "suppression_key": "research:dentists:2026-W17"
}

SEARCH_TRIGGER = {
    "trigger_id": "trg_002_search_spike",
    "kind": "search_spike",
    "merchant_id": "m_001_drmeera_dentist_delhi",
    "payload": {"demand_count": 312, "locality": "Lajpat Nagar", "search_term": "dentist near me"},
    "occurred_at": "2026-05-02T10:00:00Z",
    "suppression_key": ""
}

def _run_pipeline(trigger, label):
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print('='*60)
    signals = collect_signals(DENTIST_CATEGORY, DENTIST_MERCHANT, trigger, None)
    print(f"  Signals collected: {len(signals)}")
    ranked = rank_signals(signals, "dentists", DENTIST_MERCHANT, "new")
    winner = pick_winner(ranked, [])
    if not winner:
        print("  ERROR: No winner selected")
        return False
    print(f"  Winner signal: {winner.type} (tier={winner.tier})")
    body, cta, send_as = compose_message(winner, DENTIST_CATEGORY, DENTIST_MERCHANT, None, "dentists")
    print(f"  CTA: {cta} | send_as: {send_as}")
    print(f"  Body:\n  {body}")
    # Checks
    assert body and len(body) > 20, "Body too short"
    assert '{' not in body, f"Unfilled template vars in body: {body}"
    assert cta in ("binary_yes_no", "open_ended", "none"), f"Invalid CTA: {cta}"
    rationale = build_rationale(winner, ranked, "new", "dentists", send_as, False)
    assert rationale and len(rationale) > 20, "Rationale too short"
    print(f"  Rationale: {rationale[:100]}...")
    print(f"  PASS")
    return True

def main():
    print("\nVERA LIVE PIPELINE TESTS")
    print("Tests signal_engine → composer → rationale_engine (the actual /v1/tick path)\n")
    passed = 0
    total = 2
    try:
        if _run_pipeline(RESEARCH_TRIGGER, "research_digest → template path (clinical dentist)"):
            passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
    try:
        if _run_pipeline(SEARCH_TRIGGER, "search_spike → template path (demand signal)"):
            passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
    print(f"\n{'='*60}")
    print(f"RESULT: {passed}/{total} tests passed")
    print('='*60)
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
