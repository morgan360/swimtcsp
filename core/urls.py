from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
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
]
# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Change Site Labels
admin.site.site_header = "TCSP Administration"
admin.site.site_title = "TCSP Administration site"
admin.site.index_title = "TCSP Administration"
