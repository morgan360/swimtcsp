from django.db import models


class SecurityIncident(models.Model):
    """Something worth a look on the Live Dashboard. One row per event, not per
    request: a scanner's hundred hits are one block."""

    CHAT_REFUSED, CHAT_BLOCKED, PROBE_BLOCKED, CSRF_BLOCKED = 'chat_refused', 'chat_blocked', 'probe_blocked', 'csrf_blocked'
    KIND_CHOICES = [
        (CHAT_REFUSED, 'Chat message refused'),
        (CHAT_BLOCKED, 'Chat blocked'),
        (PROBE_BLOCKED, 'Scanner blocked'),
        (CSRF_BLOCKED, 'Form spam blocked'),
    ]
    BLOCKS = (CHAT_BLOCKED, PROBE_BLOCKED, CSRF_BLOCKED)

    created = models.DateTimeField(auto_now_add=True, db_index=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    ip = models.CharField(max_length=45, blank=True)
    path = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.get_kind_display()} {self.ip}"
