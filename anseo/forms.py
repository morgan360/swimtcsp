from django import forms
from .models import AttendanceEntry

class AttendanceForm(forms.Form):
    """
    Dynamic form for marking attendance for multiple enrolments.
    Fields are added in the view.
    """

    STATUS_CHOICES = AttendanceEntry.STATUS_CHOICES

    def __init__(self, *args, enrolments=None, **kwargs):
        """
        enrolments: iterable of LessonsEnrolment objects
        """
        super().__init__(*args, **kwargs)
        if enrolments is None:
            enrolments = []

        for e in enrolments:
            self.fields[f"status_{e.id}"] = forms.ChoiceField(
                choices=self.STATUS_CHOICES,
                widget=forms.RadioSelect,
                required=False,
                initial=AttendanceEntry.UNKNOWN,
                label=f"{e.swimling.first_name} {e.swimling.last_name}"
            )
            self.fields[f"note_{e.id}"] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={"placeholder": "Optional note…"}),
                label="Note"
            )
