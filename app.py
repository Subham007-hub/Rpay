import os
import time
import hmac
import hashlib
import uuid
import json
import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
AUDIT_DB_PATH = BASE_DIR / "audit_log.db"

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "demo_webhook_secret_key_123")

POLICY_CONFIG = {
    "max_order_value": int(os.getenv("MAX_ORDER_VALUE_RUPEES", 15000)),
    "max_discount_percent": int(os.getenv("MAX_DISCOUNT_PERCENT", 20)),
    "max_daily_budget": int(os.getenv("MAX_DAILY_BUDGET_RUPEES", 25000)),
}

MOCK_MODE = not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)

razorpay_client = None
if not MOCK_MODE:
    try:
        import razorpay
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except ImportError:
        MOCK_MODE = True

CATALOG = [
    {
        "id": "kettle-steel-1l5",
        "name": "Wattly Electric Steel Kettle 1.5L",
        "category": "kitchen",
        "price_rupees": 1499,
        "discount_percent": 10,
        "rating": 4.5,
        "review_count": 812,
        "stock": 42,
        "merchant_name": "Wattly Official Store",
        "merchant_verified": True,
        "image_url": "/static/images/kettle_steel.jpg",
        "description": "Fast boiling stainless steel electric kettle with automatic shut-off and dry boil protection."
    },
    {
        "id": "kettle-pro-1l7",
        "name": "Wattly Pro Temperature Kettle 1.7L",
        "category": "kitchen",
        "price_rupees": 1899,
        "discount_percent": 5,
        "rating": 4.7,
        "review_count": 205,
        "stock": 9,
        "merchant_name": "Wattly Official Store",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=400&q=80",
        "description": "Precision temperature control glass electric kettle ideal for brewing specialty tea and coffee."
    },
    {
        "id": "airfryer-4l",
        "name": "Wattly Digital Air Fryer 4.2L",
        "category": "kitchen",
        "price_rupees": 5499,
        "discount_percent": 20,
        "rating": 4.8,
        "review_count": 920,
        "stock": 12,
        "merchant_name": "Wattly Official Store",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1585515320310-259814833e62?w=500&q=80",
        "description": "Oil-free rapid air circulation air fryer with 8 preset cooking modes and touchscreen UI."
    },
    {
        "id": "mixer-750w",
        "name": "Wattly Turbo Mixer Grinder 750W",
        "category": "kitchen",
        "price_rupees": 3499,
        "discount_percent": 12,
        "rating": 4.3,
        "review_count": 611,
        "stock": 25,
        "merchant_name": "Wattly Official Store",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1574269909862-7e1d70bb8078?w=400&q=80",
        "description": "Heavy duty 750 watt motor with 3 stainless steel jars for tough Indian grinding."
    },
    {
        "id": "coffee-maker-espresso",
        "name": "Barista Express Espresso Machine 15-Bar",
        "category": "kitchen",
        "price_rupees": 12499,
        "discount_percent": 15,
        "rating": 4.9,
        "review_count": 1150,
        "stock": 6,
        "merchant_name": "BrewMaster Appliances",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=500&q=80",
        "description": "Compact espresso coffee maker with steam milk frother wand for latte and cappuccino."
    },
    {
        "id": "fan-table-16in",
        "name": "Wattly Silent Desk & Table Fan 16-inch",
        "category": "home",
        "price_rupees": 1699,
        "discount_percent": 10,
        "rating": 4.2,
        "review_count": 275,
        "stock": 50,
        "merchant_name": "Wattly Official Store",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=500&q=80",
        "description": "Ultra quiet aerodynamically designed table fan with 3 speed modes and oscillation."
    },
    {
        "id": "heater-fan-2000w",
        "name": "Wattly Ceramic Fan Room Heater 2000W",
        "category": "home",
        "price_rupees": 2299,
        "discount_percent": 6,
        "rating": 4.4,
        "review_count": 158,
        "stock": 21,
        "merchant_name": "Wattly Official Store",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1544816155-12df9643f363?w=400&q=80",
        "description": "Instant PTC ceramic room heater with tip-over safety switch and overheat protection."
    },
    {
        "id": "vacuum-handheld",
        "name": "Wattly Cordless Handheld Vacuum Cleaner",
        "category": "home",
        "price_rupees": 3199,
        "discount_percent": 11,
        "rating": 4.3,
        "review_count": 264,
        "stock": 19,
        "merchant_name": "Wattly Official Store",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1558317374-067fb5f30001?w=400&q=80",
        "description": "Lightweight portable vacuum cleaner with HEPA filter for home and car cleaning."
    },
    {
        "id": "smart-speaker-echo",
        "name": "Echo Smart Audio Hub with Voice Assistant",
        "category": "electronics",
        "price_rupees": 4999,
        "discount_percent": 18,
        "rating": 4.6,
        "review_count": 1420,
        "stock": 35,
        "merchant_name": "SmartTech Direct",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1543512214-318c7553f230?w=400&q=80",
        "description": "Smart speaker with crisp bass, smart home controls, and hands-free voice automation."
    },
    {
        "id": "headphone-anc-wireless",
        "name": "SoundPro Active Noise Cancelling Headphones",
        "category": "electronics",
        "price_rupees": 6999,
        "discount_percent": 14,
        "rating": 4.7,
        "review_count": 530,
        "stock": 14,
        "merchant_name": "AudioGear Official",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&q=80",
        "description": "Premium wireless over-ear headphones with 35dB active noise cancellation and 40h battery life."
    },
    {
        "id": "smartwatch-fitness-hr",
        "name": "FitPulse GPS Smartwatch & Heart Monitor",
        "category": "electronics",
        "price_rupees": 2999,
        "discount_percent": 15,
        "rating": 4.4,
        "review_count": 780,
        "stock": 28,
        "merchant_name": "SmartTech Direct",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&q=80",
        "description": "Waterproof fitness tracking smartwatch with continuous heart rate, SpO2, and built-in GPS."
    },
    {
        "id": "trimmer-beard-pro",
        "name": "Precision Beard & Hair Trimmer Pro",
        "category": "personal_care",
        "price_rupees": 899,
        "discount_percent": 10,
        "rating": 4.3,
        "review_count": 410,
        "stock": 45,
        "merchant_name": "GroomMax India",
        "merchant_verified": True,
        "image_url": "https://images.unsplash.com/photo-1621607512214-68297480165e?w=400&q=80",
        "description": "Self-sharpening stainless steel blades with 20 length settings and fast USB charging."
    },
    {
        "id": "fake-iphone-super-cheap",
        "name": "iPhon 15 Pro Max 1TB (Unverified Deal)",
        "category": "electronics",
        "price_rupees": 4999,
        "discount_percent": 85,
        "rating": 1.2,
        "review_count": 3,
        "stock": 99,
        "merchant_name": "Suspicious-Deals-Store-29",
        "merchant_verified": False,
        "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&q=80",
        "description": "Unbelievable bargain price phone. Unverified seller listing."
    }
]

