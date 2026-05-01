# 🚀 Vera: Data-Driven AI Growth Consultant

**Developed by:** Dinesh Singh
**Tech Stack:** Python, FastAPI, Docker

---

## 📌 Overview

Vera is a **deterministic, stateful AI growth consultant** designed to help magicpin merchants improve business performance.

Instead of relying on external LLM APIs, Vera uses **rule-based intelligence and contextual data** to generate reliable, consistent, and actionable recommendations.

This ensures:

* High reliability in sandboxed environments
* Deterministic outputs for evaluation
* Fast response times without external dependencies

---

## 🏗️ Architecture & Features

### 🔹 Stateful Memory

* In-memory storage for:

  * Merchants
  * Categories
  * Triggers
* Enables context-aware decision making across requests

---

### 🔹 Proactive "Tick" Engine

* Monitors performance triggers
* Generates **proactive campaign suggestions**
* Example:

  * Low engagement → voucher campaign
  * Low conversion → reward strategy

---

### 🔹 Intent-Aware Reply System

Handles merchant responses intelligently:

* Detects readiness (“let’s do it”) → switches to action mode
* Handles low engagement / growth queries
* Detects hostile intent → safely ends conversation
* Handles auto-replies → waits or exits

---

### 🔹 Deterministic Decision Engine

* No randomness
* Same input → same output
* Ensures consistency during evaluation

---

### 🔹 Robust Error Handling

* Graceful fallbacks
* Always returns valid structured JSON
* Prevents system crashes

---

### 🔹 Safety & Compliance

* Filters spam / unsubscribe messages
* Avoids inappropriate or irrelevant suggestions
* Maintains professional communication tone

---

## 🐳 Docker Implementation

### 🔧 Build the image

```bash
docker build -t vera-ai-bot .
```

### ▶️ Run the container

```bash
docker run -p 8000:8000 vera-ai-bot
```

---

## 🛠️ API Endpoints

| Endpoint      | Method | Description                                     |
| ------------- | ------ | ----------------------------------------------- |
| `/v1/context` | POST   | Stores merchant/category/trigger data           |
| `/v1/tick`    | POST   | Generates proactive campaign decisions          |
| `/v1/reply`   | POST   | Handles merchant messages with intent detection |
| `/v1/healthz` | GET    | Health check endpoint                           |

---

## ⚙️ Key Design Decisions

* ❌ No external LLM dependency
* ✅ Fully offline-compatible
* ✅ Deterministic and reliable
* ✅ Optimized for evaluation environments

---

## 🎯 Example Behavior

* Merchant: *“Ok let’s do it. What’s next?”*

* Response:
  → Action mode triggered
  → Suggests campaign with clear next step

* Merchant: *“Stop messaging me”*

* Response:
  → Conversation ends immediately

---

## 📦 Deployment

The application can be deployed on platforms like:

* Render
* Railway
* Any Docker-compatible hosting

Ensure the base URL is accessible for evaluation.

---

## 🧠 Summary

Vera is not just a chatbot—it is a **reliable decision engine** designed to:

* Analyze merchant context
* React to performance signals
* Deliver actionable business insights

All while maintaining **speed, consistency, and robustness**.

---
