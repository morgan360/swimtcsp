import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from progress.models import CoreAquaticSkill, Skill


class Command(BaseCommand):
    help = "Import Core Aquatic Skills and Skills from 'SKILLS List.xlsx' (Sheet2)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default="SKILLS List.xlsx",
            help="Path to the Excel file (default: SKILLS List.xlsx)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = options["path"]
        self.stdout.write(f"📥 Reading Excel file: {path}")

        try:
            df = pd.read_excel(path, sheet_name="Sheet2", header=None)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to read Excel: {e}"))
            return

        self.stdout.write("🧹 Clearing existing skills and CAS entries...")
        Skill.objects.all().delete()
        CoreAquaticSkill.objects.all().delete()

        current_cas = None
        created_cas_count = 0
        created_skill_count = 0

        for index, row in df.iterrows():
            raw_cas_cell = str(row[0]).strip() if pd.notna(row[0]) else ""
            code = str(row[1]).strip() if pd.notna(row[1]) else ""
            name = str(row[2]).strip() if pd.notna(row[2]) else ""

            # If the cell has text and does NOT contain "nose", treat it as CAS
            if raw_cas_cell and "nose" not in raw_cas_cell.lower():
                current_cas = CoreAquaticSkill.objects.create(name=raw_cas_cell)
                created_cas_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ CAS: {current_cas.name}"))

            # If skill data exists, associate with current CAS
            if current_cas and code and name:
                if len(code) > 20:
                    self.stderr.write(self.style.ERROR(f"❌ Code too long: '{code}' ({len(code)} characters)"))
                    continue
                Skill.objects.create(code=code, name=name, cas=current_cas)
                created_skill_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"🎉 Imported {created_cas_count} Core Aquatic Skills and {created_skill_count} Skills."
        ))

