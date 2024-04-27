from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sessions.models import Session
from timetable.admin import events_site
from custom_admins.lessonsadmin import lessons_admin_site
from custom_admins.usersadmin import users_admin_site
from custom_admins.swimsadmin import swims_admin_site
from test_area import urls as test_area_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('events/', events_site.urls),
    # Allauth
    path('accounts/', include('allauth.urls')),
    path('users/', include('users.urls', namespace='user')),
    # Lessons
    path('lessons/',
         include('lessons.urls', namespace='lessons')),
    path('lessons_cart/',
         include('lessons_cart.urls', namespace='lessons_cart')),
    path('lessons_orders/',
         include('lessons_orders.urls', namespace='lessons_orders')),
    path('', include('lessons_bookings.urls', namespace='lessons_bookings')),
    # Swims
    path('swims/', include('swims.urls', namespace='swims')),
    path('swims_orders/',
         include('swims_orders.urls', namespace='swims_orders')),
    # Schools
    path('schools/', include('schools.urls', namespace='schools')),
    path('schools_cart/', include('schools_cart.urls', namespace='schools_cart')),
    path('schools_orders/',
         include('schools_orders.urls', namespace='schools_orders')),
    path('schools_payment/', include('schools_payment.urls', namespace='schools_payment')),
    path('', include('schools_bookings.urls', namespace='schools_bookings')),
    # Others
    path('timetable/', include('timetable.urls')),
    path('hijack/', include('hijack.urls')),
    path('reports/', include('reports.urls')),
    # BOIPA
    path('boipa/', include(('boipa.urls', 'boipa'), namespace='boipa')),  # Note the namespace argument
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
urlpatterns += [path('lessonsadmin/', lessons_admin_site.urls),
                path('usersadmin/', users_admin_site.urls),
                path('swimsadmin/', swims_admin_site.urls)
                ]
# Add Admin Sites
urlpatterns += [path('test_area/', include(test_area_urls))]
# add auto reload
urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]


# Change Site Labels
admin.site.site_header = "TCSP Administration"
admin.site.site_title = "TCSP Administration site"
admin.site.index_title = "TCSP Administration"
