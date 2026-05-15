"""
analyzer.py
-----------
The diagnostic engine. Takes raw store data (and optionally the merchant's
positioning intent) and returns:
- An AI readiness score (0-100)
- A ranked list of issues, each framed as a lost sale
- Summary statistics

KEY CHANGE: analyze_store() now accepts an optional `merchant_intent` string.
When provided, it runs intent-gap checks — if the merchant CLAIMS something
(e.g. "easy EMI", "60-day returns", "eco-friendly") but the store data
doesn't confirm it anywhere, that gap is flagged AND deducted from the score.
This makes the score genuinely reflect the gap between intent and reality.

Score weighting rationale
--------------------------
Core deductions are weighted by how directly the missing data blocks an AI
agent from answering a buyer's pre-purchase query.

Intent-based deductions are weighted by how prominently buyers ask about
that feature and how damaging an unverifiable claim is to trust.
"""

import re

from config import (
    MIN_DESC_LENGTH,
    MIN_POLICY_LENGTH,
    MIN_FAQ_ENTRIES,
    SCORE_DEDUCTIONS,
    SEVERITY,
    INTENT_CHECKS,
    INTENT_ISSUE_LABELS,
)


def _keyword_match(text: str, keywords: list) -> bool:
    """
    Returns True if ANY keyword appears in text as a whole word/phrase.
    Uses \b word-boundary regex to prevent false positives like
    'emi' matching inside 'accessories'.
    """
    for kw in keywords:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text):
            return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _severity(issue_key: str) -> str:
    for level, keys in SEVERITY.items():
        if issue_key in keys:
            return level
    return "low"


def _make_issue(key, area, problem, fix, impact, product_title=None):
    """Creates a standardised issue dict."""
    title = f"[{product_title}] {problem}" if product_title else problem
    return {
        "key": key,
        "severity": _severity(key),
        "area": area,
        "problem": title,
        "fix": fix,
        "impact": impact,
        "deduction": SCORE_DEDUCTIONS.get(key, 5),
    }


def _build_full_store_text(shop: dict, products: list, pages: list) -> str:
    """
    Concatenates all store text into one lowercase string for intent-gap
    keyword matching. Covers policies, product descriptions, and pages.
    """
    parts = []

    for policy_key in ("refundPolicy", "shippingPolicy", "privacyPolicy"):
        body = (shop.get(policy_key) or {}).get("body") or ""
        parts.append(body)

    parts.append(shop.get("description") or "")

    for p in products:
        parts.append(p.get("description") or "")
        parts.append(p.get("title") or "")
        for img_edge in (p.get("images", {}).get("edges") or []):
            parts.append(img_edge.get("node", {}).get("altText") or "")

    for page in pages:
        parts.append(page.get("title") or "")
        parts.append(page.get("body") or "")

    return " ".join(parts).lower()


# ---------------------------------------------------------------------------
# Core checks (deterministic, no AI)
# ---------------------------------------------------------------------------

def check_policies(shop: dict) -> list:
    """Checks refund, shipping, privacy policies for existence and minimum length."""
    issues = []

    refund_body = ((shop.get("refundPolicy") or {}).get("body") or "").strip()
    if len(refund_body) < MIN_POLICY_LENGTH:
        issues.append(_make_issue(
            "missing_refund_policy",
            "Trust signals",
            "No clear refund policy found",
            "Add a detailed refund policy (min 100 words). Cover: the return window, "
            "condition of items accepted, refund method (store credit vs original payment), "
            "and the contact/process for initiating a return.",
            "A buyer asking an AI agent 'what is their return policy?' will get no answer — "
            "the agent will skip this store entirely.",
        ))

    shipping_body = ((shop.get("shippingPolicy") or {}).get("body") or "").strip()
    if len(shipping_body) < MIN_POLICY_LENGTH:
        issues.append(_make_issue(
            "missing_shipping_policy",
            "Trust signals",
            "Shipping policy is missing or too vague",
            "Add specific shipping times (e.g. '3-5 business days'), carriers used, "
            "and international shipping details if applicable.",
            "AI agents asked 'how fast does this store ship?' cannot answer — "
            "your store gets deprioritised vs competitors with clear policies.",
        ))

    privacy_body = ((shop.get("privacyPolicy") or {}).get("body") or "").strip()
    if len(privacy_body) < MIN_POLICY_LENGTH:
        issues.append(_make_issue(
            "missing_privacy_policy",
            "Trust signals",
            "Privacy policy is missing or too short",
            "Add a full privacy policy covering: what data you collect, how it is used, "
            "third-party sharing, and how customers can request deletion. Many AI agent "
            "platforms automatically filter stores without one.",
            "Stores without privacy policies are increasingly filtered out by "
            "AI shopping platforms as a compliance requirement.",
        ))

    return issues


