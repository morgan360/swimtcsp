PHASE_DETAILS = {
    'BK': {
        'label': 'Current Term Booking',
        'description': 'Booking for current term is open until ~ {booking_date}',
        'bulma_class': 'is-info is-light',
        'icon': '🏊',  # ✅ This must exist
    },
    'RB': {
        'label': 'Rebooking',
        'description': 'Rebooking into the same class is open until {booking_date}',
        'bulma_class': 'is-warning is-light',
        'icon': '🔁',
    },
    'BN': {
        'label': 'Open Booking',
        'description': 'Booking for next term is open until {end_date}',
        'bulma_class': 'is-success is-light',
        'icon': '🌐',
    },
}