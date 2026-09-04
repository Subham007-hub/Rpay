# Agent-ready storefront (Razorpay Buildathon — Track 01)

An AI buyer agent discovers, ranks, and purchases a product from a merchant
catalog, with every money action explainable, bounded, and gated — plus a
full audit trail and a gracefully handled failure case.

## Quick start (VSCode)

1. Open this folder in VSCode.
2. Create a virtual environment (optional but recommended):
   ```
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install razorpay python-dotenv pandas jupyter ipykernel
   ```
4. Open `agentic_commerce.ipynb`, select your Python kernel, and run all cells
   (Run > Run All). No Razorpay keys are required — it runs in **mock mode**
   by default.
5. To use real Razorpay test-mode orders: copy `.env.example` to `.env` and
   fill in your test-mode `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` from the
   Razorpay dashboard, then re-run the notebook. Section 1's output will show
   `Mock mode: False`.

## What each section does

| Section | What it shows |
|---|---|
| 2 | Seed merchant catalog (Wattly Home Appliances) |
| 3 | Agent-readable catalog search & ranking, with a stated reason per pick |
| 4 | Guardrail engine — merchant-set bounds checked before any order fires |
| 5 | Razorpay test-mode order creation (or mock fallback) |
| 6 | HMAC webhook signature verification |
| 7 | Audit logging |
| 8a | Successful purchase, end to end |
| 8b | **Guardrail rejection** — an over-limit discount is declined, not silently dropped |
| 9  | **Tampered webhook rejection** — a modified payload fails signature verification |
| 10 | Full audit trail as a table |

Sections 8b and 9 are the two moments worth demoing live — they're your
concrete proof of "explainable, bounded, gated" with a failure handled
gracefully.
