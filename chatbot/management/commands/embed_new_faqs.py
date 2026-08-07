# chatbot/management/commands/embed_new_faqs.py

from django.core.management.base import BaseCommand

from chatbot.helpers.client import embed, embed_model
from chatbot.helpers.faq_index import embedding_text
from chatbot.models import FAQEntry


class Command(BaseCommand):
    help = "Embed FAQs that don't have embeddings yet"

    def handle(self, *args, **kwargs):
        faqs_without_embeddings = FAQEntry.objects.filter(embedding__isnull=True)
        count = faqs_without_embeddings.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("✅ All FAQs already have embeddings!"))
            return

        self.stdout.write(
            f"Found {count} FAQ(s) without embeddings. Embedding with {embed_model()}..."
        )

        embedded = 0
        for faq in faqs_without_embeddings:
            self.stdout.write(f"Embedding: {faq.question[:60]}...")
            vector = embed(embedding_text(faq.question, faq.answer))
            if vector is None:
                self.stdout.write(self.style.ERROR("  ❌ Embedding API call failed"))
                continue
            faq.embedding = vector
            faq.save()
            embedded += 1
            self.stdout.write(self.style.SUCCESS("  ✅ Done"))

        style = self.style.SUCCESS if embedded == count else self.style.WARNING
        self.stdout.write(style(f"\n✅ Embedded {embedded} of {count} FAQ(s)"))
