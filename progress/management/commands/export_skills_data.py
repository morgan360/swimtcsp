# export_skills_data.py

import os
import django
import json
from django.core.serializers import serialize

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')  # or 'config.production_settings' when on PythonAnywhere
django.setup()


from progress.models import CoreAquaticSkill, Skill, CategorySkill, SkillAssessment, InstructorNote

# Collect the data
models = [CoreAquaticSkill, Skill, CategorySkill, SkillAssessment, InstructorNote]
data = []

for model in models:
    serialized = serialize('json', model.objects.all())
    data.extend(json.loads(serialized))

# Save to a file
with open('skills_export.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Export complete: skills_export.json")
