from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from chatbot.helpers.faq_index import invalidate
from chatbot.models import FAQEntry


@receiver(post_save, sender=FAQEntry)
@receiver(post_delete, sender=FAQEntry)
def invalidate_faq_index(sender, **kwargs):
    """Editing a FAQ should take effect immediately, without a restart."""
    invalidate()
