from swims.models import PublicSwimProduct
from django.utils import timezone
import pytz

def get_available_swims():
    dublin = pytz.timezone("Europe/Dublin")
    now = timezone.now().astimezone(dublin)
    today = now.date()
    weekday = today.weekday()
    current_time = now.time()

    all_swims = PublicSwimProduct.objects.filter(available=True).order_by("day_of_week", "start_time")
    filtered = []

    for swim in all_swims:
        if swim.day_of_week == weekday and swim.end_time > current_time:
            filtered.append(swim)
        elif swim.day_of_week != weekday:
            filtered.append(swim)

    sorted_swims = sorted(
        filtered,
        key=lambda s: (0 if s.day_of_week == weekday else 1, s.day_of_week, s.start_time)
    )

    return sorted_swims[:15]

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
