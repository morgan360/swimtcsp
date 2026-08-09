"""Tests for swimmer records.

Medical information is kept in its own field, separate from notes. The pool's
rule is that only medical information goes in front of a teacher at poolside; the
general notes box has years of unrelated content in it, and it is deliberately
left alone rather than migrated or cleared.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.models import Swimling

User = get_user_model()


class MedicalInfoTests(TestCase):
    def setUp(self):
        self.guardian = User.objects.create_user(
            email="parent@test.com", password="testpass123", first_name="Pat",
        )
        self.swimling = Swimling.objects.create(
            guardian=self.guardian, first_name="Aoife", last_name="Ruane",
            dob="2015-06-15",
            notes="Loves the slide. Dad collects on Tuesdays.",
            medical_info="Asthma - inhaler in bag",
        )

    def test_the_two_boxes_are_independent(self):
        self.swimling.refresh_from_db()
        self.assertEqual(self.swimling.medical_info, "Asthma - inhaler in bag")
        self.assertIn("Loves the slide", self.swimling.notes)

    def test_a_guardian_can_set_medical_info(self):
        self.client.force_login(self.guardian)

        response = self.client.post(
            reverse("swimling_dashboard:edit-swimling", args=[self.swimling.id]),
            {
                "first_name": "Aoife", "last_name": "Ruane", "dob": "2015-06-15",
                "sco_role_num": "", "medical_info": "Peanut allergy - epipen",
                "notes": "Loves the slide. Dad collects on Tuesdays.",
            },
        )
        self.assertIn(response.status_code, (200, 302))

        self.swimling.refresh_from_db()
        self.assertEqual(self.swimling.medical_info, "Peanut allergy - epipen")
        # The notes box must survive a medical edit untouched.
        self.assertIn("Loves the slide", self.swimling.notes)

    def test_a_guardian_only_sees_their_own_child(self):
        other = User.objects.create_user(
            email="other@test.com", password="x", first_name="O",
        )
        self.client.force_login(other)

        response = self.client.get(
            reverse("swimling_dashboard:edit-swimling", args=[self.swimling.id])
        )
        self.assertNotEqual(response.status_code, 200)
