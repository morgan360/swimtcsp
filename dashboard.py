"""
This file was generated with the customdashboard management command and
contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'swimtcsp.dashboard.CustomIndexDashboard'
"""

from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from grappelli.dashboard import modules, Dashboard
from grappelli.dashboard.utils import get_admin_site_name


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for www.
    """

    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        # MAIN ADMIN
        self.children.append(modules.ModelList(
            _('Customers & Swimmers'),
            column=1,
            collapsible=True,
            # title='Authentication',
            models=['django.contrib.auth.models.Group', 'users.models.User', 'users.models.Swimling'],
            # models=('django.contrib.*',),
            # exclude=('django.contrib.Sites',),
        ))
        self.children.append(modules.Group(
            _('Other Admin'),
            column=1,
            collapsible=True,
            children=[
                modules.ModelList(
                    _('AllAuth'),
                    column=1,
                    collapsible=True,
                    models=['django.contrib.sites.models.Site',],
                    # exclude=('django.contrib.*',),
                )

            ]

        ))

        # PUBLIC SWIMS
        self.children.append(modules.ModelList(
            _('Public Swims'),
            column=2,
            collapsible=True,
            models=['swims.models.PublicSwimProduct'],
        ))
        self.children.append(modules.ModelList(
            _('Public Swims Admin'),
            column=2,
            collapsible=True,
            css_classes=('collapse closed',),
            models=['PublicSwimCategory', 'swims.models.PriceVariant',],
        ))
        # LESSONS MANAGMENT
        self.children.append(modules.Group(
            _('Public Lessons'),
            column=2,
            collapsible=True,
            children = [
                modules.ModelList(
                    _('Lesson List'),
                    column=1,
                    collapsible=True,
                    models=('lessons.models.Product',),
                    exclude=('django.contrib.*',),
                ),
                modules.ModelList(
                    _('Lesson Admin'),
                    column=1,
                    collapsible=True,
                    models=['lessons.models.Program',  'lessons.models.Category','lessons.models.Group'],
                    # exclude=('users.models.User',),
                ),
                modules.ModelList(
                    _('Lesson Bookings'),
                    column=1,
                    collapsible=True,
                    models=['lessons_bookings.models.Term', 'lessons_bookings.models.LessonEnrollment',
                            'lessons_bookings.models.LessonAssignment', ],
                    # exclude=('users.models.User',),
                )
            ]
        ))
        # ORDERS MANAGEMENT
        self.children.append(modules.Group(
            _('Orders'),
            column=3,
            collapsible=True,
            children=[
                modules.ModelList(
                    _('Lesson Orders'),
                    column=1,
                    collapsible=False,
                    models=('lessons_orders.models.Order',),
                    exclude=('django.contrib.*',),
                ),
                modules.ModelList(
                    _('Swim Orders'),
                    column=1,
                    collapsible=True,
                    models=['swims_orders.models.Order',]
                    # exclude=('users.models.User',),
                )
           ]
        ))
