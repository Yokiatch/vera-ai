from fastapi import FastAPI, Request
import uvicorn
import logging
import httpx
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vera")

app = FastAPI()

# ---------- Storage ----------
storage = {
    "merchant": {},
    "category": {},
    "trigger": {},
    "merchant_profile": {},
    "customer_segment": {},
    "offer": {},
    "demand_signals": {},
}

INTENT_PHRASES = [
    "let's do it", "lets do it", "what's next", "whats next",
    "sign me up", "proceed", "sounds good", "i'm in", "im in",
    "let's go", "lets go", "do it", "start now", "get started"
]

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-20b"

# ---------- LLM message composer ----------

async def compose_message(situation: str, merchant: dict, category: dict,
                           trigger: dict, segment: dict = None,
                           offer: dict = None, demand: dict = None) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")

    identity = merchant.get("identity", {})
    name = identity.get("name", merchant.get("name", ""))
    owner = identity.get("owner_first_name", "")
    locality = identity.get("locality", identity.get("location", ""))
    languages = identity.get("languages", ["en"])

    perf = merchant.get("performance", demand or {})
    views = perf.get("views", "")
    ctr = perf.get("ctr", "")
    calls = perf.get("calls", "")
    delta = perf.get("delta_7d", {})

    signals = merchant.get("signals", [])
    active_offers = [o.get("title") for o in merchant.get("offers", [])
                     if o.get("status") == "active"]
    if offer:
        active_offers.append(offer.get("description", ""))

    review_themes = merchant.get("review_themes", [])
    conv_history = merchant.get("conversation_history", [])
    last_msg = conv_history[-1].get("body", "") if conv_history else ""

    cat_voice = category.get("voice", {})
    tone = cat_voice.get("tone", "professional")
    taboos = cat_voice.get("vocab_taboo", [])
    cat_slug = category.get("slug", merchant.get("category", "business"))

    trigger_kind = trigger.get("kind", situation)
    trigger_payload = trigger.get("payload", {})
    urgency = trigger.get("urgency", 3)

    seg = segment or {}
    seg_type = seg.get("type", "")
    seg_detail = seg.get("detail", "")

    lang_note = "Respond in Hindi if merchant prefers Hindi." if "hi" in languages else ""

    prompt = f"""You are Vera, magicpin's AI growth consultant. Write a short WhatsApp message (max 2 sentences, under 160 chars) to send to a merchant.

MERCHANT CONTEXT:
- Business: {name}{f', {locality}' if locality else ''}
- Owner: {owner or 'unknown'}
- Category: {cat_slug} | Tone: {tone}
- Performance (30d): views={views}, calls={calls}, CTR={ctr}
- 7-day trend: {delta}
- Signals: {', '.join(signals) if signals else 'none'}
- Active offers: {', '.join(active_offers) if active_offers else 'none'}
- Review issues: {[r.get('theme') for r in review_themes if r.get('sentiment') == 'neg'][:3]}
- Last conversation: "{last_msg[:100]}" (if any)

TRIGGER (WHY NOW):
- Kind: {trigger_kind}
- Payload: {trigger_payload}
- Urgency: {urgency}/5

CUSTOMER SEGMENT: {seg_type}{f' — {seg_detail}' if seg_detail else ' (not specified)'}

RULES:
- Be specific — use actual numbers from context, NOT generic advice
- Be urgent — connect to the trigger payload
- Match the {tone} tone, avoid: {taboos[:5]}
- Include one clear CTA
- Max 2 sentences, under 160 characters
- DO NOT fabricate data not in context
{lang_note}

Respond with ONLY the message text."""

    if not api_key:
        return _fallback_message(situation, name, cat_slug, active_offers, signals)

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://magicpin.com"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "max_tokens": 150,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": "You are Vera, magicpin's AI growth consultant. Write concise, high-compulsion merchant messages."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"LLM call failed, using fallback: {e}")
        return _fallback_message(situation, name, cat_slug, active_offers, signals)


def _fallback_message(situation: str, name: str, category: str,
                      active_offers: list, signals: list) -> str:
    prefix = f"{name}: " if name else ""
    offer_part = f" — {active_offers[0]}" if active_offers else ""
    signal_part = f" ({signals[0]})" if signals else ""
    sit = situation.lower()
    if "low" in sit or "engagement" in sit:
        return f"{prefix}Your visibility is below peers{signal_part}. Launch a voucher campaign{offer_part} to regain reach today."
    elif "conversion" in sit:
        return f"{prefix}Boost conversions{offer_part} — add a cashback reward to turn views into visits."
    elif "ready" in sit or "growth" in sit:
        return f"{prefix}Great move! Run a limited-time {category} campaign{offer_part} to drive 3x more footfall this week."
    elif "footfall" in sit or "research" in sit:
        return f"{prefix}New demand signal detected{signal_part}. Activate{offer_part} now to capture the surge."
    else:
        return f"{prefix}Your {category} performance has room to grow. Launch a targeted campaign{offer_part} today."


