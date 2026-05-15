"""
app.py
------
Streamlit dashboard — the merchant-facing UI.
Run with: streamlit run app.py

KEY CHANGE: merchant_intent is now passed into analyze_store().
Intent-gap issues (EMI, shipping speed, eco claims, etc.) now appear in the
ranked action plan AND affect the AI readiness score.
"""

import streamlit as st
from store_data import get_store_data, get_demo_store_keys
from analyzer import analyze_store
from ai_simulator import simulate_ai_perception, compare_to_intent, get_product_confidence

st.set_page_config(
    page_title="AI Representation Optimizer",
    page_icon="🔍",
    layout="wide",
)

st.markdown("""
<style>
.score-badge { font-size: 3rem; font-weight: 700; line-height: 1; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("AI Representation Optimizer")
st.caption(
    "See how AI shopping agents perceive any Shopify store — "
    "and exactly what to fix to get recommended more."
)
st.divider()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Store settings")

    demo_keys = get_demo_store_keys()
    selected_store = st.selectbox(
        "Select a store to analyse",
        options=demo_keys,
        help="Pick a demo store to see the tool in action. Each has different gaps built in.",
    )

    st.caption(
        "🔌 **Have a real Shopify store?** Add `SHOPIFY_DOMAIN` and "
        "`SHOPIFY_ACCESS_TOKEN` to your `.env` file to analyse your live store."
    )

    st.divider()

    merchant_intent = st.text_area(
        "How do you want AI agents to describe your store?",
        placeholder=(
            "e.g. A sustainable skincare brand for sensitive skin types who want "
            "fragrance-free, dermatologist-tested products with fast 3-day shipping, "
            "easy EMI options, and a no-questions-asked 60-day return policy."
        ),
        height=150,
    )
    st.caption(
        "Your positioning statement. Claims you make here (EMI, eco, fast shipping, etc.) "
        "are checked against your actual store data — unverifiable claims **reduce your score**."
    )

    st.divider()
    run = st.button("Run analysis", type="primary", use_container_width=True)
    st.caption("~15 seconds. Rule-based checks are instant; AI calls follow.")

# ---------------------------------------------------------------------------
# Pre-run state
# ---------------------------------------------------------------------------
if not run:
    st.info("Select a store and click **Run analysis** to get started.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🏪 Pick a store")
        st.markdown("Choose from 3 demo stores — each has different types of AI representation gaps built in.")
    with col2:
        st.markdown("### ✍️ Set your intent")
        st.markdown(
            "Describe how you *want* AI agents to describe the store. "
            "Claims you make are **verified against your store data** — "
            "unconfirmed claims lower your score."
        )
    with col3:
        st.markdown("### 📊 Get your score")
        st.markdown("See your AI readiness score, the gap, a ranked action plan, and per-product confidence scores.")

    with st.expander("What does this tool check?"):
        st.markdown("""
**5 dimensions AI shopping agents care about:**

| Dimension | What we check | Max deduction |
|-----------|--------------|---------------|
| Trust signals | Refund, shipping, privacy policies | −45 pts |
| Product content | Description length & clarity | −5 pts per product |
| Structured data | Image alt text | −3 pts per product |
| FAQ coverage | Pre-purchase Q&A | −10 pts |
| Intent vs reality | Claims in your positioning not found in store data | −5 to −10 pts each |

**Intent vs reality** is the new dimension. If you say you offer EMI, eco-friendly packaging,
or 60-day returns — but your store data doesn't confirm it — AI agents can't verify the claim.
That gap now shows up in your score and action plan.

Each issue is framed as a **lost sale** — not just a technical warning.
        """)
    st.stop()

# ---------------------------------------------------------------------------
# Load store data
# ---------------------------------------------------------------------------
with st.status("Loading store data...", expanded=False) as status:
    try:
        data = get_store_data(demo_key=selected_store)
        store_name = data["shop"].get("name", "Unknown Store")
        source = data.get("source", "")
        status.update(
            label=f"Store loaded: **{store_name}** — {len(data['products'])} products, "
                  f"{len(data['pages'])} pages. Source: {source}",
            state="complete",
        )
    except Exception as e:
        status.update(label="Error loading store data", state="error")
        st.error(f"**Could not load store data:** {e}")
        st.stop()

# ---------------------------------------------------------------------------
# Rule-based analysis — NOW passes merchant_intent so intent gaps affect score
# ---------------------------------------------------------------------------
report = analyze_store(data, merchant_intent=merchant_intent)

st.divider()
st.subheader("AI readiness score")

score = report["score"]
score_color = "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"

col1, col2, col3, col4 = st.columns(4)
col1.metric("AI Readiness Score", f"{score_color} {score}/100")
col2.metric("🔴 High priority", report["summary"]["high"])
col3.metric("🟡 Medium priority", report["summary"]["medium"])
col4.metric("Products scanned", report["total_products"])

if report["intent_checked"]:
    st.caption(
        "Score includes deductions for claims in your positioning statement "
        "that could not be verified in your store data."
    )
else:
    st.caption(
        "Score based on store data only. Add a positioning statement in the sidebar "
        "to also check whether your claims are verifiable by AI agents."
    )

# ---------------------------------------------------------------------------
# AI calls
# ---------------------------------------------------------------------------
st.divider()

with st.status("Simulating AI agent perception...", expanded=True) as ai_status:
    st.write("Asking AI to describe the store as a shopping agent would...")
    perception = simulate_ai_perception(data)

    st.write("Comparing AI view to your intended positioning...")
    gap = compare_to_intent(perception, merchant_intent)

    st.write("Scoring each product for AI recommendation confidence...")
    product_scores = get_product_confidence(data["products"])

    ai_status.update(label="AI simulation complete.", state="complete")

# ---------------------------------------------------------------------------
# Gap analysis hero
# ---------------------------------------------------------------------------
st.subheader("Why AI agents misrepresent you")
st.caption(
    "The gap between how you want to be seen and how AI agents currently describe you."
)

c1, c2 = st.columns(2)
with c1:
    st.markdown("**How AI agents currently see you**")
    if perception.startswith("AI_UNAVAILABLE"):
        st.warning("⚠️ AI perception unavailable — check your GROQ_API_KEY in .env")
    else:
        st.info(perception)

with c2:
    st.markdown("**How you want to be seen**")
    if merchant_intent.strip():
        st.success(merchant_intent)
    else:
        st.warning("No positioning statement entered — add one in the sidebar to unlock gap analysis.")

st.markdown("#### The gap — what's causing this mismatch")

if gap == "NO_INTENT":
    st.info("💡 Add your positioning statement in the sidebar to see the exact gap.")
elif gap.startswith("GAP_UNAVAILABLE"):
    st.warning(f"⚠️ Gap analysis unavailable: {gap.replace('GAP_UNAVAILABLE: ', '')}")
else:
    st.error(gap)
    st.caption("Fix the issues below to close this gap.")

# ---------------------------------------------------------------------------
# Ranked action plan
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Ranked action plan")
st.caption("Fix these in order — each adds data AI agents use to recommend your store.")

# Separate intent-gap issues for a callout banner
intent_issues = [i for i in report["issues"] if i["key"].startswith("intent_")]
store_issues   = [i for i in report["issues"] if not i["key"].startswith("intent_")]

if intent_issues and report["intent_checked"]:
    st.warning(
        f"⚠️ **{len(intent_issues)} unverifiable claim(s) detected** — "
        "your positioning statement mentions features AI agents cannot confirm in your store data. "
        "These are included in your score and listed in the action plan below."
    )

for i, issue in enumerate(report["issues"], 1):
    severity = issue["severity"]
    icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🔵"
    fn = st.error if severity == "high" else st.warning if severity == "medium" else st.info

    # Mark intent-gap issues distinctly
    intent_tag = " 🏷️ *Intent gap*" if issue["key"].startswith("intent_") else ""
    label = f"{icon} {issue['problem']}  (−{issue['deduction']} pts){intent_tag}"

    with st.expander(label):
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.markdown(f"**Area:** {issue['area']}")
            st.markdown(f"**Severity:** {severity.capitalize()}")
            st.markdown(f"**Score impact:** −{issue['deduction']} pts")
            if issue["key"].startswith("intent_"):
                st.markdown("**Type:** Intent vs reality gap")
        with col_b:
            st.markdown("**Why this hurts your AI representation:**")
            fn(issue["impact"])
            st.markdown("**How to fix it:**")
            st.success(issue["fix"])

# ---------------------------------------------------------------------------
# Per-product confidence scores
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Per-product AI confidence scores")
st.caption("Below 6/10 = unlikely to be recommended by an AI shopping agent.")

if any(ps.get("failed") for ps in product_scores):
    st.warning("⚠️ Some scores are fallbacks (5/10) due to API errors — marked with ⚠️.")

for ps in sorted(product_scores, key=lambda x: x["score"]):
    score_val = ps["score"]
    color = "🟢" if score_val >= 8 else "🟡" if score_val >= 5 else "🔴"
    failed_marker = " ⚠️" if ps.get("failed") else ""
    cols = st.columns([3, 1, 5])
    cols[0].markdown(f"**{ps['title']}**")
    cols[1].markdown(f"{color} **{score_val}/10**{failed_marker}")
    cols[2].caption(ps["reason"])

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Export report")

intent_gap_section = ""
if intent_issues:
    intent_gap_section = "\nSECTION 1B — INTENT vs REALITY GAPS\n"
    intent_gap_section += "-------------------------------------\n"
    intent_gap_section += "These claims appear in your positioning statement but could not\n"
    intent_gap_section += "be verified anywhere in your store data:\n"
    for issue in intent_issues:
        intent_gap_section += (
            f"\n  [{issue['severity'].upper()}] {issue['problem']}\n"
            f"  Score impact: -{issue['deduction']} pts\n"
            f"  Why it hurts: {issue['impact']}\n"
            f"  Fix: {issue['fix']}\n"
        )

report_text = f"""AI REPRESENTATION OPTIMIZER — FULL REPORT
==========================================
Store: {store_name}
Source: {source}
AI Readiness Score: {report['score']}/100
Intent checks ran: {'Yes' if report['intent_checked'] else 'No'}

SECTION 1 — GAP ANALYSIS
-------------------------
How AI agents currently see you:
{perception}

How you want to be seen:
{merchant_intent or 'Not specified'}

The gap:
{gap}
{intent_gap_section}
SECTION 2 — RANKED ACTION PLAN ({len(report['issues'])} issues)
---------------------------------------------------------------
"""
for i, issue in enumerate(report["issues"], 1):
    intent_flag = " [INTENT GAP]" if issue["key"].startswith("intent_") else ""
    report_text += (
        f"\n#{i} [{issue['severity'].upper()}]{intent_flag} {issue['problem']}\n"
        f"  Area: {issue['area']}\n"
        f"  Score impact: -{issue['deduction']} pts\n"
        f"  Why it hurts: {issue['impact']}\n"
        f"  Fix: {issue['fix']}\n"
    )

report_text += "\nSECTION 3 — PER-PRODUCT AI CONFIDENCE\n"
report_text += "--------------------------------------\n"
for ps in product_scores:
    flag = " [FALLBACK]" if ps.get("failed") else ""
    report_text += f"  {ps['title']}: {ps['score']}/10{flag} — {ps['reason']}\n"

st.download_button(
    label="Download full report as .txt",
    data=report_text,
    file_name=f"ai_rep_report_{store_name.replace(' ', '_')}.txt",
    mime="text/plain",
)