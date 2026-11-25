from django.urls import re_path

from .views import SettingsView

urlpatterns = [
    re_path(
        r'^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/seatmap-pro/$',
        SettingsView.as_view(),
        name='settings',
    ),
]
