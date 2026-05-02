from fastapi import FastAPI, Request
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vera")

app = FastAPI()

storage = {
    "merchants": {},
    "categories": {},
    "triggers": {}
}

INTENT_PHRASES = [
    "let's do it", "lets do it", "what's next", "whats next",
    "sign me up", "proceed", "sounds good", "i'm in", "im in",
    "let's go", "lets go", "do it", "start now", "get started"
]

# ---------- Helper Logic ----------

def get_name_prefix(merchant):
    name = merchant.get("name", "").strip()
    return f"{name}. " if name else ""

def get_campaign_recommendation(trigger_reason: str, merchant: dict):
    prefix = get_name_prefix(merchant)
    category = merchant.get("category", "business")

    reason = trigger_reason.lower()

    if "low" in reason:
        return {
            "body": f"{prefix}Your {category} visibility is low. Run a 10% voucher campaign to increase views and transactions.",
            "cta": "Create Voucher"
        }
    elif "conversion" in reason:
        return {
            "body": f"{prefix}Improve conversions by offering cashback rewards to encourage more purchases.",
            "cta": "Add Reward"
        }
    else:
        return {
            "body": f"{prefix}Boost your {category} growth using targeted campaigns like vouchers or profile promotions.",
            "cta": "View Campaigns"
        }

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
        "model_name": "deterministic-rule-engine",
        "description": "Vera AI - Rule-Based Growth Consultant"
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

        return {"accepted": True}
    except Exception as e:
        logger.error(e)
        return {"accepted": False}

@app.post("/v1/tick")
async def handle_tick(request: Request):
    try:
        data = await request.json()
        triggers = data.get("available_triggers", [])

        if not triggers:
            return {"decision": "no-op"}

        tid = triggers[0]
        trigger_info = storage["triggers"].get(tid, {})

        merchant_id = trigger_info.get("merchant_id")
        merchant = storage["merchants"].get(merchant_id, {})

        if not merchant and storage["merchants"]:
            merchant = list(storage["merchants"].values())[0]

        recommendation = get_campaign_recommendation(
            trigger_info.get("reason", "low engagement"),
            merchant
        )

        return {
            "decision": "send",
            "body": recommendation["body"],
            "cta": recommendation["cta"],
            "trigger_id": tid,
            "merchant_id": merchant_id
        }

    except Exception as e:
        logger.error(e)
        return {"decision": "no-op"}

@app.post("/v1/reply")
async def handle_reply(request: Request):
    try:
        data = await request.json()
        msg = data.get("message", "")
        merchant_id = data.get("merchant_id")
        turn = data.get("turn_number", 1)

        intent = detect_intent(msg)

        merchant = storage["merchants"].get(merchant_id, {})

        if not merchant and storage["merchants"]:
            merchant = list(storage["merchants"].values())[0]

        prefix = get_name_prefix(merchant)
        category = merchant.get("category", "business")

        # STOP
        if intent == "stop":
            return {"action": "end"}

        # AUTO REPLY DETECTION
        if any(w in msg.lower() for w in ["shortly", "thank", "automated"]):
            if turn >= 4:
                return {"action": "end"}
            return {"action": "wait", "wait_seconds": 3600}

        # READY → ACTION MODE (FIXED)
        if intent == "ready":
            return {
                "action": "send",
                "body": f"Done {prefix}Next step: Launch a 10% voucher campaign for your {category}. This can drive up to 3x more footfall within a week.",
                "cta": "Launch Campaign",
                "send_as": "vera"
            }

        # LOW ENGAGEMENT
        if intent == "low_engagement":
            return {
                "action": "send",
                "body": f"{prefix}Your {category} visibility is low. Run a targeted voucher campaign to improve reach.",
                "cta": "Create Voucher",
                "send_as": "vera"
            }

        # GROWTH
        if intent == "growth":
            return {
                "action": "send",
                "body": f"{prefix}To grow your {category}, use profile boosts and limited-time offers to attract more customers.",
                "cta": "Boost Profile",
                "send_as": "vera"
            }

        # FOOTFALL
        if intent == "footfall":
            return {
                "action": "send",
                "body": f"{prefix}Increase footfall by offering cashback rewards to encourage repeat visits.",
                "cta": "Add Reward",
                "send_as": "vera"
            }

        # DEFAULT
        return {
            "action": "send",
            "body": f"{prefix}Improve your {category} performance using campaigns like vouchers and rewards.",
            "cta": "View Dashboard",
            "send_as": "vera"
        }

    except Exception as e:
        logger.error(e)
        return {
            "action": "send",
            "body": "Let’s review your performance and launch a campaign to boost growth.",
            "cta": "Open Dashboard",
            "send_as": "vera"
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)