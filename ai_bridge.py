from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import requests
import os
import re
import base64

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ── Quick greeting cache ──────────────────────────────────────────────────────
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

# ── Company details ───────────────────────────────────────────────────────────
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
    sku_upper = sku.upper().strip()
    for p in products:
        text = p["text"].upper()
        if (f"SKU: {sku_upper}" in text or
            f"ALL SKUS: {sku_upper}" in text or
            f", {sku_upper}," in text or
            f": {sku_upper}," in text or
            f", {sku_upper}\n" in text):
            return p
    return None


def parse_product_details(product):
    text = product["text"]
    details = {}
    for line in text.split("\n"):
        if ": " in line:
            key, value = line.split(": ", 1)
            details[key.strip()] = value.strip()
    return details


def build_product_reply(details):
    name     = details.get("Product", "Product")
    sku      = details.get("SKU", "")
    price    = details.get("Price", "")
    fabric   = details.get("Fabric", "")
    sizes    = details.get("Available Sizes", "")
    sleeve   = details.get("Sleeve Options", "")
    neckline = details.get("Neckline Options", "")
    status   = details.get("Status", "Available")
    image    = details.get("Image", "")

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
    prompt = f"""You are a WhatsApp sales assistant for Invi Creation, a women's clothing boutique in Tamil Nadu.

STRICT RULES — follow exactly:
1. NEVER start with Namaste, Salam, Selvam, Hello, Hi, Vanakkam or any greeting.
2. NEVER say "I'd be happy to help", "Please let me know", "Which one catches your eye", "Our products include" — banned phrases.
3. Just answer the question directly. No intro. No outro.
4. Max 4 lines. No long paragraphs.
5. If customer asks for a product type, show max 3 options: Name - Price - SKU only.
6. Match the customer's language — Tamil, Tanglish or English.

Products:
{chr(10).join(context)}

Customer: {query}
Reply:"""

    body = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=body
    )
    return response.json()["choices"][0]["message"]["content"]


def analyse_image_and_reply(image_url, customer_message, products, meta_token=None):
    """
    Download customer image (with Meta Bearer auth if token provided)
    → send to Groq Vision → match to catalogue → reply with availability
    """
    try:
        # Download image — Meta media URLs require Authorization header
        download_headers = {}
        if meta_token:
            download_headers["Authorization"] = f"Bearer {meta_token}"

        img_response = requests.get(image_url, headers=download_headers, timeout=15)
        img_response.raise_for_status()

        img_b64      = base64.standard_b64encode(img_response.content).decode("utf-8")
        content_type = img_response.headers.get("Content-Type", "image/jpeg").split(";")[0]

        # Build short catalogue summary for Groq Vision context
        catalogue_lines = []
        for p in products:
            lines      = p["text"].split("\n")
            name       = lines[0].replace("Product: ", "")
            sku_line   = next((l for l in lines if l.startswith("SKU: ")),   "")
            price_line = next((l for l in lines if l.startswith("Price: ")), "")
            tags_line  = next((l for l in lines if l.startswith("Tags: ")),  "")
            catalogue_lines.append(f"{name} | {sku_line} | {price_line} | {tags_line}")
        catalogue_text = "\n".join(catalogue_lines)

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        system_prompt = """You are a helpful assistant for Invi Creation, a women's clothing boutique in Tamil Nadu, India.
When a customer sends a dress/kurthi/salwar image:
1. Look at the dress carefully — note type (kurthi/salwar set/coord set), color, pattern, design
2. Check if a similar product exists in the catalogue
3. Reply in this exact format:

If SIMILAR product FOUND in catalogue:
✅ We have a similar design available!
👗 [Product Name]
🏷️ SKU: [SKU code]
💰 [Price]
✂️ Yes, we can modify this design for you!
📞 Contact us: 9751100905

If NOT FOUND in catalogue:
😊 We don't have this exact design right now, but we can create a similar one for you!
✂️ We do custom modifications and stitching!
📞 Contact us for custom orders: 9751100905

Keep reply short and friendly. Use Tamil or English based on customer's message."""

        body = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{img_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Customer message: {customer_message}\n\nOur product catalogue:\n{catalogue_text}\n\nAnalyse the dress in the image and reply to the customer."
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30
        )
        result     = resp.json()
        reply_text = result["choices"][0]["message"]["content"]
        print(f"[IMAGE ANALYSIS] Done")
        return reply_text

    except Exception as e:
        print(f"[IMAGE ANALYSIS ERROR] {e}")
        return (
            "Thank you for sharing the image! 😊\n"
            "Our team will check and get back to you shortly.\n"
            "For quick help: 9751100905"
        )


# ── Main endpoint ─────────────────────────────────────────────────────────────
@app.route("/ai", methods=["POST"])
def ai_reply():
    data       = request.json
    message    = data.get("message", "").strip()
    image      = data.get("image",      None)   # WhatsApp image download URL
    meta_token = data.get("meta_token", None)   # Bearer token for Meta image download

    if not message and not image:
        return jsonify({"reply": "", "image": None, "type": "text"})

    msg_lower = message.lower().strip() if message else ""

    # ── 1. Customer sent an IMAGE ─────────────────────────────────────────────
    if image:
        print(f"[IMAGE] Received customer image")
        products = load_products()
        reply = analyse_image_and_reply(
            image,
            message or "Is this available?",
            products,
            meta_token=meta_token      # ← pass token for authenticated download
        )
        return jsonify({"reply": reply, "image": None, "type": "text"})

    # ── 2. Greeting cache ─────────────────────────────────────────────────────
    if msg_lower in QUICK_REPLIES:
        print(f"[CACHE] {message}")
        return jsonify({"reply": QUICK_REPLIES[msg_lower], "image": None, "type": "text"})

    # ── 3. Company details ────────────────────────────────────────────────────
    if any(kw in msg_lower for kw in COMPANY_KEYWORDS):
        print(f"[COMPANY] {message}")
        return jsonify({"reply": COMPANY_REPLY, "image": None, "type": "text"})

    # ── 4. SKU detection ──────────────────────────────────────────────────────
    sku_match = re.search(r'\b(ICK\d+|ICS\d+|ICC\d+)\b', message, re.IGNORECASE)
    if sku_match:
        sku      = sku_match.group(1).upper()
        products = load_products()
        product  = find_product_by_sku(sku, products)
        if product:
            details = parse_product_details(product)
            reply, image_url = build_product_reply(details)
            print(f"[SKU] {sku} → {details.get('Product', '')}")
            return jsonify({"reply": reply, "image": image_url, "type": "product"})
        else:
            return jsonify({
                "reply": f"Sorry, I could not find product *{sku}*. Please check the SKU and try again. Browse at https://www.invicreation.com 😊",
                "image": None,
                "type": "text"
            })

    # ── 5. General question → Groq ────────────────────────────────────────────
    products = load_products()
    context  = search(message, products)
    reply    = ask_groq(message, context)
    print(f"[GROQ] {message}")
    return jsonify({"reply": reply, "image": None, "type": "text"})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "AI bridge running"})


if __name__ == "__main__":
    print("AI Bridge started on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
