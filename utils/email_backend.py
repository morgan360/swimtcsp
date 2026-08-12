"""SMTP backend that stamps a default Reply-To on outgoing mail.

Every message leaves as `From: web@tcsp.ie`, because that is the Microsoft 365
account Django authenticates as. Almost none of them set a Reply-To, so a
customer hitting Reply on a booking confirmation lands in the web@ mailbox —
while the body of that same email tells them to write to swimming@tcsp.ie.

Done as a backend rather than a `reply_to=` argument at each send site because
the send sites are not all ours: allauth's password reset and email
confirmation go through django.core.mail without ever consulting our code, and
those are the messages customers are most likely to reply to. A backend catches
everything that leaves the process, including whatever gets added next.

An explicit Reply-To always wins — see the contact form in home/views.py, which
sets its own on purpose.
"""
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend


class ReplyToEmailBackend(SMTPEmailBackend):
    """SMTP backend applying settings.DEFAULT_REPLY_TO_EMAIL where none is set."""

    def send_messages(self, email_messages):
        default = getattr(settings, "DEFAULT_REPLY_TO_EMAIL", "") or ""
        if default:
            reply_to = [default] if isinstance(default, str) else list(default)
            for message in email_messages or []:
                # `reply_to` is a list on EmailMessage, but a message can arrive
                # with the header set directly (allauth builds some that way),
                # and a duplicate Reply-To is worse than none at all.
                if not getattr(message, "reply_to", None) and not any(
                    key.lower() == "reply-to"
                    for key in getattr(message, "extra_headers", {})
                ):
                    message.reply_to = reply_to

        return super().send_messages(email_messages)