def check_products(products: list) -> list:
    """Checks each product for description quality and alt text."""
    issues = []
    seen_desc_issue = 0

    for p in products:
        title = p.get("title", "Unknown product")
        desc = (p.get("description") or "").strip()

        if len(desc) < MIN_DESC_LENGTH:
            seen_desc_issue += 1
            if seen_desc_issue <= 5:
                issues.append(_make_issue(
                    "short_product_desc",
                    "Product content",
                    f"Description too short ({len(desc)} chars, need {MIN_DESC_LENGTH}+)",
                    f"Rewrite '{title}' description to include: what it is, who it's for, "
                    f"key benefits, materials/specs, sizing, and a use case. Aim for 150-400 words.",
                    f"AI agents won't confidently recommend '{title}' because there's not "
                    f"enough information to match it to a buyer's query.",
                    product_title=title,
                ))

        images = p.get("images", {}).get("edges", [])
        for img_edge in images:
            alt = (img_edge.get("node", {}).get("altText") or "").strip()
            if len(alt) < 10:
                issues.append(_make_issue(
                    "missing_alt_text",
                    "Structured data",
                    "Product image has no alt text",
                    f"Add descriptive alt text to all images for '{title}'. "
                    f"Example: 'Sky blue chiffon bridesmaid dress, A-line silhouette, Size S, front view'",
                    f"AI agents that process visual data cannot identify '{title}' from "
                    f"its images — it becomes invisible in image-based AI searches.",
                    product_title=title,
                ))
                break  # one issue per product is enough

    if seen_desc_issue > 5:
        issues.append(_make_issue(
            "short_product_desc",
            "Product content",
            f"{seen_desc_issue - 5} more products also have short descriptions",
            "Apply the same description improvements across all flagged products. "
            "Prioritise your best-selling items first.",
            "Each weak product description is a missed AI recommendation opportunity.",
        ))

    return issues


def check_faq(pages: list) -> list:
    """Checks for an FAQ page and whether it has enough entries."""
    issues = []
    faq_page = None

    for page in pages:
        title_lower = (page.get("title") or "").lower()
        if "faq" in title_lower or "frequently" in title_lower:
            faq_page = page
            break

    if not faq_page:
        issues.append(_make_issue(
            "missing_faq_page",
            "FAQ coverage",
            "No FAQ page found",
            "Create an FAQ page covering: shipping times, return process, product materials, "
            "sizing/compatibility, and payment methods. Each question = one AI query answered.",
            "AI shopping agents are essentially FAQ engines. Without an FAQ, your store "
            "cannot answer the most common pre-purchase questions buyers ask AI agents.",
        ))
    else:
        body = (faq_page.get("body") or "").lower()
        q_count = body.count("?")
        if q_count < MIN_FAQ_ENTRIES:
            issues.append(_make_issue(
                "missing_faq_page",
                "FAQ coverage",
                f"FAQ page exists but only has ~{q_count} questions (need {MIN_FAQ_ENTRIES}+)",
                "Expand your FAQ with more questions. Cover: returns, shipping, product care, "
                "compatibility, payment options, and sustainability/ethics if relevant.",
                f"With only {q_count} FAQ entries, most buyer questions go unanswered — "
                "AI agents will express uncertainty when recommending your store.",
            ))

    return issues


def check_contradictions(shop: dict, products: list) -> list:
    """Looks for contradicting or unverifiable shipping claims in product descriptions."""
    issues = []
    shipping_body = ((shop.get("shippingPolicy") or {}).get("body") or "").lower()

    fast_words = ["same day", "next day", "ships immediately", "instant"]
    slow_words = ["7-10 days", "2-3 weeks", "allow 14 days"]
    policy_is_vague_or_missing = len(shipping_body.strip()) < 50 or not any(
        w in shipping_body for w in ["day", "week", "hour", "business"]
    )

    for p in products:
        desc = (p.get("description") or "").lower()
        title = p.get("title", "Unknown")
        has_fast = any(w in desc for w in fast_words)
        has_slow_policy = any(w in shipping_body for w in slow_words)

        if has_fast and has_slow_policy:
            issues.append(_make_issue(
                "contradicting_info",
                "Data consistency",
                f"'{title}' says fast shipping but policy says slow",
                "Align your product descriptions with your shipping policy. "
                "Use exact timeframes from your policy in product copy.",
                "AI agents detect contradictions and flag them as unreliable — "
                "your store may be shown with a trust warning or skipped entirely.",
                product_title=title,
            ))
        elif has_fast and policy_is_vague_or_missing:
            issues.append(_make_issue(
                "contradicting_info",
                "Data consistency",
                f"'{title}' claims fast shipping but your shipping policy doesn't confirm it",
                "Update your shipping policy with specific timeframes (e.g. '1-2 business days') "
                "so it matches the claims made in your product descriptions.",
                "AI agents cannot verify the shipping claim in this product — "
                "they will either skip it or warn buyers that shipping details are unconfirmed.",
                product_title=title,
            ))

    return issues


