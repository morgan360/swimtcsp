from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from lessons.models import Category, Product, Program
from lessons_bookings.models import LessonEnrollment, Term
from users.models import Swimling


class ClassPrintScopeTests(TestCase):
    """The print filter has to cover a single slot, a whole day and a whole week."""

    @classmethod
    def setUpTestData(cls):
        today = date.today()
        cls.term = Term.objects.create(
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=70),
            rebooking_date=today - timedelta(days=30),
            booking_date=today - timedelta(days=14),
        )
        program = Program.objects.create(name="Public Lessons")
        cls.category = Category.objects.create(
            name="Beginners 1", slug="beginners-1", program=program
        )

        cls.mon_early = cls._make_product(0, time(17, 0))
        cls.mon_late = cls._make_product(0, time(18, 0))
        cls.tue_early = cls._make_product(1, time(17, 0))

        cls.swimling = Swimling.objects.create(
            first_name="Aoife", last_name="Byrne", dob=today - timedelta(days=3000)
        )
        for lesson in (cls.mon_early, cls.mon_late, cls.tue_early):
            LessonEnrollment.objects.create(
                lesson=lesson, swimling=cls.swimling, term=cls.term
            )

    @classmethod
    def _make_product(cls, day_of_week, start_time):
        return Product.objects.create(
            category=cls.category,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=time(start_time.hour + 1, start_time.minute),
            active=True,
        )

    def _print(self, **params):
        return self.client.get(reverse('reports:class_print'), params)

    def _printed_lessons(self, response):
        return [entry['product'] for entry in response.context['lesson_lists']]

    def test_day_and_time_prints_only_that_slot(self):
        response = self._print(term='current', day='0', time='17:00')
        self.assertEqual(self._printed_lessons(response), [self.mon_early])

    def test_day_without_time_prints_the_whole_day(self):
        response = self._print(term='current', day='0')
        self.assertEqual(self._printed_lessons(response), [self.mon_early, self.mon_late])

    def test_all_days_prints_the_whole_week_in_teaching_order(self):
        response = self._print(term='current', day='all')
        self.assertEqual(
            self._printed_lessons(response),
            [self.mon_early, self.mon_late, self.tue_early],
        )

    def test_all_days_can_still_be_narrowed_to_one_time(self):
        response = self._print(term='current', day='all', time='17:00')
        self.assertEqual(self._printed_lessons(response), [self.mon_early, self.tue_early])

    def test_inactive_lessons_are_left_off_a_day_print(self):
        self.mon_late.active = False
        self.mon_late.save()
        response = self._print(term='current', day='0')
        self.assertEqual(self._printed_lessons(response), [self.mon_early])

    def test_a_short_print_job_carries_no_warning(self):
        response = self._print(term='current', day='all')
        self.assertNotContains(response, 'Long print job')

    def test_a_long_print_job_warns_with_the_class_count(self):
        for hour in range(8, 20):
            self._make_product(2, time(hour, 0))
        response = self._print(term='current', day='2')
        self.assertContains(response, 'Long print job: 12 classes')
        self.assertContains(response, 'Print All (12 pages)')

    def test_a_specific_lesson_still_prints_a_single_sheet(self):
        response = self._print(term='current', day='0', lesson=str(self.mon_late.id))
        self.assertNotIn('lesson_lists', response.context)
        self.assertEqual(response.context['product'], self.mon_late)

    def test_the_sheets_carry_no_stray_template_comment_text(self):
        # A {# #} comment cannot span lines in Django, and the ones that did were
        # printing their own source onto the top of the attendance sheet.
        multi = self._print(term='current', day='0')
        self.assertNotContains(multi, 'One attendance sheet per class')
        self.assertNotContains(multi, '#}')

        single = self._print(term='current', day='0', lesson=str(self.mon_early.id))
        self.assertNotContains(single, 'Attendance sheet as specified by the pool')
        self.assertNotContains(single, '#}')


class FilterOptionTests(TestCase):
    """The day/time/lesson dropdowns have to understand the whole-week option."""

    @classmethod
    def setUpTestData(cls):
        program = Program.objects.create(name="Public Lessons")
        cls.category = Category.objects.create(
            name="Beginners 1", slug="beginners-1", program=program
        )
        cls.mon = Product.objects.create(
            category=cls.category, day_of_week=0,
            start_time=time(17, 0), end_time=time(17, 45), active=True,
        )
        cls.tue = Product.objects.create(
            category=cls.category, day_of_week=1,
            start_time=time(18, 30), end_time=time(19, 15), active=True,
        )

    def test_times_for_all_days_span_the_week(self):
        response = self.client.get(reverse('reports:update-times'), {'day': 'all'})
        self.assertEqual(response.context['times'], ['17:00', '18:30'])

    def test_lessons_for_all_days_span_the_week(self):
        response = self.client.get(reverse('reports:update-lessons'), {'day': 'all'})
        self.assertEqual(list(response.context['lessons']), [self.mon, self.tue])

    def test_lessons_for_a_day_without_a_time_list_that_day(self):
        response = self.client.get(reverse('reports:update-lessons'), {'day': '1'})
        self.assertEqual(list(response.context['lessons']), [self.tue])

    def test_day_options_offer_the_whole_week(self):
        response = self.client.get(reverse('reports:update-days'))
        self.assertContains(response, 'value="all"')
