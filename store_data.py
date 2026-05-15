"""
store_data.py
-------------
Loads store data from one of three sources (in priority order):

1. Shopify store URL — merchant just pastes their store URL, we fetch what
   we can from public-facing pages (no API key needed)
2. Live Shopify API — SHOPIFY_DOMAIN + SHOPIFY_ACCESS_TOKEN in .env
3. Preset demo stores — pre-built realistic stores the judge can pick from
   to see the tool in action immediately

Design decision: For the hackathon demo, a URL input is the lowest-friction
entry point. A merchant can paste "https://mystore.myshopify.com" and get
results without any technical setup. We scrape what's publicly visible
(policies pages, product pages) — the same data an AI agent would see.
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Preset demo stores — judges can explore without any setup
# ---------------------------------------------------------------------------
DEMO_STORES = {
    # -------------------------------------------------------------------------
    # BlueVeil: Has a refund policy and privacy policy, but they are vague/short.
    # Shipping policy is missing. No FAQ. Several weak product descriptions.
    # One contradiction (fast shipping claim vs no policy).
    # Target score without intent: ~48/100. Good for showing policy + FAQ gaps.
    # -------------------------------------------------------------------------
    "🛍️ BlueVeil (Bridesmaid Dresses) — vague policies, no FAQ, weak descriptions": {
        "shop": {
            "name": "BlueVeil",
            "description": "Elegant bridesmaid and occasion dresses for weddings, parties, and formal events.",
            "refundPolicy": {
                "body": (
                    "We accept returns within 14 days of delivery. Items must be unworn and in "
                    "original packaging. Sale items are non-refundable. To start a return, "
                    "contact our team at returns@blueveil.co. Refunds are issued within 10 "
                    "business days once the item is received and inspected."
                )
            },
            "shippingPolicy": {
                "body": (
                    "BlueVeil ships orders across the UK and internationally. "
                    "Delivery times vary depending on your location and the shipping "
                    "method selected at checkout. Please allow additional time during "
                    "busy periods such as sale events and public holidays."
                )
            },
            "privacyPolicy": {
                "body": (
                    "BlueVeil collects your name, email, and delivery address to process orders. "
                    "We do not sell your personal data to third parties. You may contact us at "
                    "privacy@blueveil.co to request data deletion. We use cookies to improve "
                    "your browsing experience on our site."
                )
            },
        },
        "products": [
            {
                "title": "Sky Blue Chiffon Bridesmaid Dress - Size S",
                "description": (
                    "Our Sky Blue Chiffon Bridesmaid Dress is the perfect choice for a romantic "
                    "spring or summer wedding. Cut from lightweight, floaty chiffon fabric, it "
                    "drapes beautifully and moves with the wearer. The A-line silhouette flatters "
                    "a wide range of body types, with a V-neckline and adjustable spaghetti straps "
                    "for a customised fit. Available in Size S (UK 8-10). Dry clean only."
                ),
                "images": {"edges": [{"node": {"altText": "Sky blue chiffon bridesmaid dress, A-line, Size S"}}]},
            },
            {
                "title": "Blush Pink Satin Bridesmaid Dress - Size S",
                "description": (
                    "Timeless and elegant, the Blush Pink Satin Bridesmaid Dress is crafted from "
                    "premium satin with a subtle sheen. The cowl neckline and bias-cut skirt create "
                    "a fluid, figure-skimming silhouette. Available in Size S (UK 8-10). "
                    "Machine wash cold, hang dry. Fully lined. Back zip closure."
                ),
                "images": {"edges": [{"node": {"altText": "Blush pink satin bridesmaid dress, cowl neck, Size S"}}]},
            },
            {
                "title": "Navy Blue Satin Evening Gown - Size S",
                "description": (
                    "Deep, rich navy satin cut into a floor-length column silhouette with a "
                    "sweetheart neckline and subtle side slit. Boning in the bodice provides "
                    "structure and support. Fully lined. Back zip closure. Available in Size S. "
                    "Perfect for black-tie events, galas, or formal weddings. Dry clean recommended."
                ),
                "images": {"edges": [{"node": {"altText": "Navy blue satin evening gown, sweetheart neckline"}}]},
            },
            # Short descriptions — intentional gaps
            {"title": "Sage Green Chiffon Wrap Dress - Size S", "description": "Beautiful wrap dress in sage green. Perfect for weddings.", "images": {"edges": [{"node": {"altText": ""}}]}},
            {"title": "Lavender Floral Midi Dress - Size S",    "description": "Floral midi dress in lavender. Great for summer events.",  "images": {"edges": []}},
            {"title": "Baby Blue Lace Cocktail Dress - Size S", "description": "Lace cocktail dress in baby blue. Elegant and stylish.",    "images": {"edges": []}},
            {"title": "Rose Gold Crystal Stud Earrings",        "description": "Crystal stud earrings in rose gold finish.",               "images": {"edges": [{"node": {"altText": ""}}]}},
            {"title": "Gold Leaf Bridal Party Necklace",        "description": "Delicate gold leaf necklace for bridesmaids.",             "images": {"edges": [{"node": {"altText": ""}}]}},
            # Contradiction — claims fast shipping but shipping policy is vague
            {"title": "Blue Floral Hair Vine", "description": "Delicate blue floral hair vine. Ships same day on all orders. Beautiful wire base with silk flowers.", "images": {"edges": [{"node": {"altText": ""}}]}},
        ],
        "pages": [],
        "source": "preset demo — BlueVeil (bridesmaid dresses)",
    },

    # -------------------------------------------------------------------------
    # GlowLab: GOOD STORE — strong policies, rich descriptions, comprehensive
    # FAQ. But 2 products lack alt text and FAQ is just under the threshold.
    # Realistic "good but not perfect" store. Target: ~78/100 without intent.
    # -------------------------------------------------------------------------
    "💄 GlowLab (Skincare) — strong policies, complete descriptions": {
        "shop": {
            "name": "GlowLab",
            "description": (
                "GlowLab makes clean, fragrance-free skincare for sensitive and reactive skin types. "
                "All formulas are dermatologist-tested, 100% vegan, and cruelty-free. We believe "
                "effective skincare should never irritate — every product is free from parabens, "
                "sulphates, artificial fragrance, and alcohol. Founded by a team of cosmetic "
                "chemists and dermatology nurses in London."
            ),
            "refundPolicy": {
                "body": (
                    "We offer a full 30-day money-back guarantee on all GlowLab products. "
                    "If you are not satisfied for any reason, contact hello@glowlab.com within "
                    "30 days of delivery and we will arrange a free return and full refund — "
                    "no questions asked. Refunds are processed to your original payment method "
                    "within 5-7 business days of receiving the returned item. Opened products "
                    "are accepted. Sale items are eligible for store credit. We cover return "
                    "postage for UK customers. International customers are responsible for "
                    "return shipping costs."
                )
            },
            "shippingPolicy": {
                "body": (
                    "All GlowLab orders are dispatched within 1-2 business days from our London "
                    "warehouse. Standard UK delivery via Royal Mail takes 3-5 business days and "
                    "is free on orders over £40 (£3.99 below that). Express delivery (1-2 business "
                    "days) is available at checkout for £6.99. International shipping is available "
                    "to all EU countries (7-14 business days, tracked). USA and Canada shipping "
                    "available (10-18 business days). All orders include a tracking number sent "
                    "by email at dispatch."
                )
            },
            "privacyPolicy": {
                "body": (
                    "GlowLab Ltd is committed to protecting your personal data. We collect only "
                    "the information necessary to process your order: your name, delivery address, "
                    "email, and payment details (processed securely by Stripe — we never store "
                    "card data). We do not sell, rent, or share your personal data with third-party "
                    "advertisers. You have the right to access, correct, or request deletion of "
                    "your data at any time by emailing privacy@glowlab.com. This policy is "
                    "governed by UK GDPR."
                )
            },
        },
        "products": [
            {
                "title": "Hydrating Hyaluronic Acid Face Serum",
                "description": (
                    "Our bestselling Hydrating Face Serum delivers three molecular weights of "
                    "hyaluronic acid deep into the skin to plump, smooth, and retain moisture for "
                    "up to 72 hours. Fragrance-free, alcohol-free, and suitable for all skin types "
                    "including rosacea-prone and eczema-prone skin. Dermatologist-tested. Apply 3-4 "
                    "drops to clean skin morning and evening before moisturiser. 30ml. Vegan and "
                    "cruelty-free. Free from parabens, sulphates, and artificial fragrance."
                ),
                "images": {"edges": [{"node": {"altText": "GlowLab Hydrating Hyaluronic Acid Face Serum 30ml, fragrance-free, clear dropper bottle"}}]},
            },
            {
                "title": "SPF 50 Daily Moisturiser",
                "description": (
                    "Lightweight daily moisturiser with broad-spectrum SPF 50 UVA/UVB protection. "
                    "Formulated with niacinamide to even skin tone, ceramides to strengthen the "
                    "skin barrier, and hyaluronic acid for all-day hydration. No white cast. "
                    "Fragrance-free and non-comedogenic — safe for acne-prone and sensitive skin. "
                    "Dermatologist-tested. 50ml. Vegan, cruelty-free, paraben-free."
                ),
                # Missing alt text — realistic gap, photographer forgot to add it
                "images": {"edges": [{"node": {"altText": ""}}]},
            },
            {
                "title": "Gentle Foaming Cleanser",
                "description": (
                    "A pH-balanced foaming cleanser that removes makeup, SPF, and daily impurities "
                    "without stripping the skin barrier. Enriched with oat extract and panthenol "
                    "to calm and soothe reactive skin. Fragrance-free, sulphate-free, and "
                    "alcohol-free. Suitable for dry, sensitive, and combination skin. 150ml pump. "
                    "Dermatologist-tested. Vegan and cruelty-free."
                ),
                "images": {"edges": [{"node": {"altText": "GlowLab Gentle Foaming Cleanser 150ml pump, sulphate-free"}}]},
            },
            {
                "title": "Niacinamide 10% Brightening Toner",
                "description": (
                    "High-strength 10% niacinamide toner that visibly reduces the appearance of "
                    "pores, controls excess sebum, and brightens uneven skin tone with consistent "
                    "use. Paired with zinc PCA to balance oil production. Fragrance-free, "
                    "alcohol-free, and suitable for oily, combination, and acne-prone skin. "
                    "Apply with a cotton pad after cleansing. 100ml. Vegan and cruelty-free."
                ),
                # Missing alt text — another realistic omission
                "images": {"edges": [{"node": {"altText": ""}}]},
            },
            {
                "title": "Barrier Repair Night Cream",
                "description": (
                    "Our Barrier Repair Night Cream is formulated with ceramides, hyaluronic acid, "
                    "and squalane to restore and strengthen the skin barrier overnight. Fragrance-free, "
                    "alcohol-free, and tested by dermatologists for sensitive skin. Apply a pea-sized "
                    "amount to clean skin before bed. 50ml. Suitable for all skin types including "
                    "rosacea-prone and eczema-prone skin. Vegan, cruelty-free, paraben-free."
                ),
                "images": {"edges": [{"node": {"altText": "GlowLab Barrier Repair Night Cream 50ml, fragrance-free, ceramide formula"}}]},
            },
        ],
        # FAQ exists but has only 4 questions — just under the 5-question threshold
        # Realistic: merchant wrote a quick FAQ and never expanded it
        "pages": [
            {
                "title": "FAQ",
                "body": (
                    "How long does standard shipping take? Standard UK delivery takes 3-5 business days. "
                    "Express delivery (1-2 business days) is available at checkout. "
                    "Can I return an opened product? Yes — we offer a no-questions-asked 30-day return policy on all products, including opened items. "
                    "Are your products vegan and cruelty-free? Yes, every GlowLab product is 100% vegan and cruelty-free, and free from parabens, sulphates, and artificial fragrance. "
                    "Do you ship internationally? Yes, we ship to all EU countries, the USA, and Canada."
                ),
            }
        ],
        "source": "preset demo — GlowLab (skincare)",
    },

    # -------------------------------------------------------------------------
    # VoltGear: BAD STORE — no refund policy, no privacy policy, no FAQ,
    # all weak product descriptions, two fast-shipping contradictions vs
    # a vague shipping policy. Intentionally the worst demo store.
    # Target score without intent: ~28/100.
    # -------------------------------------------------------------------------
    "⚡ VoltGear (Electronics) — missing policies, weak descriptions": {
        "shop": {
            "name": "VoltGear",
            "description": "Tech accessories and electronics for everyday life.",
            "refundPolicy":  {"body": ""},
            "shippingPolicy": {"body": "We ship orders. Delivery times vary."},
            "privacyPolicy": {
                "body": (
                    "VoltGear collects your name, email, and delivery address to process orders. "
                    "We do not sell your data to third parties. Contact support@voltgear.in "
                    "to request data deletion. We use cookies on our website."
                )
            },
        },
        "products": [
            {
                "title": "Wireless Earbuds Pro X",
                "description": "Premium wireless earbuds with active noise cancellation. Great sound quality.",
                "images": {"edges": [{"node": {"altText": ""}}]},
            },
            {
                "title": "USB-C Fast Charger 65W",
                "description": "Fast charger. Great value.",
                "images": {"edges": []},
            },
            {
                "title": "Portable Power Bank 20000mAh",
                "description": "Huge capacity power bank for all your devices.",
                "images": {"edges": []},
            },
            {
                "title": "Laptop Stand Adjustable",
                "description": "Adjustable laptop stand.",
                "images": {"edges": []},
            },
            {
                "title": "Mechanical Keyboard TKL RGB",
                "description": "Tenkeyless mechanical keyboard with RGB lighting.",
                "images": {"edges": [{"node": {"altText": ""}}]},
            },
        ],
        "pages": [],
        "source": "preset demo — VoltGear (electronics)",
    },
}


# ---------------------------------------------------------------------------
# Source: Live Shopify API (for merchants with API access)
# ---------------------------------------------------------------------------
GRAPHQL_QUERY = """
{
  shop {
    name description
    refundPolicy { body } shippingPolicy { body } privacyPolicy { body }
  }
  products(first: 30) {
    edges { node { title description images(first: 5) { edges { node { altText } } } } }
  }
  pages(first: 20) { edges { node { title body } } }
}
"""

def load_from_shopify_api() -> dict:
    domain = os.getenv("SHOPIFY_DOMAIN")
    token  = os.getenv("SHOPIFY_ACCESS_TOKEN")
    url = f"https://{domain}/admin/api/2024-01/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    response = requests.post(url, json={"query": GRAPHQL_QUERY}, headers=headers, timeout=15)
    response.raise_for_status()
    raw = response.json().get("data", {})
    return {
        "shop":     raw.get("shop", {}),
        "products": [e["node"] for e in raw.get("products", {}).get("edges", [])],
        "pages":    [e["node"] for e in raw.get("pages", {}).get("edges", [])],
        "source":   f"live Shopify API ({domain})",
    }


# ---------------------------------------------------------------------------
# Master loader
# ---------------------------------------------------------------------------
def get_store_data(demo_key: str = None) -> dict:
    """
    Returns store data. Priority:
      1. Preset demo store (selected from dropdown)
      2. Live Shopify API (env vars set)
      3. First preset demo as default
    """
    if demo_key and demo_key in DEMO_STORES:
        return DEMO_STORES[demo_key]

    if os.getenv("SHOPIFY_DOMAIN") and os.getenv("SHOPIFY_ACCESS_TOKEN"):
        return load_from_shopify_api()

    # Default to first demo store
    first_key = next(iter(DEMO_STORES))
    return DEMO_STORES[first_key]


def get_demo_store_keys() -> list:
    return list(DEMO_STORES.keys())