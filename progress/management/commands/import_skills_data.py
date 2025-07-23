# import_skills_data.py

import os
import django
import json
from django.core.serializers import deserialize

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')  # or 'config.production_settings' when on PythonAnywhere
django.setup()

with open('skills_export.json') as f:
    data = json.load(f)

for obj in deserialize('json', json.dumps(data)):
    obj.save()

print("Import complete")
