"""Tests for FAQ retrieval, scoping and throttling.

No test here touches the OpenAI API: match_faq accepts an `embed_func`, so
vectors are supplied directly and scores are exact and predictable.
"""
from datetime import datetime, time

import pytz
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings

from chatbot.checks import check_faq_thresholds
from chatbot.helpers import faq as faq_helper
from chatbot.helpers import swim as swim_helper
from chatbot.helpers.faq_index import embedding_text, get_index, normalize
from chatbot.helpers.throttle import client_ip, is_rate_limited
from chatbot.models import FAQEntry
from swims.models import PublicSwimCategory, PublicSwimProduct


def unit(*components):
    """A vector on the unit sphere, padded to a small fixed dimension."""
    vector = list(components) + [0.0] * (4 - len(components))
    return vector


# Orthogonal axes: cosine similarity against each is simply the shared component.
HAT = unit(1.0, 0.0, 0.0, 0.0)
LEVELS = unit(0.0, 1.0, 0.0, 0.0)
PARKING = unit(0.0, 0.0, 1.0, 0.0)


@override_settings(
    FAQ_MATCH_THRESHOLD=0.65,
    FAQ_MIN_CONFIDENCE=0.45,
    FAQ_CONTEXT_MIN_SCORE=0.40,
)
class MatchFAQTests(TestCase):
    def setUp(self):
        cache.clear()
        FAQEntry.objects.create(
            question="Do I need to wear a swimming hat?",
            answer="<p>Yes, swimming hats are required.</p>",
            embedding=HAT,
            lessons_only=False,
        )
        FAQEntry.objects.create(
            question="How many levels for children are there?",
            answer="<p>5 widths levels and 3 lengths levels.</p>",
            embedding=LEVELS,
            lessons_only=True,
        )

    def match(self, message, vector, **kwargs):
        return faq_helper.match_faq(
            message, embed_func=lambda _: vector, **kwargs
        )

    def test_strong_similarity_answers_verbatim(self):
        result = self.match("hats?", HAT)
        self.assertEqual(result.tier, faq_helper.MATCH)
        self.assertIn("swimming hats are required", result.answer)
        self.assertAlmostEqual(result.score, 1.0, places=5)

    def test_middling_similarity_is_hedged(self):
        # cos = 0.55: past FAQ_MIN_CONFIDENCE but short of FAQ_MATCH_THRESHOLD.
        result = self.match("something about hats", unit(0.55, 0.0, 0.835))
        self.assertEqual(result.tier, faq_helper.HEDGED)
        self.assertTrue(result.answer.startswith(faq_helper.HEDGE_PREFIX))
        self.assertIn("swimming hats are required", result.answer)

    def test_weak_similarity_misses_but_still_returns_context(self):
        # cos = 0.42: below the hedge floor, above the context floor.
        result = self.match("where do I park?", unit(0.42, 0.0, 0.907))
        self.assertEqual(result.tier, faq_helper.MISS)
        self.assertIsNone(result.answer)
        self.assertEqual(len(result.context), 1)
        # Context carries plain text, not the stored markup.
        self.assertNotIn("<p>", result.context[0]["answer"])

    def test_unrelated_query_yields_no_context(self):
        result = self.match("where do I park?", PARKING)
        self.assertEqual(result.tier, faq_helper.MISS)
        self.assertEqual(result.context, [])

    def test_exact_question_needs_no_embedding(self):
        """A verbatim repeat should cost nothing at the API."""
        def explode(_):
            raise AssertionError("embed_func must not be called for an exact match")

        result = faq_helper.match_faq(
            "  do i need to wear a SWIMMING hat?  ", embed_func=explode
        )
        self.assertEqual(result.tier, faq_helper.MATCH)
        self.assertAlmostEqual(result.score, 1.0)

    def test_embedding_failure_degrades_to_miss(self):
        result = faq_helper.match_faq("anything", embed_func=lambda _: None)
        self.assertEqual(result.tier, faq_helper.MISS)


