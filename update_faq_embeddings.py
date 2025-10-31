"""
Update FAQ embeddings in database from JSON file
Run this after embed_faqs.py to sync embeddings to database
"""
import django
import os
import sys
from pathlib import Path
import json

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')
django.setup()

from chatbot.models import FAQEntry

def update_embeddings_from_json():
    """Update database with embeddings from JSON file"""
    json_path = BASE_DIR / "chatbot" / "data" / "faq_with_embeddings.json"

    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        print("   Run: python embed_faqs.py first")
        return

    print("📖 Loading embeddings from JSON file...")
    with open(json_path, 'r') as f:
        faqs = json.load(f)

    print(f"Found {len(faqs)} FAQs in JSON file")

    updated = 0
    not_found = 0

    for faq_data in faqs:
        faq = FAQEntry.objects.filter(question=faq_data['question']).first()
        if faq:
            faq.embedding = faq_data['embedding']
            # Update lessons_only if present in data
            if 'lessons_only' in faq_data:
                faq.lessons_only = faq_data['lessons_only']
            faq.save()
            updated += 1
            print(f"✅ Updated: {faq.question[:60]}...")
        else:
            not_found += 1
            print(f"❌ Not found in DB: {faq_data['question'][:60]}...")

    print(f"\n✅ Updated {updated} FAQs")
    if not_found > 0:
        print(f"⚠️  {not_found} FAQs not found in database")

if __name__ == "__main__":
    update_embeddings_from_json()
    print("\n🎯 Embeddings updated! Restart your Django server to use them.")