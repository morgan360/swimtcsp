# chatbot/management/commands/embed_new_faqs.py

from django.core.management.base import BaseCommand
from chatbot.models import FAQEntry
from openai import OpenAI
import os

class Command(BaseCommand):
    help = "Embed FAQs that don't have embeddings yet"

    def handle(self, *args, **kwargs):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Get FAQs without embeddings
        faqs_without_embeddings = FAQEntry.objects.filter(embedding__isnull=True)
        count = faqs_without_embeddings.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("✅ All FAQs already have embeddings!"))
            return

        self.stdout.write(f"Found {count} FAQ(s) without embeddings. Embedding now...")

        for faq in faqs_without_embeddings:
            self.stdout.write(f"Embedding: {faq.question[:60]}...")
            try:
                response = client.embeddings.create(
                    input=[faq.question],
                    model="text-embedding-3-small"
                )
                faq.embedding = response.data[0].embedding
                faq.save()
                self.stdout.write(self.style.SUCCESS("  ✅ Done"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Error: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully embedded {count} FAQ(s)"))