from django.core.management.base import BaseCommand
from django.core.serializers import deserialize
import json
from progress.models import CoreAquaticSkill, Skill, CategorySkill, SkillAssessment, InstructorNote

# Clear existing data in reverse dependency order
InstructorNote.objects.all().delete()
SkillAssessment.objects.all().delete()
CategorySkill.objects.all().delete()
Skill.objects.all().delete()
CoreAquaticSkill.objects.all().delete()

class Command(BaseCommand):
    help = "Import skill-related data from a JSON file"

    def handle(self, *args, **kwargs):
        with open('skills_export.json') as f:
            data = json.load(f)

        for obj in deserialize('json', json.dumps(data)):
            obj.save()

        self.stdout.write(self.style.SUCCESS("Import complete"))
