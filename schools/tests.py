from django.test import TestCase


class SchoolUrlTests(TestCase):
    def test_menu_school_dashboard_link_redirects_to_the_guardian_dashboard(self):
        # The "School Dashboard" menu link 500'd on 23 Nov 2026: the slug route took it.
        response = self.client.get("/schools/school_dashboard/")
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)

    def test_category_slug_route_does_not_crash(self):
        self.assertEqual(self.client.get("/schools/some-category/").status_code, 200)
