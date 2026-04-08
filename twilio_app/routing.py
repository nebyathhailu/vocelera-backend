from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/projects/(?P<project_id>\d+)/messages/$",
        consumers.MessageConsumer.as_asgi(),
    ),
    re_path(
        r"ws/projects/(?P<project_id>\d+)/insights/$",
        consumers.InsightConsumer.as_asgi(),
    ),
]