# ---------- Helper logic ----------

def get_context(merchant_id: str):
    merchant = (
        storage["merchant"].get(merchant_id)
        or storage["merchant_profile"].get(merchant_id)
        or {}
    )
    if not merchant:
        for s in ("merchant", "merchant_profile"):
            if storage[s]:
                merchant = list(storage[s].values())[0]
                break

    cat_slug = merchant.get("category_slug") or merchant.get("category", "")
    category = storage["category"].get(cat_slug, {})
    segment = storage["customer_segment"].get(merchant_id, {})
    offer = storage["offer"].get(merchant_id, {})
    demand = storage["demand_signals"].get(merchant_id, {})
    return merchant, category, segment, offer, demand


def detect_intent(msg: str):
    msg = msg.lower()
    if any(w in msg for w in ["stop", "spam", "unsubscribe"]):
        return "stop"
    if any(phrase in msg for phrase in INTENT_PHRASES):
        return "ready"
    if "not getting" in msg or "low" in msg:
        return "low_engagement"
    if "grow" in msg or "increase" in msg:
        return "growth"
    if "customers" in msg or "footfall" in msg:
        return "footfall"
    return "general"


def pick_cta(situation: str) -> str:
    sit = situation.lower()
    if "low" in sit or "engagement" in sit:
        return "Create Voucher"
    elif "conversion" in sit:
        return "Add Reward"
    elif "ready" in sit:
        return "Launch Campaign"
    elif "growth" in sit:
        return "Boost Profile"
    elif "footfall" in sit:
        return "Add Reward"
    else:
        return "View Dashboard"


# ---------- Routes ----------

@app.get("/")
async def root():
    return {
        "message": "Vera AI Growth Consultant API is running",
        "health": "/v1/healthz"
    }


@app.get("/v1/healthz")
async def health_check():
    return {"status": "ok"}


@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": "Dinesh",
        "model": "vera-llm-rule-hybrid",
        "model_name": "vera-llm-rule-hybrid",
        "description": "Vera AI — LLM message composer with rule-based decision engine",
        "context_layers": ["merchant", "category", "trigger", "customer_segment"]
    }


@app.post("/v1/context")
async def handle_context(request: Request):
    try:
        data = await request.json()
        scope = data.get("scope")
        cid = data.get("context_id")
        payload = data.get("payload", {})

        if scope in storage and cid:
            storage[scope][cid] = payload
            return {"accepted": True, "scope": scope, "context_id": cid}

        return {"accepted": False, "reason": f"unknown scope '{scope}' or missing context_id"}
    except Exception as e:
        logger.error(e)
        return {"accepted": False}


@app.post("/v1/tick")
async def handle_tick(request: Request):
    try:
        data = await request.json()
        trigger_ids = data.get("available_triggers", [])

        if not trigger_ids:
            return {"actions": []}

        actions = []
        for tid in trigger_ids:
            trigger = storage["trigger"].get(tid, {})
            merchant_id = trigger.get("merchant_id")
            customer_id = trigger.get("customer_id")

            merchant, category, segment, offer, demand = get_context(merchant_id)
            situation = trigger.get("kind", "low engagement")

            body = await compose_message(
                situation, merchant, category, trigger, segment, offer, demand
            )

            actions.append({
                "decision": "send",
                "body": body,
                "cta": pick_cta(situation),
                "send_as": "vera",
                "trigger_id": tid,
                "merchant_id": merchant_id,
                "customer_id": customer_id
            })

        return {"actions": actions}

    except Exception as e:
        logger.error(e)
        return {"actions": []}


@app.post("/v1/reply")
async def handle_reply(request: Request):
    try:
        data = await request.json()
        msg = data.get("message", "")
        merchant_id = data.get("merchant_id")
        turn = data.get("turn_number", 1)

        intent = detect_intent(msg)
        merchant, category, segment, offer, demand = get_context(merchant_id)

        if intent == "stop":
            return {"action": "end"}

        if any(w in msg.lower() for w in ["shortly", "thank", "automated"]):
            if turn >= 4:
                return {"action": "end"}
            return {"action": "wait", "wait_seconds": 3600}

        body = await compose_message(
            intent, merchant, category, {}, segment, offer, demand
        )

        return {
            "action": "send",
            "body": body,
            "cta": pick_cta(intent),
            "send_as": "vera"
        }

    except Exception as e:
        logger.error(e)
        return {
            "action": "send",
            "body": "Let's review your performance and launch a campaign to boost growth.",
            "cta": "Open Dashboard",
            "send_as": "vera"
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
