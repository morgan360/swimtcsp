# Terms

* In root utils

```Python
def get_current_term():
    today = date.today()
    current_term = Term.objects.filter(start_date__lte=today, end_date__gte=today).first()
    return current_term


def get_previous_term():
    current_term = get_current_term()
    if current_term:
        return Term.objects.filter(id=current_term.id - 1).first()
    return none


def get_next_term():
    current_term = get_current_term()
    if curent_term:
        return Term.objects.filter(id=current_term.id + 1).first()
    return none
```

## Methods for Terms

def get\_current\_term\_id()

concatenated\_term()

determine\_phase()

get\_phase\_code()

return&#x20;

return '1' # Code for 'Booking for Current Term'

return '2' # Code for 'Rebooking for Next Term'

return '3' # Code for 'Booking for Next Term'

return '0' # Code for 'Outside Term'
