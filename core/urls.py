from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sessions.models import Session
from custom_admins.lessonsadmin import lessons_admin_site
from custom_admins.usersadmin import users_admin_site
from custom_admins.swimsadmin import swims_admin_site
from custom_admins.schoolsadmin import schools_admin_site
from custom_admins.generaladmin import general_admin_site
from custom_admins.instructorsadmin import instructors_admin_site
from custom_admins.coupons_admin import coupons_admin_site


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    # Allauth
    path('accounts/', include('allauth.urls')),
    path('users/', include('users.urls', namespace='user')),
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
    # BOIPA
    path('boipa/', include(('boipa.urls', 'boipa'), namespace='boipa')),  # Note the namespace argument
    # Waiting List
    path('waiting-list/', include('waiting_list.urls')),
    path("dashboard/", include("swimling_dashboard.urls", namespace="swimling_dashboard")),
    path("mailchimp/", include("mailchimp.urls")),
]
# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]

# Add Admin Sites
urlpatterns += [
    path('lessonsadmin/', lessons_admin_site.urls),
    path('usersadmin/', users_admin_site.urls),
    path('swimsadmin/', swims_admin_site.urls),
    path('schoolsadmin/', schools_admin_site.urls),
    path('generaladmin/', general_admin_site.urls),
    path('instructorsadmin/', instructors_admin_site.urls),
    path("couponsadmin/", coupons_admin_site.urls),
    ]
# add auto reload
urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]


# Change Site Labels
admin.site.site_header = "TCSP Administration"
admin.site.site_title = "TCSP Administration site"
admin.site.index_title = "TCSP Administration"

# dashboard
urlpatterns += [
path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard"))
]

urlpatterns += [
path("chatbot/", include("chatbot.urls")),
path("instructors/", include("instructors.urls")),
]