@override_settings(FAQ_MATCH_THRESHOLD=0.65, FAQ_MIN_CONFIDENCE=0.45)
class LessonsOnlyScopingTests(TestCase):
    """lessons_only entries belong to the lesson bot; the rest are shared.

    The old filter used exact equality on the flag, so the lesson bot saw only
    lessons_only rows — and with none tagged, it matched nothing at all.
    """

    def setUp(self):
        cache.clear()
        FAQEntry.objects.create(
            question="Do I need to wear a swimming hat?",
            answer="<p>Yes.</p>",
            embedding=HAT,
            lessons_only=False,
        )
        FAQEntry.objects.create(
            question="How many levels for children are there?",
            answer="<p>Eight.</p>",
            embedding=LEVELS,
            lessons_only=True,
        )

    def test_lesson_bot_sees_shared_entries(self):
        result = faq_helper.match_faq(
            "hats?", lessons_mode=True, embed_func=lambda _: HAT
        )
        self.assertEqual(result.tier, faq_helper.MATCH)
        self.assertIn("Yes.", result.answer)

    def test_lesson_bot_sees_lessons_only_entries(self):
        result = faq_helper.match_faq(
            "levels?", lessons_mode=True, embed_func=lambda _: LEVELS
        )
        self.assertEqual(result.tier, faq_helper.MATCH)
        self.assertIn("Eight.", result.answer)

    def test_swim_bot_cannot_see_lessons_only_entries(self):
        result = faq_helper.match_faq(
            "levels?", lessons_mode=False, embed_func=lambda _: LEVELS
        )
        self.assertEqual(result.tier, faq_helper.MISS)


class FAQIndexTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_saving_an_entry_rebuilds_the_index(self):
        self.assertEqual(len(get_index()), 0)

        entry = FAQEntry.objects.create(
            question="Do you open on Bank Holidays?",
            answer="<p>No.</p>",
            embedding=HAT,
        )
        self.assertEqual(len(get_index()), 1)

        entry.delete()
        self.assertEqual(len(get_index()), 0)

    def test_entries_without_embeddings_are_excluded(self):
        FAQEntry.objects.create(question="Unembedded", answer="<p>x</p>")
        self.assertEqual(len(get_index()), 0)

    def test_mismatched_vector_dimensions_are_dropped(self):
        """A partial re-embed with a different model must not break matching."""
        FAQEntry.objects.create(question="A", answer="<p>a</p>", embedding=HAT)
        FAQEntry.objects.create(question="B", answer="<p>b</p>", embedding=[1.0] * 9)

        index = get_index()
        self.assertEqual(len(index), 1)
        self.assertEqual(index.matrix.shape, (1, 4))

    def test_embedding_text_is_the_question_alone(self):
        """Answers are deliberately excluded — see embedding_text's docstring.

        Including them turned the one FAQ with a long answer into a hub that
        came top for unrelated queries.
        """
        text = embedding_text("How deep is the pool?", "<p>Six feet six.</p>")
        self.assertEqual(text, "How deep is the pool?")

    def test_normalize_collapses_case_and_whitespace(self):
        self.assertEqual(normalize("  Do I   Need\na Hat? "), "do i need a hat?")


class SkillSummaryTests(TestCase):
    """The summary must actually build.

    It traversed a `lesson` field CategorySkill does not have, so it raised
    FieldError on every call — and the caller caught the exception, so the
    lesson bot silently prompted without the skill tree for as long as the
    feature had existed.
    """

    def test_builds_without_error(self):
        from chatbot.utils import _build_skill_structure_summary

        summary = _build_skill_structure_summary()
        self.assertIn("Skill Structure by Core Aquatic Skill", summary)

    def test_only_progression_questions_get_the_skill_tree(self):
        from chatbot.views import _is_progression_question

        for message in ["why hasn't my child moved up a level",
                        "when will she be ready to progress",
                        "what skills are assessed"]:
            self.assertTrue(_is_progression_question(message), message)

        for message in ["how do i pay", "where do i park", "do i need a hat"]:
            self.assertFalse(_is_progression_question(message), message)


class BookingPhaseTests(TestCase):
    """"How do I rebook?" needs today's booking stage, not a raw term date."""

    def test_no_current_term_yields_empty_string(self):
        from chatbot.helpers.lesson import format_booking_phase

        # No Term fixtures, so there is no phase — the prompt block is simply
        # omitted rather than carrying "None".
        self.assertEqual(format_booking_phase(), "")

    def test_phase_summary_is_rendered_for_the_prompt(self):
        from unittest.mock import patch

        from chatbot.helpers import lesson

        summary = {
            "current": {"id": "BK", "label": "Current Term Booking", "until": "10 Sep 2026"},
            "next": {"id": "RB", "label": "Rebooking", "starts": "17 Aug 2026"},
        }
        with patch.object(lesson, "get_term_info", return_value={"phase_summary": summary}):
            rendered = lesson.format_booking_phase()

        self.assertIn("Current Term Booking", rendered)
        self.assertIn("10 Sep 2026", rendered)
        self.assertIn("Rebooking", rendered)
        self.assertIn("17 Aug 2026", rendered)

    def test_failure_degrades_to_empty_rather_than_breaking_the_reply(self):
        from unittest.mock import patch

        from chatbot.helpers import lesson

        with patch.object(lesson, "get_term_info", side_effect=RuntimeError("boom")):
            self.assertEqual(lesson.format_booking_phase(), "")


