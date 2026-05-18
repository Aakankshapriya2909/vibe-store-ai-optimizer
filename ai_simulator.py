"""
ai_simulator.py
---------------
Simulates how an AI shopping agent perceives the store.
Uses Groq API (free tier available at console.groq.com) with Llama 3.3 70B.

Three public functions:
1. simulate_ai_perception()  — describes the store as an AI agent would
2. compare_to_intent()       — finds the gap between AI view and merchant goal
3. get_product_confidence()  — scores each product 1-10 with reasoning

Design decisions
-----------------
- All LLM calls are isolated here. analyzer.py is fully deterministic.
  This boundary is intentional — it keeps the rule-based scoring reproducible
  and the AI layer independently testable.
- The Groq client is instantiated once per process (not per call) to avoid
  redundant object creation on every retry.
- Product confidence calls run concurrently (ThreadPoolExecutor) to cut
  wall-clock time from ~30s sequential to ~8-10s for 15 products.
"""

import os
import time
import concurrent.futures
from groq import Groq
from dotenv import load_dotenv
from config import GROQ_MODEL, MAX_TOKENS

load_dotenv()

# ---------------------------------------------------------------------------
# Module-level Groq client (instantiated once, not per call)
# ---------------------------------------------------------------------------
_client: Groq | None = None


def _get_client() -> Groq:
    """Returns a shared Groq client, creating it on first call."""
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError(
                "GROQ_API_KEY not found. Add it to your .env file:\n"
                "  GROQ_API_KEY=your_key_here\n"
                "Get a free key at https://console.groq.com"
            )
        _client = Groq(api_key=key)
    return _client


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ask(prompt: str, retries: int = 2, timeout_secs: int = 20) -> str:
    """
    Wrapper around Groq API with retry logic and timeout handling.

    Retries up to `retries` times on transient failures with exponential
    backoff. Raises a clear RuntimeError on final failure so callers can
    surface a meaningful message rather than a raw traceback.
    """
    client = _get_client()
    last_error = None

    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS,
                timeout=timeout_secs,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(2 ** attempt)  # 1s then 2s backoff

    raise RuntimeError(
        f"Groq API call failed after {retries + 1} attempts. "
        f"Last error: {last_error}\n"
        "Check your API key and internet connection."
    )


