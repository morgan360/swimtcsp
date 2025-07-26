import openai
import yaml
import json
import os
import time
from pathlib import Path

# ✅ Use OpenAI's v1 client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 📂 Define file paths
BASE_DIR = Path(__file__).resolve().parent
FAQ_YAML_PATH = BASE_DIR / "chatbot" / "data" / "faq.yaml"
FAQ_JSON_PATH = BASE_DIR / "chatbot" / "data" / "faq_with_embeddings.json"

# 📘 Load FAQ YAML
def load_faqs(path=FAQ_YAML_PATH):
    with open(path, "r") as f:
        return yaml.safe_load(f)

# 🔠 Get embedding via OpenAI v1 API
def get_embedding(text):
    time.sleep(1)
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

# 🧠 Embed all FAQs
def embed_faqs(faqs):
    for faq in faqs:
        print(f"Embedding: {faq['question']}")
        faq["embedding"] = get_embedding(faq["question"])
    return faqs

# 💾 Save output
def save_to_json(faqs, path=FAQ_JSON_PATH):
    with open(path, "w") as f:
        json.dump(faqs, f, indent=2)
    print(f"✅ Saved to {path}")

if __name__ == "__main__":
    faqs = load_faqs()
    faqs = embed_faqs(faqs)
    save_to_json(faqs)
    print("✅ All FAQs embedded and saved.")
