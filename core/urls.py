from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sessions.models import Session
from custom_admins.panels import finance_site, operations_site, settings_site

# custom_admins/ is not an installed app, so Django's autodiscover never imports
# these modules. Importing them here for their side effects is what puts their
# models on the panels — without it the panels come up silently half empty.
import custom_admins.attendance_admin  # noqa: F401
import custom_admins.coupons_admin  # noqa: F401
import custom_admins.generaladmin  # noqa: F401
import custom_admins.instructorsadmin  # noqa: F401
import custom_admins.lessonsadmin  # noqa: F401
import custom_admins.schoolsadmin  # noqa: F401
import custom_admins.usersadmin  # noqa: F401
from users.views import CustomSignupView
from waiting_list.views import redirect_to_swimling_waiting_list
from django.views.generic import RedirectView, TemplateView
from django.http import HttpResponse
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    # Allauth
# ✅ Add these global routes
    path('accounts/password/reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password/reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Other apps
    path('accounts/signup/', CustomSignupView.as_view(), name='account_signup'),
    path('accounts/', include('allauth.urls')),
    # Use namespace 'users' to match templates and redirects
    path('users/', include('users.urls', namespace='users')),
    # Lessons
    path('lessons/',
         include('lessons.urls', namespace='lessons')),
    path('lessons_orders/',
         include('lessons_orders.urls', namespace='lessons_orders')),
    path('', include('lessons_bookings.urls', namespace='lessons_bookings')),
    # Swims
    path('swims/', include('swims.urls', namespace='swims')),
    path('swims_orders/',
         include('swims_orders.urls', namespace='swims_orders')),
    # Schools
    path('schools/', include('schools.urls', namespace='schools')),
    path('schools_orders/',
         include('schools_orders.urls', namespace='schools_orders')),
    path('', include('schools_bookings.urls', namespace='schools_bookings')),

   # Shopping
    path('shopping_cart/', include('shopping_cart.urls', namespace='shopping_cart')),

    # Others
    path('timetable/', include('timetable.urls')),
    path('hijack/', include('hijack.urls')),
    path('reports/', include('reports.urls')),
    path("finances/", include("finances.urls")),
    # BOIPA
    path('boipa/', include(('boipa.urls', 'boipa'), namespace='boipa')),  # Note the namespace argument
    # Waiting List
    path('waiting-list/', include('waiting_list.urls')),
    path("dashboard/", include("swimling_dashboard.urls", namespace="swimling_dashboard")),
    path("mailchimp/", include("mailchimp.urls")),
    # Coupons
    path("coupons/", include(("coupons.urls", "coupons"), namespace="coupons")),
]
# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
        # Dev-only preview routes for error templates (status will be 200)
        path("dev/404/", TemplateView.as_view(template_name="404.html"), name="dev-404"),
        path("dev/500/", TemplateView.as_view(template_name="500.html"), name="dev-500"),
        path("dev/403/", TemplateView.as_view(template_name="403.html"), name="dev-403"),
        path("dev/401/", TemplateView.as_view(template_name="401.html"), name="dev-401"),
        path("dev/503/", TemplateView.as_view(template_name="503.html"), name="dev-503"),
        # Dev-only endpoints that emit specific statuses to exercise middleware/handlers
        path("dev/status/401/", lambda r: HttpResponse("Unauthorized", status=401), name="dev-status-401"),
        path("dev/status/503/", lambda r: HttpResponse("Service Unavailable", status=503), name="dev-status-503"),
    ]

# The three admin panels. Stock admin.site stays at /admin/ for superusers.
urlpatterns += [
    path('operations/', operations_site.urls),
    path('finance/', finance_site.urls),
    path('settings-admin/', settings_site.urls),
]

# The nine panels these replaced. Staff have these bookmarked and they appear in
# old emails, so they redirect rather than 404. Safe to drop after a year or so
# (added September 2026).
_RETIRED_PANELS = {
    'lessonsadmin': '/operations/',
    'swimsadmin': '/operations/',
    'schoolsadmin': '/operations/',
    'instructorsadmin': '/operations/',
    'attendanceadmin': '/operations/',
    'generaladmin': '/settings-admin/',
    'usersadmin': '/settings-admin/',
    'couponsadmin': '/finance/',
    'finance-admin': '/finance/',
}
urlpatterns += [
    re_path(
        rf'^{old}/(?P<rest>.*)$',
        RedirectView.as_view(url=new + '%(rest)s', permanent=False, query_string=True),
    )
    for old, new in _RETIRED_PANELS.items()
]
if settings.DEBUG:
    # add auto reload (only in development)
    urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]


# Change Site Labels
admin.site.site_header = "TCSP Administration"
admin.site.site_title = "TCSP Administration site"
admin.site.index_title = "TCSP Administration"

# dashboard
urlpatterns += [
path("admin-dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard"))
]

urlpatterns += [
path("chatbot/", include("chatbot.urls")),
path("instructors/", include("instructors.urls")),
path("anseo/", include("anseo.urls")),
]
# Custom URL Shortcuts
urlpatterns += [
path('join-waitlist/', redirect_to_swimling_waiting_list, name='join_waitlist')
]


# Custom error handlers (used when DEBUG=False)
handler404 = 'core.error_handlers.custom_handler404'
handler500 = 'core.error_handlers.custom_handler500'
handler403 = 'core.error_handlers.custom_handler403'

