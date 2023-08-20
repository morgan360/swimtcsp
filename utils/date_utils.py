# utils/date_utils.py

from datetime import timedelta, date

def get_next_occurrence(product_day_of_week):
    today = date.today()
    current_day_of_week = (today.weekday()) % 7  # Adjust the mapping to match your model

    if product_day_of_week == current_day_of_week:
        days_until_next_occurrence = 0
    else:
        days_until_next_occurrence = (product_day_of_week - current_day_of_week) % 7

    next_occurrence = today + timedelta(days=days_until_next_occurrence)
    return next_occurrence
