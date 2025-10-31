"""
Export all FAQs from database to YAML file
Run this before re-embedding to ensure all FAQs are included
"""
import django
import os
import sys
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')
django.setup()

from chatbot.models import FAQEntry
import yaml

def export_faqs_to_yaml():
    """Export all FAQs from database to YAML"""
    faqs = FAQEntry.objects.all().order_by('id')

    faq_list = []
    for faq in faqs:
        faq_dict = {
            'question': faq.question,
            'answer': faq.answer,
        }
        if faq.lessons_only:
            faq_dict['lessons_only'] = True
        faq_list.append(faq_dict)

    yaml_path = BASE_DIR / "chatbot" / "data" / "faq.yaml"

    # Backup existing file
    if yaml_path.exists():
        backup_path = yaml_path.with_suffix('.yaml.backup')
        import shutil
        shutil.copy(yaml_path, backup_path)
        print(f"📦 Backed up existing file to {backup_path}")

    # Write to YAML
    with open(yaml_path, 'w') as f:
        yaml.dump(faq_list, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"✅ Exported {len(faq_list)} FAQs to {yaml_path}")
    return len(faq_list)

if __name__ == "__main__":
    count = export_faqs_to_yaml()
    print(f"\n🎯 Next steps:")
    print(f"   1. Review chatbot/data/faq.yaml")
    print(f"   2. Run: python embed_faqs.py")
    print(f"   3. Run: python update_faq_embeddings.py")