import openai
import yaml
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
        model="text-embedding-3-small"
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
    import sys

    # Check if user wants to embed from database instead of YAML
    if len(sys.argv) > 1 and sys.argv[1] == "--from-db":
        print("📊 Loading FAQs from database...")
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')
        django.setup()
        from chatbot.models import FAQEntry

        db_faqs = FAQEntry.objects.all()
        faqs = []
        for faq in db_faqs:
            faq_dict = {
                'question': faq.question,
                'answer': faq.answer,
            }
            if faq.lessons_only:
                faq_dict['lessons_only'] = True
            faqs.append(faq_dict)
        print(f"✅ Loaded {len(faqs)} FAQs from database")
    else:
        print("📖 Loading FAQs from YAML file...")
        faqs = load_faqs()
        print(f"✅ Loaded {len(faqs)} FAQs from YAML")

    faqs = embed_faqs(faqs)
    save_to_json(faqs)
    print("✅ All FAQs embedded and saved.")