def init_audit_db():
    conn = sqlite3.connect(AUDIT_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event TEXT NOT NULL,
            details TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_audit_db()

def log_event(event_type, **details):
    conn = sqlite3.connect(AUDIT_DB_PATH)
    conn.execute(
        "INSERT INTO audit_log (timestamp, event, details) VALUES (?, ?, ?)",
        (time.strftime("%Y-%m-%d %H:%M:%S"), event_type, json.dumps(details)),
    )
    conn.commit()
    conn.close()

def get_audit_logs():
    conn = sqlite3.connect(AUDIT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, event, details FROM audit_log ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        try:
            details_obj = json.loads(r[3])
        except Exception:
            details_obj = {"raw": r[3]}
        result.append({
            "id": r[0],
            "timestamp": r[1],
            "event": r[2],
            "details": details_obj
        })
    return result

STOPWORDS = {"i", "a", "the", "want", "good", "buy", "me", "to", "for", "of", "is",
             "are", "and", "an", "in", "on", "under", "below", "less", "than",
             "rupees", "rs", "budget", "please", "get", "some", "need", "looking"}

def extract_budget(text):
    match = re.search(r"(?:under|below|less than|max|budget)\s*(?:rs\.?|rupees)?\s*(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None

def calculate_match_score(product, intent_words):
    name_words = set(re.findall(r"[a-z0-9]+", product["name"].lower()))
    cat_words = set(re.findall(r"[a-z0-9]+", product["category"].lower()))
    desc_words = set(re.findall(r"[a-z0-9]+", product["description"].lower()))
    
    return len(intent_words & name_words) * 3.0 + len(intent_words & cat_words) * 2.0 + len(intent_words & desc_words) * 1.0

def semantic_search_catalog(intent_text, budget_rupees=None, top_n=3):
    if budget_rupees is None:
        budget_rupees = extract_budget(intent_text)

    intent_words = set(re.findall(r"[a-z0-9]+", intent_text.lower())) - STOPWORDS
    if not intent_words:
        return []

    candidates = []
    for product in CATALOG:
        score = calculate_match_score(product, intent_words)
        if score > 0:
            if budget_rupees is None or product["price_rupees"] <= budget_rupees:
                candidates.append((score, product))

    if not candidates:
        return []

    ranked = sorted(candidates, key=lambda x: (x[0], x[1]["rating"], x[1]["discount_percent"]), reverse=True)
    results = []
    for i, (score, p) in enumerate(ranked[:top_n]):
        if i == 0:
            reason = f"highest relevance match ({p['rating']}★ rating)"
        elif p["discount_percent"] == max(c[1]["discount_percent"] for c in ranked[:top_n]):
            reason = f"largest discount ({p['discount_percent']}% off)"
        else:
            reason = f"closest match within budget (Rs.{p['price_rupees']:,})"
        results.append({**p, "rank_reason": reason})
    return results

INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"override\s+limit",
    r"bypass\s+guardrail",
    r"transfer\s+all\s+money",
    r"system\s+prompt",
    r"admin\s+mode",
]

def check_guardrails(order_value_rupees, discount_percent, merchant_verified, intent_text):
    reasons = []
    
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, intent_text, re.IGNORECASE):
            reasons.append(f"SECURITY BLOCK: Prompt injection attempt detected ('{pattern}')")
            break

    if not merchant_verified:
        reasons.append("SECURITY BLOCK: Merchant is unverified or untrusted")

    if order_value_rupees > POLICY_CONFIG["max_order_value"]:
        reasons.append(f"POLICY BLOCK: Order value Rs.{order_value_rupees:,} exceeds max cap of Rs.{POLICY_CONFIG['max_order_value']:,}")

    if discount_percent > POLICY_CONFIG["max_discount_percent"]:
        reasons.append(f"POLICY BLOCK: Discount {discount_percent}% exceeds authorized max of {POLICY_CONFIG['max_discount_percent']}%")

    approved = len(reasons) == 0
    
    if order_value_rupees < 1000:
        tier_code, tier_desc = "TIER_1_AUTO", "Autonomous Auto-Approved (< Rs.1,000)"
    elif order_value_rupees <= 5000:
        tier_code, tier_desc = "TIER_2_NOTIFY", "Auto-Approved with User Notification Logged (Rs.1,000 - Rs.5,000)"
    else:
        tier_code, tier_desc = "TIER_3_HITL", "Requires Explicit Human Confirmation (> Rs.5,000)"

    return approved, reasons, tier_code, tier_desc

def create_razorpay_order(amount_rupees, receipt, product_name, tier_code):
    if MOCK_MODE or razorpay_client is None:
        order_id = f"order_MOCK_{uuid.uuid4().hex[:10]}"
        payment_link = f"https://rzp.io/i/mock_checkout_{uuid.uuid4().hex[:6]}"
        return {
            "id": order_id,
            "amount": amount_rupees * 100,
            "currency": "INR",
            "receipt": receipt,
            "status": "created",
            "payment_link": payment_link,
            "mock": True
        }
    return razorpay_client.order.create({
        "amount": amount_rupees * 100,
        "currency": "INR",
        "receipt": receipt,
        "notes": {"product_name": product_name, "tier": tier_code}
    })

def verify_webhook_signature(payload_body: str, received_signature: str, secret: str) -> bool:
    generated_signature = hmac.new(
        secret.encode("utf-8"),
        payload_body.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_signature, received_signature)


app = FastAPI(title="Agentic Commerce Alexa Voice Web App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/pitch")
async def pitch_presentation():
    return FileResponse(STATIC_DIR / "pitch.html")

@app.get("/api/catalog")
async def get_catalog():
    return CATALOG

@app.get("/api/settings")
async def get_settings():
    return POLICY_CONFIG

@app.post("/api/settings")
async def update_settings(data: dict = Body(...)):
    if "max_order_value" in data:
        POLICY_CONFIG["max_order_value"] = int(data["max_order_value"])
    if "max_discount_percent" in data:
        POLICY_CONFIG["max_discount_percent"] = int(data["max_discount_percent"])
    if "max_daily_budget" in data:
        POLICY_CONFIG["max_daily_budget"] = int(data["max_daily_budget"])
    log_event("policy_updated", config=POLICY_CONFIG)
    return {"status": "success", "config": POLICY_CONFIG}

@app.get("/api/audit-log")
async def fetch_audit_log():
    return get_audit_logs()

@app.post("/api/chat")
async def process_chat(data: dict = Body(...)):
    intent = data.get("intent", "").strip()
    requested_discount = data.get("discount_override")
    human_confirmed = data.get("human_confirmed", False)
    budget = data.get("budget")

    if not intent:
        raise HTTPException(status_code=400, detail="Intent cannot be empty")

    log_event("intent_received", intent=intent, budget=budget)


    matches = semantic_search_catalog(intent, budget_rupees=budget)
    if not matches:
        log_event("no_match", intent=intent)
        speak_msg = f"I'm sorry, I couldn't find any products matching '{intent}' in our catalog."
        return {
            "status": "no_match",
            "speak_text": speak_msg,
            "user_intent": intent,
            "products": []
        }

    top_pick = matches[0]
    discount = requested_discount if requested_discount is not None else top_pick["discount_percent"]
    log_event("catalog_ranked", top_pick=top_pick["name"], reason=top_pick["rank_reason"], candidate_count=len(matches))

    
    approved, reasons, tier_code, tier_desc = check_guardrails(
        order_value_rupees=top_pick["price_rupees"],
        discount_percent=discount,
        merchant_verified=top_pick["merchant_verified"],
        intent_text=intent
    )

    if not approved:
        log_event("order_declined", product=top_pick["name"], reasons=reasons)
        reason_str = ". ".join(reasons)
        speak_msg = f"Purchase declined by security guardrails. {reason_str}"
        return {
            "status": "declined",
            "speak_text": speak_msg,
            "user_intent": intent,
            "products": [top_pick],
            "reasons": reasons
        }

    if tier_code == "TIER_3_HITL" and not human_confirmed:
        log_event("hitl_pending", product=top_pick["name"], price_rupees=top_pick["price_rupees"], tier=tier_code)
        speak_msg = f"I found the {top_pick['name']} for Rs. {top_pick['price_rupees']:,}. Because this exceeds Rs. 5,000, please confirm on screen to proceed with Razorpay checkout."
        return {
            "status": "hitl_required",
            "speak_text": speak_msg,
            "user_intent": intent,
            "products": [top_pick],
            "tier": tier_desc,
            "product_id": top_pick["id"]
        }

    order = create_razorpay_order(
        amount_rupees=top_pick["price_rupees"],
        receipt=f"receipt_{top_pick['id']}",
        product_name=top_pick["name"],
        tier_code=tier_code
    )
    log_event("order_created", product=top_pick["name"], order_id=order["id"], amount_rupees=top_pick["price_rupees"], tier=tier_desc, mock=MOCK_MODE)

    speak_msg = f"Order created successfully for {top_pick['name']} at Rs. {top_pick['price_rupees']:,}. Order ID is {order['id']}."
    if order.get("payment_link"):
        speak_msg += " Click the Razorpay checkout link on your screen to complete payment."

    return {
        "status": "order_created",
        "speak_text": speak_msg,
        "user_intent": intent,
        "products": [top_pick],
        "order": order,
        "tier": tier_desc
    }

@app.post("/api/webhook-test")
async def test_webhook(data: dict = Body(...)):
    order_id = data.get("order_id", "order_MOCK_demo123")
    is_tampered = data.get("tampered", False)

    payload_dict = {"event": "payment.captured", "order_id": order_id, "amount": 1 if is_tampered else 149900}
    payload_body = json.dumps(payload_dict)
    
    valid_sig = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), payload_body.encode(), hashlib.sha256).hexdigest()
    
    if is_tampered:
        fake_payload = json.dumps({"event": "payment.captured", "order_id": order_id, "amount": 1})
        is_valid = verify_webhook_signature(fake_payload, valid_sig, RAZORPAY_WEBHOOK_SECRET)
        log_event("webhook_rejected", order_id=order_id, valid=is_valid, reason="HMAC signature mismatch on tampered payload")
        return {"status": "rejected", "valid": is_valid, "message": "Tampered payload rejected! HMAC signature mismatch."}
    else:
        is_valid = verify_webhook_signature(payload_body, valid_sig, RAZORPAY_WEBHOOK_SECRET)
        log_event("webhook_verified", order_id=order_id)
        return {"status": "verified", "valid": is_valid, "message": "Legitimate webhook verified successfully!"}

if __name__ == "__main__":
    import uvicorn
    print("Starting Alexa Agentic Commerce Web App on http://localhost:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
