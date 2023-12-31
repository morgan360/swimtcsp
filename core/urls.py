from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sessions.models import Session
from timetable.admin import events_site
from custom_admins.lessonsadmin import lessons_admin_site
from custom_admins.usersadmin import users_admin_site
from custom_admins.swimsadmin import swims_admin_site

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
    path('lessons_payment/', include('lessons_payment.urls', namespace='lessons_payment')),
    path('', include('lessons_bookings.urls', namespace='lessons_bookings')),

    path('swims/',
         include('swims.urls', namespace='swims')),
    path('swims_cart/',
         include('swims_cart.urls', namespace='swims_cart')),
    path('swims_orders/',
         include('swims_orders.urls', namespace='swims_orders')),
    path('swims_payment/',
         include('swims_payment.urls', namespace='swims_payment')),
    path('timetable/', include('timetable.urls')),
    path('hijack/', include('hijack.urls')),
    path('reports/', include('reports.urls')),
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


# Change Site Labels
admin.site.site_header = "TCSP Administration"
admin.site.site_title = "TCSP Administration site"
admin.site.index_title = "TCSP Administration"
