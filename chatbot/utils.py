from collections import defaultdict

from django.core.cache import cache
from django.db.models import Prefetch

from progress.models import CategorySkill, CoreAquaticSkill, Skill

SKILL_SUMMARY_CACHE_KEY = "chatbot:skill_structure_summary"
SKILL_SUMMARY_TTL = 60 * 60


def get_skill_structure_summary():
    """
    Returns a markdown-formatted string describing each Core Aquatic Skill
    and its progression skills, grouped by CAS and showing relevant lesson levels.

    Cached: the skill tree changes a few times a year but this was rebuilt — with
    one query per skill — on every lesson-bot message, and its output is the
    largest block in the prompt.
    """
    cached = cache.get(SKILL_SUMMARY_CACHE_KEY)
    if cached is not None:
        return cached

    summary = _build_skill_structure_summary()
    cache.set(SKILL_SUMMARY_CACHE_KEY, summary, SKILL_SUMMARY_TTL)
    return summary


def _build_skill_structure_summary():
    # One pass for every skill→level mapping, instead of a query per skill.
    levels_by_skill = defaultdict(set)
    for link in CategorySkill.objects.select_related("lesson__category"):
        levels_by_skill[link.skill_id].add(link.lesson.category.name)

    lines = ["## 🏊 Skill Structure by Core Aquatic Skill\n"]

    cas_qs = CoreAquaticSkill.objects.prefetch_related(
        Prefetch("skills", queryset=Skill.objects.order_by("code"))
    )

    for cas in cas_qs:
        lines.append(f"### {cas.name}")
        lines.append(f"*{cas.description}*" if cas.description else "")

        for skill in cas.skills.all():
            levels = sorted(levels_by_skill.get(skill.id, ()))
            level_info = f" — Taught in: {', '.join(levels)}" if levels else ""
            lines.append(f"- **{skill.name}** ({skill.code}){level_info}")

        lines.append("")  # spacing between CAS sections

    return "\n".join(lines)
