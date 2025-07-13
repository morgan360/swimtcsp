from progress.models import CoreAquaticSkill, Skill, LessonSkill
from django.db.models import Prefetch


def get_skill_structure_summary():
    """
    Returns a markdown-formatted string describing each Core Aquatic Skill
    and its progression skills, grouped by CAS and showing relevant lesson levels.
    """
    lines = ["## 🏊 Skill Structure by Core Aquatic Skill\n"]

    cas_qs = CoreAquaticSkill.objects.prefetch_related(
        Prefetch("skills", queryset=Skill.objects.order_by("code"))
    )

    for cas in cas_qs:
        lines.append(f"### {cas.name}")
        lines.append(f"*{cas.description}*" if cas.description else "")

        for skill in cas.skills.all():
            lessons = (
                LessonSkill.objects
                .filter(skill=skill)
                .select_related("lesson__category")
                .distinct()
            )
            levels = sorted({ls.lesson.category.name for ls in lessons})
            level_info = f" — Taught in: {', '.join(levels)}" if levels else ""
            lines.append(f"- **{skill.name}** ({skill.code}){level_info}")

        lines.append("")  # spacing between CAS sections

    return "\n".join(lines)