def _build_store_summary(data: dict) -> str:
    """Builds a compact text summary of the store for use in prompts."""
    shop = data.get("shop", {})
    products = data.get("products", [])[:10]

    product_lines = []
    for p in products:
        desc = (p.get("description") or "")[:200]
        product_lines.append(f"- {p['title']}: {desc or '[no description]'}")

    refund = (shop.get("refundPolicy") or {}).get("body", "") or "Not provided"
    shipping = (shop.get("shippingPolicy") or {}).get("body", "") or "Not provided"

    return (
        f"Store name: {shop.get('name', 'Unknown')}\n"
        f"Store description: {shop.get('description') or 'Not provided'}\n"
        f"Refund policy: {refund[:300]}\n"
        f"Shipping policy: {shipping[:300]}\n"
        f"Products ({len(products)} shown):\n"
        + "\n".join(product_lines)
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def simulate_ai_perception(data: dict) -> str:
    """
    Sends store data to Groq/Llama and asks how an AI shopping agent
    would describe this store to a buyer.
    Returns: raw LLM response string.
    All LLM calls in the project are isolated to this file.
    """
    summary = _build_store_summary(data)

    prompt = (
        "You are an AI shopping assistant helping a customer find products online.\n"
        'A customer asks you: "Tell me about this store — should I buy from them?"\n\n'
        "You only know what is written below. Do not invent information.\n"
        "If something is unclear or missing, say so honestly.\n\n"
        f"{summary}\n\n"
        "Respond in 3-5 sentences as if talking directly to the buyer.\n"
        "Be honest about gaps — if you can't confirm shipping times, say so."
    )

    try:
        return _ask(prompt)
    except (RuntimeError, ValueError) as e:
        return f"AI_UNAVAILABLE: {e}"


def compare_to_intent(ai_perception: str, merchant_intent: str) -> str:
    """
    Compares AI's actual perception vs what the merchant wants to be known for.
    Returns a gap analysis string with specific missing data identified.
    """
    if not merchant_intent or not merchant_intent.strip():
        return "NO_INTENT"

    if ai_perception.startswith("AI_UNAVAILABLE"):
        return "GAP_UNAVAILABLE: AI perception call failed — gap analysis skipped."

    prompt = (
        f'A merchant wants their Shopify store to be perceived as:\n"{merchant_intent}"\n\n'
        f'But an AI shopping agent currently describes the store like this:\n"{ai_perception}"\n\n'
        "In 2-3 sentences, identify the key gap between these two.\n"
        "Be specific — what information is missing from the store that causes this gap?\n"
        "Do not suggest generic fixes; identify the exact missing data."
    )

    try:
        return _ask(prompt)
    except (RuntimeError, ValueError) as e:
        return f"GAP_UNAVAILABLE: {e}"


def _score_single_product(p: dict) -> dict:
    """
    Scores a single product. Designed to be called from a thread pool.
    Returns: { title, score, reason, failed }
    """
    title = p.get("title", "Unknown")
    desc = (p.get("description") or "")[:400]
    images = p.get("images", {}).get("edges", [])
    has_alt = any(
        (img.get("node", {}).get("altText") or "").strip()
        for img in images
    )

    prompt = (
        "You are an AI shopping agent deciding whether to recommend this product.\n\n"
        f"Product title: {title}\n"
        f"Description: {desc or '[none provided]'}\n"
        f"Has image alt text: {'Yes' if has_alt else 'No'}\n\n"
        "Rate your confidence in recommending this product to a buyer on a scale of 1-10.\n"
        "Then give ONE sentence explaining what is holding your confidence back (or why it's high).\n\n"
        "Reply in this exact format:\n"
        "SCORE: [number]\n"
        "REASON: [one sentence]"
    )

    try:
        response = _ask(prompt)
        lines = response.strip().split("\n")
        score_line = next((l for l in lines if l.startswith("SCORE:")), "SCORE: 5")
        reason_line = next((l for l in lines if l.startswith("REASON:")), "REASON: No reason given.")
        score = int(score_line.replace("SCORE:", "").strip())
        reason = reason_line.replace("REASON:", "").strip()
        failed = False
    except (RuntimeError, ValueError) as e:
        score = 5
        reason = f"Score unavailable — API error. ({e})"
        failed = True
    except Exception:
        score = 5
        reason = "Could not parse AI response — description may be missing or malformed."
        failed = True

    return {
        "title": title,
        "score": max(1, min(10, score)),
        "reason": reason,
        "failed": failed,
    }


def get_product_confidence(products: list) -> list:
    """
    Scores each product on how confidently an AI agent would recommend it.
    Uses ThreadPoolExecutor with max 5 workers to respect Groq free-tier limits.
    Order is restored after concurrent execution via index mapping.
    """
    target = products[:15]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_score_single_product, p): p for p in target}
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                p = futures[future]
                results.append({
                    "title": p.get("title", "Unknown"),
                    "score": 5,
                    "reason": f"Thread error: {e}",
                    "failed": True,
                })

    # Preserve original product order
    order = {p.get("title"): i for i, p in enumerate(target)}
    results.sort(key=lambda r: order.get(r["title"], 999))

    return results


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    dummy = {
        "shop": {
            "name": "TheSkullStore",
            "description": "Cool skull stuff",
            "refundPolicy": None,
            "shippingPolicy": None,
        },
        "products": [
            {"title": "Skull Mug", "description": "Great mug.", "images": {"edges": []}},
        ],
        "pages": [],
    }
    print("Testing Groq AI perception...")
    perception = simulate_ai_perception(dummy)
    print(f"AI says: {perception}")