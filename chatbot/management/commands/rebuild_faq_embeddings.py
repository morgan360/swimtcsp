# chatbot/management/commands/rebuild_faq_embeddings.py

import yaml
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from chatbot.models import FAQEntry
from chatbot.helpers.client import embed, embed_model
from chatbot.helpers.faq_index import embedding_text
from django.db import transaction


class Command(BaseCommand):
    help = "Rebuild all FAQ embeddings from faq.yaml - use during deployment"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-embedding even if embeddings already exist',
        )
        parser.add_argument(
            '--delete-orphans',
            action='store_true',
            help='Delete FAQ entries not present in faq.yaml',
        )

    def handle(self, *args, **options):
        force = options['force']
        delete_orphans = options['delete_orphans']

        self.stdout.write(self.style.WARNING("\n🔄 Starting FAQ Rebuild Process...\n"))

        # Step 1: Load YAML file
        faq_path = Path(settings.BASE_DIR) / 'chatbot' / 'data' / 'faq.yaml'
        if not faq_path.exists():
            self.stderr.write(self.style.ERROR(f"❌ FAQ YAML file not found at {faq_path}"))
            return

        with faq_path.open('r', encoding='utf-8') as f:
            faq_data = yaml.safe_load(f)

        if not faq_data:
            self.stderr.write(self.style.ERROR("❌ No FAQs found in YAML file"))
            return

        self.stdout.write(f"📄 Loaded {len(faq_data)} FAQs from faq.yaml")

        # Step 2: Confirm the API is configured before touching the database
        if not settings.OPENAI_API_KEY:
            self.stderr.write(self.style.ERROR("❌ OPENAI_API_KEY is not configured"))
            return

        self.stdout.write(f"🤖 Using embedding model: {embed_model()}")

        # Step 3: Track questions from YAML
        yaml_questions = {item['question'] for item in faq_data}

        # Step 4: Delete orphaned FAQs if requested
        if delete_orphans:
            orphans = FAQEntry.objects.exclude(question__in=yaml_questions)
            orphan_count = orphans.count()
            if orphan_count > 0:
                self.stdout.write(f"🗑️  Deleting {orphan_count} orphaned FAQ(s)...")
                orphans.delete()
                self.stdout.write(self.style.SUCCESS(f"✅ Deleted {orphan_count} orphaned FAQ(s)"))

        # Step 5: Import/Update FAQs with embeddings
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        with transaction.atomic():
            for item in faq_data:
                question = item['question']
                answer = item['answer']
                lessons_only = item.get('lessons_only', False)

                try:
                    # Get or create FAQ entry
                    faq, was_created = FAQEntry.objects.get_or_create(
                        question=question,
                        defaults={
                            'answer': answer,
                            'lessons_only': lessons_only
                        }
                    )

                    # Update answer and lessons_only if changed. Saved here and
                    # not with the embedding: these are cheap local edits that
                    # must survive an embedding API failure. Previously the only
                    # save() sat inside the embedding branch, so a bad API key
                    # silently discarded every content and scoping change while
                    # still reporting them as updated.
                    if not was_created:
                        if faq.answer != answer or faq.lessons_only != lessons_only:
                            faq.answer = answer
                            faq.lessons_only = lessons_only
                            faq.save(update_fields=["answer", "lessons_only", "updated"])
                            updated_count += 1

                    # Generate embedding if needed
                    needs_embedding = force or faq.embedding is None

                    if needs_embedding:
                        self.stdout.write(f"🔧 Embedding: {question[:60]}...")

                        vector = embed(embedding_text(question, answer))
                        if vector is None:
                            raise RuntimeError(
                                "embedding API returned no vector (check OPENAI_API_KEY)"
                            )

                        faq.embedding = vector
                        faq.save(update_fields=["embedding", "updated"])

                        if was_created:
                            created_count += 1
                            self.stdout.write(self.style.SUCCESS(f"  ✅ Created & embedded"))
                        else:
                            self.stdout.write(self.style.SUCCESS(f"  ✅ Re-embedded"))
                    else:
                        skipped_count += 1
                        if was_created:
                            created_count += 1

                except Exception as e:
                    error_count += 1
                    self.stderr.write(self.style.ERROR(f"  ❌ Error processing '{question[:60]}': {e}"))

        # Step 6: Summary
        self.stdout.write("\n" + "="*60)
        if error_count:
            self.stdout.write(self.style.ERROR("❌ FAQ Rebuild finished with errors"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ FAQ Rebuild Complete!"))
        self.stdout.write("="*60)
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   • New FAQs created: {created_count}")
        self.stdout.write(f"   • Existing FAQs updated: {updated_count}")
        self.stdout.write(f"   • Skipped (already embedded): {skipped_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"   • Errors: {error_count}"))

        total_in_db = FAQEntry.objects.count()
        total_with_embeddings = FAQEntry.objects.filter(embedding__isnull=False).count()

        self.stdout.write(f"\n📈 Database Status:")
        self.stdout.write(f"   • Total FAQs in database: {total_in_db}")
        self.stdout.write(f"   • FAQs with embeddings: {total_with_embeddings}")

        if total_with_embeddings < total_in_db:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  Warning: {total_in_db - total_with_embeddings} FAQ(s) still missing embeddings"
            ))
        elif not error_count:
            self.stdout.write(self.style.SUCCESS("\n✅ All FAQs have embeddings!"))

        self.stdout.write("")

        # Exit non-zero so a deploy stops here. "Every FAQ has an embedding" was
        # previously reported even when every call had failed, because the rows
        # still held their previous vectors — a failed rebuild looked like a
        # clean one, and the deploy script's error check could never fire.
        if error_count:
            raise CommandError(
                f"{error_count} FAQ(s) failed to embed — the corpus may be stale. "
                f"Check OPENAI_API_KEY for this environment."
            )