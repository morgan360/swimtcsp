from django import forms
from django.forms import modelformset_factory
from progress.models import SkillAssessment, InstructorNote, CategorySkill, Skill, CoreAquaticSkill
from lessons_bookings.models import Term, LessonEnrollment
from progress.models import SkillAssessment
# Assumptions:
# Assessment has fields: swimling, term, skill, rating (int/nullable)
# Term has fields: id, short_name/number

# instructors/forms.py
from django import forms
from django.forms import modelformset_factory
from progress.models import SkillAssessment

class AssessmentForm(forms.ModelForm):
    class Meta:
        model = SkillAssessment
        fields = ["rating"]
        widgets = {
            "rating": forms.Select(
                choices=[("", "—")] + [(i, str(i)) for i in range(1, 6)],
                attrs={"class": "rating-select"}
            )
        }

AssessmentFormSet = modelformset_factory(
    SkillAssessment,
    form=AssessmentForm,
    extra=0,
)


class InstructorNoteForm(forms.Form):
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Instructor notes for this term…"})
    )
