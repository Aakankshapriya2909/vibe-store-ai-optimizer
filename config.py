# config.py — Single source of truth for all scoring weights and thresholds
# Modify these values to tune the AI readiness scoring engine
# config.py
# All thresholds and constants in one place.
# Scoring rationale documented inline.

# ---------------------------------------------------------------------------
# Product description quality
# ---------------------------------------------------------------------------
MIN_DESC_LENGTH = 150
GOOD_DESC_LENGTH = 400
MIN_ALT_TEXT_LENGTH = 10

# ---------------------------------------------------------------------------
# Policy quality
# ---------------------------------------------------------------------------
MIN_POLICY_LENGTH = 100
MIN_FAQ_ENTRIES = 5

# ---------------------------------------------------------------------------
# Score deductions (out of 100)
# ---------------------------------------------------------------------------
SCORE_DEDUCTIONS = {
    # Core store data gaps
    "missing_refund_policy":   20,
    "missing_shipping_policy": 15,
    "contradicting_info":      10,
    "missing_faq_page":        10,
    "missing_privacy_policy":  10,
    "short_product_desc":       5,
    "missing_alt_text":         3,
    "vague_policy":             8,

    # Intent-based deductions — triggered when the merchant's positioning
    # statement claims a feature that is NOT confirmed anywhere in store data.
    # This makes the score reflect the real gap between what the merchant
    # SAYS they offer and what AI agents can actually verify.
    "intent_emi_missing":              10,
    "intent_shipping_speed_missing":   10,
    "intent_sustainability_missing":    8,
    "intent_return_window_missing":     8,
    "intent_certification_missing":     7,
    "intent_ingredient_claim_missing":  6,
    "intent_sizing_missing":            5,
    "intent_payment_method_missing":    5,
}

# ---------------------------------------------------------------------------
# Severity levels — used for UI colour coding and sort order
# ---------------------------------------------------------------------------
SEVERITY = {
    "high": [
        "missing_refund_policy",
        "missing_shipping_policy",
        "contradicting_info",
        "intent_emi_missing",
        "intent_shipping_speed_missing",
    ],
    "medium": [
        "missing_faq_page",
        "short_product_desc",
        "missing_privacy_policy",
        "vague_policy",
        "intent_sustainability_missing",
        "intent_return_window_missing",
        "intent_certification_missing",
        "intent_ingredient_claim_missing",
    ],
    "low": [
        "missing_alt_text",
        "intent_sizing_missing",
        "intent_payment_method_missing",
    ],
}

# ---------------------------------------------------------------------------
# AI model settings (Groq)
# ---------------------------------------------------------------------------
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 600

# ---------------------------------------------------------------------------
# Scan limits
# ---------------------------------------------------------------------------
MAX_PRODUCTS = 30

# ---------------------------------------------------------------------------
# INTENT_CHECKS — keyword map for intent-vs-store-data gap detection
#
# Structure: { issue_key: (trigger_words, confirm_words) }
#
# trigger_words : if ANY of these appear in the merchant's intent text,
#                 the merchant is making this claim → we check for it.
# confirm_words : if ANY of these appear anywhere in the full store text
#                 (policies + product descriptions + pages),
#                 the claim is confirmed → NO deduction.
# If triggered but NOT confirmed → deduction applied + issue raised.
# ---------------------------------------------------------------------------
INTENT_CHECKS = {
    "intent_emi_missing": (
        ["emi", "easy emi", "financing", "installment", "instalment",
         "buy now pay later", "bnpl", "klarna", "afterpay", "laybuy", "zest money"],
        ["emi", "financing", "installment", "instalment", "klarna",
         "afterpay", "laybuy", "bnpl", "zest money", "pay later"],
    ),
    "intent_shipping_speed_missing": (
        ["same day", "next day", "1-day", "2-day", "3-day", "overnight",
         "express shipping", "fast shipping", "quick shipping", "rapid delivery",
         "ships in", "delivered in"],
        ["same day", "next day", "1-2 business", "2-3 business", "1 business",
         "express", "overnight", "within 24", "within 48"],
    ),
    "intent_sustainability_missing": (
        ["sustainable", "eco-friendly", "eco friendly", "vegan", "cruelty-free",
         "cruelty free", "organic", "green", "biodegradable", "recycled", "ethical",
         "carbon neutral", "planet friendly"],
        ["sustainable", "eco", "vegan", "cruelty-free", "cruelty free",
         "organic", "biodegradable", "recycled", "ethical", "carbon neutral"],
    ),
    "intent_return_window_missing": (
        ["30-day return", "60-day return", "90-day return",
         "30 day return", "60 day return", "90 day return",
         "30-day refund", "60-day refund", "90-day refund",
         "no-questions-asked", "no questions asked", "hassle-free return"],
        ["30 day", "60 day", "90 day", "30-day", "60-day", "90-day",
         "no question", "hassle-free", "hassle free"],
    ),
    "intent_certification_missing": (
        ["dermatologist", "clinically tested", "clinically proven", "certified",
         "fda approved", "iso certified", "lab tested", "doctor recommended",
         "tested by"],
        ["dermatologist", "clinically", "certified", "fda", "iso",
         "lab tested", "doctor", "tested by"],
    ),
    "intent_ingredient_claim_missing": (
        ["fragrance-free", "fragrance free", "allergen-free", "hypoallergenic",
         "paraben-free", "sulfate-free", "alcohol-free", "dye-free",
         "non-comedogenic", "sensitive skin"],
        ["fragrance-free", "fragrance free", "allergen", "hypoallergenic",
         "paraben", "sulfate-free", "alcohol-free", "dye-free",
         "non-comedogenic", "sensitive skin"],
    ),
    "intent_sizing_missing": (
        ["size guide", "sizing guide", "size range", "xs to xxl",
         "plus size", "inclusive sizing", "petite", "tall sizes",
         "size chart"],
        ["size guide", "sizing guide", "size range", "size chart",
         "xs", "xxl", "plus size", "petite"],
    ),
    "intent_payment_method_missing": (
        ["paypal", "apple pay", "google pay", "klarna", "afterpay",
         "stripe", "visa", "mastercard", "amex", "upi", "razorpay"],
        ["paypal", "apple pay", "google pay", "klarna", "afterpay",
         "stripe", "visa", "mastercard", "amex", "upi", "razorpay"],
    ),
}

