"""
test_analyzer.py
----------------
Run with: python -m pytest test_analyzer.py -v
"""
import pytest
from analyzer import analyze_store, check_intent_gaps, _build_full_store_text

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _store(refund="", shipping="", privacy="", products=None, pages=None, desc=""):
    return {
        "shop": {
            "name": "Test Store",
            "description": desc,
            "refundPolicy":   {"body": refund},
            "shippingPolicy": {"body": shipping},
            "privacyPolicy":  {"body": privacy},
        },
        "products": products or [],
        "pages":    pages or [],
    }

# ---------------------------------------------------------------------------
# Core scoring tests
# ---------------------------------------------------------------------------

def test_perfect_store_scores_100():
    """A store with all data present should score 100."""
    data = _store(
        refund="We offer a full refund within 30 days. Items must be unused. "
               "Contact us at returns@store.com. Refunds processed in 5 business days.",
        shipping="Orders ship in 1-2 business days via Royal Mail. "
                 "Standard delivery 3-5 days. Express 1-2 days available.",
        privacy="We collect only data needed to process your order. "
                "We never sell your data. Request deletion at privacy@store.com.",
        products=[{
            "title": "Great Product",
            "description": "A" * 200,  # Long enough description
            "images": {"edges": [{"node": {"altText": "Descriptive alt text here"}}]},
        }],
        pages=[{
            "title": "FAQ",
            "body": "What is your return policy? 30 days. "
                    "How fast do you ship? 1-2 days. "
                    "Do you ship internationally? Yes. "
                    "What payment methods? Visa, Mastercard. "
                    "Can I exchange? Yes we offer exchanges.",
        }],
    )
    result = analyze_store(data)
    assert result["score"] == 100, f"Expected 100, got {result['score']}"


def test_missing_refund_deducts_20():
    result = analyze_store(_store(refund=""))
    score_without = analyze_store(_store(
        refund="Full refund within 30 days on all items. "
               "Contact returns@store.com to initiate. "
               "Processed within 5 business days to original payment."
    ))["score"]
    assert result["score"] == score_without - 20


def test_missing_shipping_deducts_15():
    base = analyze_store(_store())["score"]
    with_shipping = analyze_store(_store(
        shipping="Orders ship within 1-2 business days via Royal Mail. "
                 "Standard delivery takes 3-5 business days. "
                 "Express delivery available at checkout for next day. "
                 "Free shipping on orders over forty pounds minimum."
    ))["score"]
    assert with_shipping == base + 15


def test_score_never_goes_below_zero():
    """Worst-case store should floor at 0, not go negative."""
    result = analyze_store(_store())
    assert result["score"] >= 0


def test_short_product_desc_deducts_5():
    data = _store(products=[{
        "title": "Widget",
        "description": "Short.",
        "images": {"edges": []},
    }])
    result = analyze_store(data)
    issues = [i for i in result["issues"] if i["key"] == "short_product_desc"]
    assert len(issues) >= 1
    assert issues[0]["deduction"] == 5


# ---------------------------------------------------------------------------
# Intent gap tests — the critical new feature
# ---------------------------------------------------------------------------

def test_emi_intent_gap_detected_when_missing():
    """Merchant claims EMI but store has no EMI data → issue raised."""
    data = _store()
    result = analyze_store(data, merchant_intent="We offer easy EMI options.")
    keys = [i["key"] for i in result["issues"]]
    assert "intent_emi_missing" in keys


def test_emi_confirmed_in_store_no_deduction():
    """Merchant claims EMI and store confirms it → no deduction."""
    data = _store(
        pages=[{"title": "FAQ", "body": "We offer EMI through Klarna and ZestMoney."}]
    )
    result = analyze_store(data, merchant_intent="We offer easy EMI options.")
    keys = [i["key"] for i in result["issues"]]
    assert "intent_emi_missing" not in keys


def test_no_intent_no_intent_issues():
    """Without a positioning statement, no intent issues should appear."""
    data = _store()
    result = analyze_store(data, merchant_intent="")
    intent_issues = [i for i in result["issues"] if i["key"].startswith("intent_")]
    assert len(intent_issues) == 0
    assert result["intent_checked"] is False


def test_sustainability_intent_gap():
    data = _store()
    result = analyze_store(data, merchant_intent="We are an eco-friendly, vegan brand.")
    keys = [i["key"] for i in result["issues"]]
    assert "intent_sustainability_missing" in keys


def test_sustainability_confirmed_no_gap():
    data = _store(desc="100% vegan and cruelty-free products.")
    result = analyze_store(data, merchant_intent="We are an eco-friendly, vegan brand.")
    keys = [i["key"] for i in result["issues"]]
    assert "intent_sustainability_missing" not in keys


# ---------------------------------------------------------------------------
# Word-boundary false positive tests — the bug we fixed
# ---------------------------------------------------------------------------

def test_emi_not_matched_inside_accessories():
    """'accessories' contains 'emi' as substring — must NOT trigger EMI confirmation."""
    store_text = "tech accessories and electronics for everyday life"
    from analyzer import _keyword_match
    confirm_words = ["emi", "financing", "klarna"]
    assert _keyword_match(store_text, confirm_words) is False


def test_emi_matched_as_standalone_word():
    from analyzer import _keyword_match
    store_text = "we offer easy emi through klarna"
    confirm_words = ["emi", "financing"]
    assert _keyword_match(store_text, confirm_words) is True


def test_no_false_positive_on_accessories_store():
    """
    Real regression test: a store named 'Accessories Plus' with no EMI
    should get the EMI intent gap flagged when merchant claims EMI.
    """
    data = _store(desc="Premium accessories for everyday use.")
    result = analyze_store(data, merchant_intent="We offer easy EMI options.")
    keys = [i["key"] for i in result["issues"]]
    assert "intent_emi_missing" in keys, \
        "EMI gap should be flagged — 'accessories' must not falsely confirm EMI"


# ---------------------------------------------------------------------------
# Contradiction tests
# ---------------------------------------------------------------------------

def test_fast_shipping_claim_without_policy_flagged():
    data = _store(
        shipping="",
        products=[{
            "title": "Widget",
            "description": "Ships same day guaranteed!",
            "images": {"edges": []},
        }]
    )
    result = analyze_store(data)
    keys = [i["key"] for i in result["issues"]]
    assert "contradicting_info" in keys


# ---------------------------------------------------------------------------
# Severity ordering tests
# ---------------------------------------------------------------------------

def test_high_severity_issues_come_first():
    data = _store()
    result = analyze_store(data)
    severities = [i["severity"] for i in result["issues"]]
    # Once we see a medium, we should not see a high after it
    seen_non_high = False
    for s in severities:
        if s != "high":
            seen_non_high = True
        if seen_non_high and s == "high":
            pytest.fail("High severity issue appeared after a non-high issue")