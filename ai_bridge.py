from flask import Flask, request, jsonify
import json
import requests

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def load_products():
    with open("invi_products.json", "r", encoding="utf-8") as f:
        return json.load(f)

def search(query, products, top_k=5):
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
    prompt = f"""You are a WhatsApp shopping assistant for Invi Creation,
a women's boutique selling pure cotton kurthi, kurthi sets and salwar sets.
Price range: Rs.725 - Rs.1899. Sizes: XS to 5XL.

Relevant Products:
{chr(10).join(context)}

Customer message: {query}

Instructions:
- Reply friendly and short like a boutique staff on WhatsApp
- If customer says hi or hello, greet them and introduce Invi Creation
- Show product name, price, SKU if relevant
- If asking about order, ask for their size
- Reply in same language as customer (Tamil or English)
- Always end with a call to action

Answer:"""

    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300
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
    message = data.get("message", "")
    if not message:
        return jsonify({"reply": ""})
    products = load_products()
    context = search(message, products)
    reply = ask_groq(message, context)
    return jsonify({"reply": reply})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "AI bridge running"})

if __name__ == "__main__":
    print("AI Bridge started on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)