# ---------------------------------------------------------------------------
# Intent-gap checks (new) — affects the score
# ---------------------------------------------------------------------------

def check_intent_gaps(merchant_intent: str, store_text: str) -> list:
    """
    Compares the merchant's positioning statement against the full store text.

    For each known claim type (EMI, fast shipping, eco credentials, etc.):
    - If the merchant's intent mentions it (trigger_words match)
    - AND the store data doesn't confirm it anywhere (confirm_words absent)
    → Raise an issue and deduct from the score.

    This is what makes the score genuinely reflect the gap between
    what the merchant WANTS to be known for and what AI agents can actually verify.
    """
    if not merchant_intent or not merchant_intent.strip():
        return []

    intent_lower = merchant_intent.lower()
    issues = []

    for issue_key, (trigger_words, confirm_words) in INTENT_CHECKS.items():
        # Step 1: Is the merchant making this claim?
        claim_made = _keyword_match(intent_lower, trigger_words)
        if not claim_made:
            continue

        # Step 2: Is the claim confirmed anywhere in store data?
        claim_confirmed = _keyword_match(store_text, confirm_words)
        if claim_confirmed:
            continue

        # Step 3: Claim made but not confirmed — raise issue
        problem, fix, impact = INTENT_ISSUE_LABELS[issue_key]
        issues.append(_make_issue(
            issue_key,
            "Intent vs reality gap",
            problem,
            fix,
            impact,
        ))

    return issues


# ---------------------------------------------------------------------------
# Master function
# ---------------------------------------------------------------------------

def analyze_store(data: dict, merchant_intent: str = "") -> dict:
    """
    Master function. Runs all checks, deducts score, sorts by severity.

    Args:
        data:            Raw store data dict (shop, products, pages).
        merchant_intent: Optional positioning statement from the merchant.
                         When provided, intent-gap checks run and affect the score.

    Returns:
        {
            score,          # 0-100
            issues,         # ranked list of issue dicts
            total_products,
            total_pages,
            summary,        # { high, medium, low } counts
            intent_checked, # bool — whether intent checks ran
        }
    """
    shop = data.get("shop", {})
    products = data.get("products", [])
    pages = data.get("pages", [])

    all_issues = []
    all_issues += check_policies(shop)
    all_issues += check_products(products)
    all_issues += check_faq(pages)
    all_issues += check_contradictions(shop, products)

    # Intent-gap checks — only run if merchant provided a positioning statement
    intent_checked = bool(merchant_intent and merchant_intent.strip())
    if intent_checked:
        store_text = _build_full_store_text(shop, products, pages)
        all_issues += check_intent_gaps(merchant_intent, store_text)

    # Calculate score
    score = 100
    for issue in all_issues:
        score -= issue["deduction"]
    score = max(score, 0)

    # Sort: high → medium → low, then by deduction size descending
    order = {"high": 0, "medium": 1, "low": 2}
    all_issues.sort(key=lambda x: (order[x["severity"]], -x["deduction"]))

    summary = {
        "high":   sum(1 for i in all_issues if i["severity"] == "high"),
        "medium": sum(1 for i in all_issues if i["severity"] == "medium"),
        "low":    sum(1 for i in all_issues if i["severity"] == "low"),
    }

    return {
        "score": score,
        "issues": all_issues,
        "total_products": len(products),
        "total_pages": len(pages),
        "summary": summary,
        "intent_checked": intent_checked,
    }


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    dummy = {
        "shop": {
            "name": "Test Store",
            "description": "",
            "refundPolicy":   {"body": ""},
            "shippingPolicy": {"body": ""},
            "privacyPolicy":  {"body": ""},
        },
        "products": [
            {"title": "Phone Case", "description": "Great case.", "images": {"edges": []}},
        ],
        "pages": [],
    }
    intent = "A tech store with easy EMI options, next-day shipping, and eco-friendly packaging."
    result = analyze_store(dummy, merchant_intent=intent)
    print(f"Score: {result['score']}/100")
    print(f"Issues: {len(result['issues'])} (intent checked: {result['intent_checked']})")
    for issue in result["issues"]:
        print(f"  [{issue['severity'].upper()}] -{issue['deduction']}pts {issue['problem']}")