# Product Document — AI Representation Optimizer
**Kasparro Hackathon — Track 5 (Advanced): AI Representation Optimizer**

---

## The Problem We Are Solving

When a buyer asks an AI shopping agent — "find me a bridesmaid dress store with good returns and fast shipping" — the agent reads store data: product descriptions, policies, FAQ pages, image alt text.

If that data is missing, vague, or contradictory, the AI does one of three things:
- **Skips the store entirely** — not enough data to recommend confidently
- **Misrepresents it** — "I couldn't confirm their return policy"
- **Warns the buyer** — "shipping details are unconfirmed for this store"

Most merchants don't know this is happening. They see low conversion but have zero visibility into how AI agents are describing them. **This tool makes that visible and actionable.**

---

## Who Is the Target User

**Primary:** Shopify store owners who sell fashion, accessories, or lifestyle products and want to improve how AI shopping agents (like Google Shopping AI, ChatGPT plugins, Perplexity shopping) recommend their store.

**Secondary:** Kasparro product team — this tool directly mirrors what Kasparro evaluates when deciding which stores to surface to AI agents.

---

## What the Current Experience Looks Like (Before This Tool)

A typical merchant:
1. Writes product descriptions quickly — short, promotional, not descriptive
2. Leaves policies as Shopify defaults or blank
3. Has no FAQ page
4. Has no idea that an AI agent reading their store sees almost nothing useful
5. Wonders why AI-driven traffic is low

There is no tool today that shows a merchant exactly what an AI agent sees when it reads their store — and scores the gap.

---

## What We Built

A merchant-facing diagnostic tool that:

1. **Gap analysis (hero feature)** — compares how AI agents currently describe your store vs how you *want* to be described. Shows the exact missing data causing the mismatch.

2. **AI readiness score** — 0–100 score with point deductions tied to specific, fixable issues.

3. **Intent vs reality gap** — if the merchant claims "fast shipping" or "easy EMI" in their positioning statement but the store data doesn't confirm it anywhere, that gap is flagged AND deducts from the score. This is the key original insight: *the score reflects not just what's missing, but how far the store is from what the merchant wants AI to say about them.*

4. **Ranked action plan** — every issue framed as a lost sale, with a concrete fix template the merchant can copy-paste.

5. **Per-product confidence scores** — how confidently would an AI agent recommend each product? Below 6/10 = unlikely to be recommended.

6. **Downloadable report** — full .txt export of everything above.

---

## Core User Journey

```
Merchant opens tool
       ↓
Selects a store (demo or live)
       ↓
Enters positioning statement — "how I want AI to describe me"
       ↓
Clicks Run analysis
       ↓
Sees: AI readiness score + gap + ranked action plan + product scores
       ↓
Downloads report
       ↓
Goes and fixes their store data
```

---

## Key Product Decisions

### Decision 1: Positioning statement as input
We chose to ask merchants for their positioning statement because it unlocks the most valuable insight: the gap between *intent* and *reality*. A store with a 70/100 score that claims "next-day delivery" but has no shipping policy is fundamentally different from a 70/100 store that makes no delivery claims. The positioning statement makes that difference visible and scored.

### Decision 2: Score deductions for unverifiable claims
We deduct from the score when a merchant's intent claims something (EMI, eco, fast shipping) that the store data doesn't confirm. This creates urgency. If the gap only showed in text, merchants would ignore it. A score drop forces action.

### Decision 3: Frame every issue as a lost sale
We never say "you are missing a refund policy." We say "a buyer asking an AI agent 'what is their return policy?' will get no answer — the agent will skip this store entirely." Framing issues as lost sales (not technical warnings) is the product thinking behind this tool.

### Decision 4: Deterministic scoring, AI for perception only
The score is fully deterministic — pure Python rule checks. This means it's reproducible, testable, and never changes between runs. AI (Groq/Llama) is only used for the qualitative perception and gap analysis — the parts that genuinely need language understanding.

---

## What We Chose NOT to Build

- **A Shopify app** — out of scope for a hackathon. The tool is standalone.
- **Automatic fixes** — we considered auto-rewriting product descriptions but decided against it. Merchants need to own their copy. We give templates, not rewrites.
- **A subscription model** — not relevant for this submission.
- **Support for all e-commerce platforms** — we scoped to Shopify only for focus.

---

## Scope Decisions and Tradeoffs

| Decision | Chosen approach | Tradeoff accepted |
|---|---|---|
| Description quality check | Length threshold (150 chars) | Can't judge quality, only length |
| Intent gap detection | Keyword matching with word boundaries | Won't catch paraphrased claims |
| Product scoring | AI confidence score 1–10 | Subjective, model-dependent |
| Store data | Simulated demo stores | No live Shopify data in demo |
| Concurrent scoring | ThreadPoolExecutor max 5 workers | Rate limit friendly, not fastest possible |

---

## Success Metrics (if this were a real product)

- % of merchants who fix at least 1 issue after running the tool
- Score improvement on second run vs first run
- Reduction in "I couldn't confirm" responses from AI agents for stores that used the tool
- Time to fix (merchants who act within 24 hours of seeing the report)
