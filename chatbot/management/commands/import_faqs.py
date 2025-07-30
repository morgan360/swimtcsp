# chatbot/management/commands/import_faqs.py

import yaml
from django.core.management.base import BaseCommand
from chatbot.models import FAQEntry
from pathlib import Path

class Command(BaseCommand):
    help = "Import FAQs from chatbot/data/faq.yaml"

    def handle(self, *args, **kwargs):
        faq_path = Path('chatbot/data/faq.yaml')

        if not faq_path.exists():
            self.stderr.write("❌ FAQ YAML file not found at chatbot/data/faq.yaml")
            return

        with faq_path.open('r') as f:
            faq_data = yaml.safe_load(f)

        created, skipped = 0, 0
        for item in faq_data:
            obj, was_created = FAQEntry.objects.get_or_create(
                question=item['question'],
                defaults={'answer': item['answer']}
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Imported: {created}, Skipped (already exists): {skipped}"))
