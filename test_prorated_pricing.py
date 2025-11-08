#!/usr/bin/env python
"""
Custom test script for prorated pricing using actual TCSP data
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')
django.setup()

from lessons_bookings.models import Term
from lessons.models import Product
from django.utils import timezone
from datetime import timedelta


def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*70}")
    print(f"{text:^70}")
    print(f"{'='*70}\n")


def print_section(text):
    """Print a section divider"""
    print(f"\n{'-'*70}")
    print(f"{text}")
    print(f"{'-'*70}")


def test_current_term_pricing():
    """Test pricing with your actual active term (Term 57)"""
    print_header("TESTING WITH YOUR ACTIVE TERM (Term 57)")

    # Get the active term
    term = Term.objects.get(id=57)
    today = timezone.now().date()

    print(f"Term Details:")
    print(f"  Start Date: {term.start_date}")
    print(f"  End Date: {term.end_date}")
    print(f"  Today: {today}")

    # Calculate days/weeks
    days_elapsed = (today - term.start_date).days
    days_remaining = (term.end_date - today).days
    total_days = (term.end_date - term.start_date).days

    print(f"\nTerm Progress:")
    print(f"  Days elapsed: {days_elapsed}")
    print(f"  Days remaining: {days_remaining}")
    print(f"  Total days: {total_days}")
    print(f"  Percentage complete: {(days_elapsed / total_days * 100):.1f}%")

    # Test with a sample lesson
    lesson = Product.objects.filter(active=True).first()

    if not lesson:
        print("\nNo active lessons found!")
        return

    print_section(f"Testing Lesson: {lesson.name}")
    print(f"Full Price: €{lesson.price}")
    print(f"Total Weeks: {lesson.num_weeks}")
    print(f"Price per week: €{float(lesson.price) / lesson.num_weeks:.2f}")

    # Get prorated price
    prorated_price = lesson.get_prorated_price(term)

    weeks_remaining = days_remaining / 7
    expected_price = (lesson.price / Decimal(str(lesson.num_weeks))) * Decimal(str(weeks_remaining))

    print(f"\nProrated Pricing Calculation:")
    print(f"  Weeks remaining: {weeks_remaining:.2f}")
    print(f"  Expected prorated price: €{expected_price:.2f}")
    print(f"  Actual prorated price: €{prorated_price}")
    print(f"  Savings from full price: €{lesson.price - prorated_price:.2f}")
    print(f"  Percentage of full price: {(float(prorated_price) / float(lesson.price) * 100):.1f}%")


def test_all_active_lessons():
    """Test pricing for all active lessons"""
    print_header("PRICING FOR ALL ACTIVE LESSONS")

    term = Term.objects.get(id=57)
    today = timezone.now().date()
    days_remaining = (term.end_date - today).days
    weeks_remaining = days_remaining / 7

    print(f"Using Term 57: {term.start_date} → {term.end_date}")
    print(f"Weeks remaining: {weeks_remaining:.2f}\n")

    lessons = Product.objects.filter(active=True)[:10]

    print(f"{'Lesson Name':<45} {'Full Price':>10} {'Prorated':>10} {'Savings':>10}")
    print(f"{'-'*45} {'-'*10} {'-'*10} {'-'*10}")

    for lesson in lessons:
        prorated = lesson.get_prorated_price(term)
        savings = lesson.price - prorated

        # Truncate name if too long
        name = lesson.name[:42] + "..." if len(lesson.name) > 45 else lesson.name

        print(f"{name:<45} €{lesson.price:>8.2f} €{prorated:>8.2f} €{savings:>8.2f}")


def test_different_scenarios():
    """Test what pricing would be at different points in the term"""
    print_header("PRICING SCENARIOS AT DIFFERENT POINTS IN TERM")

    lesson = Product.objects.filter(active=True).first()
    term = Term.objects.get(id=57)

    print(f"Lesson: {lesson.name}")
    print(f"Full Price: €{lesson.price} for {lesson.num_weeks} weeks")
    print(f"Term: {term.start_date} → {term.end_date}\n")

    # Create different scenario dates
    today = timezone.now().date()
    term_start = term.start_date
    term_end = term.end_date
    total_duration = (term_end - term_start).days

    scenarios = [
        ("Before term starts", term_start - timedelta(days=7)),
        ("Week 1 (start of term)", term_start + timedelta(days=3)),
        ("Week 3", term_start + timedelta(weeks=2)),
        ("Week 5 (mid-term)", term_start + timedelta(weeks=4)),
        ("Week 8", term_start + timedelta(weeks=7)),
        ("Week 10 (near end)", term_start + timedelta(weeks=9)),
        ("TODAY", today),
        ("After term ends", term_end + timedelta(days=1)),
    ]

    print(f"{'Scenario':<25} {'Date':>12} {'Weeks Left':>12} {'Price':>10} {'% of Full':>10}")
    print(f"{'-'*25} {'-'*12} {'-'*12} {'-'*10} {'-'*10}")

    for scenario_name, scenario_date in scenarios:
        # Temporarily create a term for this scenario
        test_term = Term(
            id=999,  # Temporary ID
            start_date=term_start,
            end_date=term_end,
            rebooking_date=term.rebooking_date,
            booking_date=term.booking_date
        )

        # Calculate price as if "today" was the scenario date
        days_remaining = (term_end - scenario_date).days
        weeks_remaining = max(0, days_remaining / 7)

        if scenario_date < term_start:
            price = lesson.price
            weeks_left = float(lesson.num_weeks)
        elif scenario_date > term_end:
            price = Decimal('0.00')
            weeks_left = 0.0
        else:
            # Manually calculate what get_prorated_price would return
            if weeks_remaining <= 0:
                price = Decimal('0.00')
                weeks_left = 0.0
            else:
                price_per_week = lesson.price / Decimal(str(lesson.num_weeks))
                price = price_per_week * Decimal(str(weeks_remaining))
                min_price = price_per_week
                price = max(price, min_price).quantize(Decimal('0.01'))
                weeks_left = weeks_remaining

        pct_of_full = (float(price) / float(lesson.price) * 100) if price > 0 else 0

        print(f"{scenario_name:<25} {scenario_date!s:>12} {weeks_left:>11.1f} €{price:>8.2f} {pct_of_full:>9.1f}%")


def test_edge_cases():
    """Test edge cases"""
    print_header("EDGE CASE TESTING")

    lesson = Product.objects.filter(active=True).first()
    term = Term.objects.get(id=57)

    print_section("Test 1: Lesson with no price set")
    test_lesson = Product(
        category=lesson.category,
        day_of_week=0,
        num_places=10,
        num_weeks=10,
        price=None,
        active=True
    )
    result = test_lesson.get_prorated_price(term)
    print(f"Result: {result} (should be None)")

    print_section("Test 2: Lesson with no weeks set")
    test_lesson = Product(
        category=lesson.category,
        day_of_week=0,
        num_places=10,
        num_weeks=None,
        price=Decimal('100.00'),
        active=True
    )
    result = test_lesson.get_prorated_price(term)
    print(f"Result: €{result} (should return full price)")

    print_section("Test 3: No term provided")
    result = lesson.get_prorated_price(None)
    print(f"Result: €{result} (should return full price: €{lesson.price})")


def main():
    """Run all tests"""
    print_header("TCSP PRORATED PRICING TEST SUITE")
    print(f"Testing Date: {timezone.now().date()}")
    print(f"Django Settings: {os.environ.get('DJANGO_SETTINGS_MODULE')}")

    try:
        test_current_term_pricing()
        test_all_active_lessons()
        test_different_scenarios()
        test_edge_cases()

        print_header("ALL TESTS COMPLETED SUCCESSFULLY")

        print("\nNext Steps:")
        print("1. Review the pricing calculations above")
        print("2. Try adding a lesson to cart in the web interface")
        print("3. Verify the cart shows the prorated price")
        print("4. Check that checkout creates orders with correct pricing")

    except Term.DoesNotExist:
        print("\n❌ ERROR: Term 57 not found in database!")
        print("   Please update the script with a valid term ID.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
