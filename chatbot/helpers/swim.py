from swims.models import PublicSwimProduct
from django.utils import timezone
import pytz

def get_available_swims():
    dublin = pytz.timezone("Europe/Dublin")
    now = timezone.now().astimezone(dublin)
    today = now.date()
    weekday = today.weekday()
    current_time = now.time()

    all_swims = PublicSwimProduct.objects.filter(available=True)

    # Today's sessions only count while they are still running.
    upcoming = [
        swim for swim in all_swims
        if swim.day_of_week != weekday or swim.end_time > current_time
    ]

    # Order by how many days ahead each session is, wrapping around the end of the
    # week. Sorting on the raw day number put Sunday last whatever day it was, so on
    # a Saturday the list ran Monday, Tuesday, ... and the cap below cut Sunday off
    # entirely — the genuinely next session was not in the list the bot was given.
    # Only Sunday and Monday came out right, being the two days from which the raw
    # numbers already ascend; Tuesday through Saturday were all wrong.
    upcoming.sort(key=lambda s: ((s.day_of_week - weekday) % 7, s.start_time))

    return upcoming[:15]

def format_swim_list(swims):
    def get_price_table(product):
        prices = product.price_variants.all()
        if not prices:
            return ""
        price_lines = [f"  - {pv.get_variant_display()}: €{pv.price:.2f}" for pv in prices]
        return f"\n**Prices:**\n" + "\n".join(price_lines)

    return "\n\n".join([
        f"- **{s.name}** on **{s.get_day_of_week_display()}** from **{s.start_time.strftime('%H:%M')}** to **{s.end_time.strftime('%H:%M')}** – **{s.num_places} places available**\n{get_price_table(s)}"
        for s in swims
    ])