class ThresholdCheckTests(TestCase):
    """The thresholds are only meaningful in a strict order.

    Production was found with FAQ_MATCH_THRESHOLD=0.40 against a hedge floor of
    0.58, which makes the hedged tier unreachable.
    """

    def ids(self):
        return {m.id for m in check_faq_thresholds(None)}

    @override_settings(
        FAQ_MATCH_THRESHOLD=0.68, FAQ_MIN_CONFIDENCE=0.58, FAQ_CONTEXT_MIN_SCORE=0.50
    )
    def test_calibrated_defaults_pass(self):
        self.assertEqual(self.ids(), set())

    @override_settings(
        FAQ_MATCH_THRESHOLD=0.40, FAQ_MIN_CONFIDENCE=0.58, FAQ_CONTEXT_MIN_SCORE=0.50
    )
    def test_match_below_hedge_is_an_error(self):
        self.assertIn("chatbot.E003", self.ids())

    @override_settings(
        FAQ_MATCH_THRESHOLD=0.68, FAQ_MIN_CONFIDENCE=0.58, FAQ_CONTEXT_MIN_SCORE=0.60
    )
    def test_context_floor_above_hedge_is_an_error(self):
        self.assertIn("chatbot.E004", self.ids())

    @override_settings(
        FAQ_MATCH_THRESHOLD=1.5, FAQ_MIN_CONFIDENCE=0.58, FAQ_CONTEXT_MIN_SCORE=0.50
    )
    def test_out_of_range_is_an_error(self):
        self.assertIn("chatbot.E002", self.ids())

    @override_settings(
        FAQ_MATCH_THRESHOLD=0.50, FAQ_MIN_CONFIDENCE=0.45, FAQ_CONTEXT_MIN_SCORE=0.40
    )
    def test_low_but_ordered_thresholds_only_warn(self):
        ids = self.ids()
        self.assertIn("chatbot.W001", ids)
        self.assertFalse({i for i in ids if i.startswith("chatbot.E")})


@override_settings(CHATBOT_MAX_MESSAGES_PER_HOUR=3, CHATBOT_MAX_MESSAGES_PER_HOUR_PER_IP=8)
class ThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def _request(self, session_key="abc123", ip="203.0.113.10", **headers):
        request = self.factory.post("/chatbot/api/chat/public-swim/", **headers)
        request.META["HTTP_X_REAL_IP"] = ip
        request.session = type("S", (), {"session_key": session_key})()
        return request

    def test_allows_up_to_the_limit_then_blocks(self):
        request = self._request()
        for _ in range(3):
            self.assertFalse(is_rate_limited(request))
        self.assertTrue(is_rate_limited(request))

    def test_sessions_are_counted_separately(self):
        first = self._request("session-one")
        for _ in range(3):
            is_rate_limited(first)
        self.assertTrue(is_rate_limited(first))
        self.assertFalse(is_rate_limited(self._request("session-two", ip="203.0.113.99")))

    def test_rotating_sessions_from_one_ip_is_still_capped(self):
        """The bypass this exists to close.

        A caller that discards cookies gets a fresh session — and so a fresh,
        empty session bucket — on every request, because the view mints one for
        anybody arriving without it. Only the IP bucket stops them.
        """
        for i in range(8):
            self.assertFalse(is_rate_limited(self._request(f"rotating-{i}")))
        self.assertTrue(is_rate_limited(self._request("rotating-fresh")))

    def test_per_ip_bucket_does_not_punish_other_addresses(self):
        for i in range(8):
            is_rate_limited(self._request(f"rotating-{i}"))
        self.assertTrue(is_rate_limited(self._request("rotating-fresh")))
        self.assertFalse(is_rate_limited(self._request("elsewhere", ip="198.51.100.7")))

    @override_settings(CHATBOT_MAX_MESSAGES_PER_HOUR=0, CHATBOT_MAX_MESSAGES_PER_HOUR_PER_IP=0)
    def test_zero_disables_throttling(self):
        request = self._request()
        for _ in range(10):
            self.assertFalse(is_rate_limited(request))

    def test_session_bucket_still_applies_within_one_ip(self):
        """Both buckets are live: the tighter session one trips first."""
        request = self._request("chatty")
        for _ in range(3):
            self.assertFalse(is_rate_limited(request))
        self.assertTrue(is_rate_limited(request))


