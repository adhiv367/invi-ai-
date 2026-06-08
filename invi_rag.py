import json
import requests

GROQ_API_KEY = "GROQ_API_KEY"

COMPANY_INFO = """
Company: Invi Creation
Type: Women's Boutique
Products: Cotton Kurthi, Cotton Kurthi Set, Salwar Suit Set
Price Range: Rs.725 - Rs.1899
Sizes: XS, S, M, L, XL, 2XL, 3XL, 4XL, 5XL
Fabric: Pure Cotton
Care: Hand wash / Machine washable
"""

def load_products():
    with open('invi_products.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def search(query, products, top_k=5):
    query_words = set(query.lower().split())
    scores = []
    for p in products:
        doc_words = set(p['text'].lower().split())
        common = query_words.intersection(doc_words)
        score = len(common)
        scores.append((score, p['text']))
    scores.sort(reverse=True)
    return [text for _, text in scores[:top_k]]

def ask_groq(query, context):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""You are a helpful shopping assistant for Invi Creation, a women's boutique selling pure cotton kurthi, kurthi sets and salwar sets.

Company Info:
{COMPANY_INFO}

Relevant Products:
{chr(10).join(context)}

Customer Question: {query}

Instructions:
- Reply in a friendly, helpful tone like a boutique staff
- Show matching products with name, price, SKU and image link
- If asking about sizes, mention we have XS to 5XL
- If asking to place order, ask for their size and preferred product
- Keep reply short and clear
- Reply in the same language the customer uses (Tamil or English)
- Always end with: "Reply with your size to place order! 🛍️"

Answer:"""

    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=body
    )
    result = response.json()
    return result['choices'][0]['message']['content']

print("=" * 50)
print("   Invi Creation - AI Shopping Assistant")
print("=" * 50)

products = load_products()
print(f"Loaded {len(products)} products.")
print("Type your question or 'quit' to exit\n")

while True:
    query = input("Customer: ")
    if query.lower() == 'quit':
        break
    context = search(query, products)
    answer = ask_groq(query, context)
    print(f"\nInvi Creation AI: {answer}\n")
    print("-" * 40)