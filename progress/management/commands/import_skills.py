import pandas as pd
from django.core.management.base import BaseCommand
from lessons.models import Product
from progress.models import Skill, LessonSkill, CoreAquaticSkill
from pathlib import Path

# ✅ Lesson code → list of Category.name values
CODE_TO_CATEGORY_NAME = {
    "B1": ["Beginners - 1", "Beginners 1 - BG", "Beginners 8+"],
    "B2": ["Beginners - 2", "Beginners 2 - BG", "Beginners - C"],

    "I1": ["Improvers - 1", "Improvers 1 - BG"],
    "I2": ["Improvers - 2", "Improvers 2 - BG"],
    "I3": ["Improvers - C"],

    "L1": ["Lengths - L1"],
    "L2": ["Lengths - L2"],
    "L3": ["Lengths - L3"],

    "A": ["Advanced", "Advanced - BG", "Adult Begin & Improvers"]
}


class Command(BaseCommand):
    help = "Import skills from SKILLS List.xlsx (Sheet2), and link to Core Aquatic Skills + lesson categories"

    def handle(self, *args, **kwargs):
        file_path = Path("SKILLS List.xlsx")
        if not file_path.exists():
            self.stderr.write("❌ SKILLS List.xlsx not found in the root directory.")
            return

        self.stdout.write("📥 Reading Excel file...")
        df = pd.read_excel(file_path, sheet_name="Sheet2")

        skill_count = 0
        link_count = 0
        cas_count = 0
        errors = []

        # Extract CAS names from top-level columns (e.g. 'B1', 'B2', etc.)
        for i in range(0, len(df.columns) - 1, 2):
            cas_name = str(df.columns[i]).strip()
            skill_code_col = df.columns[i + 1]

            # 🔁 Get or create the CAS
            cas, created = CoreAquaticSkill.objects.get_or_create(name=cas_name)
            if created:
                cas_count += 1

            for _, row in df.iterrows():
                skill_name = row.get(cas_name)
                skill_code = row.get(skill_code_col)

                if pd.isna(skill_name) or pd.isna(skill_code):
                    continue

                skill_name = str(skill_name).strip()
                skill_code = str(skill_code).strip()

                # Extract lesson code (e.g. 'B1' from 'B1-EE2')
                if "-" not in skill_code:
                    continue
                lesson_code = skill_code.split("-")[0]

                # 🔁 Map code to one or more category names
                category_names = CODE_TO_CATEGORY_NAME.get(lesson_code)
                if not category_names:
                    errors.append(f"⚠️ No category mapping for lesson code '{lesson_code}'")
                    continue

                # Create Skill (activity)
                skill, created = Skill.objects.get_or_create(
                    code=skill_code,
                    defaults={
                        "name": skill_name,
                        "description": skill_name,
                        "cas": cas
                    }
                )
                if created:
                    skill_count += 1

                # Link Skill to all lessons under matching categories
                for cat_name in category_names:
                    lessons = Product.objects.filter(category__name__iexact=cat_name)
                    if not lessons.exists():
                        errors.append(f"⚠️ No lessons found in category '{cat_name}' for skill '{skill_code}'")
                        continue

                    for lesson in lessons:
                        link, created = LessonSkill.objects.get_or_create(
                            skill=skill,
                            lesson=lesson,
                        )
                        if created:
                            link_count += 1

        self.stdout.write(f"\n✅ Imported {skill_count} skills, linked to {link_count} lessons.")
        self.stdout.write(f"✅ Created {cas_count} Core Aquatic Skills.")
        if errors:
            self.stdout.write("\n⚠️ Issues found:")
            for err in sorted(set(errors)):
                self.stdout.write(f" - {err}")
