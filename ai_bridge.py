from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import requests
import os
import re

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ── Cache for common greetings — no Groq tokens used ──
QUICK_REPLIES = {
    "hi":        "Vanakkam! Welcome to Invi Creation 👗 Pure cotton kurthi, kurthi sets & salwar sets. Rs.725-1899. Sizes XS-5XL.\n\nWhat are you looking for today?",
    "hii":       "Vanakkam! Welcome to Invi Creation 👗 Pure cotton kurthi, kurthi sets & salwar sets. Rs.725-1899. Sizes XS-5XL.\n\nWhat are you looking for today?",
    "hiii":      "Vanakkam! Welcome to Invi Creation 👗 Pure cotton kurthi, kurthi sets & salwar sets. Rs.725-1899. Sizes XS-5XL.\n\nWhat are you looking for today?",
    "hello":     "Hello! Welcome to Invi Creation 👗 Pure cotton kurthi, kurthi sets & salwar sets. Rs.725-1899. Sizes XS-5XL.\n\nHow can I help you?",
    "hey":       "Hey! Welcome to Invi Creation 👗 Pure cotton kurthi & salwar sets. Rs.725-1899. Sizes XS-5XL.\n\nWhat are you looking for?",
    "heyy":      "Hey! Welcome to Invi Creation 👗 Pure cotton kurthi & salwar sets. Rs.725-1899. Sizes XS-5XL.\n\nWhat are you looking for?",
    "vanakkam":  "Vanakkam! Invi Creation-la vanga 👗 Pure cotton kurthi, kurthi sets, salwar sets. Rs.725 mudhal. Enna vennum?",
    "hai":       "Vanakkam! Welcome to Invi Creation 👗 Pure cotton kurthi & salwar sets. Rs.725-1899. Sizes XS-5XL.\n\nWhat are you looking for?",
    "ok":        "Sure! Tell me what you are looking for — kurthi, kurthi set, or salwar set? I will show you the best options 😊",
    "okay":      "Sure! Tell me what you are looking for — kurthi, kurthi set, or salwar set? I will show you the best options 😊",
    "thanks":    "Thank you for contacting Invi Creation 😊 Feel free to message anytime!",
    "thank you": "Thank you for contacting Invi Creation 😊 Feel free to message anytime!",
    "bye":       "Thank you for visiting Invi Creation 😊 Come back anytime! Have a great day!",
}

# ── Company details ──
COMPANY_KEYWORDS = [
    "company", "address", "location", "where are you", "contact",
    "phone", "email", "website", "about", "shop", "store",
    "kadai", "enge irukeenga", "details", "info", "office"
]

COMPANY_REPLY = """🏪 *Invi Creation*

🌐 Website: https://www.invicreation.com
📞 Phone: 9751100905
📧 Email: invi0905@gmail.com

📍 Address:
144, Vellakkal Medu, Post,
Near Manjal Vaniga Valagam, Nasiyanur,
Near Standard Roofs,
Erode - 638107, Tamil Nadu, India

🕐 Feel free to visit us or order online!
For orders, just tell us the product SKU and your size 😊"""


def load_products():
    with open("invi_products.json", "r", encoding="utf-8") as f:
        return json.load(f)


def find_product_by_sku(sku, products):
    """Find exact product by SKU code like ICK00020 or ICS00118"""
    sku_upper = sku.upper().strip()
    for p in products:
        if sku_upper in p["text"].upper():
            return p
    return None


def parse_product_details(product):
    """Extract structured details from product text"""
    text = product["text"]
    details = {}

    for line in text.split("\n"):
        if ": " in line:
            key, value = line.split(": ", 1)
            details[key.strip()] = value.strip()

    return details


def build_product_reply(details):
    """Build a clean WhatsApp-style product reply"""
    name = details.get("Product", "Product")
    sku = details.get("SKU", "")
    price = details.get("Price", "")
    fabric = details.get("Fabric", "")
    sizes = details.get("Available Sizes", "")
    sleeve = details.get("Sleeve Options", "")
    neckline = details.get("Neckline Options", "")
    status = details.get("Status", "Available")
    image = details.get("Image", "")

    reply = f"""👗 *{name}*

🏷️ SKU: {sku}
💰 Price: {price}
🧵 Fabric: {fabric}
📏 Sizes: {sizes.upper()}
👚 Sleeve: {sleeve}
👔 Neckline: {neckline}
✅ Status: {status}

To order, reply with your *size* and we will process it! 😊"""

    return reply, image


def search(query, products, top_k=3):
    query_words = set(query.lower().split())
    scores = []
    for p in products:
        doc_words = set(p["text"].lower().split())
        score = len(query_words.intersection(doc_words))
        scores.append((score, p["text"]))
    scores.sort(reverse=True)
    return [text for _, text in scores[:top_k]]


def ask_groq(query, context):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""Invi Creation boutique assistant. Cotton kurthi/salwar sets. Rs.725-1899. XS-5XL.
Products: {', '.join(context)}
Customer: {query}
Reply short, friendly, Tamil or English. Show name+price+SKU if relevant."""

    body = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=body
    )
    return response.json()["choices"][0]["message"]["content"]


@app.route("/ai", methods=["POST"])
def ai_reply():
    data = request.json
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"reply": "", "image": None, "type": "text"})

    msg_lower = message.lower().strip()

    # ── 1. Greeting cache — no Groq call ──
    if msg_lower in QUICK_REPLIES:
        print(f"[CACHE] {message}")
        return jsonify({
            "reply": QUICK_REPLIES[msg_lower],
            "image": None,
            "type": "text"
        })

    # ── 2. Company details ──
    if any(kw in msg_lower for kw in COMPANY_KEYWORDS):
        print(f"[COMPANY] {message}")
        return jsonify({
            "reply": COMPANY_REPLY,
            "image": None,
            "type": "text"
        })

    # ── 3. SKU detection — send image + details ──
    sku_match = re.search(r'\b(ICK\d+|ICS\d+|ICC\d+)\b', message, re.IGNORECASE)
    if sku_match:
        sku = sku_match.group(1).upper()
        products = load_products()
        product = find_product_by_sku(sku, products)
        if product:
            details = parse_product_details(product)
            reply, image_url = build_product_reply(details)
            print(f"[SKU] {sku} → {details.get('Product', '')}")
            return jsonify({
                "reply": reply,
                "image": image_url,
                "type": "product"
            })
        else:
            return jsonify({
                "reply": f"Sorry, I could not find product *{sku}*. Please check the SKU and try again. You can browse our collection at https://www.invicreation.com 😊",
                "image": None,
                "type": "text"
            })

    # ── 4. General question — call Groq ──
    products = load_products()
    context = search(message, products)
    reply = ask_groq(message, context)
    print(f"[GROQ] {message}")
    return jsonify({
        "reply": reply,
        "image": None,
        "type": "text"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "AI bridge running"})


if __name__ == "__main__":
    print("AI Bridge started on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)