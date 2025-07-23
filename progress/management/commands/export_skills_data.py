from django.core.management.base import BaseCommand
from django.core.serializers import serialize
from progress.models import CoreAquaticSkill, Skill, CategorySkill, SkillAssessment, InstructorNote
import json

class Command(BaseCommand):
    help = "Export skill-related data to a JSON file"

    def handle(self, *args, **kwargs):
        data = []

        models = [CoreAquaticSkill, Skill, CategorySkill, SkillAssessment, InstructorNote]
        for model in models:
            serialized = serialize('json', model.objects.all())
            data.extend(json.loads(serialized))

        with open('skills_export.json', 'w') as f:
            json.dump(data, f, indent=2)

        self.stdout.write(self.style.SUCCESS("Export complete: skills_export.json"))
