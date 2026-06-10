from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import requests
import os

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ── Cache for common greetings — no Groq call needed ──
QUICK_REPLIES = {
    "hi":       "Vanakkam! Welcome to Invi Creation 👗 We sell pure cotton kurthi, kurthi sets & salwar sets. Price: Rs.725-1899. Sizes: XS-5XL. What are you looking for?",
    "hii":      "Vanakkam! Welcome to Invi Creation 👗 We sell pure cotton kurthi, kurthi sets & salwar sets. Price: Rs.725-1899. Sizes: XS-5XL. What are you looking for?",
    "hiii":     "Vanakkam! Welcome to Invi Creation 👗 We sell pure cotton kurthi, kurthi sets & salwar sets. Price: Rs.725-1899. Sizes: XS-5XL. What are you looking for?",
    "hello":    "Hello! Welcome to Invi Creation 👗 Pure cotton kurthi, kurthi sets & salwar sets. Price: Rs.725-1899. Sizes: XS-5XL. How can I help you?",
    "hey":      "Hey! Welcome to Invi Creation 👗 Pure cotton kurthi & salwar sets. Price: Rs.725-1899. Sizes: XS-5XL. What are you looking for?",
    "heyy":     "Hey! Welcome to Invi Creation 👗 Pure cotton kurthi & salwar sets. Price: Rs.725-1899. Sizes: XS-5XL. What are you looking for?",
    "vanakkam": "Vanakkam! Invi Creation-la vanga 👗 Pure cotton kurthi, kurthi sets, salwar sets. Rs.725 mudhal thodangiradhu. Enna vennum?",
    "hai":      "Vanakkam! Welcome to Invi Creation 👗 Pure cotton kurthi & salwar sets. Rs.725-1899. Sizes: XS-5XL. What are you looking for?",
    "ok":       "Sure! Tell me what you are looking for — kurthi, kurthi set, or salwar set? I will show you the best options 😊",
    "okay":     "Sure! Tell me what you are looking for — kurthi, kurthi set, or salwar set? I will show you the best options 😊",
    "thanks":   "Thank you for contacting Invi Creation 😊 Feel free to message anytime!",
    "thank you":"Thank you for contacting Invi Creation 😊 Feel free to message anytime!",
    "bye":      "Thank you for visiting Invi Creation 😊 Come back anytime! Have a great day!",
}

def load_products():
    with open("invi_products.json", "r", encoding="utf-8") as f:
        return json.load(f)

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
        return jsonify({"reply": ""})

    # Check cache first — no Groq call needed for greetings
    msg_lower = message.lower().strip()
    if msg_lower in QUICK_REPLIES:
        print(f"[CACHE] Reply to: {message}")
        return jsonify({"reply": QUICK_REPLIES[msg_lower]})

    # Call Groq only for real product questions
    products = load_products()
    context = search(message, products)
    reply = ask_groq(message, context)
    print(f"[GROQ] Reply to: {message}")
    return jsonify({"reply": reply})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "AI bridge running"})

if __name__ == "__main__":
    print("AI Bridge started on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)