class ClientIPTests(TestCase):
    """Which header the throttle trusts, which is the whole basis of the IP bucket."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_prefers_the_configured_proxy_header(self):
        request = self.factory.post("/", HTTP_X_REAL_IP="203.0.113.10")
        # RequestFactory sets REMOTE_ADDR to 127.0.0.1, standing in for
        # PythonAnywhere's load balancer address.
        self.assertEqual(client_ip(request), "203.0.113.10")

    def test_ignores_client_supplied_forwarded_for(self):
        """X-Forwarded-For is attacker-controlled on PythonAnywhere.

        Honouring it would reopen the bypass: a caller could put a different
        address in the header on every request and never fill a bucket.
        """
        request = self.factory.post(
            "/",
            HTTP_X_REAL_IP="203.0.113.10",
            HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8",
        )
        self.assertEqual(client_ip(request), "203.0.113.10")

    def test_forwarded_for_alone_is_not_trusted(self):
        request = self.factory.post("/", HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.assertEqual(client_ip(request), "127.0.0.1")

    @override_settings(CHATBOT_CLIENT_IP_HEADER="")
    def test_falls_back_to_remote_addr_with_no_proxy(self):
        request = self.factory.post("/", HTTP_X_REAL_IP="203.0.113.10")
        self.assertEqual(client_ip(request), "127.0.0.1")


class NextSwimOrderingTests(TestCase):
    """get_available_swims sorted on the raw day number, so Sunday came last
    whatever day it was. On a Saturday evening the list therefore began at Monday
    and the 15-session cap dropped Sunday entirely, so the bot named a session
    days after the one that was genuinely next."""

    DUBLIN = pytz.timezone("Europe/Dublin")

    def setUp(self):
        self.public = PublicSwimCategory.objects.create(
            name="Public Swim", slug="public-swim", description="Open swim",
        )
        self.lanes = PublicSwimCategory.objects.create(
            name="Sunday Lanes", slug="sunday-lanes", description="Lanes",
        )

    def _session(self, category, day, start, end):
        return PublicSwimProduct.objects.create(
            category=category, day_of_week=day,
            start_time=start, end_time=end, num_places=30, available=True,
        )

    def _at(self, year, month, day, hour, minute):
        return self.DUBLIN.localize(datetime(year, month, day, hour, minute))

    def _first_at(self, moment):
        """The head of the list the bot is handed, at a given moment."""
        from unittest.mock import patch
        with patch.object(swim_helper.timezone, "now", return_value=moment):
            swims = swim_helper.get_available_swims()
        return swims[0] if swims else None

    def _build_week(self):
        # Saturday 8 Aug 2026 is a Saturday; day_of_week is 0=Monday.
        self._session(self.public, 5, time(13, 15), time(14, 0))   # Sat
        self._session(self.public, 5, time(16, 0), time(17, 0))    # Sat
        self._session(self.lanes, 6, time(12, 50), time(13, 50))   # Sun
        self._session(self.public, 6, time(14, 0), time(14, 55))   # Sun
        self._session(self.public, 0, time(12, 0), time(13, 0))    # Mon

    def test_saturday_evening_rolls_over_to_sunday_not_monday(self):
        self._build_week()
        first = self._first_at(self._at(2026, 8, 8, 20, 34))

        self.assertEqual(first.get_day_of_week_display(), "Sunday")
        self.assertEqual(first.start_time, time(12, 50))

    def test_todays_remaining_sessions_come_first(self):
        self._build_week()
        first = self._first_at(self._at(2026, 8, 8, 12, 0))

        self.assertEqual(first.get_day_of_week_display(), "Saturday")
        self.assertEqual(first.start_time, time(13, 15))

    def test_a_session_already_finished_today_is_dropped(self):
        self._build_week()
        # 14:30 on the Saturday: the 13:15 has ended, the 16:00 has not.
        first = self._first_at(self._at(2026, 8, 8, 14, 30))

        self.assertEqual(first.get_day_of_week_display(), "Saturday")
        self.assertEqual(first.start_time, time(16, 0))

    def test_sunday_night_rolls_over_to_monday(self):
        self._build_week()
        first = self._first_at(self._at(2026, 8, 9, 23, 0))

        self.assertEqual(first.get_day_of_week_display(), "Monday")

    def test_every_weekday_starts_no_further_away_than_any_other_session(self):
        """The head of the list must be the soonest session, whatever day it is —
        the property the raw-day-number sort broke from Tuesday to Saturday."""
        self._build_week()
        for offset in range(7):
            moment = self._at(2026, 8, 8 + offset, 6, 0)
            with self.subTest(day=moment.strftime("%A")):
                from unittest.mock import patch
                with patch.object(swim_helper.timezone, "now", return_value=moment):
                    swims = swim_helper.get_available_swims()
                weekday = moment.date().weekday()
                distances = [(s.day_of_week - weekday) % 7 for s in swims]
                self.assertEqual(distances, sorted(distances))
                self.assertEqual(distances[0], min(distances))