# ---------------------------------------------------------------------------
# Human-readable labels for intent issues (used in UI)
# ---------------------------------------------------------------------------
INTENT_ISSUE_LABELS = {
    "intent_emi_missing": (
        "You claim EMI/financing options but store data doesn't confirm it",
        "Add EMI/financing details to your FAQ page or payment policy. "
        "List the providers (e.g. Klarna, ZestMoney), minimum order value, "
        "and number of instalments available.",
        "AI agents asked 'do they offer EMI?' will say no — buyers who need "
        "financing will go to a competitor whose store confirms it.",
    ),
    "intent_shipping_speed_missing": (
        "You claim fast/express shipping but your shipping policy doesn't confirm it",
        "Add exact shipping timeframes to your shipping policy "
        "(e.g. 'Express delivery: 1-2 business days'). Match the claim in your intent.",
        "AI agents cannot verify your shipping speed claim — they will either "
        "omit it or warn buyers that shipping times are unconfirmed.",
    ),
    "intent_sustainability_missing": (
        "You claim sustainability/eco credentials but no store data confirms them",
        "Add your sustainability credentials to product descriptions, an About page, "
        "or a dedicated sustainability page. Be specific: certifications, materials, "
        "packaging, carbon offset programmes.",
        "Buyers asking AI agents 'are they eco-friendly?' will get no confirmation — "
        "a significant missed opportunity for differentiation.",
    ),
    "intent_return_window_missing": (
        "You claim a specific return window but your refund policy doesn't mention it",
        "Update your refund policy to explicitly state the return window "
        "(e.g. '60-day no-questions-asked returns'). Match the exact claim in your intent.",
        "Your return policy is a key trust signal. If AI agents can't confirm "
        "the return window you're advertising, buyers won't trust the claim.",
    ),
    "intent_certification_missing": (
        "You claim certifications (dermatologist-tested etc.) but store data is silent",
        "Add certification details to product descriptions or a dedicated credentials page. "
        "Name the certifying body, what was tested, and when.",
        "Unverifiable certification claims are ignored or flagged by AI agents — "
        "they need concrete store data to pass the claim to a buyer.",
    ),
    "intent_ingredient_claim_missing": (
        "You claim ingredient benefits (fragrance-free etc.) but products don't confirm it",
        "Add ingredient claims to each relevant product description. "
        "Be explicit: 'fragrance-free', 'paraben-free', 'suitable for sensitive skin'.",
        "Buyers who filter for fragrance-free / hypoallergenic products rely on AI "
        "agents reading product descriptions — if it's not there, they're excluded.",
    ),
    "intent_sizing_missing": (
        "You mention sizing options/guides but no size information exists in store data",
        "Add a size guide page or size chart to each relevant product. "
        "Include measurements, fit notes, and a comparison table.",
        "AI agents asked 'do they have my size?' cannot answer — "
        "sizing uncertainty is a top reason buyers abandon fashion stores.",
    ),
    "intent_payment_method_missing": (
        "You mention a specific payment method but it's not confirmed in store data",
        "Add your accepted payment methods to your FAQ page or checkout policy. "
        "List each method explicitly so AI agents can confirm it.",
        "Buyers who ask AI agents 'do they accept PayPal / UPI?' will get no "
        "confirmation — a simple FAQ entry can prevent this lost sale.",
    ),
}